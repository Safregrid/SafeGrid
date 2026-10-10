/**
 * Pure decision helpers for offline behaviour.
 *
 * Person 4 implements this module. Kept free of browser APIs so the rules can
 * be tested without a running service worker.
 */

export const RISK_ZONES_PATH = "/api/risk-zones";

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

export function isStale(cachedAt, now, maxAgeMs) {
  const cached = new Date(cachedAt).getTime();
  if (Number.isNaN(cached)) {
    return true;
  }
  return now.getTime() - cached > maxAgeMs;
}
