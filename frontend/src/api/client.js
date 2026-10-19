/**
 * SafeGrid backend API client.
 * Person 3 owns this file.
 * Person 4's Service Worker will intercept these fetch calls for caching.
 *
 * All API calls go through this module — do not inline fetch() calls
 * in UI components.
 */

const BASE_URL = "/api";

/**
 * Fetches active hazards from the backend.
 * Contract: returns { is_live: boolean, hazards: Hazard[] }
 * Throws on network failure without falling back to local mocks.
 */
export async function fetchHazards() {
  const response = await fetch(`${BASE_URL}/hazards`);
  if (!response.ok) {
    throw new Error(`Failed to fetch hazards: ${response.status}`);
  }
  const data = await response.json();
  return {
    is_live: Boolean(data?.is_live),
    hazards: Array.isArray(data?.hazards) ? data.hazards : []
  };
}

/**
 * Fetches GeoJSON risk zones from the backend.
 * Returns GeoJSON FeatureCollection.
 * Throws on failure (e.g. 404 stub) without fabricating data.
 */
export async function fetchRiskZones() {
  const response = await fetch(`${BASE_URL}/risk-zones`);
  if (!response.ok) {
    throw new Error(`Failed to fetch risk zones: ${response.status}`);
  }
  return await response.json();
}

/**
 * Fetches risk at a single coordinate from the regional grid.
 * Contract: GET /api/risk?lat=&lon= -> { in_coverage, reason, risk_level, ... }
 * Throws on failure without fabricating a zone.
 */
export async function fetchRiskAtPoint(lat, lon) {
  const response = await fetch(`${BASE_URL}/risk?lat=${lat}&lon=${lon}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch risk at point: ${response.status}`);
  }
  return await response.json();
}
