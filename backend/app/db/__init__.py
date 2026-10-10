"""
SafeGrid Database layer.
Owner: Person 4 (Database & Offline System)

Public interface for data persistence:
- init_db: initialize tables and indexes
- save_hazard: persist normalized hazard from Person 1
- get_hazard: retrieve hazard by ID
- list_hazards: retrieve recent hazards
- save_risk_result: persist risk calculation from Person 2
- get_risk_result: retrieve risk result by hazard ID
- list_hazards_with_risk: retrieve hazards joined with risk data for the map
"""

from app.db.repository import (
    get_data_record,
    get_hazard,
    get_risk_result,
    init_db,
    list_data_records,
    list_hazards,
    list_hazards_with_risk,
    save_data_record,
    save_hazard,
    save_risk_result,
)
from app.db.session import Database, db

__all__ = [
    "Database",
    "db",
    "init_db",
    "save_data_record",
    "get_data_record",
    "list_data_records",
    "save_hazard",
    "get_hazard",
    "list_hazards",
    "save_risk_result",
    "get_risk_result",
    "list_hazards_with_risk",
]
