"""SQLite adapter for ``RevisionRepositoryPort`` (A5, dio 2).

Owns saving ``Revision`` rows and reading them back (single revision and by
entity). ``origin`` is stored as ``.value`` and reconstructed as the domain
enum.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

from ai_campaign_studio.domain.common.ids import RevisionId
from ai_campaign_studio.domain.content.revisions import Revision, RevisionOrigin


class SqliteRevisionRepository:
    """SQLite implementation of ``RevisionRepositoryPort``."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def save_revision(self, revision: Revision) -> None:
        self._connection.execute(
            "INSERT INTO revisions (id, entity_type, entity_id, version,"
            " timestamp, origin, previous_value, new_value, provider, model,"
            " prompt_version, instruction)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET entity_type=excluded.entity_type,"
            " entity_id=excluded.entity_id, version=excluded.version,"
            " timestamp=excluded.timestamp, origin=excluded.origin,"
            " previous_value=excluded.previous_value,"
            " new_value=excluded.new_value, provider=excluded.provider,"
            " model=excluded.model, prompt_version=excluded.prompt_version,"
            " instruction=excluded.instruction",
            (
                revision.id,
                revision.entity_type,
                revision.entity_id,
                revision.version,
                revision.timestamp.isoformat(),
                revision.origin.value,
                revision.previous_value,
                revision.new_value,
                revision.provider,
                revision.model,
                revision.prompt_version,
                revision.instruction,
            ),
        )

    def get_revision(self, revision_id: RevisionId) -> Revision | None:
        row = self._connection.execute(
            "SELECT * FROM revisions WHERE id = ?", (revision_id,)
        ).fetchone()
        if row is None:
            return None
        return _revision_from_row(row)

    def list_entity_revisions(
        self, entity_type: str, entity_id: str
    ) -> tuple[Revision, ...]:
        rows = self._connection.execute(
            "SELECT * FROM revisions WHERE entity_type = ? AND entity_id = ?"
            " ORDER BY version",
            (entity_type, entity_id),
        ).fetchall()
        return tuple(_revision_from_row(row) for row in rows)


def _revision_from_row(row: sqlite3.Row) -> Revision:
    return Revision(
        id=RevisionId(row["id"]),
        entity_type=row["entity_type"],
        entity_id=row["entity_id"],
        version=row["version"],
        timestamp=datetime.fromisoformat(row["timestamp"]),
        origin=RevisionOrigin(row["origin"]),
        previous_value=row["previous_value"],
        new_value=row["new_value"],
        provider=row["provider"],
        model=row["model"],
        prompt_version=row["prompt_version"],
        instruction=row["instruction"],
    )
