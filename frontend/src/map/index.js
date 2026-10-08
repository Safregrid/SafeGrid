/**
 * SafeGrid Map Module
 * Person 3 owns this file.
 *
 * Responsibilities:
 * - Create and configure the MapLibre map instance
 * - Add GeoJSON layers for risk zones (HIGH / MODERATE / LOW)
 * - Apply 🔴🟡🟢 color styling to features based on risk_level property
 * - Handle map events (click to show hazard detail)
 */

import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

// Free dark vector map tile style
const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';
const RISK_SOURCE_ID = 'risk-zones';

// Standardized color conventions
const COLOR_HIGH = '#ef4444';     // Red
const COLOR_MODERATE = '#f59e0b'; // Amber
const COLOR_LOW = '#22c55e';      // Green

/**
 * Initializes the MapLibre GL map instance.
 */
export function initMap(containerId = 'map') {
  const map = new maplibregl.Map({
    container: containerId,
    style: MAP_STYLE,
    center: [77.5946, 12.9716], // Default Bengaluru [lng, lat]
    zoom: 5,
  });

  map.addControl(new maplibregl.NavigationControl(), 'top-right');
  return map;
}

/**
 * Adds GeoJSON risk zone layers (fill & outline) to the map.
 */
export function addRiskZoneLayer(map, geojson) {
  if (!map.getSource(RISK_SOURCE_ID)) {
    map.addSource(RISK_SOURCE_ID, {
      type: 'geojson',
      data: geojson || { type: 'FeatureCollection', features: [] }
    });

    // Fill Layer for Risk Polygons / Buffer Zones
    map.addLayer({
      id: 'risk-zones-fill',
      type: 'fill',
      source: RISK_SOURCE_ID,
      paint: {
        'fill-color': [
          'match',
          ['get', 'risk_level'],
          'HIGH', COLOR_HIGH,
          'RED', COLOR_HIGH,
          'MODERATE', COLOR_MODERATE,
          'YELLOW', COLOR_MODERATE,
          'LOW', COLOR_LOW,
          'GREEN', COLOR_LOW,
          '#6b7280' // Default Gray
        ],
        'fill-opacity': 0.35
      }
    });

    // Outline Layer for Risk Zones
    map.addLayer({
      id: 'risk-zones-line',
      type: 'line',
      source: RISK_SOURCE_ID,
      paint: {
        'line-color': [
          'match',
          ['get', 'risk_level'],
          'HIGH', COLOR_HIGH,
          'RED', COLOR_HIGH,
          'MODERATE', COLOR_MODERATE,
          'YELLOW', COLOR_MODERATE,
          'LOW', COLOR_LOW,
          'GREEN', COLOR_LOW,
          '#6b7280'
        ],
        'line-width': 2
      }
    });
  }
}

/**
 * Updates existing GeoJSON risk zones source with new data.
 */
export function updateRiskZones(map, geojson) {
  const source = map.getSource(RISK_SOURCE_ID);
  if (source) {
    source.setData(geojson || { type: 'FeatureCollection', features: [] });
  } else {
    addRiskZoneLayer(map, geojson);
  }
}

/**
 * Renders color-coded hazard point markers on the map.
 */
export function renderHazardMarkers(map, hazards, onSelectHazard) {
  const existing = document.querySelectorAll('.hazard-marker');
  existing.forEach((el) => el.remove());

  (hazards ?? []).forEach((hazard) => {
    const el = document.createElement('div');
    const risk = (hazard?.risk_level ?? 'GREEN').toUpperCase();
    
    let markerColor = COLOR_LOW;
    if (risk === 'HIGH' || risk === 'RED') markerColor = COLOR_HIGH;
    if (risk === 'MODERATE' || risk === 'YELLOW') markerColor = COLOR_MODERATE;

    el.className = 'hazard-marker';
    el.style.cssText = `
      width: 20px;
      height: 20px;
      border-radius: 50%;
      background-color: ${markerColor};
      border: 2px solid #ffffff;
      cursor: pointer;
      box-shadow: 0 0 8px rgba(0,0,0,0.5);
    `;

    const isLive = hazard?.is_live ?? true;
    const recordedAt = hazard?.recorded_at ? new Date(hazard.recorded_at).toLocaleTimeString() : 'Recently';
    const statusBadge = isLive
      ? '<span style="color: #22c55e; font-weight: bold; font-size: 11px;">● LIVE</span>'
      : `<span style="color: #9ca3af; font-weight: bold; font-size: 11px;">🕒 CACHED (${recordedAt})</span>`;

    const title = hazard?.title ?? 'Unknown Hazard';
    const severity = hazard?.severity_value ?? 'N/A';

    const popupHTML = `
      <div style="color: #111827; font-family: sans-serif; padding: 4px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; gap: 8px;">
          <h4 style="margin: 0; font-size: 14px;">${title}</h4>
          ${statusBadge}
        </div>
        <p style="margin: 2px 0; font-size: 12px;"><strong>Severity:</strong> ${severity}</p>
        <p style="margin: 2px 0; font-size: 12px;"><strong>Risk Level:</strong> <span style="color: ${markerColor}; font-weight: bold;">${risk}</span></p>
      </div>
    `;

    const popup = new maplibregl.Popup({ offset: 25 }).setHTML(popupHTML);

    if (onSelectHazard) {
      el.addEventListener('click', () => onSelectHazard(hazard));
    }

    new maplibregl.Marker({ element: el })
      .setLngLat([hazard?.longitude ?? 77.5946, hazard?.latitude ?? 12.9716])
      .setPopup(popup)
      .addTo(map);
  });
}
