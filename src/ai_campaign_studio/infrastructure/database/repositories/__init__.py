"""SQLite repository adapters (A5).

Concrete ``sqlite3`` implementations of the ``ports.repositories`` protocol
interfaces. Built on the P0 connection/migration foundation; callers pass a
``sqlite3.Connection`` (typically from ``SqliteUnitOfWork``).
"""

from .sqlite_brand_repository import SqliteBrandRepository
from .sqlite_fact_repository import SqliteFactRepository

__all__ = ["SqliteBrandRepository", "SqliteFactRepository"]
