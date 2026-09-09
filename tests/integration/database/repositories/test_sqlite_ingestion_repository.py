"""Integration tests for SqliteIngestionRepository (S2-G2)."""

from __future__ import annotations

import sqlite3
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ai_campaign_studio.domain.common.ids import (
    BrandId,
    CrawlTargetId,
    FactCandidateId,
    IngestionCheckpointId,
    IngestionRunId,
    SourceChunkId,
    SourceSnapshotId,
)
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
)
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories import (
    SqliteIngestionRepository,
)
from ai_campaign_studio.ports.repositories import IngestionRepositoryPort

_MIGRATIONS_DIR = Path(__file__).resolve().parents[4] / "resources" / "migrations"
_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def _setup_db(tmp_path: Path) -> sqlite3.Connection:
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)
    return connection


def _seed_brand(connection: sqlite3.Connection) -> None:
    connection.execute(
        "INSERT OR IGNORE INTO brands (id, name, created_at) VALUES (?, ?, ?)",
        ("brand-1", "Brand", _CREATED_AT.isoformat()),
    )


def _run(
    run_id: str = "run-1", stats: IngestionRunStats | None = None
) -> IngestionRun:
    return IngestionRun(
        id=IngestionRunId(run_id),
        brand_id=BrandId("brand-1"),
        status=IngestionRunStatus.RUNNING,
        started_at=_CREATED_AT,
        source_scope=("https://example.com/",),
        stats=stats if stats is not None else IngestionRunStats(),
    )


def _snapshot(snapshot_id: str = "snap-1") -> SourceSnapshot:
    return SourceSnapshot(
        id=SourceSnapshotId(snapshot_id),
        url="https://example.com/about",
        fetched_at=_CREATED_AT,
        content_hash="abc123",
        raw_content_ref="store://snap-1",
        content_type="text/html",
        status_code=200,
    )


def _chunk(chunk_id: str = "chunk-1") -> SourceChunk:
    return SourceChunk(
        id=SourceChunkId(chunk_id),
        snapshot_id=SourceSnapshotId("snap-1"),
        locator_type="css_selector",
        locator="#main > p",
        text="We offer implantology.",
    )


def _checkpoint(checkpoint_id: str = "cp-1") -> IngestionCheckpoint:
    return IngestionCheckpoint(
        id=IngestionCheckpointId(checkpoint_id),
        run_id=IngestionRunId("run-1"),
        phase=IngestionPhase.FETCH,
        finished_at=_CREATED_AT,
    )


def _candidate(candidate_id: str = "cand-1") -> FactCandidate:
    return FactCandidate(
        id=FactCandidateId(candidate_id),
        snapshot_id=SourceSnapshotId("snap-1"),
        content="We offer implantology.",
        created_at=_CREATED_AT,
        status=FactStatus.PROPOSED,
    )


def _crawl_target(
    target_id: str,
    *,
    url: str | None = None,
    priority: int = 0,
    state: CrawlTargetState = CrawlTargetState.PENDING,
    lease_until: datetime | None = None,
    snapshot_id: SourceSnapshotId | None = None,
    run_id: str = "run-1",
) -> CrawlTarget:
    return CrawlTarget(
        id=CrawlTargetId(target_id),
        run_id=IngestionRunId(run_id),
        normalized_url=url or f"https://example.com/{target_id}",
        depth=1,
        priority=priority,
        state=state,
        attempts=0,
        lease_until=lease_until,
        snapshot_id=snapshot_id,
    )


