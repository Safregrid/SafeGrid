"""
SafeGrid - Database Prototype (Part A)
Owner: Person 4 (Database & Offline System)

Description:
This script uses Python's built-in SQLite database to:
1. Create a database file ('safegrid.db') and a 'hazards' table.
2. Provide a function to save a hazard (mock or real).
3. Provide a function to read back all saved hazards.
"""

import sqlite3
from datetime import datetime, timezone

# The database file will be created in the current directory
DB_NAME = "safegrid.db"


def get_connection():
    """Establishes and returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    # Enable accessing columns by name (like a dictionary)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Step 1: Initializes the database and creates the 'hazards' table
    if it does not already exist.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hazards (
                id TEXT PRIMARY KEY,
                hazard_type TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                magnitude REAL,
                risk_level TEXT NOT NULL,
                reason TEXT,
                event_time TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)
        conn.commit()
    print("✅ Database initialized! Table 'hazards' is ready.")


def save_hazard(hazard: dict):
    """
    Step 2: Saves a hazard dictionary into the 'hazards' table.
    Uses INSERT OR REPLACE to update existing records if the same ID arrives again.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO hazards (
                id, hazard_type, latitude, longitude, magnitude,
                risk_level, reason, event_time, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            hazard["id"],
            hazard["hazard_type"],
            hazard["latitude"],
            hazard["longitude"],
            hazard.get("magnitude"),
            hazard["risk_level"],
            hazard.get("reason", "No reason provided"),
            hazard["event_time"],
            datetime.now(timezone.utc).isoformat()
        ))
        conn.commit()
    print(f"💾 Saved hazard to database: {hazard['id']} ({hazard['risk_level']})")


def get_all_hazards():
    """
    Step 3: Fetches all saved hazards from the database,
    ordered from newest to oldest.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM hazards ORDER BY created_at DESC;")
        rows = cursor.fetchall()
        # Convert sqlite3.Row objects into standard Python dictionaries
        return [dict(row) for row in rows]


# -------------------------------------------------------------
# Test run: Testing with fake (mock) data
# -------------------------------------------------------------
if __name__ == "__main__":
    print("--- SafeGrid Database Prototype Test ---\n")

    # 1. Initialize DB
    init_db()

    # 2. Create some sample fake disaster data (Mocks)
    sample_hazard_1 = {
        "id": "eq-sf-2026-001",
        "hazard_type": "earthquake",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "magnitude": 6.7,
        "risk_level": "HIGH",
        "reason": "Magnitude > 6.0 near populated area",
        "event_time": "2026-10-06T12:30:00Z"
    }

    sample_hazard_2 = {
        "id": "eq-la-2026-002",
        "hazard_type": "earthquake",
        "latitude": 34.0522,
        "longitude": -118.2437,
        "magnitude": 4.2,
        "risk_level": "MODERATE",
        "reason": "Moderate shaking detected within 50km radius",
        "event_time": "2026-10-06T14:15:00Z"
    }

    # 3. Save mock hazards to the database
    print("\nSaving test data...")
    save_hazard(sample_hazard_1)
    save_hazard(sample_hazard_2)

    # 4. Read back the data to verify it works
    print("\nReading all hazards from the database:")
    saved_records = get_all_hazards()
    for idx, item in enumerate(saved_records, start=1):
        print(f"\n[{idx}] Disaster ID: {item['id']}")
        print(f"    Type:        {item['hazard_type']}")
        print(f"    Magnitude:   {item['magnitude']}")
        print(f"    Risk Level:  {item['risk_level']}")
        print(f"    Reason:      {item['reason']}")
        print(f"    Coordinates: ({item['latitude']}, {item['longitude']})")
        print(f"    Event Time:  {item['event_time']}")

    print("\n🎉 Part A test completed successfully!")
