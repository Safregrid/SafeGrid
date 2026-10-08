"""
Database schema models and table definitions for SafeGrid.
Owner: Person 4 (Database & Offline System)

Updated 2026-10-07: Aligned with agreed Hazard model fields from Person 1.
Fields updated:
  - raw_magnitude → magnitude
  - probability (new): rainfall/weather probability score
  - raw_values → specific_data: source-specific JSON blob
"""

# Schema for hazard events (normalized data from Person 1)
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

# Indexes for fast querying by risk level, hazard type, and timestamp
INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_hazards_timestamp ON hazards(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_hazards_type ON hazards(hazard_type);
CREATE INDEX IF NOT EXISTS idx_risk_level ON risk_results(risk_level);
"""
