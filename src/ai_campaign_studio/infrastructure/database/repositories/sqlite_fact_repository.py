"""SQLite adapter for ``FactRepositoryPort`` (A5).

Owns saving ``ApprovedFact`` rows (provenance fields flattened into columns)
and reading them back, including listing facts by brand snapshot in the
original order. ``save_fact`` is idempotent (upsert by primary key).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

from ai_campaign_studio.domain.common.ids import (
    BrandId,
    BrandSnapshotId,
    FactCandidateId,
    FactId,
    SourceChunkId,
    SourceSnapshotId,
)
from ai_campaign_studio.domain.facts.entities import (
    ApprovedFact,
    FactCandidate,
    SourceReference,
)
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

    def list_approved_facts_by_brand(
        self, brand_id: BrandId
    ) -> tuple[ApprovedFact, ...]:
        """Return all APPROVED facts for a brand, newest first.

        A web-ingestion ``ApprovedFact`` is linked to its brand through the
        provenance chain ``approved_facts.source_snapshot_id → source_snapshots
        → crawl_targets → ingestion_runs.brand_id``. Facts with a NULL
        ``source_snapshot_id`` (manual fixtures) are deliberately NOT returned
        here — this read model exists for the ingestion review flow.
        """
        rows = self._connection.execute(
            "SELECT approved_facts.* FROM approved_facts"
            " JOIN source_snapshots"
            "   ON source_snapshots.id = approved_facts.source_snapshot_id"
            " JOIN crawl_targets"
            "   ON crawl_targets.snapshot_id = source_snapshots.id"
            " JOIN ingestion_runs"
            "   ON ingestion_runs.id = crawl_targets.run_id"
            " WHERE ingestion_runs.brand_id = ?"
            " ORDER BY approved_facts.created_at DESC, approved_facts.id DESC",
            (brand_id,),
        ).fetchall()
        return tuple(_fact_from_row(row) for row in rows)

    def list_fact_candidates_by_brand(
        self, brand_id: BrandId, statuses: tuple[FactStatus, ...] | None = None
    ) -> tuple[FactCandidate, ...]:
        """Return FactCandidate rows for a brand, optionally filtered by
        statuses. The brand link is the same provenance chain as
        ``list_approved_facts_by_brand`` (candidate → snapshot → crawl target
        → ingestion run).
        """
        clauses = ["ingestion_runs.brand_id = ?"]
        params: list[object] = [brand_id]
        if statuses is not None:
            placeholders = ", ".join("?" for _ in statuses)
            clauses.append(f"fact_candidates.status IN ({placeholders})")
            params.extend(status.value for status in statuses)
        where = " AND ".join(clauses)
        rows = self._connection.execute(
            "SELECT fact_candidates.* FROM fact_candidates"
            " JOIN source_snapshots"
            "   ON source_snapshots.id = fact_candidates.snapshot_id"
            " JOIN crawl_targets"
            "   ON crawl_targets.snapshot_id = source_snapshots.id"
            " JOIN ingestion_runs"
            "   ON ingestion_runs.id = crawl_targets.run_id"
            f" WHERE {where}"
            " ORDER BY fact_candidates.created_at DESC, fact_candidates.id DESC",
            params,
        ).fetchall()
        return tuple(_fact_candidate_from_row(row) for row in rows)


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


def _fact_candidate_from_row(row: sqlite3.Row) -> FactCandidate:
    return FactCandidate(
        id=FactCandidateId(row["id"]),
        snapshot_id=SourceSnapshotId(row["snapshot_id"]),
        content=row["content"],
        created_at=datetime.fromisoformat(row["created_at"]),
        status=FactStatus(row["status"]),
        chunk_id=(
            SourceChunkId(row["chunk_id"]) if row["chunk_id"] is not None else None
        ),
    )
