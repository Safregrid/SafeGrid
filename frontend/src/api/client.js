/**
 * SafeGrid backend API client.
 *
 * Person 3 implements this module.
 * Person 4's Service Worker will intercept these fetch calls for caching.
 *
 * All API calls go through this module — do not inline fetch() calls
 * in UI components.
 *
 * Base URL: resolved at runtime — /api
 */

const BASE_URL = "/api";
const CACHE_KEY_HAZARDS = "safegrid_cached_hazards";
const CACHE_KEY_RISK_ZONES = "safegrid_cached_risk_zones";

/**
 * Fetches hazard data from the backend.
 * Caches fresh data to localStorage and falls back gracefully when offline.
 */
export async function fetchHazards() {
  try {
    const response = await fetch(`${BASE_URL}/hazards`);
    if (!response.ok) {
      throw new Error(`Failed to fetch hazards: ${response.status}`);
    }
    const hazards = await response.json();

    try {
      localStorage.setItem(CACHE_KEY_HAZARDS, JSON.stringify(hazards));
    } catch (e) {
      console.warn("Unable to save hazards to local cache:", e);
    }

    return hazards;
  } catch (error) {
    console.warn("Network/Backend offline. Loading local offline hazard cache:", error);

    const cachedData = localStorage.getItem(CACHE_KEY_HAZARDS);
    if (cachedData) {
      const parsed = JSON.parse(cachedData);
      return parsed.map((item) => ({ ...item, is_live: false }));
    }

    return [
      {
        id: "usgs_offline_1",
        title: "M 5.2 Earthquake (Offline Cache)",
        hazard_type: "EARTHQUAKE",
        risk_level: "HIGH",
        latitude: 12.9716,
        longitude: 77.5946,
        severity_value: 5.2,
        is_live: false,
      },
      {
        id: "meteo_offline_2",
        title: "High Wind Warning (Offline Cache)",
        hazard_type: "HIGH_WIND",
        risk_level: "MODERATE",
        latitude: 13.0827,
        longitude: 80.2707,
        severity_value: 58.0,
        is_live: false,
      },
    ];
  }
}

/**
 * Fetches GeoJSON risk zones from the backend.
 */
export async function fetchRiskZones() {
  try {
    const response = await fetch(`${BASE_URL}/risk-zones`);
    if (!response.ok) {
      throw new Error(`Failed to fetch risk zones: ${response.status}`);
    }
    const geojson = await response.json();

    try {
      localStorage.setItem(CACHE_KEY_RISK_ZONES, JSON.stringify(geojson));
    } catch (e) {
      console.warn("Unable to save risk zones to local cache:", e);
    }

    return geojson;
  } catch (error) {
    console.warn("Network/Backend offline. Loading local offline risk zones cache:", error);

    const cachedZones = localStorage.getItem(CACHE_KEY_RISK_ZONES);
    if (cachedZones) {
      return JSON.parse(cachedZones);
    }

    return {
      type: "FeatureCollection",
      features: [],
    };
  }
}

/**
 * Fetches emergency shelter locations.
 */
export async function fetchShelters() {
  try {
    const response = await fetch(`${BASE_URL}/shelters`);
    if (!response.ok) {
      throw new Error(`Failed to fetch shelters: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.warn("Backend server unavailable. Returning fallback shelters:", error);
    return [];
  }
}
