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
        const lat = selectedHazard?.latitude ?? 12.9716;
        const lng = selectedHazard?.longitude ?? 77.5946;
        map.flyTo({ center: [lng, lat], zoom: 8 });
      });

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
              risk_level: h.risk_level ?? 'LOW',
              severity_score: h.severity_score
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
