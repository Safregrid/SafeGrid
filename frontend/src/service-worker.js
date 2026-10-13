/**
 * SafeGrid service worker (offline support).
 *
 * Person 4 implements this file.
 *
 * Strategy (see docs/OFFLINE.md):
 * - App shell: precache at install, serve cache-first with background refresh.
 * - /api/risk-zones: network-first. On a successful live response the body is
 *   stored in IndexedDB. When the network fails, the last known body is served
 *   with is_live: false so the UI can label it as cached data.
 * - /api/hazards: network-first, same as risk-zones. Cached payloads are served
 *   with is_live: false and every hazard stamped is_live: false + cached_at.
 */

import {
  saveRiskZones,
  getLastKnownRiskZones,
  getDataAge,
  saveHazards,
  getLastKnownHazards,
  getHazardsAge,
} from "./offline/storage.js";
import {
  isRiskZonesRequest,
  markAsCached,
  isHazardsRequest,
  markHazardsCached,
} from "./offline/policy.js";

const SW_VERSION = "offline-v4";
const SHELL_CACHE = "safegrid-shell-v4";
const RUNTIME_CACHE = "safegrid-runtime-v4";

const MANIFEST = self.__WB_MANIFEST || [];
const PRECACHE_URLS = MANIFEST.map((entry) =>
  typeof entry === "string" ? entry : entry && entry.url
).filter(Boolean);

const JSON_HEADERS = { "Content-Type": "application/json" };

self.addEventListener("install", (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(SHELL_CACHE);
      await cache.addAll(PRECACHE_URLS);
      await self.skipWaiting();
    })()
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keep = new Set([SHELL_CACHE, RUNTIME_CACHE]);
      const names = await caches.keys();
      await Promise.all(
        names.filter((name) => !keep.has(name)).map((name) => caches.delete(name))
      );
      await self.clients.claim();
      console.log(`SafeGrid service worker active: ${SW_VERSION}`);
    })()
  );
});

async function handleRiskZones(request) {
  try {
    const response = await fetch(request);
    if (response && response.ok) {
      response
        .clone()
        .json()
        .then((body) => saveRiskZones(body, new Date(), true))
        .catch(() => {});
    }
    return response;
  } catch {
    const [cached, age] = await Promise.all([
      getLastKnownRiskZones(),
      getDataAge(),
    ]);
    if (cached) {
      const cachedAt = age.timestamp ? age.timestamp.toISOString() : null;
      return new Response(JSON.stringify(markAsCached(cached, cachedAt)), {
        status: 200,
        headers: { ...JSON_HEADERS, "X-SafeGrid-Cache": "hit" },
      });
    }
    return new Response(JSON.stringify({ error: "offline_no_cache" }), {
      status: 503,
      headers: JSON_HEADERS,
    });
  }
}

async function handleHazards(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      try {
        const payload = await response.clone().json();
        await saveHazards(payload, new Date(), true);
      } catch {
        // Non-JSON or unreadable body: keep the live response, cache nothing.
      }
    }
    return response;
  } catch {
    const [payload, age] = await Promise.all([
      getLastKnownHazards(),
      getHazardsAge(),
    ]);
    if (payload) {
      const cachedAt = age.timestamp ? age.timestamp.toISOString() : null;
      return new Response(JSON.stringify(markHazardsCached(payload, cachedAt)), {
        status: 200,
        headers: {
          "Content-Type": "application/json",
          "X-SafeGrid-Cache": "hazards",
        },
      });
    }
    return new Response(JSON.stringify({ is_live: false, hazards: [] }), {
      status: 503,
      headers: { "Content-Type": "application/json" },
    });
  }
}

async function handleShell(request) {
  const cached =
    (await caches.match(request, { ignoreVary: true })) ||
    (await caches.match(request, { ignoreSearch: true, ignoreVary: true }));

  const network = fetch(request)
    .then((response) => {
      if (response && response.ok) {
        caches
          .open(RUNTIME_CACHE)
          .then((cache) => cache.put(request, response.clone()));
      }
      return response;
    })
    .catch(() => null);

  if (cached) {
    return cached;
  }

  const response = await network;
  if (response) {
    return response;
  }

  if (request.mode === "navigate") {
    const shell = await caches.open(SHELL_CACHE);
    const index = (await shell.match("/index.html")) || (await shell.match("/"));
    if (index) {
      return index;
    }
  }

  return new Response("Offline", { status: 503 });
}

self.addEventListener("fetch", (event) => {
  const { request } = event;

  if (isRiskZonesRequest(request.url, request.method)) {
    event.respondWith(handleRiskZones(request));
    return;
  }

  if (isHazardsRequest(request.url, request.method)) {
    event.respondWith(handleHazards(request));
    return;
  }

  if (request.method !== "GET") {
    return;
  }

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) {
    return;
  }

  event.respondWith(handleShell(request));
});
