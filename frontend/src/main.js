/**
 * SafeGrid frontend entry point.
 * Person 3 owns this file.
 */

import { initMap, renderHazardMarkers, addRiskZoneLayer, updateRiskZones } from './map/index.js';
import { fetchHazards, fetchRiskZones, fetchRiskAtPoint } from './api/client.js';

console.log("SafeGrid frontend initializing...");

// Person 4: register the offline service worker so cached data is available
// when the network is down.
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("/service-worker.js", { type: "module" })
      .catch((error) => {
        console.error("Service worker registration failed:", error);
      });
  });
}

document.addEventListener('DOMContentLoaded', () => {
  // ---------------------------------------------------------------------------
  // State variables
  // ---------------------------------------------------------------------------
  let currentZone = 'UNKNOWN'; // 'HIGH' | 'MODERATE' | 'LOW' | 'UNKNOWN'
  let currentCoords = null;    // { lat: number, lon: number }
  let currentAccuracy = null;  // number (meters)
  let currentAssessmentTime = null;
  let currentSeverityScore = null;
  let mapInstance = null;

  // ---------------------------------------------------------------------------
  // DOM Elements
  // ---------------------------------------------------------------------------
  const tabHome = document.getElementById('tab-home');
  const tabMap = document.getElementById('tab-map');
  const viewHome = document.getElementById('view-home');
  const viewMap = document.getElementById('view-map');
  const btnGotoMap = document.getElementById('btn-goto-map');
  const btnDetectLocation = document.getElementById('btn-detect-location');

  const zoneCard = document.getElementById('user-zone-card');
  const zoneTitle = document.getElementById('zone-title');
  const zoneMeaning = document.getElementById('zone-meaning');
  const zoneIcon = document.getElementById('zone-icon');
  const userCoordsText = document.getElementById('user-coords-text');
  const zoneScoreText = document.getElementById('zone-score-text');
  const zoneTimestampText = document.getElementById('zone-timestamp-text');
  const zoneFreshnessPill = document.getElementById('zone-freshness-pill');
  const zoneFreshnessText = document.getElementById('zone-freshness-text');
  const dashboardHazardSummary = document.getElementById('dashboard-hazard-summary');

  // SOS elements
  const btnSosTrigger = document.getElementById('btn-sos-trigger');
  const sosBtnHint = document.getElementById('sos-btn-hint');
  const modalSos = document.getElementById('modal-sos');
  const btnCloseSos = document.getElementById('btn-close-sos');
  const sosZoneDisplay = document.getElementById('sos-zone-display');
  const sosCoordsDisplay = document.getElementById('sos-coords-display');
  const sosAccuracyDisplay = document.getElementById('sos-accuracy-display');
  const sosTimestampDisplay = document.getElementById('sos-timestamp-display');
  const btnShareSos = document.getElementById('btn-share-sos');
  const sosCopyToast = document.getElementById('sos-copy-toast');

  // Guidelines elements
  const btnGuidelinesTrigger = document.getElementById('btn-guidelines-trigger');
  const modalGuidelines = document.getElementById('modal-guidelines');
  const btnCloseGuidelines = document.getElementById('btn-close-guidelines');
  const btnPrintGuidelines = document.getElementById('btn-print-guidelines');
  const guidelineTabBtns = document.querySelectorAll('.g-tab-btn');
  const guidelinePanels = document.querySelectorAll('.guide-panel');

  // ---------------------------------------------------------------------------
  // Tab Navigation Handling
  // ---------------------------------------------------------------------------
  function switchTab(target) {
    if (target === 'home') {
      tabHome.classList.add('active');
      tabHome.setAttribute('aria-selected', 'true');
      tabMap.classList.remove('active');
      tabMap.setAttribute('aria-selected', 'false');

      viewHome.classList.add('active');
      viewMap.classList.remove('active');
    } else if (target === 'map') {
      tabMap.classList.add('active');
      tabMap.setAttribute('aria-selected', 'true');
      tabHome.classList.remove('active');
      tabHome.setAttribute('aria-selected', 'false');

      viewMap.classList.add('active');
      viewHome.classList.remove('active');

      // Trigger MapLibre resize so canvas recalculates dimensions properly
      if (mapInstance) {
        setTimeout(() => mapInstance.resize(), 60);
      }
    }
  }

  if (tabHome) tabHome.addEventListener('click', () => switchTab('home'));
  if (tabMap) tabMap.addEventListener('click', () => switchTab('map'));
  if (btnGotoMap) btnGotoMap.addEventListener('click', () => switchTab('map'));

  // ---------------------------------------------------------------------------
  // Zone UI & SOS State Synchronization
  // ---------------------------------------------------------------------------
  function updateZoneUI() {
    if (!zoneCard) return;

    // Reset card class list
    zoneCard.classList.remove('zone-high', 'zone-moderate', 'zone-low', 'zone-unknown');

    if (currentZone === 'HIGH') {
      zoneCard.classList.add('zone-high');
      if (zoneTitle) zoneTitle.textContent = 'HIGH RISK (RED ZONE)';
      if (zoneIcon) zoneIcon.textContent = '🔴';
      if (zoneMeaning) {
        zoneMeaning.textContent = 'Severe hazard threat in your vicinity. Evacuate if ordered by local authorities, disconnect gas/power, and seek high ground or shelter.';
      }
      // Enable SOS button
      if (btnSosTrigger) {
        btnSosTrigger.disabled = false;
        btnSosTrigger.classList.remove('disabled');
      }
      if (sosBtnHint) sosBtnHint.textContent = 'Ready — Tap for SOS Card';
    } else if (currentZone === 'MODERATE') {
      zoneCard.classList.add('zone-moderate');
      if (zoneTitle) zoneTitle.textContent = 'MODERATE RISK (YELLOW ZONE)';
      if (zoneIcon) zoneIcon.textContent = '🟡';
      if (zoneMeaning) {
        zoneMeaning.textContent = 'Elevated hazard risk detected. Stay alert, avoid low-lying roads/culverts, and monitor official weather and civil bulletins.';
      }
      // Enable SOS button
      if (btnSosTrigger) {
        btnSosTrigger.disabled = false;
        btnSosTrigger.classList.remove('disabled');
      }
      if (sosBtnHint) sosBtnHint.textContent = 'Ready — Tap for SOS Card';
    } else if (currentZone === 'LOW') {
      zoneCard.classList.add('zone-low');
      if (zoneTitle) zoneTitle.textContent = 'LOW RISK (GREEN ZONE)';
      if (zoneIcon) zoneIcon.textContent = '🟢';
      if (zoneMeaning) {
        zoneMeaning.textContent = 'Low hazard activity currently recorded. Critical reminder: LOW does not mean safe. Maintain emergency go-bag supplies.';
      }
      // Disable SOS button for GREEN zone per safety rules
      if (btnSosTrigger) {
        btnSosTrigger.disabled = true;
        btnSosTrigger.classList.add('disabled');
      }
      if (sosBtnHint) sosBtnHint.textContent = 'Disabled for LOW zone (LOW ≠ safe)';
    } else {
      zoneCard.classList.add('zone-unknown');
      if (zoneTitle) zoneTitle.textContent = 'ZONE UNKNOWN';
      if (zoneIcon) zoneIcon.textContent = '⚪';
      // Disable SOS button when zone is unknown
      if (btnSosTrigger) {
        btnSosTrigger.disabled = true;
        btnSosTrigger.classList.add('disabled');
      }
      if (sosBtnHint) sosBtnHint.textContent = 'Location or Zone Unverified';
    }

    if (zoneScoreText) {
      zoneScoreText.textContent = typeof currentSeverityScore === 'number' ? currentSeverityScore.toFixed(1) : '—';
    }

    if (zoneTimestampText) {
      zoneTimestampText.textContent = currentAssessmentTime
        ? new Date(currentAssessmentTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        : '—';
    }
  }

  // ---------------------------------------------------------------------------
  // Location Detection & Point Risk Lookup
  // ---------------------------------------------------------------------------
  async function detectAndAssessLocation() {
    if (!('geolocation' in navigator)) {
      if (userCoordsText) userCoordsText.textContent = 'Geolocation not supported';
      if (zoneMeaning) zoneMeaning.textContent = 'Browser does not support geolocation. Inspect hazard areas manually on the Map tab.';
      currentZone = 'UNKNOWN';
      updateZoneUI();
      return;
    }

    if (userCoordsText) userCoordsText.textContent = 'Acquiring GPS location...';
    if (zoneFreshnessText) zoneFreshnessText.textContent = 'Locating...';
    if (zoneFreshnessPill) zoneFreshnessPill.className = 'badge-pill cached';

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        currentCoords = { lat, lon };
        currentAccuracy = Math.round(pos.coords.accuracy || 0);

        if (userCoordsText) {
          userCoordsText.textContent = `${lat.toFixed(4)}°, ${lon.toFixed(4)}° (±${currentAccuracy}m)`;
        }

        try {
          if (zoneFreshnessText) zoneFreshnessText.textContent = 'Evaluating...';

          // Call Point-Lookup API via client.js
          const riskData = await fetchRiskAtPoint(lat, lon);

          // Handle the 3 contract states from docs/API.md
          if (riskData.in_coverage === false) {
            // State 1: Outside pilot region
            currentZone = 'UNKNOWN';
            currentSeverityScore = null;
            currentAssessmentTime = new Date().toISOString();
            if (zoneMeaning) {
              zoneMeaning.textContent = 'Your location is outside the current pilot model area. SafeGrid does not model this region; never assume safe.';
            }
            if (zoneFreshnessPill) zoneFreshnessPill.className = 'badge-pill offline';
            if (zoneFreshnessText) zoneFreshnessText.textContent = 'Outside Coverage';
          } else if (riskData.in_coverage === true && riskData.reason === 'no_data') {
            // State 2: Inside pilot region, no cell scored yet
            currentZone = 'UNKNOWN';
            currentSeverityScore = null;
            currentAssessmentTime = new Date().toISOString();
            if (zoneMeaning) {
              zoneMeaning.textContent = 'Inside pilot region, but no grid data has been scored yet for this grid coordinate.';
            }
            if (zoneFreshnessPill) zoneFreshnessPill.className = 'badge-pill cached';
            if (zoneFreshnessText) zoneFreshnessText.textContent = 'No Cell Data';
          } else if (riskData.in_coverage === true && riskData.risk_level) {
            // State 3: Scored cell
            currentZone = riskData.risk_level.toUpperCase();
            currentSeverityScore = riskData.severity_score;
            currentAssessmentTime = riskData.generated_at || riskData.computed_at || new Date().toISOString();

            if (riskData.is_live) {
              if (zoneFreshnessPill) zoneFreshnessPill.className = 'badge-pill live';
              if (zoneFreshnessText) zoneFreshnessText.textContent = 'Live Grid Data';
            } else {
              if (zoneFreshnessPill) zoneFreshnessPill.className = 'badge-pill cached';
              const genTime = riskData.generated_at ? new Date(riskData.generated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Stale';
              if (zoneFreshnessText) zoneFreshnessText.textContent = `Cached Grid (${genTime})`;
            }
          } else {
            // Fallback for unexpected contract shape
            currentZone = 'UNKNOWN';
            if (zoneMeaning) zoneMeaning.textContent = 'Unable to determine point risk. Consult local authorities.';
            if (zoneFreshnessPill) zoneFreshnessPill.className = 'badge-pill offline';
            if (zoneFreshnessText) zoneFreshnessText.textContent = 'Unknown Status';
          }
        } catch (err) {
          console.warn('fetchRiskAtPoint failed or endpoint stubbed:', err);
          currentZone = 'UNKNOWN';
          currentSeverityScore = null;
          currentAssessmentTime = new Date().toISOString();
          if (zoneMeaning) {
            zoneMeaning.textContent = 'Point risk lookup unavailable (endpoint stub or offline). SafeGrid never guesses risk levels.';
          }
          if (zoneFreshnessPill) zoneFreshnessPill.className = 'badge-pill offline';
          if (zoneFreshnessText) zoneFreshnessText.textContent = 'Service Offline';
        }

        updateZoneUI();
      },
      (err) => {
        console.warn('Geolocation permission error or timeout:', err.message);
        if (userCoordsText) userCoordsText.textContent = 'Permission Denied';
        if (zoneMeaning) {
          zoneMeaning.textContent = 'Location access denied or unavailable. Grant location permission to assess your area, or inspect risk zones on the Map tab.';
        }
        if (zoneFreshnessPill) zoneFreshnessPill.className = 'badge-pill offline';
        if (zoneFreshnessText) zoneFreshnessText.textContent = 'No Location';
        currentZone = 'UNKNOWN';
        updateZoneUI();
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  }

  if (btnDetectLocation) {
    btnDetectLocation.addEventListener('click', detectAndAssessLocation);
  }

  // ---------------------------------------------------------------------------
  // MapLibre Initialization & Risk Pipeline
  // ---------------------------------------------------------------------------
  mapInstance = initMap('map');

  mapInstance.on('load', async () => {
    try {
      addRiskZoneLayer(mapInstance, null);

      const [hazardPayload, riskZonesGeoJSON] = await Promise.all([
        fetchHazards().catch(err => {
          console.warn('Hazards fetch failed:', err);
          return null;
        }),
        fetchRiskZones().catch(err => {
          console.warn('Risk zones fetch failed (endpoint stub or offline):', err);
          return null;
        })
      ]);

      // Telemetry status badge in header
      const statusPill = document.getElementById('connection-status');
      const statusText = document.getElementById('status-text');
      if (hazardPayload) {
        if (statusPill && statusText) {
          if (hazardPayload.is_live) {
            statusPill.className = 'system-status live';
            statusText.textContent = 'LIVE DATA';
          } else {
            statusPill.className = 'system-status cached';
            statusText.textContent = 'CACHED DATA';
          }
        }
      } else if (statusPill && statusText) {
        statusPill.className = 'system-status offline';
        statusText.textContent = 'API UNAVAILABLE';
      }

      const hazards = hazardPayload?.hazards ?? [];
      console.log(`Loaded ${hazards.length} hazard records.`);

      // Update dashboard hazard summary list
      if (dashboardHazardSummary) {
        if (hazards.length > 0) {
          dashboardHazardSummary.innerHTML = hazards.slice(0, 4).map(h => `
            <div class="summary-item">
              <span><strong>${(h.hazard_type || 'Hazard').toUpperCase()}</strong> (${h.source || 'feed'})</span>
              <span style="color: #94a3b8; font-size: 0.75rem;">${h.timestamp ? new Date(h.timestamp).toLocaleTimeString() : 'Recent'}</span>
            </div>
          `).join('');
        } else {
          dashboardHazardSummary.innerHTML = '<p class="summary-empty">No active hazard events reported in current regional window.</p>';
        }
      }

      renderHazardMarkers(mapInstance, hazards, (selectedHazard) => {
        if (typeof selectedHazard?.latitude === 'number' && typeof selectedHazard?.longitude === 'number') {
          mapInstance.flyTo({ center: [selectedHazard.longitude, selectedHazard.latitude], zoom: 8 });
        }
      });

      if (riskZonesGeoJSON && riskZonesGeoJSON.features) {
        updateRiskZones(mapInstance, riskZonesGeoJSON);
      } else {
        updateRiskZones(mapInstance, { type: 'FeatureCollection', features: [] });
      }
    } catch (err) {
      console.error('Failed to load map data pipeline:', err);
    }
  });

  // ---------------------------------------------------------------------------
  // SOS Modal Logic
  // ---------------------------------------------------------------------------
  function openSosModal() {
    if (!modalSos) return;
    if (currentZone !== 'HIGH' && currentZone !== 'MODERATE') {
      return; // Safety rule: SOS info only active for RED / YELLOW
    }

    // Populate SOS fields
    if (sosZoneDisplay) {
      if (currentZone === 'HIGH') {
        sosZoneDisplay.className = 'sos-zone-pill high';
        sosZoneDisplay.textContent = '🔴 HIGH RISK (RED ZONE)';
      } else {
        sosZoneDisplay.className = 'sos-zone-pill moderate';
        sosZoneDisplay.textContent = '🟡 MODERATE RISK (YELLOW ZONE)';
      }
    }

    if (sosCoordsDisplay) {
      if (currentCoords) {
        sosCoordsDisplay.textContent = `${currentCoords.lat.toFixed(5)}° N, ${currentCoords.lon.toFixed(5)}° E`;
      } else {
        sosCoordsDisplay.textContent = 'Coordinates Pending GPS';
      }
    }

    if (sosAccuracyDisplay) {
      sosAccuracyDisplay.textContent = currentAccuracy != null ? `GPS Accuracy: ±${currentAccuracy}m` : 'GPS Accuracy: Unknown';
    }

    if (sosTimestampDisplay) {
      sosTimestampDisplay.textContent = currentAssessmentTime
        ? new Date(currentAssessmentTime).toLocaleString()
        : new Date().toLocaleString();
    }

    modalSos.hidden = false;
    btnSosTrigger.setAttribute('aria-expanded', 'true');
  }

  function closeSosModal() {
    if (!modalSos) return;
    modalSos.hidden = true;
    if (btnSosTrigger) btnSosTrigger.setAttribute('aria-expanded', 'false');
    if (sosCopyToast) sosCopyToast.hidden = true;
  }

  if (btnSosTrigger) btnSosTrigger.addEventListener('click', openSosModal);
  if (btnCloseSos) btnCloseSos.addEventListener('click', closeSosModal);
  if (modalSos) {
    modalSos.addEventListener('click', (e) => {
      if (e.target === modalSos) closeSosModal();
    });
  }

  if (btnShareSos) {
    btnShareSos.addEventListener('click', async () => {
      const latStr = currentCoords ? currentCoords.lat.toFixed(5) : 'Unknown';
      const lonStr = currentCoords ? currentCoords.lon.toFixed(5) : 'Unknown';
      const accStr = currentAccuracy != null ? `±${currentAccuracy}m` : 'Unknown';
      const timeStr = currentAssessmentTime ? new Date(currentAssessmentTime).toLocaleString() : new Date().toLocaleString();

      const message = `EMERGENCY ALERT: I need assistance. My GPS location is Lat: ${latStr}, Lon: ${lonStr} (${accStr}). SafeGrid assessed hazard zone: ${currentZone} as of ${timeStr}. (Academic prototype alert)`;

      if (navigator.share) {
        try {
          await navigator.share({
            title: 'Emergency Location Card - SafeGrid',
            text: message,
          });
          return;
        } catch {
          // User cancelled or share failed, fallback to clipboard
        }
      }

      if (navigator.clipboard && navigator.clipboard.writeText) {
        try {
          await navigator.clipboard.writeText(message);
          if (sosCopyToast) {
            sosCopyToast.hidden = false;
            setTimeout(() => { if (sosCopyToast) sosCopyToast.hidden = true; }, 3500);
          }
        } catch (copyErr) {
          console.warn('Clipboard write failed:', copyErr);
        }
      }
    });
  }

  // ---------------------------------------------------------------------------
  // Guidelines Modal Logic
  // ---------------------------------------------------------------------------
  function openGuidelinesModal() {
    if (!modalGuidelines) return;
    modalGuidelines.hidden = false;
    btnGuidelinesTrigger.setAttribute('aria-expanded', 'true');
  }

  function closeGuidelinesModal() {
    if (!modalGuidelines) return;
    modalGuidelines.hidden = true;
    if (btnGuidelinesTrigger) btnGuidelinesTrigger.setAttribute('aria-expanded', 'false');
  }

  if (btnGuidelinesTrigger) btnGuidelinesTrigger.addEventListener('click', openGuidelinesModal);
  if (btnCloseGuidelines) btnCloseGuidelines.addEventListener('click', closeGuidelinesModal);
  if (modalGuidelines) {
    modalGuidelines.addEventListener('click', (e) => {
      if (e.target === modalGuidelines) closeGuidelinesModal();
    });
  }

  // Guidelines internal tab switching
  guidelineTabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-target');
      guidelineTabBtns.forEach(b => b.classList.remove('active'));
      guidelinePanels.forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const targetPanel = document.getElementById(targetId);
      if (targetPanel) targetPanel.classList.add('active');
    });
  });

  // Print Guidelines as PDF action
  if (btnPrintGuidelines) {
    btnPrintGuidelines.addEventListener('click', () => {
      window.print();
    });
  }

  // ---------------------------------------------------------------------------
  // Auto-detect location on initial start
  // ---------------------------------------------------------------------------
  detectAndAssessLocation();
});
