"""Integration tests for the S2-G6 ingestion pipeline (real SQLite).

Covers the full DISCOVER→DONE flow with real persisted counts, the
G-WI-RECOVER resume-after-kill invariant, the G-WI-EVIDENCE provenance chain,
the SSRF → SKIPPED_UNSAFE mapping, and cooperative cancellation.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ai_campaign_studio.application.ingestion import IngestBrandSources
from ai_campaign_studio.domain.brand.value_objects import VisualIdentity
from ai_campaign_studio.domain.common.ids import (
    BrandId,
    CrawlTargetId,
    IngestionRunId,
    SourceSnapshotId,
)
from ai_campaign_studio.domain.ingestion.entities import (
    CrawlTarget,
    IngestionRun,
    SourceSnapshot,
)
from ai_campaign_studio.domain.ingestion.enums import (
    CrawlTargetState,
    IngestionPhase,
    IngestionRunStatus,
    PageType,
)
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories import (
    SqliteIngestionRepository,
)
from ai_campaign_studio.infrastructure.extraction import (
    BoilerplateFilter,
    Deduplicator,
)
from ai_campaign_studio.infrastructure.web_ingestion import UrlClassifier, normalize_url
from ai_campaign_studio.jobs.cancellation import CancellationError, CancellationToken
from ai_campaign_studio.ports.web_ingestion import FetchResult

_MIGRATIONS_DIR = Path(__file__).resolve().parents[4] / "resources" / "migrations"
_BRAND_ID = BrandId("brand-1")
_START = "https://example.com/"
_ABOUT = "https://example.com/o-nama"
_CONTACT = "https://example.com/kontakt"

_HTML = b"<html><body><p>Prvi pasus o brendu.</p><p>Drugi pasus.</p></body></html>"


def _setup_db(tmp_path: Path) -> sqlite3.Connection:
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)
    connection.execute(
        "INSERT OR IGNORE INTO brands (id, name, created_at) VALUES (?, ?, ?)",
        (_BRAND_ID, "Brand", datetime(2026, 1, 1, tzinfo=UTC).isoformat()),
    )
    connection.commit()
    return connection


class _FakeDiscovery:
    def __init__(self, mapping: dict[str, tuple[str, ...]]) -> None:
        self._mapping = mapping

    def discover(self, start_url: str) -> tuple[str, ...]:
        return self._mapping.get(start_url, ())


class _FakeFetcher:
    def __init__(self, mapping: dict[str, FetchResult]) -> None:
        self._mapping = mapping
        self.calls: list[str] = []

    def fetch(self, url: str) -> FetchResult:
        self.calls.append(url)
        if url in self._mapping:
            return self._mapping[url]
        return FetchResult(
            url=url, final_url=url, status_code=0, error="fetch_error:ConnectionError"
        )


class _FakeVisual:
    def extract(self, html: str, base_url: str) -> VisualIdentity:
        return VisualIdentity()


class _FakeBudget:
    def can_crawl(self, domain: str) -> bool:
        return True

    def wait_politeness(self, domain: str) -> float:
        return 0.0

    def record_fetch(self, domain: str) -> None:
        return None


def _ok(url: str) -> FetchResult:
    return FetchResult(
        url=url,
        final_url=url,
        status_code=200,
        content=_HTML,
        content_type="text/html; charset=utf-8",
    )


def _content_extractor(html: str, base_url: str) -> str:
    return "Prvi pasus o brendu.\n\nDrugi pasus."


def _make_use_case(
    connection: sqlite3.Connection,
    *,
    discovery: _FakeDiscovery,
    fetcher: _FakeFetcher,
) -> IngestBrandSources:
    return IngestBrandSources(
        repository=SqliteIngestionRepository(connection),
        fetcher=fetcher,
        classifier=UrlClassifier(),
        discovery=discovery,
        budget=_FakeBudget(),
        normalizer=normalize_url,
        visual_identity_extractor=_FakeVisual(),
        content_extractor=_content_extractor,
        boilerplate_filter=BoilerplateFilter().filter,
        deduplicator=Deduplicator().deduplicate,
        document_extractors={},
    )


def test_full_pipeline_persists_real_counts_and_provenance(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repository = SqliteIngestionRepository(connection)
    fetcher = _FakeFetcher(
        {_START: _ok(_START), _ABOUT: _ok(_ABOUT), _CONTACT: _ok(_CONTACT)}
    )
    use_case = _make_use_case(
        connection,
        discovery=_FakeDiscovery({_START: (_START, _ABOUT, _CONTACT)}),
        fetcher=fetcher,
    )

    run = use_case.execute(_BRAND_ID, (_START,))

    assert run.status is IngestionRunStatus.SUCCEEDED
    assert run.stats.discovered_urls == 3
    assert run.stats.fetched_pages == 3
    assert run.stats.extracted_chunks == 6
    assert run.stats.built_candidates == 6

    # G-WI-EVIDENCE: every candidate is traceable to a persisted snapshot/chunk.
    snapshots = repository.list_source_snapshots_by_run(run.id)
    assert len(snapshots) == 3
    snapshot_ids = {str(s.id) for s in snapshots}
    total_candidates = 0
    for snapshot in snapshots:
        for candidate in repository.list_fact_candidates_by_snapshot(snapshot.id):
            assert str(candidate.snapshot_id) in snapshot_ids
            assert candidate.chunk_id is not None
            assert repository.get_source_chunk(candidate.chunk_id) is not None
            total_candidates += 1
    assert total_candidates == 6

    # State machine complete.
    latest = repository.get_latest_checkpoint(run.id)
    assert latest is not None
    assert latest.phase is IngestionPhase.DONE


def test_recover_expired_lease_resumes_without_duplicate_work(tmp_path: Path) -> None:
    """G-WI-RECOVER: a target killed mid-FETCH (LEASED with expired lease)
    is requeued and processed exactly once on resume."""
    connection = _setup_db(tmp_path)
    repository = SqliteIngestionRepository(connection)
    run_id = IngestionRunId("run-recover")
    repository.save_ingestion_run(
        IngestionRun(
            id=run_id,
            brand_id=_BRAND_ID,
            status=IngestionRunStatus.RUNNING,
            started_at=datetime(2026, 1, 1, tzinfo=UTC),
            source_scope=(_START,),
        )
    )
    repository.register_crawl_targets(
        [
            CrawlTarget(
                id=CrawlTargetId("t-1"),
                run_id=run_id,
                normalized_url=_START,
                depth=0,
                priority=100,
                state=CrawlTargetState.PENDING,
                attempts=0,
                page_type_hint=PageType.HOME,
            )
        ]
    )
    # Simulate a worker that crashed mid-fetch: it claimed the target (LEASED)
    # and then the process died, leaving an expired lease in the DB.
    claimed = repository.claim_next_crawl_target(run_id, 1)
    assert claimed is not None and claimed.state is CrawlTargetState.LEASED
    expired = (datetime.now(UTC) - timedelta(seconds=60)).isoformat()
    connection.execute(
        "UPDATE crawl_targets SET lease_until = ? WHERE id = ?", (expired, "t-1")
    )
    connection.commit()

    fetcher = _FakeFetcher({_START: _ok(_START)})
    use_case = _make_use_case(
        connection, discovery=_FakeDiscovery({_START: (_START,)}), fetcher=fetcher
    )
    run = use_case.execute(_BRAND_ID, (_START,), run_id=str(run_id))

    assert run.status is IngestionRunStatus.SUCCEEDED
    targets = repository.list_crawl_targets_by_run(run_id)
    assert len(targets) == 1
    assert targets[0].state is CrawlTargetState.DONE
    # Exactly one snapshot — no duplicate work.
    assert len(repository.list_source_snapshots_by_run(run_id)) == 1


def test_fetch_succeeded_before_crash_does_not_duplicate_snapshot(
    tmp_path: Path,
) -> None:
    """Codex edge case: fetch wrote a snapshot but the crash hit before
    ``update_crawl_target_state(FETCHED)``. Resume re-fetches and the
    deterministic snapshot id upserts instead of duplicating."""
    connection = _setup_db(tmp_path)
    repository = SqliteIngestionRepository(connection)
    run_id = IngestionRunId("run-partial")
    repository.save_ingestion_run(
        IngestionRun(
            id=run_id,
            brand_id=_BRAND_ID,
            status=IngestionRunStatus.RUNNING,
            started_at=datetime(2026, 1, 1, tzinfo=UTC),
            source_scope=(_START,),
        )
    )
    repository.register_crawl_targets(
        [
            CrawlTarget(
                id=CrawlTargetId("t-1"),
                run_id=run_id,
                normalized_url=_START,
                depth=0,
                priority=100,
                state=CrawlTargetState.PENDING,
                attempts=0,
            )
        ]
    )
    claimed = repository.claim_next_crawl_target(run_id, 1)
    assert claimed is not None
    connection.execute(
        "UPDATE crawl_targets SET lease_until = ? WHERE id = ?",
        ((datetime.now(UTC) - timedelta(seconds=60)).isoformat(), "t-1"),
    )
    connection.commit()
    # The prior attempt already persisted the snapshot (deterministic id).
    from ai_campaign_studio.application.ingestion.ingest_brand_sources import (
        _stable_id,
    )

    snapshot_id = SourceSnapshotId(_stable_id(run_id, _START))
    repository.save_source_snapshot(
        SourceSnapshot(
            id=snapshot_id,
            url=_START,
            fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
            content_hash="old",
            content_type="text/html",
            status_code=200,
        )
    )
    connection.commit()

    use_case = _make_use_case(
        connection,
        discovery=_FakeDiscovery({_START: (_START,)}),
        fetcher=_FakeFetcher({_START: _ok(_START)}),
    )
    run = use_case.execute(_BRAND_ID, (_START,), run_id=str(run_id))

    assert run.status is IngestionRunStatus.SUCCEEDED
    snapshots = repository.list_source_snapshots_by_run(run_id)
    assert len(snapshots) == 1  # upsert, not a second row
    assert snapshots[0].content_hash != "old"  # refreshed by the re-fetch


def test_ssrf_rejected_url_is_skipped_unsafe_without_snapshot(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repository = SqliteIngestionRepository(connection)
    unsafe_url = "http://127.0.0.1/"
    fetcher = _FakeFetcher(
        {
            unsafe_url: FetchResult(
                url=unsafe_url,
                final_url=unsafe_url,
                status_code=0,
                error="unsafe:ip_not_global:127.0.0.1",
            )
        }
    )
    use_case = _make_use_case(
        connection,
        discovery=_FakeDiscovery({unsafe_url: (unsafe_url,)}),
        fetcher=fetcher,
    )

    run = use_case.execute(_BRAND_ID, (unsafe_url,))

    targets = repository.list_crawl_targets_by_run(run.id)
    assert len(targets) == 1
    assert targets[0].state is CrawlTargetState.SKIPPED_UNSAFE
    assert repository.list_source_snapshots_by_run(run.id) == ()


def test_cancellation_marks_run_cancelled(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    fetcher = _FakeFetcher({_START: _ok(_START)})
    use_case = _make_use_case(
        connection, discovery=_FakeDiscovery({_START: (_START,)}), fetcher=fetcher
    )
    token = CancellationToken(job_id="job-1")
    token.request_cancel()

    with pytest.raises(CancellationError):
        use_case.execute(_BRAND_ID, (_START,), token=token)

    runs = connection.execute("SELECT id, status FROM ingestion_runs").fetchall()
    assert len(runs) == 1
    assert runs[0]["status"] == IngestionRunStatus.CANCELLED.value
