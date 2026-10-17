"""
Database schema models and table definitions for SafeGrid.
Owner: Person 4 (Database & Offline System)

Updated 2026-10-07: Aligned with agreed Hazard model fields from Person 1.
Fields updated:
  - raw_magnitude → magnitude
  - probability (new): rainfall/weather probability score
  - raw_values → specific_data: source-specific JSON blob

Updated 2026-10-17: Added the standing regional risk grid table (`grid_cells`).
A grid cell is NOT a hazard event — it has no `hazard_id` and is deliberately kept
out of `risk_results`, because `risk_results.affected_area` is NOT NULL and keyed by
`hazard_id` (see docs/RISK_MODEL.md § 4.1). `generated_at` is stored per cell so the
API can derive a dynamic `is_live` (see docs/OFFLINE.md).
"""

# Schema for raw provider data records (ingest from Person 1)
DATA_RECORDS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS data_records (
    id TEXT PRIMARY KEY,
    data_type TEXT NOT NULL,
    source TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    magnitude REAL,
    probability REAL,
    specific_data TEXT DEFAULT '{}',
    created_at TEXT NOT NULL
);
"""

# Schema for hazard events (identified from data records or explicitly reported)
HAZARDS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS hazards (
    id TEXT PRIMARY KEY,
    hazard_type TEXT NOT NULL,
    source TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    magnitude REAL,
    probability REAL,
    specific_data TEXT DEFAULT '{}',
    created_at TEXT NOT NULL
);
"""

# Schema for risk calculation results (produced by Person 2)
RISK_RESULTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS risk_results (
    hazard_id TEXT PRIMARY KEY,
    risk_level TEXT NOT NULL,
    severity_score REAL NOT NULL,
    affected_area TEXT NOT NULL,
    notes TEXT,
    calculated_at TEXT NOT NULL,
    FOREIGN KEY (hazard_id) REFERENCES hazards(id) ON DELETE CASCADE
);
"""

# Schema for the standing regional risk grid (scored by Person 2, stored by Person 4).
# One row per grid cell of the last run. A cell is NOT a hazard event: there is no
# hazard_id and no FK to risk_results. `cell_id` is indexed against a fixed global
# anchor, so it stays stable as the region grows (docs/RISK_MODEL.md § 4.1).
GRID_CELLS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS grid_cells (
    cell_id TEXT PRIMARY KEY,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    cell_size REAL NOT NULL,
    risk_level TEXT NOT NULL,
    severity_score REAL NOT NULL,
    precipitation_mm REAL,
    affected_area TEXT,
    computed_at TEXT NOT NULL,
    generated_at TEXT NOT NULL
);
"""

# Indexes for fast querying by timestamp, data type, hazard type, and risk level
INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_data_records_timestamp ON data_records(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_data_records_type ON data_records(data_type);
CREATE INDEX IF NOT EXISTS idx_hazards_timestamp ON hazards(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_hazards_type ON hazards(hazard_type);
CREATE INDEX IF NOT EXISTS idx_risk_level ON risk_results(risk_level);
CREATE INDEX IF NOT EXISTS idx_grid_cells_generated_at ON grid_cells(generated_at);
CREATE INDEX IF NOT EXISTS idx_grid_cells_risk_level ON grid_cells(risk_level);
"""
