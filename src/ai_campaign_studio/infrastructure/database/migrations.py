"""Migration runner (P0.17).

Owns discovering ``NNNN_name.sql`` files, tracking applied versions in
``schema_migrations``, and applying pending migrations transactionally (no
partial apply, no rollback of a transaction it did not open itself). Does
not define Brand/Campaign/Content schema — only P0 foundation tables.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from ai_campaign_studio.domain.common.errors import MigrationError
from ai_campaign_studio.domain.common.timestamps import utc_now

_SCHEMA_MIGRATIONS_DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT NOT NULL,
    checksum TEXT NOT NULL
)
"""

_FILENAME_RE = re.compile(r"^(?P<version>\d+)_(?P<name>.+)\.sql$")


@dataclass(frozen=True)
class Migration:
    """A discovered migration file with its parsed metadata."""

    version: int
    name: str
    checksum: str
    sql: str


def discover_migrations(migrations_dir: Path) -> list[Migration]:
    """Discover and parse ``NNNN_name.sql`` migration files, sorted by version."""
    migrations: list[Migration] = []
    for path in migrations_dir.glob("*.sql"):
        match = _FILENAME_RE.match(path.name)
        if match is None:
            raise MigrationError(f"unparsable migration filename: {path.name}")
        sql = path.read_text(encoding="utf-8")
        migrations.append(
            Migration(
                version=int(match.group("version")),
                name=match.group("name"),
                checksum=_checksum(sql),
                sql=sql,
            )
        )
    migrations.sort(key=lambda m: m.version)
    return migrations


def run_migrations(
    connection: sqlite3.Connection, migrations_dir: Path
) -> list[int]:
    """Apply pending migrations; return the newly applied versions."""
    _ensure_schema_migrations(connection)
    applied = _read_applied(connection)

    newly_applied: list[int] = []
    for migration in discover_migrations(migrations_dir):
        if migration.version in applied:
            if applied[migration.version] != migration.checksum:
                raise MigrationError(
                    f"checksum mismatch for migration {migration.version} "
                    f"({migration.name})"
                )
            continue
        _apply_migration(connection, migration)
        newly_applied.append(migration.version)
    return newly_applied


def _ensure_schema_migrations(connection: sqlite3.Connection) -> None:
    # Autocommit (isolation_level=None): this DDL is committed immediately.
    connection.execute(_SCHEMA_MIGRATIONS_DDL)


def _read_applied(connection: sqlite3.Connection) -> dict[int, str]:
    rows = connection.execute(
        "SELECT version, checksum FROM schema_migrations"
    ).fetchall()
    return {int(row["version"]): row["checksum"] for row in rows}


def _apply_migration(connection: sqlite3.Connection, migration: Migration) -> None:
    connection.execute("BEGIN")
    try:
        for statement in _split_statements(migration.sql):
            connection.execute(statement)
        connection.execute(
            "INSERT INTO schema_migrations (version, name, applied_at, checksum)"
            " VALUES (?, ?, ?, ?)",
            (
                migration.version,
                migration.name,
                utc_now().isoformat(),
                migration.checksum,
            ),
        )
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise


def _split_statements(sql: str) -> list[str]:
    return [statement.strip() for statement in sql.split(";") if statement.strip()]


def _checksum(sql: str) -> str:
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()
