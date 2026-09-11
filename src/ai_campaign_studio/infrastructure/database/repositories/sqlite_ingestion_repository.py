"""SQLite adapter for ``IngestionRepositoryPort`` (S2-G2).

Owns persisting and reading back the Slice 2 ingestion value objects
(``SourceSnapshot``/``SourceChunk``/``IngestionRun``/``IngestionCheckpoint``/
``CrawlTarget``/``FactCandidate``) plus the crawl-target lease queue
(canonical plan §7). Same style as ``sqlite_performance_repository.py``:
``ON CONFLICT(id) DO UPDATE`` upsert, enum ``.value``/reconstruction, ISO
timestamps, JSON text for ``source_scope``. Does NOT own crawl orchestration
(S2-G6) or CSV/web ingestion — only the persistence surface.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from datetime import datetime, timedelta

from ai_campaign_studio.domain.common.ids import (
    BrandId,
    CrawlTargetId,
    FactCandidateId,
    IngestionCheckpointId,
    IngestionRunId,
    SourceChunkId,
    SourceSnapshotId,
)
from ai_campaign_studio.domain.common.timestamps import utc_now
from ai_campaign_studio.domain.facts.entities import FactCandidate
from ai_campaign_studio.domain.facts.enums import FactStatus
from ai_campaign_studio.domain.ingestion.entities import (
    CrawlTarget,
    IngestionCheckpoint,
    IngestionRun,
    IngestionRunStats,
    SourceChunk,
    SourceSnapshot,
)
from ai_campaign_studio.domain.ingestion.enums import (
    CrawlTargetState,
    IngestionPhase,
    IngestionRunStatus,
    PageType,
)


class SqliteIngestionRepository:
    """SQLite implementation of ``IngestionRepositoryPort``."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    # --- SourceSnapshot ---

    def save_source_snapshot(self, snapshot: SourceSnapshot) -> None:
        self._connection.execute(
            "INSERT INTO source_snapshots (id, url, fetched_at, content_hash,"
            " raw_content_ref, content_type, status_code)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET"
            " url=excluded.url, fetched_at=excluded.fetched_at,"
            " content_hash=excluded.content_hash,"
            " raw_content_ref=excluded.raw_content_ref,"
            " content_type=excluded.content_type,"
            " status_code=excluded.status_code",
            (
                snapshot.id,
                snapshot.url,
                snapshot.fetched_at.isoformat(),
                snapshot.content_hash,
                snapshot.raw_content_ref,
                snapshot.content_type,
                snapshot.status_code,
            ),
        )

    def get_source_snapshot(
        self, snapshot_id: SourceSnapshotId
    ) -> SourceSnapshot | None:
        row = self._connection.execute(
            "SELECT * FROM source_snapshots WHERE id = ?", (snapshot_id,)
        ).fetchone()
        if row is None:
            return None
        return _source_snapshot_from_row(row)

    def list_source_snapshots_by_run(
        self, run_id: IngestionRunId
    ) -> tuple[SourceSnapshot, ...]:
        # Snapshots are associated to a run through ``crawl_targets.snapshot_id``
        # (set when FETCH completes, S2-G6). Before any target in the run has
        # a snapshot_id this returns an EMPTY tuple — correct, not a bug.
        rows = self._connection.execute(
            "SELECT source_snapshots.* FROM source_snapshots"
            " JOIN crawl_targets"
            "   ON crawl_targets.snapshot_id = source_snapshots.id"
            " WHERE crawl_targets.run_id = ?"
            " ORDER BY source_snapshots.id",
            (run_id,),
        ).fetchall()
        return tuple(_source_snapshot_from_row(row) for row in rows)

    # --- SourceChunk ---

    def save_source_chunk(self, chunk: SourceChunk) -> None:
        self._connection.execute(
            "INSERT INTO source_chunks (id, snapshot_id, locator_type, locator,"
            " text) VALUES (?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET"
            " snapshot_id=excluded.snapshot_id,"
            " locator_type=excluded.locator_type, locator=excluded.locator,"
            " text=excluded.text",
            (
                chunk.id,
                chunk.snapshot_id,
                chunk.locator_type,
                chunk.locator,
                chunk.text,
            ),
        )

    def get_source_chunk(self, chunk_id: SourceChunkId) -> SourceChunk | None:
        row = self._connection.execute(
            "SELECT * FROM source_chunks WHERE id = ?", (chunk_id,)
        ).fetchone()
        if row is None:
            return None
        return _source_chunk_from_row(row)

    def list_source_chunks_by_snapshot(
        self, snapshot_id: SourceSnapshotId
    ) -> tuple[SourceChunk, ...]:
        rows = self._connection.execute(
            "SELECT * FROM source_chunks WHERE snapshot_id = ? ORDER BY id",
            (snapshot_id,),
        ).fetchall()
        return tuple(_source_chunk_from_row(row) for row in rows)

    # --- IngestionRun ---

    def save_ingestion_run(self, run: IngestionRun) -> None:
        self._connection.execute(
            "INSERT INTO ingestion_runs (id, brand_id, status, started_at,"
            " finished_at, source_scope_json, discovered_urls, fetched_pages,"
            " extracted_chunks, built_candidates, failed_pages)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET"
            " brand_id=excluded.brand_id, status=excluded.status,"
            " started_at=excluded.started_at, finished_at=excluded.finished_at,"
            " source_scope_json=excluded.source_scope_json,"
            " discovered_urls=excluded.discovered_urls,"
            " fetched_pages=excluded.fetched_pages,"
            " extracted_chunks=excluded.extracted_chunks,"
            " built_candidates=excluded.built_candidates,"
            " failed_pages=excluded.failed_pages",
            (
                run.id,
                run.brand_id,
                run.status.value,
                run.started_at.isoformat(),
                run.finished_at.isoformat() if run.finished_at is not None else None,
                json.dumps(list(run.source_scope)),
                run.stats.discovered_urls,
                run.stats.fetched_pages,
                run.stats.extracted_chunks,
                run.stats.built_candidates,
                run.stats.failed_pages,
            ),
        )

    def get_ingestion_run(self, run_id: IngestionRunId) -> IngestionRun | None:
        row = self._connection.execute(
            "SELECT * FROM ingestion_runs WHERE id = ?", (run_id,)
        ).fetchone()
        if row is None:
            return None
        return _ingestion_run_from_row(row)

    # --- IngestionCheckpoint ---

    def save_ingestion_checkpoint(
        self, checkpoint: IngestionCheckpoint
    ) -> None:
        self._connection.execute(
            "INSERT INTO ingestion_checkpoints (id, run_id, phase, finished_at)"
            " VALUES (?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET"
            " run_id=excluded.run_id, phase=excluded.phase,"
            " finished_at=excluded.finished_at",
            (
                checkpoint.id,
                checkpoint.run_id,
                checkpoint.phase.value,
                checkpoint.finished_at.isoformat(),
            ),
        )

    def get_latest_checkpoint(
        self, run_id: IngestionRunId
    ) -> IngestionCheckpoint | None:
        row = self._connection.execute(
            "SELECT * FROM ingestion_checkpoints WHERE run_id = ?"
            " ORDER BY finished_at DESC, rowid DESC LIMIT 1",
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        return _ingestion_checkpoint_from_row(row)

    # --- FactCandidate ---

    def save_fact_candidate(self, candidate: FactCandidate) -> None:
        self._connection.execute(
            "INSERT INTO fact_candidates (id, snapshot_id, chunk_id, content,"
            " created_at, status) VALUES (?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET"
            " snapshot_id=excluded.snapshot_id, chunk_id=excluded.chunk_id,"
            " content=excluded.content, created_at=excluded.created_at,"
            " status=excluded.status",
            (
                candidate.id,
                candidate.snapshot_id,
                candidate.chunk_id,
                candidate.content,
                candidate.created_at.isoformat(),
                candidate.status.value,
            ),
        )

    def get_fact_candidate(
        self, candidate_id: FactCandidateId
    ) -> FactCandidate | None:
        row = self._connection.execute(
            "SELECT * FROM fact_candidates WHERE id = ?", (candidate_id,)
        ).fetchone()
        if row is None:
            return None
        return _fact_candidate_from_row(row)

    def list_fact_candidates_by_snapshot(
        self, snapshot_id: SourceSnapshotId
    ) -> tuple[FactCandidate, ...]:
        rows = self._connection.execute(
            "SELECT * FROM fact_candidates WHERE snapshot_id = ? ORDER BY id",
            (snapshot_id,),
        ).fetchall()
        return tuple(_fact_candidate_from_row(row) for row in rows)

    # --- CrawlTarget lease queue ---

    def register_crawl_targets(
        self, targets: Sequence[CrawlTarget]
    ) -> int:
        inserted = 0
        for target in targets:
            cursor = self._connection.execute(
                "INSERT INTO crawl_targets (id, run_id, normalized_url, depth,"
                " page_type_hint, priority, state, attempts, lease_until,"
                " next_attempt_at, last_error, snapshot_id)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(run_id, normalized_url) DO NOTHING",
                (
                    target.id,
                    target.run_id,
                    target.normalized_url,
                    target.depth,
                    target.page_type_hint.value
                    if target.page_type_hint is not None
                    else None,
                    target.priority,
                    target.state.value,
                    target.attempts,
                    target.lease_until.isoformat()
                    if target.lease_until is not None
                    else None,
                    target.next_attempt_at.isoformat()
                    if target.next_attempt_at is not None
                    else None,
                    target.last_error,
                    target.snapshot_id,
                ),
            )
            # SQLite reports 1 for an inserted row, 0 for a DO-NOTHING skip.
            inserted += cursor.rowcount
        return inserted

    def claim_next_crawl_target(
        self, run_id: IngestionRunId, lease_duration_seconds: int
    ) -> CrawlTarget | None:
        """Atomically claim the highest-priority PENDING target.

        Uses an explicit ``BEGIN IMMEDIATE`` transaction so the read-then-
        update is atomic under concurrency: a second writer blocks on the
        reserved lock until this claim commits, then re-reads and claims a
        DIFFERENT row (its ``state='PENDING'`` filter no longer matches the
        already-claimed row). ``attempts`` is deliberately NOT incremented
        here (retry accounting is an S2-G6 orchestration decision).

        BF-1 (Codex): ``lease_until`` is computed INSIDE the transaction,
        AFTER ``BEGIN IMMEDIATE`` acquires the write lock — computing it
        before would let a long lock wait expire the lease before the claim
        even commits, letting ``recover_expired_leases`` immediately re-queue
        a target that is still being worked.
        """
        if lease_duration_seconds <= 0:
            raise ValueError(
                f"lease_duration_seconds must be positive, got "
                f"{lease_duration_seconds}"
            )
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            lease_until = utc_now() + timedelta(seconds=lease_duration_seconds)
            row = self._connection.execute(
                "SELECT * FROM crawl_targets WHERE run_id = ? AND state = ?"
                " ORDER BY priority DESC, id ASC LIMIT 1",
                (run_id, CrawlTargetState.PENDING.value),
            ).fetchone()
            if row is None:
                self._connection.execute("COMMIT")
                return None
            self._connection.execute(
                "UPDATE crawl_targets SET state = ?, lease_until = ?"
                " WHERE id = ?",
                (CrawlTargetState.LEASED.value, lease_until.isoformat(), row["id"]),
            )
            self._connection.execute("COMMIT")
        except Exception:
            self._connection.execute("ROLLBACK")
            raise
        updated = self._connection.execute(
            "SELECT * FROM crawl_targets WHERE id = ?", (row["id"],)
        ).fetchone()
        return _crawl_target_from_row(updated)

    def update_crawl_target_state(
        self,
        target_id: CrawlTargetId,
        state: CrawlTargetState,
        *,
        last_error: str | None = None,
        snapshot_id: SourceSnapshotId | None = None,
    ) -> None:
        """Set the target's state (and optionally ``last_error``/``snapshot_id``).

        ASYMMETRY (deliberate): ``last_error=None`` writes SQL ``NULL``
        (clears a previous error), but ``snapshot_id=None`` KEEPS the existing
        value (``COALESCE``) — the snapshot is set once when FETCH completes
        and most callers never pass it, so a missing kwarg must not wipe it.
        """
        self._connection.execute(
            "UPDATE crawl_targets SET state = ?, last_error = ?,"
            " snapshot_id = COALESCE(?, snapshot_id) WHERE id = ?",
            (state.value, last_error, snapshot_id, target_id),
        )

    def recover_expired_leases(self, run_id: IngestionRunId) -> int:
        """Return LEASED rows with an expired ``lease_until`` to PENDING."""
        cursor = self._connection.execute(
            "UPDATE crawl_targets SET state = ?, lease_until = NULL"
            " WHERE run_id = ? AND state = ? AND lease_until < ?",
            (
                CrawlTargetState.PENDING.value,
                run_id,
                CrawlTargetState.LEASED.value,
                utc_now().isoformat(),
            ),
        )
        return cursor.rowcount

    def get_crawl_target(self, target_id: CrawlTargetId) -> CrawlTarget | None:
        row = self._connection.execute(
            "SELECT * FROM crawl_targets WHERE id = ?", (target_id,)
        ).fetchone()
        if row is None:
            return None
        return _crawl_target_from_row(row)

    def list_crawl_targets_by_run(
        self, run_id: IngestionRunId
    ) -> tuple[CrawlTarget, ...]:
        rows = self._connection.execute(
            "SELECT * FROM crawl_targets WHERE run_id = ?"
            " ORDER BY priority DESC, id ASC",
            (run_id,),
        ).fetchall()
        return tuple(_crawl_target_from_row(row) for row in rows)

    def delete_ingestion_data_for_brand(self, brand_id: BrandId) -> int:
        """Delete every ingestion run for ``brand_id`` and its dependents.

        ``foreign_keys = ON`` (connection.py) means delete order matters:
        ``source_snapshots``/``crawl_targets`` reference each other, so the
        snapshot id set is captured BEFORE anything is deleted, then deletes
        run children-before-parents (fact_candidates/source_chunks ->
        crawl_targets -> source_snapshots -> ingestion_checkpoints ->
        ingestion_runs). Does NOT touch ``approved_facts`` — see the port
        docstring.
        """
        run_rows = self._connection.execute(
            "SELECT id FROM ingestion_runs WHERE brand_id = ?", (brand_id,)
        ).fetchall()
        run_ids = [row["id"] for row in run_rows]
        if not run_ids:
            return 0
        run_placeholders = ",".join("?" for _ in run_ids)

        snapshot_rows = self._connection.execute(
            "SELECT DISTINCT snapshot_id FROM crawl_targets"
            f" WHERE run_id IN ({run_placeholders}) AND snapshot_id IS NOT NULL",
            run_ids,
        ).fetchall()
        snapshot_ids = [row["snapshot_id"] for row in snapshot_rows]

        if snapshot_ids:
            snap_placeholders = ",".join("?" for _ in snapshot_ids)
            self._connection.execute(
                "DELETE FROM fact_candidates"
                f" WHERE snapshot_id IN ({snap_placeholders})",
                snapshot_ids,
            )
            self._connection.execute(
                f"DELETE FROM source_chunks WHERE snapshot_id IN ({snap_placeholders})",
                snapshot_ids,
            )
        self._connection.execute(
            f"DELETE FROM crawl_targets WHERE run_id IN ({run_placeholders})",
            run_ids,
        )
        if snapshot_ids:
            snap_placeholders = ",".join("?" for _ in snapshot_ids)
            self._connection.execute(
                f"DELETE FROM source_snapshots WHERE id IN ({snap_placeholders})",
                snapshot_ids,
            )
        self._connection.execute(
            f"DELETE FROM ingestion_checkpoints WHERE run_id IN ({run_placeholders})",
            run_ids,
        )
        self._connection.execute(
            "DELETE FROM ingestion_runs WHERE brand_id = ?", (brand_id,)
        )
        return len(run_ids)


# --- row reconstruction helpers ---


def _source_snapshot_from_row(row: sqlite3.Row) -> SourceSnapshot:
    return SourceSnapshot(
        id=SourceSnapshotId(row["id"]),
        url=row["url"],
        fetched_at=datetime.fromisoformat(row["fetched_at"]),
        content_hash=row["content_hash"],
        raw_content_ref=row["raw_content_ref"],
        content_type=row["content_type"],
        status_code=row["status_code"],
    )


def _source_chunk_from_row(row: sqlite3.Row) -> SourceChunk:
    return SourceChunk(
        id=SourceChunkId(row["id"]),
        snapshot_id=SourceSnapshotId(row["snapshot_id"]),
        locator_type=row["locator_type"],
        locator=row["locator"],
        text=row["text"],
    )


def _ingestion_run_from_row(row: sqlite3.Row) -> IngestionRun:
    return IngestionRun(
        id=IngestionRunId(row["id"]),
        brand_id=BrandId(row["brand_id"]),
        status=IngestionRunStatus(row["status"]),
        started_at=datetime.fromisoformat(row["started_at"]),
        finished_at=(
            datetime.fromisoformat(row["finished_at"])
            if row["finished_at"] is not None
            else None
        ),
        source_scope=tuple(json.loads(row["source_scope_json"])),
        stats=IngestionRunStats(
            discovered_urls=row["discovered_urls"],
            fetched_pages=row["fetched_pages"],
            extracted_chunks=row["extracted_chunks"],
            built_candidates=row["built_candidates"],
            failed_pages=row["failed_pages"],
        ),
    )


def _ingestion_checkpoint_from_row(row: sqlite3.Row) -> IngestionCheckpoint:
    return IngestionCheckpoint(
        id=IngestionCheckpointId(row["id"]),
        run_id=IngestionRunId(row["run_id"]),
        phase=IngestionPhase(row["phase"]),
        finished_at=datetime.fromisoformat(row["finished_at"]),
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


def _crawl_target_from_row(row: sqlite3.Row) -> CrawlTarget:
    return CrawlTarget(
        id=CrawlTargetId(row["id"]),
        run_id=IngestionRunId(row["run_id"]),
        normalized_url=row["normalized_url"],
        depth=row["depth"],
        priority=row["priority"],
        state=CrawlTargetState(row["state"]),
        attempts=row["attempts"],
        page_type_hint=(
            PageType(row["page_type_hint"])
            if row["page_type_hint"] is not None
            else None
        ),
        lease_until=(
            datetime.fromisoformat(row["lease_until"])
            if row["lease_until"] is not None
            else None
        ),
        next_attempt_at=(
            datetime.fromisoformat(row["next_attempt_at"])
            if row["next_attempt_at"] is not None
            else None
        ),
        last_error=row["last_error"],
        snapshot_id=(
            SourceSnapshotId(row["snapshot_id"])
            if row["snapshot_id"] is not None
            else None
        ),
    )


__all__ = ["SqliteIngestionRepository"]
