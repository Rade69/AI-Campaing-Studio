"""SQLite adapter for ``FactRepositoryPort`` (A5).

Owns saving ``ApprovedFact`` rows (provenance fields flattened into columns)
and reading them back, including listing facts by brand snapshot in the
original order. ``save_fact`` is idempotent (upsert by primary key).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

from ai_campaign_studio.domain.common.ids import BrandSnapshotId, FactId
from ai_campaign_studio.domain.facts.entities import ApprovedFact, SourceReference
from ai_campaign_studio.domain.facts.enums import FactStatus


class SqliteFactRepository:
    """SQLite implementation of ``FactRepositoryPort``."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def save_fact(self, fact: ApprovedFact) -> None:
        self._connection.execute(
            "INSERT INTO approved_facts (id, logical_fact_id, version, content,"
            " source_type, source_uri, source_snapshot_id, source_chunk_id,"
            " status, created_at, superseded_by, deleted_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET logical_fact_id=excluded.logical_fact_id,"
            " version=excluded.version, content=excluded.content,"
            " source_type=excluded.source_type, source_uri=excluded.source_uri,"
            " source_snapshot_id=excluded.source_snapshot_id,"
            " source_chunk_id=excluded.source_chunk_id, status=excluded.status,"
            " created_at=excluded.created_at, superseded_by=excluded.superseded_by,"
            " deleted_at=excluded.deleted_at",
            (
                fact.id,
                fact.logical_fact_id,
                fact.version,
                fact.content,
                fact.source_ref.source_type,
                fact.source_ref.uri,
                fact.source_ref.snapshot_id,
                fact.source_ref.chunk_id,
                fact.status.value,
                fact.created_at.isoformat(),
                fact.superseded_by,
                fact.deleted_at.isoformat() if fact.deleted_at is not None else None,
            ),
        )

    def get_fact(self, fact_id: FactId) -> ApprovedFact | None:
        row = self._connection.execute(
            "SELECT * FROM approved_facts WHERE id = ?",
            (fact_id,),
        ).fetchone()
        if row is None:
            return None
        return _fact_from_row(row)

    def list_snapshot_facts(
        self, snapshot_id: BrandSnapshotId
    ) -> tuple[ApprovedFact, ...]:
        rows = self._connection.execute(
            "SELECT approved_facts.* FROM approved_facts"
            " JOIN brand_snapshot_facts"
            "   ON brand_snapshot_facts.fact_id = approved_facts.id"
            " WHERE brand_snapshot_facts.snapshot_id = ?"
            " ORDER BY brand_snapshot_facts.position",
            (snapshot_id,),
        ).fetchall()
        return tuple(_fact_from_row(row) for row in rows)


def _fact_from_row(row: sqlite3.Row) -> ApprovedFact:
    return ApprovedFact(
        id=FactId(row["id"]),
        logical_fact_id=row["logical_fact_id"],
        version=row["version"],
        content=row["content"],
        source_ref=SourceReference(
            source_type=row["source_type"],
            uri=row["source_uri"],
            snapshot_id=row["source_snapshot_id"],
            chunk_id=row["source_chunk_id"],
        ),
        status=FactStatus(row["status"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        superseded_by=FactId(row["superseded_by"]) if row["superseded_by"] else None,
        deleted_at=(
            datetime.fromisoformat(row["deleted_at"]) if row["deleted_at"] else None
        ),
    )
