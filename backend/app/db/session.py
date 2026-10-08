"""
Database session and connection management for SafeGrid.
Owner: Person 4 (Database & Offline System)

Manages connections to the SQLite database.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

# By default, store safegrid.db in the backend root or project directory
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "safegrid.db"


class Database:
    """Encapsulates SQLite connection lifecycle and configuration."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = str(db_path)
        self._memory_conn: sqlite3.Connection | None = None
        if self.db_path == ":memory:":
            # Keep one shared connection alive for in-memory databases
            self._memory_conn = sqlite3.connect(":memory:")
            self._memory_conn.row_factory = sqlite3.Row
            self._memory_conn.execute("PRAGMA foreign_keys = ON;")

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Yields an open SQLite connection with Row factory enabled.
        Automatically commits or rolls back transactions, and closes connection when done.
        """
        if self._memory_conn is not None:
            try:
                yield self._memory_conn
                self._memory_conn.commit()
            except Exception:
                self._memory_conn.rollback()
                raise
            return

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def close(self) -> None:
        """Closes any persistent memory connections."""
        if self._memory_conn is not None:
            self._memory_conn.close()
            self._memory_conn = None


# Default database instance
db = Database()
