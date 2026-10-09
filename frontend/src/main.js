/**
 * SafeGrid frontend entry point.
 * Person 3 owns this file.
 */

import { initMap, renderHazardMarkers, addRiskZoneLayer, updateRiskZones } from './map/index.js';
import { fetchHazards, fetchRiskZones } from './api/client.js';

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
