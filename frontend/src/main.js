/**
 * SafeGrid frontend entry point.
 *
 * Person 3 owns this file.
 *
 * Initial goal: given valid GeoJSON from the backend, render risk zones on the map.
 * Do not build UI polish before the data pipeline works.
 */

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

console.log("SafeGrid frontend initializing...");
