/**
 * SafeGrid Map Module
 * Person 3 owns this file.
 */

import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';
const RISK_SOURCE_ID = 'risk-zones';

const COLOR_HIGH = '#ef4444';     // Red
const COLOR_MODERATE = '#f59e0b'; // Amber
const COLOR_LOW = '#22c55e';      // Green

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

export function addRiskZoneLayer(map, geojson) {
  if (!map.getSource(RISK_SOURCE_ID)) {
    map.addSource(RISK_SOURCE_ID, {
      type: 'geojson',
      data: geojson || { type: 'FeatureCollection', features: [] }
    });

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
          '#6b7280'
        ],
        'fill-opacity': 0.35
      }
    });

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

export function updateRiskZones(map, geojson) {
  const source = map.getSource(RISK_SOURCE_ID);
  if (source) {
    source.setData(geojson || { type: 'FeatureCollection', features: [] });
  } else {
    addRiskZoneLayer(map, geojson);
  }
}

export function renderHazardMarkers(map, hazards, onSelectHazard) {
  const existing = document.querySelectorAll('.hazard-marker');
  existing.forEach((el) => el.remove());

  let highCount = 0;
  let modCount = 0;
  let lowCount = 0;

  (hazards ?? []).forEach((hazard) => {
    const risk = (hazard?.risk_level ?? 'LOW').toUpperCase();
    
    let markerColor = COLOR_LOW;
    if (risk === 'HIGH' || risk === 'RED') { markerColor = COLOR_HIGH; highCount++; }
    else if (risk === 'MODERATE' || risk === 'YELLOW') { markerColor = COLOR_MODERATE; modCount++; }
    else { lowCount++; }

    const el = document.createElement('div');
    el.className = 'hazard-marker';
    el.style.backgroundColor = markerColor;

    const isLive = hazard?.is_live ?? true;
    const recordedAt = hazard?.recorded_at ? new Date(hazard.recorded_at).toLocaleTimeString() : 'Recently';
    const statusBadge = isLive
      ? '<span style="color: #22c55e; font-weight: bold; font-size: 11px;">● LIVE DATA</span>'
      : `<span style="color: #94a3b8; font-weight: bold; font-size: 11px;">🕒 CACHED (${recordedAt})</span>`;

    const displayType = (hazard?.hazard_type ?? 'Event').toUpperCase();
    const source = hazard?.source ?? 'Global Feed';
    const severity = hazard?.severity_score ?? 'N/A';

    const popupHTML = `
      <div style="color: #0f172a; font-family: sans-serif; padding: 4px; min-width: 180px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px;">
          <strong style="font-size: 13px;">${displayType}</strong>
        </div>
        <p style="margin: 3px 0; font-size: 12px;"><strong>Source:</strong> ${source}</p>
        <p style="margin: 3px 0; font-size: 12px;"><strong>Severity Score:</strong> ${severity}</p>
        <p style="margin: 3px 0; font-size: 12px;"><strong>Risk Rating:</strong> <span style="color: ${markerColor}; font-weight: bold;">${risk}</span></p>
        <div style="margin-top: 6px; padding-top: 4px; border-top: 1px solid #e2e8f0;">
          ${statusBadge}
        </div>
      </div>
    `;

    const popup = new maplibregl.Popup({ offset: 25 }).setHTML(popupHTML);

    el.addEventListener('click', () => {
      const panelCard = document.getElementById('hazard-details-card');
      if (panelCard) {
        panelCard.innerHTML = `
          <h4 style="color: #f8fafc; font-size: 0.95rem; margin-bottom: 0.4rem;">${displayType}</h4>
          <p style="color: #94a3b8; font-size: 0.8rem; margin-bottom: 0.2rem;"><strong>Origin Source:</strong> ${source}</p>
          <p style="color: #94a3b8; font-size: 0.8rem; margin-bottom: 0.2rem;"><strong>Severity Score:</strong> ${severity}</p>
          <p style="color: #94a3b8; font-size: 0.8rem; margin-bottom: 0.4rem;"><strong>Assessed Risk:</strong> <span style="color: ${markerColor}; font-weight: bold;">${risk}</span></p>
          <div style="background: #0f172a; padding: 0.4rem; border-radius: 4px; border: 1px solid #334155; font-size: 0.75rem;">
            ${statusBadge}
          </div>
        `;
      }
      if (onSelectHazard) onSelectHazard(hazard);
    });

    new maplibregl.Marker({ element: el })
      .setLngLat([hazard?.longitude ?? 77.5946, hazard?.latitude ?? 12.9716])
      .setPopup(popup)
      .addTo(map);
  });

  const elHigh = document.getElementById('count-high');
  const elMod = document.getElementById('count-moderate');
  const elLow = document.getElementById('count-low');
  if (elHigh) elHigh.innerText = highCount;
  if (elMod) elMod.innerText = modCount;
  if (elLow) elLow.innerText = lowCount;
}
