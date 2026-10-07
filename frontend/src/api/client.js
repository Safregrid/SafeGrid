/**
 * SafeGrid backend API client.
 *
 * Person 3 implements this module.
 * Person 4's Service Worker will intercept these fetch calls for caching.
 *
 * All API calls go through this module — do not inline fetch() calls
 * in UI components.
 *
 * Base URL: resolved at runtime — /api (proxied to backend in dev,
 * direct URL in production — update when hosting is decided).
 */

const BASE_URL = "/api";

// TODO (Person 3): implement fetchHazards() -> Promise<Hazard[]>
// TODO (Person 3): implement fetchRiskZones() -> Promise<GeoJSON.FeatureCollection>
//
// Example:
//   export async function fetchRiskZones() {
//     const response = await fetch(`${BASE_URL}/risk-zones`);
//     if (!response.ok) {
//       throw new Error(`Failed to fetch risk zones: ${response.status}`);
//     }
//     return response.json();
//   }
