"""
Repository functions for SafeGrid persistence.
Owner: Person 4 (Database & Offline System)

This is the ONLY interface Person 1 and other subsystems should call
to save or load data from the database. No raw SQL outside this module.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.db.models import HAZARDS_TABLE_SQL, INDEXES_SQL, RISK_RESULTS_TABLE_SQL
from app.db.session import Database, db


def init_db(database: Database = db) -> None:
    """Creates database tables and indexes if they do not already exist."""
    with database.get_connection() as conn:
        conn.execute(HAZARDS_TABLE_SQL)
        conn.execute(RISK_RESULTS_TABLE_SQL)
        conn.executescript(INDEXES_SQL)


def save_hazard(hazard: Any, database: Database = db) -> dict:
    """
    Saves or updates a normalized Hazard in the database.
    Accepts either a Pydantic Hazard model or a dictionary.
    """
    # Handle Pydantic model or dictionary
    if hasattr(hazard, "model_dump"):
        data = hazard.model_dump()
    elif isinstance(hazard, dict):
        data = hazard.copy()
    else:
        raise ValueError(f"Unsupported hazard type: {type(hazard)}")

    # Extract coordinates from location.coordinates [lon, lat] or lat/lon fields
    if "location" in data and isinstance(data["location"], dict):
        coords = data["location"].get("coordinates", [0.0, 0.0])
        lon, lat = coords[0], coords[1]
    else:
        lat = data.get("latitude", 0.0)
        lon = data.get("longitude", 0.0)

    # Format timestamp
    ts = data.get("timestamp")
    if isinstance(ts, datetime):
        ts_str = ts.isoformat()
    else:
        ts_str = str(ts)

    raw_values_json = json.dumps(data.get("raw_values", {}))
    created_at = datetime.now(timezone.utc).isoformat()

    with database.get_connection() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO hazards (
                id, hazard_type, source, timestamp, latitude, longitude,
                raw_magnitude, raw_values, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            data["id"],
            data.get("hazard_type", "unknown"),
            data.get("source", "unknown"),
            ts_str,
            lat,
            lon,
            data.get("raw_magnitude"),
            raw_values_json,
            created_at
        ))

    return get_hazard(data["id"], database=database)  # type: ignore[return-value]


def get_hazard(hazard_id: str, database: Database = db) -> dict | None:
    """Fetches a single hazard by ID."""
    with database.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM hazards WHERE id = ?;", (hazard_id,))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["raw_values"] = json.loads(res.get("raw_values") or "{}")
        return res


def list_hazards(limit: int = 50, database: Database = db) -> list[dict]:
    """Fetches the latest hazards, sorted from newest to oldest."""
    with database.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM hazards ORDER BY timestamp DESC LIMIT ?;", (limit,))
        rows = cursor.fetchall()
        hazards = []
        for r in rows:
            item = dict(r)
            item["raw_values"] = json.loads(item.get("raw_values") or "{}")
            hazards.append(item)
        return hazards


def save_risk_result(risk: Any, database: Database = db) -> dict:
    """
    Saves or updates a RiskResult produced by Person 2's risk engine.
    Accepts either a Pydantic RiskResult model or a dictionary.
    """
    if hasattr(risk, "model_dump"):
        data = risk.model_dump()
    elif isinstance(risk, dict):
        data = risk.copy()
    else:
        raise ValueError(f"Unsupported risk result type: {type(risk)}")

    calc_at = data.get("calculated_at")
    if isinstance(calc_at, datetime):
        calc_at_str = calc_at.isoformat()
    else:
        calc_at_str = str(calc_at or datetime.now(timezone.utc).isoformat())

    affected_area_json = json.dumps(data.get("affected_area", {}))

    with database.get_connection() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO risk_results (
                hazard_id, risk_level, severity_score, affected_area, notes, calculated_at
            )
            VALUES (?, ?, ?, ?, ?, ?);
        """, (
            data["hazard_id"],
            data["risk_level"],
            data["severity_score"],
            affected_area_json,
            data.get("notes"),
            calc_at_str
        ))

    return get_risk_result(data["hazard_id"], database=database)  # type: ignore[return-value]


def get_risk_result(hazard_id: str, database: Database = db) -> dict | None:
    """Fetches risk classification details for a hazard ID."""
    with database.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM risk_results WHERE hazard_id = ?;", (hazard_id,))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["affected_area"] = json.loads(res.get("affected_area") or "{}")
        return res


def list_hazards_with_risk(limit: int = 50, database: Database = db) -> list[dict]:
    """
    Fetches hazards joined with their calculated risk results.
    Ideal for feeding Person 3's map with 🔴 🟡 🟢 GeoJSON data.
    """
    with database.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                h.id, h.hazard_type, h.source, h.timestamp, h.latitude, h.longitude,
                h.raw_magnitude, h.raw_values,
                r.risk_level, r.severity_score, r.affected_area, r.notes
            FROM hazards h
            LEFT JOIN risk_results r ON h.id = r.hazard_id
            ORDER BY h.timestamp DESC
            LIMIT ?;
        """, (limit,))
        rows = cursor.fetchall()
        results = []
        for r in rows:
            item = dict(r)
            item["raw_values"] = json.loads(item.get("raw_values") or "{}")
            item["affected_area"] = json.loads(item.get("affected_area") or "{}") if item.get("affected_area") else None
            results.append(item)
        return results
