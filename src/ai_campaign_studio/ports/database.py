"""Database connection port (interface implemented by adapters)."""

from typing import Protocol


class DatabaseConnectionPort(Protocol):
    """Framework-neutral database connection lifecycle contract.

    The concrete sqlite3 adapter lives in
    ``ai_campaign_studio.infrastructure.database.connection``. This port is
    intentionally minimal in P0: it exposes the transaction/connection
    lifecycle without leaking driver details, and declares no
    Brand/Campaign/Content repository ports (those arrive with the domain).
    """

    def commit(self) -> None: ...

    def rollback(self) -> None: ...

    def close(self) -> None: ...
