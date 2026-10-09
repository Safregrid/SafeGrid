/**
 * SafeGrid backend API client.
 * Person 3 owns this file.
 * Person 4's Service Worker will intercept these fetch calls for caching.
 */

const BASE_URL = "/api";

/**
 * Fetches active hazards from the backend.
 * Throws on HTTP/Network error so Service Worker handles offline fallback.
 */
export async function fetchHazards() {
  const response = await fetch(`${BASE_URL}/hazards`);
  if (!response.ok) {
    throw new Error(`Failed to fetch hazards: ${response.status}`);
  }
  return await response.json();
}

/**
 * Fetches GeoJSON risk zones from the backend.
 */
export async function fetchRiskZones() {
  const response = await fetch(`${BASE_URL}/risk-zones`);
  if (!response.ok) {
    throw new Error(`Failed to fetch risk zones: ${response.status}`);
  }
  return await response.json();
}
