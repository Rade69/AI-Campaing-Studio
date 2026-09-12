"""SQLite adapter for ``BrandKnowledgeRepositoryPort`` (BK-G2).

Owns saving ``KnowledgeEntry`` rows (with their fact provenance as a real
join table) and ``BrandKnowledgeSnapshot`` rows (with their entry ordering as
a real join table), and reading them back. ``save_*`` are idempotent (upsert
by primary key) and atomic -- each wraps its multi-statement write (main row
+ join-table replace) in its own transaction unless the caller already
opened one (e.g. ``SqliteUnitOfWork``), detected via
``connection.in_transaction`` so this never issues a nested ``BEGIN``.
Provenance is NEVER stored as a JSON blob — the
``brand_knowledge_entry_facts``/``brand_knowledge_snapshot_entries`` join
tables are the source of truth, same pattern as ``brand_snapshot_facts``.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime

from ai_campaign_studio.domain.brand_knowledge.entities import (
    BrandKnowledgeSnapshot,
    KnowledgeEntry,
)
from ai_campaign_studio.domain.brand_knowledge.enums import (
    EvidenceType,
    KnowledgeCategory,
    KnowledgeStatus,
)
from ai_campaign_studio.domain.common.errors import InvariantViolation
from ai_campaign_studio.domain.common.ids import (
    BrandKnowledgeSnapshotId,
    BrandSnapshotId,
    FactId,
    KnowledgeEntryId,
)


class SqliteBrandKnowledgeRepository:
    """SQLite implementation of ``BrandKnowledgeRepositoryPort``."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    @contextmanager
    def _own_transaction(self) -> Iterator[None]:
        """Wrap a multi-statement write atomically, unless the caller
        already opened a transaction (e.g. ``SqliteUnitOfWork``) --
        detected via ``connection.in_transaction`` so this never issues a
        nested ``BEGIN``. Rolls back on any exception so a mid-write
        failure (e.g. an FK violation on a later statement) never leaves
        a partial row behind (adversarial review finding F1, ACS-BK-002).
        """
        owns_transaction = not self._connection.in_transaction
        if owns_transaction:
            self._connection.execute("BEGIN")
        try:
            yield
        except BaseException:
            if owns_transaction:
                self._connection.execute("ROLLBACK")
            raise
        else:
            if owns_transaction:
                self._connection.execute("COMMIT")

    def save_entry(self, entry: KnowledgeEntry) -> None:
        if len(set(entry.source_fact_ids)) != len(entry.source_fact_ids):
            raise InvariantViolation(
                "KnowledgeEntry.source_fact_ids must not contain"
                f" duplicates, got {entry.source_fact_ids!r} (adversarial"
                " review finding F5, ACS-BK-002)"
            )
        with self._own_transaction():
            existing = self._connection.execute(
                "SELECT brand_snapshot_id FROM brand_knowledge_entries"
                " WHERE id = ?",
                (entry.id,),
            ).fetchone()
            if (
                existing is not None
                and existing["brand_snapshot_id"] != entry.brand_snapshot_id
            ):
                raise InvariantViolation(
                    f"KnowledgeEntry {entry.id!r} already belongs to"
                    f" brand_snapshot_id={existing['brand_snapshot_id']!r};"
                    " save_entry cannot reassign it to"
                    f" {entry.brand_snapshot_id!r} -- a KnowledgeEntry's"
                    " brand_snapshot_id is fixed at creation (adversarial"
                    " review finding F4, ACS-BK-002)."
                )
            self._connection.execute(
                "INSERT INTO brand_knowledge_entries (id, brand_snapshot_id,"
                " category, field_name, value, evidence_type, status, confidence,"
                " conflict_group_id, created_at, reviewed_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(id) DO UPDATE SET"
                " category=excluded.category, field_name=excluded.field_name,"
                " value=excluded.value, evidence_type=excluded.evidence_type,"
                " status=excluded.status, confidence=excluded.confidence,"
                " conflict_group_id=excluded.conflict_group_id,"
                " created_at=excluded.created_at,"
                " reviewed_at=excluded.reviewed_at",
                (
                    entry.id,
                    entry.brand_snapshot_id,
                    entry.category.value,
                    entry.field,
                    entry.value,
                    entry.evidence_type.value,
                    entry.status.value,
                    entry.confidence,
                    entry.conflict_group_id,
                    entry.created_at.isoformat(),
                    entry.reviewed_at.isoformat()
                    if entry.reviewed_at is not None
                    else None,
                ),
            )
            # Replace the join rows so a re-save of the same entry is idempotent.
            self._connection.execute(
                "DELETE FROM brand_knowledge_entry_facts WHERE entry_id = ?",
                (entry.id,),
            )
            for position, fact_id in enumerate(entry.source_fact_ids):
                self._connection.execute(
                    "INSERT INTO brand_knowledge_entry_facts"
                    " (entry_id, fact_id, position) VALUES (?, ?, ?)",
                    (entry.id, fact_id, position),
                )

    def get_entry(self, entry_id: KnowledgeEntryId) -> KnowledgeEntry | None:
        row = self._connection.execute(
            "SELECT * FROM brand_knowledge_entries WHERE id = ?",
            (entry_id,),
        ).fetchone()
        if row is None:
            return None
        return self._entry_from_row(row)

    def list_entries_for_brand_snapshot(
        self, brand_snapshot_id: BrandSnapshotId
    ) -> tuple[KnowledgeEntry, ...]:
        rows = self._connection.execute(
            "SELECT * FROM brand_knowledge_entries WHERE brand_snapshot_id = ?"
            " ORDER BY created_at",
            (brand_snapshot_id,),
        ).fetchall()
        return tuple(self._entry_from_row(row) for row in rows)

    def list_entries_by_status(
        self, brand_snapshot_id: BrandSnapshotId, status: KnowledgeStatus
    ) -> tuple[KnowledgeEntry, ...]:
        rows = self._connection.execute(
            "SELECT * FROM brand_knowledge_entries WHERE brand_snapshot_id = ?"
            " AND status = ? ORDER BY created_at",
            (brand_snapshot_id, status.value),
        ).fetchall()
        return tuple(self._entry_from_row(row) for row in rows)

    def _entry_from_row(self, row: sqlite3.Row) -> KnowledgeEntry:
        fact_rows = self._connection.execute(
            "SELECT fact_id FROM brand_knowledge_entry_facts WHERE entry_id = ?"
            " ORDER BY position",
            (row["id"],),
        ).fetchall()
        return KnowledgeEntry(
            id=KnowledgeEntryId(row["id"]),
            brand_snapshot_id=BrandSnapshotId(row["brand_snapshot_id"]),
            category=KnowledgeCategory(row["category"]),
            field=row["field_name"],
            value=row["value"],
            evidence_type=EvidenceType(row["evidence_type"]),
            status=KnowledgeStatus(row["status"]),
            source_fact_ids=tuple(FactId(fr["fact_id"]) for fr in fact_rows),
            confidence=row["confidence"],
            conflict_group_id=row["conflict_group_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            reviewed_at=(
                datetime.fromisoformat(row["reviewed_at"])
                if row["reviewed_at"] is not None
                else None
            ),
        )

    def save_knowledge_snapshot(self, snapshot: BrandKnowledgeSnapshot) -> None:
        if len(set(snapshot.approved_entry_ids)) != len(
            snapshot.approved_entry_ids
        ):
            raise InvariantViolation(
                "BrandKnowledgeSnapshot.approved_entry_ids must not contain"
                f" duplicates, got {snapshot.approved_entry_ids!r} (same"
                " class of bug as adversarial review finding F5,"
                " ACS-BK-002)"
            )
        with self._own_transaction():
            self._connection.execute(
                "INSERT INTO brand_knowledge_snapshots (id, brand_snapshot_id,"
                " version, created_at) VALUES (?, ?, ?, ?)"
                " ON CONFLICT(id) DO UPDATE SET"
                " brand_snapshot_id=excluded.brand_snapshot_id,"
                " version=excluded.version, created_at=excluded.created_at",
                (
                    snapshot.id,
                    snapshot.brand_snapshot_id,
                    snapshot.version,
                    snapshot.created_at.isoformat(),
                ),
            )
            self._connection.execute(
                "DELETE FROM brand_knowledge_snapshot_entries"
                " WHERE knowledge_snapshot_id = ?",
                (snapshot.id,),
            )
            for position, entry_id in enumerate(snapshot.approved_entry_ids):
                self._connection.execute(
                    "INSERT INTO brand_knowledge_snapshot_entries"
                    " (knowledge_snapshot_id, entry_id, position)"
                    " VALUES (?, ?, ?)",
                    (snapshot.id, entry_id, position),
                )

    def get_knowledge_snapshot(
        self, snapshot_id: BrandKnowledgeSnapshotId
    ) -> BrandKnowledgeSnapshot | None:
        row = self._connection.execute(
            "SELECT * FROM brand_knowledge_snapshots WHERE id = ?",
            (snapshot_id,),
        ).fetchone()
        if row is None:
            return None
        entry_rows = self._connection.execute(
            "SELECT entry_id FROM brand_knowledge_snapshot_entries"
            " WHERE knowledge_snapshot_id = ? ORDER BY position",
            (snapshot_id,),
        ).fetchall()
        return BrandKnowledgeSnapshot(
            id=BrandKnowledgeSnapshotId(row["id"]),
            brand_snapshot_id=BrandSnapshotId(row["brand_snapshot_id"]),
            version=row["version"],
            approved_entry_ids=tuple(
                KnowledgeEntryId(er["entry_id"]) for er in entry_rows
            ),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def get_latest_knowledge_snapshot(
        self, brand_snapshot_id: BrandSnapshotId
    ) -> BrandKnowledgeSnapshot | None:
        row = self._connection.execute(
            "SELECT * FROM brand_knowledge_snapshots WHERE brand_snapshot_id = ?"
            " ORDER BY version DESC LIMIT 1",
            (brand_snapshot_id,),
        ).fetchone()
        if row is None:
            return None
        return self.get_knowledge_snapshot(BrandKnowledgeSnapshotId(row["id"]))
