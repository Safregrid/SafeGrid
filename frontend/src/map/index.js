/**
 * SafeGrid Map Module
 * Person 3 owns this file.
 *
 * Responsibilities:
 * - Create and configure the MapLibre map instance (initMap)
 * - Add GeoJSON layers for risk zones (addRiskZoneLayer)
 * - Apply 🔴🟡🟢 color styling to features based on risk_level property
 * - Update risk zones and telemetry counters (updateRiskZones)
 * - Plot hazard event markers with real data fields (renderHazardMarkers)
 */

import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

// Free dark vector map tile style
const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';
const RISK_SOURCE_ID = 'risk-zones';

// Standardized color conventions (exported per docs/FRONTEND_CONTRACT.md §4, §6)
export const COLOR_HIGH = '#ef4444';     // Red
export const COLOR_MODERATE = '#f59e0b'; // Amber
export const COLOR_LOW = '#22c55e';      // Green
export const COLOR_HAZARD_MARKER = '#38bdf8'; // Sky blue neutral marker

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
  const data = geojson || { type: 'FeatureCollection', features: [] };

  if (!map.getSource(RISK_SOURCE_ID)) {
    map.addSource(RISK_SOURCE_ID, {
      type: 'geojson',
      data: data,
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
          'MODERATE', COLOR_MODERATE,
          'LOW', COLOR_LOW,
          '#64748b' // Default slate gray
        ],
        'fill-opacity': 0.35,
      },
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
          'MODERATE', COLOR_MODERATE,
          'LOW', COLOR_LOW,
          '#64748b'
        ],
        'line-width': 2,
      },
    });

    // Click handler for risk zone polygons
    map.on('click', 'risk-zones-fill', (e) => {
      if (e.features && e.features.length > 0) {
        const props = e.features[0].properties || {};
        const panelCard = document.getElementById('hazard-details-card');
        if (panelCard) {
          const riskColor =
            props.risk_level === 'HIGH'
              ? COLOR_HIGH
              : props.risk_level === 'MODERATE'
              ? COLOR_MODERATE
              : COLOR_LOW;
          const statusBadge = props.is_live
            ? '<span style="color: #22c55e; font-weight: bold; font-size: 11px;">● LIVE RISK CALCULATION</span>'
            : '<span style="color: #f59e0b; font-weight: bold; font-size: 11px;">🕒 CACHED RISK CALCULATION</span>';

          panelCard.innerHTML = `
            <h4 style="color: #f8fafc; font-size: 0.95rem; margin-bottom: 0.4rem;">Risk Zone: ${(props.hazard_type || 'Unknown').toUpperCase()}</h4>
            <p style="color: #94a3b8; font-size: 0.8rem; margin-bottom: 0.2rem;"><strong>Risk Level:</strong> <span style="color: ${riskColor}; font-weight: bold;">${props.risk_level || 'N/A'}</span></p>
            <p style="color: #94a3b8; font-size: 0.8rem; margin-bottom: 0.2rem;"><strong>Severity Score:</strong> ${props.severity_score ?? 'N/A'}</p>
            <p style="color: #94a3b8; font-size: 0.8rem; margin-bottom: 0.2rem;"><strong>Hazard ID:</strong> ${props.hazard_id || 'N/A'}</p>
            <p style="color: #94a3b8; font-size: 0.8rem; margin-bottom: 0.2rem;"><strong>Calculated At:</strong> ${props.calculated_at ? new Date(props.calculated_at).toLocaleString() : 'N/A'}</p>
            <div style="background: #0f172a; padding: 0.4rem; border-radius: 4px; border: 1px solid #334155; font-size: 0.75rem; margin-top: 0.4rem;">
              ${statusBadge}
            </div>
          `;
        }
      }
    });

    map.on('mouseenter', 'risk-zones-fill', () => {
      map.getCanvas().style.cursor = 'pointer';
    });
    map.on('mouseleave', 'risk-zones-fill', () => {
      map.getCanvas().style.cursor = '';
    });
  } else {
    const source = map.getSource(RISK_SOURCE_ID);
    source.setData(data);
  }
}

/**
 * Updates existing GeoJSON risk zones source and telemetry counters.
 */
