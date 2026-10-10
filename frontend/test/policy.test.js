import test from "node:test";
import assert from "node:assert/strict";

import {
  isRiskZonesRequest,
  markAsCached,
  isStale,
  RISK_ZONES_PATH,
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
