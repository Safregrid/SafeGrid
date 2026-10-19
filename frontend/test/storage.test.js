import test, { beforeEach } from "node:test";
import assert from "node:assert/strict";
import "fake-indexeddb/auto";

import {
  saveRiskZones,
  getLastKnownRiskZones,
  getDataAge,
  clearRiskZones,
  RISK_ZONES_STORE_KEY,
  saveHazards,
  getLastKnownHazards,
  getHazardsAge,
  clearHazards,
  HAZARDS_STORE_KEY,
  saveGridCellRisk,
  getLastKnownGridCellRisk,
  getGridCellRiskAge,
  clearGridCellRisk,
  GRID_CELL_STORE_KEY,
} from "../src/offline/storage.js";

const originalIndexedDB = globalThis.indexedDB;

function sampleZones(level = "HIGH") {
  return {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        properties: { risk_level: level, severity_score: 3 },
        geometry: {
          type: "Polygon",
          coordinates: [
            [
              [7.2, 44.4],
              [7.3, 44.4],
              [7.3, 44.5],
              [7.2, 44.5],
              [7.2, 44.4],
            ],
          ],
        },
      },
    ],
  };
}

function sampleHazards() {
  return {
    is_live: true,
    hazards: [
      {
        id: "rain-001",
        hazard_type: "rainfall",
        latitude: 44.4,
        longitude: 7.2,
        probability: 60,
      },
    ],
  };
}

function sampleGridCell() {
  return {
    cell_id: "0.1:12.9:77.5",
    risk_level: "HIGH",
    severity_score: 8.1,
    affected_area: { type: "Polygon", coordinates: [] },
    computed_at: "2026-05-05T05:05:05.000Z",
    is_live: true,
  };
}

function withoutIndexedDB() {
  globalThis.indexedDB = undefined;
}

function restoreIndexedDB() {
  globalThis.indexedDB = originalIndexedDB;
}

beforeEach(async () => {
  restoreIndexedDB();
  await clearRiskZones();
  await clearHazards();
  await clearGridCellRisk();
});

test("exports a stable store key", () => {
  assert.equal(RISK_ZONES_STORE_KEY, "risk-zones");
});

test("returns null before any data is saved", async () => {
  assert.equal(await getLastKnownRiskZones(), null);
});

test("reports no data age before any data is saved", async () => {
  assert.deepEqual(await getDataAge(), { timestamp: null, isLive: false });
});

test("reads back exactly what was saved", async () => {
  const zones = sampleZones();
  await saveRiskZones(zones);
  assert.deepEqual(await getLastKnownRiskZones(), zones);
});

test("does not mutate the object it is given", async () => {
  const zones = sampleZones();
  const before = JSON.stringify(zones);
  await saveRiskZones(zones, new Date(), true);
  assert.equal(JSON.stringify(zones), before);
  assert.equal("is_live" in zones, false);
  assert.equal("cached_at" in zones, false);
});

test("getDataAge returns a Date instance", async () => {
  await saveRiskZones(sampleZones(), new Date("2026-01-01T00:00:00.000Z"));
  const age = await getDataAge();
  assert.ok(age.timestamp instanceof Date);
});

test("preserves the saved timestamp", async () => {
  const savedAt = new Date("2026-03-15T10:30:00.000Z");
  await saveRiskZones(sampleZones(), savedAt);
  const age = await getDataAge();
  assert.equal(age.timestamp.toISOString(), savedAt.toISOString());
});

test("accepts an ISO string timestamp", async () => {
  const iso = "2026-02-02T02:02:02.000Z";
  await saveRiskZones(sampleZones(), iso);
  const age = await getDataAge();
  assert.equal(age.timestamp.toISOString(), iso);
});

test("falls back to now when the timestamp is unusable", async () => {
  const before = Date.now();
  await saveRiskZones(sampleZones(), "not-a-real-date");
  const after = Date.now();
  const age = await getDataAge();
  assert.ok(age.timestamp instanceof Date);
  assert.ok(age.timestamp.getTime() >= before);
  assert.ok(age.timestamp.getTime() <= after);
});

test("reports isLive true for live data", async () => {
  await saveRiskZones(sampleZones(), new Date(), true);
  const age = await getDataAge();
  assert.equal(age.isLive, true);
});

test("defaults isLive to false", async () => {
  await saveRiskZones(sampleZones());
  const age = await getDataAge();
  assert.equal(age.isLive, false);
});

test("re-saving replaces the previous snapshot", async () => {
  await saveRiskZones(sampleZones("LOW"));
  await saveRiskZones(sampleZones("HIGH"));
  const zones = await getLastKnownRiskZones();
  assert.equal(zones.features[0].properties.risk_level, "HIGH");
  assert.equal(zones.features.length, 1);
});

test("re-saving updates the stored timestamp", async () => {
  await saveRiskZones(sampleZones(), new Date("2026-01-01T00:00:00.000Z"));
  await saveRiskZones(sampleZones(), new Date("2026-02-02T00:00:00.000Z"));
  const age = await getDataAge();
  assert.equal(age.timestamp.toISOString(), "2026-02-02T00:00:00.000Z");
});

test("rejects a null payload", async () => {
  await assert.rejects(() => saveRiskZones(null), TypeError);
});

test("rejects a non-object payload", async () => {
  await assert.rejects(() => saveRiskZones("nope"), TypeError);
});

test("rejects an array payload", async () => {
  await assert.rejects(() => saveRiskZones([]), TypeError);
});

test("clearRiskZones removes the snapshot", async () => {
  await saveRiskZones(sampleZones());
  await clearRiskZones();
  assert.equal(await getLastKnownRiskZones(), null);
  assert.deepEqual(await getDataAge(), { timestamp: null, isLive: false });
});

