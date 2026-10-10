/**
 * SafeGrid frontend entry point.
 * Person 3 owns this file.
 */

<<<<<<< HEAD
// TODO (Person 3): initialize the MapLibre map — see src/map/index.js
// TODO (Person 3): fetch risk zones from the API — see src/api/client.js
// Person 4: register the offline service worker so cached risk zones are
// available when the network is down.
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("/service-worker.js", { type: "module" })
      .catch((error) => {
        console.error("Service worker registration failed:", error);
      });
  });
}
=======
import { initMap, renderHazardMarkers, addRiskZoneLayer, updateRiskZones } from './map/index.js';
import { fetchHazards, fetchRiskZones } from './api/client.js';
>>>>>>> origin/feature/frontend-maplibre-ui

console.log("SafeGrid frontend initializing...");

// TODO (Person 4): register service worker for offline support — see src/service-worker.js

document.addEventListener('DOMContentLoaded', async () => {
  const map = initMap('map');

  map.on('load', async () => {
    try {
      addRiskZoneLayer(map, null);

      const [hazards, riskZonesGeoJSON] = await Promise.all([
        fetchHazards().catch(err => {
          console.warn('Hazards fetch failed:', err);
          return [];
        }),
        fetchRiskZones().catch(err => {
          console.warn('Risk zones fetch failed:', err);
          return null;
        })
      ]);

      console.log(`Loaded ${hazards?.length ?? 0} hazard records.`);

      renderHazardMarkers(map, hazards, (selectedHazard) => {
        if (typeof selectedHazard?.latitude === 'number' && typeof selectedHazard?.longitude === 'number') {
          map.flyTo({ center: [selectedHazard.longitude, selectedHazard.latitude], zoom: 8 });
        }
      });

      // Pass actual GeoJSON if available, otherwise pass empty collection (no fabrication)
      if (riskZonesGeoJSON && riskZonesGeoJSON.features) {
        updateRiskZones(map, riskZonesGeoJSON);
      } else {
        updateRiskZones(map, { type: 'FeatureCollection', features: [] });
      }
    } catch (err) {
      console.error('Failed to load map data pipeline:', err);
    }
  });
});
