/**
 * Pure decision helpers for offline behaviour.
 *
 * Person 4 implements this module. Kept free of browser APIs so the rules can
 * be tested without a running service worker.
 */

export const RISK_ZONES_PATH = "/api/risk-zones";
export const HAZARDS_PATH = "/api/hazards";
// Point lookup into the regional risk grid: GET /api/risk?lat=&lon=
// (Person 1's endpoint; see docs/RISK_MODEL.md § 4.1 and docs/OFFLINE.md).
export const RISK_POINT_PATH = "/api/risk";

// Default age after which cached data is considered stale (see docs/OFFLINE.md).
// 3 hours matches the normal ingestion cadence; tighten it when an active
// hazard exists (adaptive cadence) so the UI flags older data sooner.
export const STALE_AFTER_MS = 3 * 60 * 60 * 1000;

// A grid cell is refreshed on the same 3-hour cadence as the rest of the offline
// layer, so the same default applies (kept separate so it can diverge later).
export const GRID_POINT_STALE_AFTER_MS = 3 * 60 * 60 * 1000;

export function isRiskZonesRequest(url, method = "GET") {
  if (String(method).toUpperCase() !== "GET") {
    return false;
  }
  try {
    const parsed = new URL(url, "http://localhost");
    return parsed.pathname === RISK_ZONES_PATH;
  } catch {
    return false;
  }
}

export function markAsCached(geojson, cachedAt) {
  if (geojson === null || typeof geojson !== "object" || Array.isArray(geojson)) {
    return geojson;
  }
  return { ...geojson, is_live: false, cached_at: cachedAt ?? null };
}

export function isHazardsRequest(url, method = "GET") {
  if (String(method).toUpperCase() !== "GET") {
    return false;
  }
  try {
    const parsed = new URL(url, "http://localhost");
    return parsed.pathname === HAZARDS_PATH;
  } catch {
    return false;
  }
}

export function markHazardsCached(payload, cachedAt) {
  if (payload === null || typeof payload !== "object" || Array.isArray(payload)) {
    return payload;
  }
  const hazards = Array.isArray(payload.hazards)
    ? payload.hazards.map((hazard) =>
        hazard !== null && typeof hazard === "object" && !Array.isArray(hazard)
          ? { ...hazard, is_live: false, cached_at: cachedAt ?? null }
          : hazard
      )
    : [];
  return { ...payload, is_live: false, cached_at: cachedAt ?? null, hazards };
}

export function isStale(cachedAt, now, maxAgeMs) {
  const cached = new Date(cachedAt).getTime();
  if (Number.isNaN(cached)) {
    return true;
  }
  return now.getTime() - cached > maxAgeMs;
}

export function isRiskPointRequest(url, method = "GET") {
  if (String(method).toUpperCase() !== "GET") {
    return false;
  }
  try {
    const parsed = new URL(url, "http://localhost");
    return parsed.pathname === RISK_POINT_PATH;
  } catch {
    return false;
  }
}

export function markPointRiskCached(payload, cachedAt) {
  if (payload === null || typeof payload !== "object" || Array.isArray(payload)) {
    return payload;
  }
  return { ...payload, is_live: false, cached_at: cachedAt ?? null };
}
