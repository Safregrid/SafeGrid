import test from "node:test";
import assert from "node:assert/strict";

import {
  isRiskZonesRequest,
  markAsCached,
  isStale,
  RISK_ZONES_PATH,
  isHazardsRequest,
  markHazardsCached,
  HAZARDS_PATH,
  STALE_AFTER_MS,
} from "../src/offline/policy.js";

test("targets the risk-zones endpoint", () => {
  assert.equal(RISK_ZONES_PATH, "/api/risk-zones");
});

test("recognises a plain GET to /api/risk-zones", () => {
  assert.equal(isRiskZonesRequest("/api/risk-zones"), true);
});

test("recognises an absolute URL to /api/risk-zones", () => {
  assert.equal(isRiskZonesRequest("https://safegrid.example/api/risk-zones"), true);
});

test("ignores the query string", () => {
  assert.equal(isRiskZonesRequest("/api/risk-zones?limit=10"), true);
});

test("rejects non-GET methods", () => {
  assert.equal(isRiskZonesRequest("/api/risk-zones", "POST"), false);
  assert.equal(isRiskZonesRequest("/api/risk-zones", "DELETE"), false);
});

test("rejects other endpoints", () => {
  assert.equal(isRiskZonesRequest("/api/hazards"), false);
  assert.equal(isRiskZonesRequest("/health"), false);
});

test("rejects malformed input without throwing", () => {
  assert.equal(isRiskZonesRequest("http://[::bad"), false);
});

test("markAsCached flips is_live to false and stamps cached_at", () => {
  const marked = markAsCached({ type: "FeatureCollection", features: [] }, "2026-01-01T00:00:00.000Z");
  assert.equal(marked.is_live, false);
  assert.equal(marked.cached_at, "2026-01-01T00:00:00.000Z");
  assert.equal(marked.type, "FeatureCollection");
});

test("markAsCached does not mutate its input", () => {
  const input = { type: "FeatureCollection", features: [], is_live: true };
  markAsCached(input, "2026-01-01T00:00:00.000Z");
  assert.equal(input.is_live, true);
  assert.equal("cached_at" in input, false);
});

test("markAsCached tolerates a missing timestamp", () => {
  const marked = markAsCached({ type: "FeatureCollection" });
  assert.equal(marked.cached_at, null);
});

test("markAsCached passes through non-object values untouched", () => {
  assert.equal(markAsCached(null), null);
  assert.deepEqual(markAsCached([1, 2]), [1, 2]);
});

test("isStale reports fresh data as not stale", () => {
  const now = new Date("2026-01-01T12:00:00.000Z");
  assert.equal(isStale("2026-01-01T11:59:00.000Z", now, 60 * 60 * 1000), false);
});

test("isStale reports old data as stale", () => {
  const now = new Date("2026-01-02T12:00:00.000Z");
  assert.equal(isStale("2026-01-01T12:00:00.000Z", now, 60 * 60 * 1000), true);
});

test("isStale treats an unknown timestamp as stale", () => {
  const now = new Date("2026-01-01T12:00:00.000Z");
  assert.equal(isStale("garbage", now, 1000), true);
  assert.equal(isStale(null, now, 1000), true);
});

test("documents a 3 hour staleness default", () => {
  assert.equal(STALE_AFTER_MS, 3 * 60 * 60 * 1000);
  const now = new Date("2026-01-01T12:00:00.000Z");
  assert.equal(isStale("2026-01-01T10:00:00.000Z", now, STALE_AFTER_MS), false);
  assert.equal(isStale("2026-01-01T08:00:00.000Z", now, STALE_AFTER_MS), true);
});

test("targets the hazards endpoint", () => {
  assert.equal(HAZARDS_PATH, "/api/hazards");
});

test("recognises a plain GET to /api/hazards", () => {
  assert.equal(isHazardsRequest("/api/hazards"), true);
});

test("recognises an absolute URL to /api/hazards", () => {
  assert.equal(isHazardsRequest("https://safegrid.example/api/hazards?limit=5"), true);
});

test("isHazardsRequest rejects non-GET methods and other endpoints", () => {
  assert.equal(isHazardsRequest("/api/hazards", "POST"), false);
  assert.equal(isHazardsRequest("/api/risk-zones"), false);
  assert.equal(isHazardsRequest("/health"), false);
});

test("isHazardsRequest rejects malformed input without throwing", () => {
  assert.equal(isHazardsRequest("http://[::bad"), false);
});

test("markHazardsCached flips payload and every hazard to cached", () => {
  const marked = markHazardsCached(
    {
      is_live: true,
      hazards: [
        { id: "eq-1", is_live: true },
        { id: "eq-2", is_live: true },
      ],
    },
    "2026-01-01T00:00:00.000Z"
  );
  assert.equal(marked.is_live, false);
  assert.equal(marked.cached_at, "2026-01-01T00:00:00.000Z");
  assert.equal(marked.hazards.length, 2);
  marked.hazards.forEach((hazard) => {
    assert.equal(hazard.is_live, false);
    assert.equal(hazard.cached_at, "2026-01-01T00:00:00.000Z");
  });
});

test("markHazardsCached does not mutate its input", () => {
  const input = { is_live: true, hazards: [{ id: "h1", is_live: true }] };
  markHazardsCached(input, "2026-01-01T00:00:00.000Z");
  assert.equal(input.is_live, true);
  assert.equal(input.hazards[0].is_live, true);
  assert.equal("cached_at" in input.hazards[0], false);
});

test("markHazardsCached defaults an absent hazards array to empty", () => {
  const marked = markHazardsCached({ is_live: true }, "2026-01-01T00:00:00.000Z");
  assert.deepEqual(marked.hazards, []);
  assert.equal(marked.is_live, false);
});

test("markHazardsCached passes through non-object values untouched", () => {
  assert.equal(markHazardsCached(null), null);
  assert.deepEqual(markHazardsCached([1, 2]), [1, 2]);
});