test("getLastKnownRiskZones returns null without IndexedDB", async () => {
  withoutIndexedDB();
  assert.equal(await getLastKnownRiskZones(), null);
});

test("getDataAge is empty without IndexedDB", async () => {
  withoutIndexedDB();
  assert.deepEqual(await getDataAge(), { timestamp: null, isLive: false });
});

test("saveRiskZones rejects without IndexedDB", async () => {
  withoutIndexedDB();
  await assert.rejects(() => saveRiskZones(sampleZones()), Error);
});

test("clearRiskZones is a no-op without IndexedDB", async () => {
  withoutIndexedDB();
  await assert.doesNotReject(() => clearRiskZones());
});

test("targets the hazards store key", () => {
  assert.equal(HAZARDS_STORE_KEY, "hazards");
});

test("getLastKnownHazards returns null before any data is saved", async () => {
  assert.equal(await getLastKnownHazards(), null);
});

test("getHazardsAge is empty before any data is saved", async () => {
  assert.deepEqual(await getHazardsAge(), { timestamp: null, isLive: false });
});

test("hazards round-trip and preserve payload shape", async () => {
  const payload = sampleHazards();
  await saveHazards(payload);
  assert.deepEqual(await getLastKnownHazards(), payload);
});

test("hazards are stored independently from risk zones", async () => {
  await saveHazards(sampleHazards());
  assert.equal(await getLastKnownRiskZones(), null);
  await saveRiskZones(sampleZones());
  assert.deepEqual(await getLastKnownHazards(), sampleHazards());
});

test("saveHazards does not mutate the object it is given", async () => {
  const payload = sampleHazards();
  const before = JSON.stringify(payload);
  await saveHazards(payload, new Date(), true);
  assert.equal(JSON.stringify(payload), before);
  assert.equal("cached_at" in payload, false);
});

test("saveHazards preserves the saved timestamp and live flag", async () => {
  const savedAt = new Date("2026-04-04T04:04:04.000Z");
  await saveHazards(sampleHazards(), savedAt, true);
  const age = await getHazardsAge();
  assert.equal(age.timestamp.toISOString(), savedAt.toISOString());
  assert.equal(age.isLive, true);
});

test("saveHazards rejects a payload without a hazards array", async () => {
  await assert.rejects(() => saveHazards(null), TypeError);
  await assert.rejects(() => saveHazards({ is_live: true }), TypeError);
  await assert.rejects(() => saveHazards([]), TypeError);
});

test("clearHazards removes the snapshot", async () => {
  await saveHazards(sampleHazards());
  await clearHazards();
  assert.equal(await getLastKnownHazards(), null);
  assert.deepEqual(await getHazardsAge(), { timestamp: null, isLive: false });
});

test("hazards helpers degrade without IndexedDB", async () => {
  withoutIndexedDB();
  assert.equal(await getLastKnownHazards(), null);
  assert.deepEqual(await getHazardsAge(), { timestamp: null, isLive: false });
  await assert.doesNotReject(() => clearHazards());
  await assert.rejects(() => saveHazards(sampleHazards()), Error);
});

test("targets the grid-cell store key", () => {
  assert.equal(GRID_CELL_STORE_KEY, "grid-cell");
});

test("grid-cell lookup returns null before anything is saved", async () => {
  assert.equal(await getLastKnownGridCellRisk(), null);
  assert.deepEqual(await getGridCellRiskAge(), { timestamp: null, isLive: false });
});

test("grid-cell lookup round-trips and preserves shape", async () => {
  const cell = sampleGridCell();
  await saveGridCellRisk(cell);
  assert.deepEqual(await getLastKnownGridCellRisk(), cell);
});

test("grid-cell lookup does not mutate its input", async () => {
  const cell = sampleGridCell();
  const before = JSON.stringify(cell);
  await saveGridCellRisk(cell, new Date(), true);
  assert.equal(JSON.stringify(cell), before);
  assert.equal("cached_at" in cell, false);
});

test("grid-cell lookup preserves timestamp and live flag", async () => {
  const savedAt = new Date("2026-06-06T06:06:06.000Z");
  await saveGridCellRisk(sampleGridCell(), savedAt, true);
  const age = await getGridCellRiskAge();
  assert.equal(age.timestamp.toISOString(), savedAt.toISOString());
  assert.equal(age.isLive, true);
});

test("grid-cell lookup is stored independently from hazards and zones", async () => {
  await saveGridCellRisk(sampleGridCell());
  assert.equal(await getLastKnownHazards(), null);
  assert.equal(await getLastKnownRiskZones(), null);
});

test("saveGridCellRisk rejects non-object payloads", async () => {
  await assert.rejects(() => saveGridCellRisk(null), TypeError);
  await assert.rejects(() => saveGridCellRisk([1, 2]), TypeError);
});

test("clearGridCellRisk removes the snapshot", async () => {
  await saveGridCellRisk(sampleGridCell());
  await clearGridCellRisk();
  assert.equal(await getLastKnownGridCellRisk(), null);
  assert.deepEqual(await getGridCellRiskAge(), { timestamp: null, isLive: false });
});

test("grid-cell helpers degrade without IndexedDB", async () => {
  withoutIndexedDB();
  assert.equal(await getLastKnownGridCellRisk(), null);
  assert.deepEqual(await getGridCellRiskAge(), { timestamp: null, isLive: false });
  await assert.doesNotReject(() => clearGridCellRisk());
  await assert.rejects(() => saveGridCellRisk(sampleGridCell()), Error);
});