def test_repository_is_an_ingestion_repository_port(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteIngestionRepository(connection)
    assert isinstance(repo, IngestionRepositoryPort)
    connection.close()


def test_round_trip_source_snapshot(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteIngestionRepository(connection)
    repo.save_source_snapshot(_snapshot())
    assert repo.get_source_snapshot(SourceSnapshotId("snap-1")) == _snapshot()
    connection.close()


def test_round_trip_source_chunk(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteIngestionRepository(connection)
    repo.save_source_snapshot(_snapshot())
    repo.save_source_chunk(_chunk())
    assert repo.get_source_chunk(SourceChunkId("chunk-1")) == _chunk()
    assert repo.list_source_chunks_by_snapshot(
        SourceSnapshotId("snap-1")
    ) == (_chunk(),)
    connection.close()


def test_round_trip_ingestion_run_with_flattened_stats(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    _seed_brand(connection)
    repo = SqliteIngestionRepository(connection)
    run = _run(
        stats=IngestionRunStats(
            discovered_urls=5,
            fetched_pages=3,
            extracted_chunks=2,
            built_candidates=1,
            failed_pages=1,
        )
    )
    repo.save_ingestion_run(run)
    loaded = repo.get_ingestion_run(IngestionRunId("run-1"))
    assert loaded == run
    assert loaded is not None
    assert loaded.stats.fetched_pages == 3
    assert loaded.source_scope == ("https://example.com/",)
    connection.close()


def test_round_trip_ingestion_checkpoint_and_latest(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    _seed_brand(connection)
    repo = SqliteIngestionRepository(connection)
    repo.save_ingestion_run(_run())
    repo.save_ingestion_checkpoint(_checkpoint("cp-1"))
    later = IngestionCheckpoint(
        id=IngestionCheckpointId("cp-2"),
        run_id=IngestionRunId("run-1"),
        phase=IngestionPhase.EXTRACT,
        finished_at=_CREATED_AT + timedelta(minutes=1),
    )
    repo.save_ingestion_checkpoint(later)

    assert repo.get_latest_checkpoint(IngestionRunId("run-1")) == later
    connection.close()


def test_round_trip_fact_candidate(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteIngestionRepository(connection)
    repo.save_source_snapshot(_snapshot())
    repo.save_fact_candidate(_candidate())
    assert repo.get_fact_candidate(FactCandidateId("cand-1")) == _candidate()
    assert repo.list_fact_candidates_by_snapshot(
        SourceSnapshotId("snap-1")
    ) == (_candidate(),)
    connection.close()


def test_round_trip_crawl_target(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    _seed_brand(connection)
    repo = SqliteIngestionRepository(connection)
    repo.save_ingestion_run(_run())
    target = _crawl_target("ct-1", priority=3, state=CrawlTargetState.LEASED)
    repo.register_crawl_targets([target])
    assert repo.get_crawl_target(CrawlTargetId("ct-1")) == target
    connection.close()


def test_get_unknown_returns_none(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteIngestionRepository(connection)
    assert repo.get_source_snapshot(SourceSnapshotId("missing")) is None
    assert repo.get_source_chunk(SourceChunkId("missing")) is None
    assert repo.get_ingestion_run(IngestionRunId("missing")) is None
    assert repo.get_fact_candidate(FactCandidateId("missing")) is None
    assert repo.get_crawl_target(CrawlTargetId("missing")) is None
    connection.close()


def test_register_crawl_targets_idempotent_on_duplicate_url(
    tmp_path: Path,
) -> None:
    connection = _setup_db(tmp_path)
    _seed_brand(connection)
    repo = SqliteIngestionRepository(connection)
    repo.save_ingestion_run(_run())

    first = repo.register_crawl_targets([_crawl_target("ct-1", url="https://x/a")])
    # Same (run_id, normalized_url) -> DO NOTHING, returns 0, no duplicate row.
    dup = repo.register_crawl_targets([_crawl_target("ct-2", url="https://x/a")])
    assert first == 1
    assert dup == 0

    targets = repo.list_crawl_targets_by_run(IngestionRunId("run-1"))
    assert len(targets) == 1
    assert targets[0].id == CrawlTargetId("ct-1")
    connection.close()


def test_claim_next_crawl_target_picks_highest_priority(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    _seed_brand(connection)
    repo = SqliteIngestionRepository(connection)
    repo.save_ingestion_run(_run())
    repo.register_crawl_targets(
        [
            _crawl_target("ct-low", priority=1),
            _crawl_target("ct-high", priority=9),
        ]
    )

    claimed = repo.claim_next_crawl_target(IngestionRunId("run-1"), 60)
    assert claimed is not None
    assert claimed.id == CrawlTargetId("ct-high")
    assert claimed.state is CrawlTargetState.LEASED
    assert claimed.lease_until is not None

    loaded = repo.get_crawl_target(CrawlTargetId("ct-high"))
    assert loaded is not None
    assert loaded.state is CrawlTargetState.LEASED
    connection.close()


def test_claim_returns_none_when_no_pending(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    _seed_brand(connection)
    repo = SqliteIngestionRepository(connection)
    repo.save_ingestion_run(_run())
    repo.register_crawl_targets(
        [_crawl_target("ct-1", state=CrawlTargetState.DONE)]
    )
    assert repo.claim_next_crawl_target(IngestionRunId("run-1"), 60) is None
    connection.close()


def test_claim_next_crawl_target_is_atomic_under_concurrency(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "test.db"
    connection = create_connection(db_path)
    run_migrations(connection, _MIGRATIONS_DIR)
    _seed_brand(connection)
    repo = SqliteIngestionRepository(connection)
    repo.save_ingestion_run(_run())
    repo.register_crawl_targets([_crawl_target(f"ct-{i}") for i in range(4)])
    connection.close()

    results: list[CrawlTarget | None] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def _worker() -> None:
        conn = create_connection(db_path)
        try:
            worker_repo = SqliteIngestionRepository(conn)
            barrier.wait()
            claimed = worker_repo.claim_next_crawl_target(
                IngestionRunId("run-1"), 60
            )
            results.append(claimed)
        except BaseException as exc:  # pragma: no cover - assertion aid
            errors.append(exc)
        finally:
            conn.close()

    threads = [threading.Thread(target=_worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"claim raised from worker thread: {errors!r}"
    claimed_ids = [str(c.id) for c in results if c is not None]
    assert len(claimed_ids) == 2, f"expected 2 claims, got {claimed_ids!r}"
    assert len(set(claimed_ids)) == 2, "a target was claimed twice"


def test_recover_expired_leases(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    _seed_brand(connection)
    repo = SqliteIngestionRepository(connection)
    repo.save_ingestion_run(_run())

    now = datetime.now(UTC)
    repo.register_crawl_targets(
        [
            _crawl_target(
                "ct-expired",
                state=CrawlTargetState.LEASED,
                lease_until=now - timedelta(minutes=5),
            ),
            _crawl_target(
                "ct-fresh",
                state=CrawlTargetState.LEASED,
                lease_until=now + timedelta(minutes=5),
            ),
        ]
    )

    recovered = repo.recover_expired_leases(IngestionRunId("run-1"))
    assert recovered == 1
    expired = repo.get_crawl_target(CrawlTargetId("ct-expired"))
    fresh = repo.get_crawl_target(CrawlTargetId("ct-fresh"))
    assert expired is not None
    assert expired.state is CrawlTargetState.PENDING
    assert expired.lease_until is None
    assert fresh is not None
    assert fresh.state is CrawlTargetState.LEASED
    connection.close()


def test_update_crawl_target_state(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    _seed_brand(connection)
    repo = SqliteIngestionRepository(connection)
    repo.save_ingestion_run(_run())
    repo.register_crawl_targets([_crawl_target("ct-1")])

    repo.update_crawl_target_state(
        CrawlTargetId("ct-1"),
        CrawlTargetState.FAILED_RETRYABLE,
        last_error="timeout",
    )
    loaded = repo.get_crawl_target(CrawlTargetId("ct-1"))
    assert loaded is not None
    assert loaded.state is CrawlTargetState.FAILED_RETRYABLE
    assert loaded.last_error == "timeout"
    connection.close()


def test_list_source_snapshots_by_run_has_no_cross_run_leak(
    tmp_path: Path,
) -> None:
    """The Claude-review blocking finding: two runs crawling the SAME URL,
    each with its own snapshot, must NOT leak into each other's list."""
    connection = _setup_db(tmp_path)
    _seed_brand(connection)
    repo = SqliteIngestionRepository(connection)

    repo.save_ingestion_run(_run("run-a"))
    repo.save_ingestion_run(_run("run-b"))
    repo.save_source_snapshot(
        SourceSnapshot(
            id=SourceSnapshotId("snap-a"),
            url="https://x/page",
            fetched_at=_CREATED_AT,
            content_hash="a",
        )
    )
    repo.save_source_snapshot(
        SourceSnapshot(
            id=SourceSnapshotId("snap-b"),
            url="https://x/page",
            fetched_at=_CREATED_AT,
            content_hash="b",
        )
    )
    repo.register_crawl_targets(
        [
            _crawl_target(
                "ct-a",
                url="https://x/page",
                snapshot_id=SourceSnapshotId("snap-a"),
                run_id="run-a",
            ),
            _crawl_target(
                "ct-b",
                url="https://x/page",
                snapshot_id=SourceSnapshotId("snap-b"),
                run_id="run-b",
            ),
        ]
    )

    only_a = repo.list_source_snapshots_by_run(IngestionRunId("run-a"))
    only_b = repo.list_source_snapshots_by_run(IngestionRunId("run-b"))
    assert [str(s.id) for s in only_a] == ["snap-a"]
    assert [str(s.id) for s in only_b] == ["snap-b"]
    connection.close()


def test_update_crawl_target_state_keeps_snapshot_when_not_passed(
    tmp_path: Path,
) -> None:
    """COALESCE semantics: a missing snapshot_id kwarg must NOT wipe an
    already-set snapshot (last_error=None DOES clear, snapshot_id=None does
    not — deliberate asymmetry)."""
    connection = _setup_db(tmp_path)
    _seed_brand(connection)
    repo = SqliteIngestionRepository(connection)
    repo.save_ingestion_run(_run())
    repo.save_source_snapshot(_snapshot("snap-1"))
    repo.save_source_snapshot(_snapshot("snap-2"))
    repo.register_crawl_targets(
        [_crawl_target("ct-1", snapshot_id=SourceSnapshotId("snap-1"))]
    )

    repo.update_crawl_target_state(
        CrawlTargetId("ct-1"), CrawlTargetState.FETCHED
    )
    loaded = repo.get_crawl_target(CrawlTargetId("ct-1"))
    assert loaded is not None
    assert loaded.snapshot_id == SourceSnapshotId("snap-1")  # kept

    repo.update_crawl_target_state(
        CrawlTargetId("ct-1"),
        CrawlTargetState.EXTRACTED,
        snapshot_id=SourceSnapshotId("snap-2"),
    )
    overwritten = repo.get_crawl_target(CrawlTargetId("ct-1"))
    assert overwritten is not None
    assert overwritten.snapshot_id == SourceSnapshotId("snap-2")
    connection.close()


def test_claim_lease_until_is_future_under_contention(tmp_path: Path) -> None:
    """BF-1 (Codex): the lease must be computed AFTER the write lock is
    acquired, not before — a long ``BEGIN IMMEDIATE`` wait must not expire
    the lease before the claim commits."""
    db_path = tmp_path / "test.db"
    connection = create_connection(db_path)
    run_migrations(connection, _MIGRATIONS_DIR)
    _seed_brand(connection)
    repo = SqliteIngestionRepository(connection)
    repo.save_ingestion_run(_run())
    repo.register_crawl_targets([_crawl_target("ct-1")])
    connection.close()

    release = threading.Event()
    holder_acquired = threading.Event()

    def _holder() -> None:
        conn = create_connection(db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            holder_acquired.set()
            # Hold the write lock longer than the 1s lease the claimer uses.
            release.wait(timeout=10)
            conn.execute("COMMIT")
        finally:
            conn.close()

    result: dict[str, CrawlTarget | None] = {}

    def _claimer() -> None:
        conn = create_connection(db_path)
        try:
            claimer_repo = SqliteIngestionRepository(conn)
            result["claimed"] = claimer_repo.claim_next_crawl_target(
                IngestionRunId("run-1"), 1
            )
        finally:
            conn.close()

    holder = threading.Thread(target=_holder)
    holder.start()
    assert holder_acquired.wait(timeout=5), "holder did not acquire the lock"

    claimer = threading.Thread(target=_claimer)
    claimer.start()
    time.sleep(1.5)  # claimer blocks on BEGIN IMMEDIATE; lease is only 1s
    release.set()
    holder.join(timeout=5)
    claimer.join(timeout=10)

    claimed = result["claimed"]
    assert claimed is not None
    assert claimed.lease_until is not None
    # The lease must still be in the future AFTER the lock wait.
    assert claimed.lease_until > datetime.now(UTC)


def test_claim_rejects_non_positive_lease_duration(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    _seed_brand(connection)
    repo = SqliteIngestionRepository(connection)
    repo.save_ingestion_run(_run())
    repo.register_crawl_targets([_crawl_target("ct-1")])

    with pytest.raises(ValueError):
        repo.claim_next_crawl_target(IngestionRunId("run-1"), 0)
    connection.close()
