/**
 * SafeGrid frontend entry point.
 *
 * Person 3 owns this file.
 *
 * Initial goal: given valid GeoJSON from the backend, render risk zones on the map.
 * Do not build UI polish before the data pipeline works.
 */

import { initMap, renderHazardMarkers, addRiskZoneLayer, updateRiskZones } from './map/index.js';
import { fetchHazards, fetchRiskZones } from './api/client.js';

console.log("SafeGrid frontend initializing...");

// TODO (Person 4): register service worker for offline support — see src/service-worker.js
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js')
      .then((reg) => console.log('PWA ServiceWorker registered:', reg.scope))
      .catch((err) => console.warn('PWA ServiceWorker registration failed:', err));
  });
}

document.addEventListener('DOMContentLoaded', async () => {
  // TODO (Person 3): initialize the MapLibre map — see src/map/index.js
  const map = initMap('map');

  map.on('load', async () => {
    try {
      addRiskZoneLayer(map, null);

      // TODO (Person 3): fetch risk zones from the API — see src/api/client.js
      const [hazards, riskZonesGeoJSON] = await Promise.all([
        fetchHazards(),
        fetchRiskZones()
      ]);

      console.log(`Loaded ${hazards?.length ?? 0} hazard records.`);

      // Render point markers
      renderHazardMarkers(map, hazards, (selectedHazard) => {
        const lat = selectedHazard?.latitude ?? 12.9716;
        const lng = selectedHazard?.longitude ?? 77.5946;

        console.log('Hazard selected:', selectedHazard?.title ?? 'Unnamed Hazard');
        map.flyTo({ center: [lng, lat], zoom: 8 });
      });

      // Render GeoJSON risk zones from backend or construct fallback
      if (riskZonesGeoJSON && riskZonesGeoJSON.features && riskZonesGeoJSON.features.length > 0) {
        updateRiskZones(map, riskZonesGeoJSON);
      } else if (Array.isArray(hazards) && hazards.length > 0) {
        const fallbackGeoJSON = {
          type: 'FeatureCollection',
          features: hazards.map((h) => ({
            type: 'Feature',
            geometry: {
              type: 'Point',
              coordinates: [h.longitude ?? 77.5946, h.latitude ?? 12.9716]
            },
            properties: {
              id: h.id,
              title: h.title,
              risk_level: h.risk_level ?? 'LOW',
              severity_value: h.severity_value
            }
          }))
        };
        updateRiskZones(map, fallbackGeoJSON);
      }
    } catch (err) {
      console.error('Failed to load map data pipeline:', err);
    }
  });
});
