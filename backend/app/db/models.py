"""
Database schema models and table definitions for SafeGrid.
Owner: Person 4 (Database & Offline System)

Defines SQL table structures matching the internal Hazard and RiskResult models.
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
    raw_magnitude REAL,
    raw_values TEXT DEFAULT '{}',
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

# Indexes for fast querying by risk level and timestamp
INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_hazards_timestamp ON hazards(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_risk_level ON risk_results(risk_level);
"""
