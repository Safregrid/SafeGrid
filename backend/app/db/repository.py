"""
Repository functions for SafeGrid persistence.
Owner: Person 4 (Database & Offline System)

This is the ONLY interface Person 1 and other subsystems should call
to save or load data from the database. No raw SQL outside this module.

Updated 2026-10-07: Aligned with agreed Hazard model (magnitude, probability,
specific_data) replacing old raw_magnitude / raw_values fields.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.db.models import (
    DATA_RECORDS_TABLE_SQL,
    GRID_CELLS_TABLE_SQL,
    HAZARDS_TABLE_SQL,
    INDEXES_SQL,
    RISK_RESULTS_TABLE_SQL,
)
from app.db.session import Database, db


# Age after which a stored grid cell's rating is considered stale (docs/OFFLINE.md).
# 3 hours matches the default regional-grid refresh cadence; a caller may pass a
# shorter value for an active-hazard window. This is a policy default, not a fact
# about the data — always expose `generated_at` alongside `is_live`.
GRID_CELL_TTL_SECONDS = 3 * 60 * 60


def init_db(database: Database = db) -> None:
    """Creates database tables and indexes if they do not already exist."""
    with database.get_connection() as conn:
        conn.execute(DATA_RECORDS_TABLE_SQL)
        conn.execute(HAZARDS_TABLE_SQL)
        conn.execute(RISK_RESULTS_TABLE_SQL)
        conn.execute(GRID_CELLS_TABLE_SQL)
        conn.executescript(INDEXES_SQL)


def save_data_record(record: Any, database: Database = db) -> dict:
    """
    Saves or updates a normalized DataRecord in the database.

    Accepts either a Pydantic DataRecord model or a plain dict.
    """
    if hasattr(record, "model_dump"):
        data = record.model_dump()
    elif isinstance(record, dict):
        data = record.copy()
    else:
        raise ValueError(f"Unsupported record type: {type(record)}")

    if "location" in data and isinstance(data["location"], dict):
        coords = data["location"].get("coordinates", [0.0, 0.0])
        lon, lat = coords[0], coords[1]
    else:
        lat = data.get("latitude", 0.0)
        lon = data.get("longitude", 0.0)

    ts = data.get("timestamp")
    ts_str = ts.isoformat() if isinstance(ts, datetime) else str(ts)
    specific_data_json = json.dumps(data.get("specific_data", {}))
    created_at = datetime.now(timezone.utc).isoformat()

    with database.get_connection() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO data_records (
                id, data_type, source, timestamp, latitude, longitude,
                magnitude, probability, specific_data, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            data["id"],
            data.get("data_type", "unknown"),
            data.get("source", "unknown"),
            ts_str,
            lat,
            lon,
            data.get("magnitude"),
            data.get("probability"),
            specific_data_json,
            created_at
        ))

    return get_data_record(data["id"], database=database)  # type: ignore[return-value]


def get_data_record(record_id: str, database: Database = db) -> dict | None:
    """Fetches a single data record by ID. Returns None if not found."""
    with database.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM data_records WHERE id = ?;", (record_id,))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["specific_data"] = json.loads(res.get("specific_data") or "{}")
        return res


def list_data_records(limit: int = 50, database: Database = db) -> list[dict]:
    """Fetches the latest provider data records, sorted from newest to oldest."""
    with database.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM data_records ORDER BY timestamp DESC LIMIT ?;", (limit,)
        )
        results = []
        for row in cursor.fetchall():
            item = dict(row)
            item["specific_data"] = json.loads(item.get("specific_data") or "{}")
            results.append(item)
        return results


def save_hazard(hazard: Any, database: Database = db) -> dict:
    """
    Saves or updates a normalized Hazard in the database.

    Accepts either a Pydantic Hazard model (from Person 1) or a plain dict.

    Generic by design: works for earthquakes, rainfall, storms, or any
    future hazard type — specific data goes into the 'specific_data' JSON column.
    """
    # Accept Pydantic model or plain dict
    if hasattr(hazard, "model_dump"):
        data = hazard.model_dump()
    elif isinstance(hazard, dict):
        data = hazard.copy()
    else:
        raise ValueError(f"Unsupported hazard type: {type(hazard)}")

    # Extract [longitude, latitude] from GeoPoint location field
    if "location" in data and isinstance(data["location"], dict):
        coords = data["location"].get("coordinates", [0.0, 0.0])
        lon, lat = coords[0], coords[1]
    else:
        # Fallback for plain dict input
        lat = data.get("latitude", 0.0)
        lon = data.get("longitude", 0.0)

    # Normalize timestamp to ISO string
    ts = data.get("timestamp")
    ts_str = ts.isoformat() if isinstance(ts, datetime) else str(ts)

    # Serialize specific_data dict to JSON string for storage
    specific_data_json = json.dumps(data.get("specific_data", {}))

    created_at = datetime.now(timezone.utc).isoformat()

    with database.get_connection() as conn:
        # Upsert (ON CONFLICT DO UPDATE), NOT INSERT OR REPLACE:
        # REPLACE deletes the old hazards row, and ON DELETE CASCADE would
        # delete the linked risk_results row. Updating in place keeps the rating.
        conn.execute("""
            INSERT INTO hazards (
                id, hazard_type, source, timestamp, latitude, longitude,
                magnitude, probability, specific_data, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                hazard_type = excluded.hazard_type,
                source = excluded.source,
                timestamp = excluded.timestamp,
                latitude = excluded.latitude,
                longitude = excluded.longitude,
                magnitude = excluded.magnitude,
                probability = excluded.probability,
                specific_data = excluded.specific_data;
        """, (
            data["id"],
            data.get("hazard_type", "unknown"),
            data.get("source", "unknown"),
            ts_str,
            lat,
            lon,
            data.get("magnitude"),        # earthquake magnitude or storm strength
            data.get("probability"),      # rainfall probability 0 to 100%
            specific_data_json,           # source-specific JSON extras
            created_at
        ))

    return get_hazard(data["id"], database=database)  # type: ignore[return-value]


def get_hazard(hazard_id: str, database: Database = db) -> dict | None:
    """Fetches a single hazard by ID. Returns None if not found."""
    with database.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM hazards WHERE id = ?;", (hazard_id,))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["specific_data"] = json.loads(res.get("specific_data") or "{}")
        return res


def list_hazards(limit: int = 50, database: Database = db) -> list[dict]:
    """
    Fetches the latest hazards, sorted from newest to oldest.
    Works for all hazard types (earthquake, rainfall, etc.)
    """
    with database.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM hazards ORDER BY timestamp DESC LIMIT ?;", (limit,)
        )
        results = []
        for row in cursor.fetchall():
            item = dict(row)
            item["specific_data"] = json.loads(item.get("specific_data") or "{}")
            results.append(item)
        return results


def save_risk_result(risk: Any, database: Database = db) -> dict:
    """
    Saves or updates a RiskResult produced by Person 2's risk engine.
    Accepts either a Pydantic RiskResult model or a plain dict.
    """
    if hasattr(risk, "model_dump"):
        data = risk.model_dump()
    elif isinstance(risk, dict):
        data = risk.copy()
    else:
        raise ValueError(f"Unsupported risk result type: {type(risk)}")

    calc_at = data.get("calculated_at")
    calc_at_str = (
        calc_at.isoformat()
        if isinstance(calc_at, datetime)
        else str(calc_at or datetime.now(timezone.utc).isoformat())
    )

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
    """Fetches risk classification details for a hazard ID. Returns None if not found."""
    with database.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM risk_results WHERE hazard_id = ?;", (hazard_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["affected_area"] = json.loads(res.get("affected_area") or "{}")
        return res


def list_hazards_with_risk(limit: int = 50, database: Database = db) -> list[dict]:
    """
    Fetches hazards joined with their calculated risk results.

    This is the primary data feed for Person 3's map UI.
    Returns everything the map needs to paint 🔴 🟡 🟢 GeoJSON zones:
    - id, hazard_type, source, timestamp
    - latitude, longitude (for map marker placement)
    - magnitude, probability (for tooltip/detail display)
    - risk_level (HIGH / MODERATE / LOW / None)
    - severity_score
    - affected_area (GeoJSON Polygon for zone shading)
    - notes (threshold justification from Person 2)
    - calculated_at (when Person 2's engine rated the hazard; None if unrated)
    """
    with database.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                h.id,
                h.hazard_type,
                h.source,
                h.timestamp,
                h.latitude,
                h.longitude,
                h.magnitude,
                h.probability,
                h.specific_data,
                r.risk_level,
                r.severity_score,
                r.affected_area,
                r.notes,
                r.calculated_at
            FROM hazards h
            LEFT JOIN risk_results r ON h.id = r.hazard_id
            ORDER BY h.timestamp DESC
            LIMIT ?;
        """, (limit,))

        results = []
        for row in cursor.fetchall():
            item = dict(row)
            item["specific_data"] = json.loads(item.get("specific_data") or "{}")
            item["affected_area"] = (
                json.loads(item["affected_area"])
                if item.get("affected_area")
                else None
            )
            results.append(item)
        return results


# ---------------------------------------------------------------------------
# Regional risk grid (Person 4 storage; scored by Person 2, served by Person 1)
#
# A grid cell is NOT a hazard event: it is stored on its own so it never
# collides with the `hazard_id`-keyed `risk_results` contract. See
# docs/RISK_MODEL.md § 4.1 and docs/OFFLINE.md.
# ---------------------------------------------------------------------------

_GRID_CELL_REQUIRED = (
    "cell_id",
    "latitude",
    "longitude",
    "cell_size",
    "risk_level",
    "severity_score",
)

_GRID_CELL_UPSERT_SQL = """
    INSERT INTO grid_cells (
        cell_id, latitude, longitude, cell_size, risk_level,
        severity_score, precipitation_mm, affected_area,
        computed_at, generated_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(cell_id) DO UPDATE SET
        latitude = excluded.latitude,
        longitude = excluded.longitude,
        cell_size = excluded.cell_size,
        risk_level = excluded.risk_level,
        severity_score = excluded.severity_score,
        precipitation_mm = excluded.precipitation_mm,
        affected_area = excluded.affected_area,
        computed_at = excluded.computed_at,
        generated_at = excluded.generated_at;
"""


def _normalize_grid_cell(cell: Any) -> dict:
    """Accepts a plain dict, a Pydantic model, or any object exposing the fields."""
    if hasattr(cell, "model_dump"):
        data = dict(cell.model_dump())
    elif isinstance(cell, dict):
        data = dict(cell)
    elif hasattr(cell, "__dict__"):
        data = dict(vars(cell))
    else:
        raise ValueError(f"Unsupported grid cell type: {type(cell)}")
    return data


def _as_iso(value: Any) -> str | None:
    """Best-effort ISO-8601 conversion; returns None when nothing usable is given."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _grid_cell_row(data: dict, generated_at: str) -> tuple:
    """Validates one cell dict and flattens it into a row tuple for SQLite."""
    for field in _GRID_CELL_REQUIRED:
        if data.get(field) is None:
            raise ValueError(f"grid cell is missing required field: {field}")

    computed_at = _as_iso(data.get("computed_at")) or generated_at

    affected_area = data.get("affected_area")
    if isinstance(affected_area, (dict, list)):
        affected_area = json.dumps(affected_area)

    return (
        data["cell_id"],
        data["latitude"],
        data["longitude"],
        data["cell_size"],
        data["risk_level"],
        data["severity_score"],
        data.get("precipitation_mm"),
        affected_area,
        computed_at,
        generated_at,
    )


def save_grid_cell(cell: Any, database: Database = db) -> dict:
    """
    Saves or updates a single regional-grid cell rating.

    Accepts a plain dict or any object exposing the same fields. Required keys:
    `cell_id`, `latitude`, `longitude`, `cell_size`, `risk_level`, `severity_score`.
    `computed_at` defaults to now; `generated_at` defaults to `computed_at`.
    """
    data = _normalize_grid_cell(cell)
    generated_at = (
        _as_iso(data.get("generated_at"))
        or _as_iso(data.get("computed_at"))
        or datetime.now(timezone.utc).isoformat()
    )

    with database.get_connection() as conn:
        conn.execute(_GRID_CELL_UPSERT_SQL, _grid_cell_row(data, generated_at))

    return get_grid_cell(data["cell_id"], database=database)  # type: ignore[return-value]


def save_grid_snapshot(
    cells: Any, generated_at: Any = None, database: Database = db
) -> int:
    """
    Stores one immutable snapshot of the regional grid: upserts every cell under
    the same `generated_at` stamp in a single transaction. Returns how many cells
    were written. `cells` is any iterable of dicts / objects.
    """
    stamp = _as_iso(generated_at) or datetime.now(timezone.utc).isoformat()
    rows = [_grid_cell_row(_normalize_grid_cell(cell), stamp) for cell in cells]
    if not rows:
        return 0
    with database.get_connection() as conn:
        conn.executemany(_GRID_CELL_UPSERT_SQL, rows)
    return len(rows)


def get_grid_cell(cell_id: str, database: Database = db) -> dict | None:
    """Fetches one grid cell by its stable cell_id. Returns None if not found."""
    with database.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM grid_cells WHERE cell_id = ?;", (cell_id,))
        row = cursor.fetchone()
        if not row:
            return None
        item = dict(row)
        item["affected_area"] = (
            json.loads(item["affected_area"]) if item.get("affected_area") else None
        )
        return item


def list_grid_cells(limit: int = 2000, database: Database = db) -> list[dict]:
    """Fetches the most severe grid cells from the latest available snapshot."""
    with database.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM grid_cells ORDER BY severity_score DESC LIMIT ?;", (limit,)
        )
        results = []
        for row in cursor.fetchall():
            item = dict(row)
            item["affected_area"] = (
                json.loads(item["affected_area"]) if item.get("affected_area") else None
            )
            results.append(item)
        return results


def clear_grid_cells(database: Database = db) -> None:
    """Removes every stored grid cell (e.g. before a full-region re-run)."""
    with database.get_connection() as conn:
        conn.execute("DELETE FROM grid_cells;")


def is_grid_cell_live(
    cell: dict | None,
    ttl_seconds: int = GRID_CELL_TTL_SECONDS,
    now: datetime | None = None,
) -> bool:
    """
    Freshness policy for a stored cell: True when its `generated_at` is within
    `ttl_seconds` of `now`. Missing or unparseable timestamps are NOT live.

    This is the backend counterpart of the frontend `isStale()` check; both read
    the same `generated_at` so a cell is described consistently on both sides.
    """
    if not cell:
        return False
    stamp = cell.get("generated_at") or cell.get("computed_at")
    if not stamp:
        return False
    try:
        generated = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except ValueError:
        return False
    if generated.tzinfo is None:
        generated = generated.replace(tzinfo=timezone.utc)
    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    return (reference - generated).total_seconds() <= ttl_seconds
