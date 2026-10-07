/**
 * Offline data management stub.
 *
 * Person 4 implements this module.
 *
 * Responsibilities:
 * - Read/write last-known risk zone data to IndexedDB or Cache Storage
 * - Expose getLastKnownRiskZones() for use by Person 3's map code
 * - Track data staleness (timestamp of last successful fetch)
 */

// TODO (Person 4): implement getLastKnownRiskZones() -> Promise<GeoJSON | null>
// TODO (Person 4): implement saveRiskZones(geojson, timestamp) -> Promise<void>
// TODO (Person 4): implement getDataAge() -> Promise<{ timestamp: Date | null, isLive: boolean }>
