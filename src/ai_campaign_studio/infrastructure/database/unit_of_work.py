"""Unit of Work / transaction boundary (P0.18)."""

from __future__ import annotations

import sqlite3
from typing import Literal


class SqliteUnitOfWork:
    """Explicit-commit-otherwise-rollback transaction boundary.

    ``with uow: ... uow.commit()`` commits. Any other exit (an exception, or
    a plain exit without ``commit()``) rolls back. No Brand/Campaign/Content
    repositories live here in P0 — those arrive with the domain.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._committed = False

    @property
    def connection(self) -> sqlite3.Connection:
        """The underlying connection (for repository adapters in later phases)."""
        return self._connection

    def commit(self) -> None:
        self._connection.execute("COMMIT")
        self._committed = True

    def __enter__(self) -> SqliteUnitOfWork:
        self._committed = False
        self._connection.execute("BEGIN")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> Literal[False]:
        if not self._committed:
            self._connection.execute("ROLLBACK")
        return False
