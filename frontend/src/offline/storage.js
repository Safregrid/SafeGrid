/**
 * Offline data management.
 *
 * Person 4 implements this module.
 *
 * Stores the last known risk-zone GeoJSON (and when it was saved) in the
 * browser's IndexedDB so the map can still render something when the network
 * is unavailable. Cached data is never presented as live data.
 */

const DB_NAME = "safegrid-offline";
const DB_VERSION = 1;
const STORE_NAME = "snapshots";
const RISK_ZONES_KEY = "risk-zones";
const HAZARDS_KEY = "hazards";

export const RISK_ZONES_STORE_KEY = RISK_ZONES_KEY;
export const HAZARDS_STORE_KEY = HAZARDS_KEY;

function hasIndexedDB() {
  return typeof indexedDB !== "undefined" && indexedDB !== null;
}

function openDatabase() {
  return new Promise((resolve, reject) => {
    if (!hasIndexedDB()) {
      reject(new Error("IndexedDB is not available in this environment"));
      return;
    }

    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = () => {
      const database = request.result;
      if (!database.objectStoreNames.contains(STORE_NAME)) {
        database.createObjectStore(STORE_NAME, { keyPath: "key" });
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () =>
      reject(request.error ?? new Error("Failed to open offline storage"));
  });
}

function readRecord(database, key) {
  return new Promise((resolve, reject) => {
    const request = database
      .transaction(STORE_NAME, "readonly")
      .objectStore(STORE_NAME)
      .get(key);

    request.onsuccess = () => resolve(request.result ?? null);
    request.onerror = () =>
      reject(request.error ?? new Error("Failed to read offline data"));
  });
}

function deleteRecord(database, key) {
  return new Promise((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, "readwrite");
    transaction.objectStore(STORE_NAME).delete(key);
    transaction.oncomplete = () => resolve();
    transaction.onerror = () =>
      reject(transaction.error ?? new Error("Failed to clear offline data"));
  });
}

function writeRecord(database, record) {
  return new Promise((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, "readwrite");
    transaction.objectStore(STORE_NAME).put(record);
    transaction.oncomplete = () => resolve();
    transaction.onerror = () =>
      reject(transaction.error ?? new Error("Failed to write offline data"));
    transaction.onabort = () =>
      reject(transaction.error ?? new Error("Offline write aborted"));
  });
}

function normalizeTimestamp(value) {
  if (value instanceof Date && !Number.isNaN(value.getTime())) {
    return value.toISOString();
  }
  if (typeof value === "string" && value.length > 0) {
    const parsed = new Date(value);
    if (!Number.isNaN(parsed.getTime())) {
      return parsed.toISOString();
    }
  }
  return new Date().toISOString();
}

function isPlainObject(value) {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value)
  );
}

async function withDatabase(handler) {
  const database = await openDatabase();
  try {
    return await handler(database);
  } finally {
    database.close();
  }
}

export async function saveRiskZones(geojson, savedAt = new Date(), isLive = false) {
  if (!isPlainObject(geojson)) {
    throw new TypeError("saveRiskZones expects a GeoJSON object");
  }

  const record = {
    key: RISK_ZONES_KEY,
    geojson,
    savedAt: normalizeTimestamp(savedAt),
    isLive: Boolean(isLive),
  };

  await withDatabase((database) => writeRecord(database, record));
}

export async function getLastKnownRiskZones() {
  if (!hasIndexedDB()) {
    return null;
  }
  try {
    const record = await withDatabase((database) => readRecord(database, RISK_ZONES_KEY));
    if (!record || !isPlainObject(record.geojson)) {
      return null;
    }
    return record.geojson;
  } catch {
    return null;
  }
}

export async function getDataAge() {
  const empty = { timestamp: null, isLive: false };
  if (!hasIndexedDB()) {
    return empty;
  }
  try {
    const record = await withDatabase((database) => readRecord(database, RISK_ZONES_KEY));
    if (!record || typeof record.savedAt !== "string") {
      return empty;
    }
    const timestamp = new Date(record.savedAt);
    if (Number.isNaN(timestamp.getTime())) {
      return empty;
    }
    return { timestamp, isLive: Boolean(record.isLive) };
  } catch {
    return empty;
  }
}

export async function saveHazards(payload, savedAt = new Date(), isLive = false) {
  if (!isPlainObject(payload) || !Array.isArray(payload.hazards)) {
    throw new TypeError("saveHazards expects a payload with a hazards array");
  }

  const record = {
    key: HAZARDS_KEY,
    payload,
    savedAt: normalizeTimestamp(savedAt),
    isLive: Boolean(isLive),
  };

  await withDatabase((database) => writeRecord(database, record));
}

export async function getLastKnownHazards() {
  if (!hasIndexedDB()) {
    return null;
  }
  try {
    const record = await withDatabase((database) => readRecord(database, HAZARDS_KEY));
    if (!record || !isPlainObject(record.payload)) {
      return null;
    }
    return record.payload;
  } catch {
    return null;
  }
}

export async function getHazardsAge() {
  const empty = { timestamp: null, isLive: false };
  if (!hasIndexedDB()) {
    return empty;
  }
  try {
    const record = await withDatabase((database) => readRecord(database, HAZARDS_KEY));
    if (!record || typeof record.savedAt !== "string") {
      return empty;
    }
    const timestamp = new Date(record.savedAt);
    if (Number.isNaN(timestamp.getTime())) {
      return empty;
    }
    return { timestamp, isLive: Boolean(record.isLive) };
  } catch {
    return empty;
  }
}

export async function clearHazards() {
  if (!hasIndexedDB()) {
    return;
  }
  await withDatabase((database) => deleteRecord(database, HAZARDS_KEY));
}

export async function clearRiskZones() {
  if (!hasIndexedDB()) {
    return;
  }
  await withDatabase((database) => deleteRecord(database, RISK_ZONES_KEY));
}