export function updateRiskZones(map, geojson) {
  const data = geojson || { type: 'FeatureCollection', features: [] };
  const source = map.getSource(RISK_SOURCE_ID);
  if (source) {
    source.setData(data);
  } else {
    addRiskZoneLayer(map, data);
  }

  // Count features by risk_level from the risk engine
  let highCount = 0;
  let modCount = 0;
  let lowCount = 0;

  if (Array.isArray(data.features)) {
    data.features.forEach((feature) => {
      const risk = (feature.properties?.risk_level || '').toUpperCase();
      if (risk === 'HIGH') highCount++;
      else if (risk === 'MODERATE') modCount++;
      else if (risk === 'LOW') lowCount++;
    });
  }

  const elHigh = document.getElementById('count-high');
  const elMod = document.getElementById('count-moderate');
  const elLow = document.getElementById('count-low');
  if (elHigh) elHigh.textContent = highCount;
  if (elMod) elMod.textContent = modCount;
  if (elLow) elLow.textContent = lowCount;

  const mapElHigh = document.getElementById('map-count-high');
  const mapElMod = document.getElementById('map-count-moderate');
  const mapElLow = document.getElementById('map-count-low');
  if (mapElHigh) mapElHigh.textContent = highCount;
  if (mapElMod) mapElMod.textContent = modCount;
  if (mapElLow) mapElLow.textContent = lowCount;
}

/**
 * Renders neutral hazard point markers on the map using verified Hazard fields.
 * Markers do NOT carry risk ratings or severity scores.
 */
export function renderHazardMarkers(map, hazards, onSelectHazard) {
  const existing = document.querySelectorAll('.hazard-marker');
  existing.forEach((el) => el.remove());

  const hazardList = Array.isArray(hazards)
    ? hazards
    : (Array.isArray(hazards?.hazards) ? hazards.hazards : []);

  hazardList.forEach((hazard) => {
    // Skip hazards missing valid coordinates
    if (typeof hazard?.latitude !== 'number' || typeof hazard?.longitude !== 'number') {
      return;
    }

    const el = document.createElement('div');
    el.className = 'hazard-marker';

    const displayType = (hazard?.hazard_type ?? 'Event').toUpperCase();
    const source = hazard?.source ?? 'Unknown Source';
    const timestamp = hazard?.timestamp
      ? new Date(hazard.timestamp).toLocaleString()
      : (hazard?.created_at ? new Date(hazard.created_at).toLocaleString() : 'N/A');

    const magnitudeRow = hazard?.magnitude != null
      ? `<p style="margin: 3px 0; font-size: 12px;"><strong>Magnitude:</strong> ${hazard.magnitude}</p>`
      : '';
    const probRow = hazard?.probability != null
      ? `<p style="margin: 3px 0; font-size: 12px;"><strong>Probability:</strong> ${hazard.probability}%</p>`
      : '';

    const popupHTML = `
      <div style="color: #0f172a; font-family: sans-serif; padding: 4px; min-width: 180px;">
        <div style="margin-bottom: 6px; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px;">
          <strong style="font-size: 13px;">${displayType}</strong>
        </div>
        <p style="margin: 3px 0; font-size: 12px;"><strong>Source:</strong> ${source}</p>
        <p style="margin: 3px 0; font-size: 12px;"><strong>Time:</strong> ${timestamp}</p>
        ${magnitudeRow}
        ${probRow}
      </div>
    `;

    const popup = new maplibregl.Popup({ offset: 25 }).setHTML(popupHTML);

    el.addEventListener('click', () => {
      const panelCard = document.getElementById('hazard-details-card');
      if (panelCard) {
        let extrasHTML = '';
        if (hazard.specific_data && typeof hazard.specific_data === 'object') {
          const keys = Object.keys(hazard.specific_data);
          if (keys.length > 0) {
            extrasHTML = keys
              .map((k) => `<p style="color: #94a3b8; font-size: 0.8rem; margin-bottom: 0.2rem;"><strong>${k}:</strong> ${hazard.specific_data[k]}</p>`)
              .join('');
          }
        }

        panelCard.innerHTML = `
          <h4 style="color: #f8fafc; font-size: 0.95rem; margin-bottom: 0.4rem;">${displayType}</h4>
          <p style="color: #94a3b8; font-size: 0.8rem; margin-bottom: 0.2rem;"><strong>Source:</strong> ${source}</p>
          <p style="color: #94a3b8; font-size: 0.8rem; margin-bottom: 0.2rem;"><strong>Timestamp:</strong> ${timestamp}</p>
          ${hazard.magnitude != null ? `<p style="color: #94a3b8; font-size: 0.8rem; margin-bottom: 0.2rem;"><strong>Magnitude:</strong> ${hazard.magnitude}</p>` : ''}
          ${hazard.probability != null ? `<p style="color: #94a3b8; font-size: 0.8rem; margin-bottom: 0.2rem;"><strong>Probability:</strong> ${hazard.probability}%</p>` : ''}
          ${extrasHTML}
          <p style="color: #64748b; font-size: 0.75rem; margin-top: 0.4rem;">Coordinates: ${hazard.latitude.toFixed(4)}, ${hazard.longitude.toFixed(4)}</p>
        `;
      }
      if (onSelectHazard) onSelectHazard(hazard);
    });

    new maplibregl.Marker({ element: el })
      .setLngLat([hazard.longitude, hazard.latitude])
      .setPopup(popup)
      .addTo(map);
  });
}
