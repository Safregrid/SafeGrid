/**
 * SafeGrid backend API client.
 * Person 3 owns this file.
 * Person 4's Service Worker will intercept these fetch calls for caching.
 */

const BASE_URL = "/api";

/**
 * Fetches active hazards from the backend.
 * Unwraps data if Person 1 returns an envelope object {"hazards": [...]}.
 */
export async function fetchHazards() {
  const response = await fetch(`${BASE_URL}/hazards`);
  if (!response.ok) {
    throw new Error(`Failed to fetch hazards: ${response.status}`);
  }
  const data = await response.json();
  // Envelope check: Handles both {"hazards": [...]} and bare [...]
  if (data && Array.isArray(data.hazards)) {
    return data.hazards;
  }
  return Array.isArray(data) ? data : [];
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
