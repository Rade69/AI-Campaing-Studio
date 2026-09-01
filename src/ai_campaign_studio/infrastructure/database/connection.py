"""SQLite connection factory (P0.16)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

_BUSY_TIMEOUT_MS = 5000


def create_connection(database_path: str | Path) -> sqlite3.Connection:
    """Open a configured sqlite3 connection (no global singleton).

    Every call returns a fresh connection with ``row_factory``,
    ``foreign_keys`` and ``busy_timeout`` set. ``isolation_level=None`` puts
    sqlite3 in autocommit mode so that callers (migration runner, unit of
    work) control transactions explicitly with ``BEGIN``/``COMMIT``/
    ``ROLLBACK``. The caller owns the returned connection and is responsible
    for closing it.
    """
    connection = sqlite3.connect(str(database_path))
    connection.isolation_level = None
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(f"PRAGMA busy_timeout = {_BUSY_TIMEOUT_MS}")
    return connection
