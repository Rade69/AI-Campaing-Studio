"""Unit tests for the ingestion domain entities (S2-G1)."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from ai_campaign_studio.domain.common.ids import (
    BrandId,
    CrawlTargetId,
    IngestionCheckpointId,
    IngestionRunId,
    SourceChunkId,
    SourceSnapshotId,
)
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

_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def test_source_snapshot_is_frozen_and_keeps_raw_out_of_line() -> None:
    snapshot = SourceSnapshot(
        id=SourceSnapshotId("snap-1"),
        url="https://example.com/about",
        fetched_at=_CREATED_AT,
        content_hash="abc123",
        raw_content_ref="store://snap-1",
    )
    assert snapshot.raw_content_ref == "store://snap-1"
    with pytest.raises(FrozenInstanceError):
        snapshot.content_hash = "changed"


def test_source_chunk_carries_locator_precise_reference() -> None:
    chunk = SourceChunk(
        id=SourceChunkId("chunk-1"),
        snapshot_id=SourceSnapshotId("snap-1"),
        locator_type="css_selector",
        locator="#main > p:nth-child(2)",
        text="We offer implantology.",
    )
    assert chunk.snapshot_id == SourceSnapshotId("snap-1")
    assert chunk.text == "We offer implantology."
    with pytest.raises(FrozenInstanceError):
        chunk.text = "changed"


def test_ingestion_run_coerces_source_scope_to_tuple() -> None:
    run = IngestionRun(
        id=IngestionRunId("run-1"),
        brand_id=BrandId("brand-1"),
        status=IngestionRunStatus.RUNNING,
        started_at=_CREATED_AT,
        source_scope=["https://example.com/", "https://example.com/sitemap.xml"],
    )
    assert isinstance(run.source_scope, tuple)
    assert run.source_scope == (
        "https://example.com/",
        "https://example.com/sitemap.xml",
    )


def test_ingestion_run_stats_default_to_zero() -> None:
    stats = IngestionRunStats()
    assert stats.discovered_urls == 0
    assert stats.fetched_pages == 0
    assert stats.extracted_chunks == 0
    assert stats.built_candidates == 0
    assert stats.failed_pages == 0


def test_ingestion_checkpoint_records_last_completed_phase() -> None:
    checkpoint = IngestionCheckpoint(
        id=IngestionCheckpointId("cp-1"),
        run_id=IngestionRunId("run-1"),
        phase=IngestionPhase.FETCH,
        finished_at=_CREATED_AT,
    )
    assert checkpoint.phase is IngestionPhase.FETCH
    with pytest.raises(FrozenInstanceError):
        checkpoint.phase = IngestionPhase.DONE


def test_page_type_covers_canonical_plan_vocabulary() -> None:
    """PageType exposes every bucket from canonical plan §8 (ARTICLE/BLOG
    kept as two separate values)."""

    values = {p.value for p in PageType}
    expected = {
        "HOME",
        "ABOUT",
        "PRODUCT",
        "SERVICE",
        "PRICING",
        "FAQ",
        "SHIPPING",
        "RETURNS",
        "CONTACT",
        "CATEGORY",
        "ARTICLE",
        "BLOG",
        "LEGAL",
        "OTHER",
    }
    assert expected <= values


def _crawl_target(state: CrawlTargetState = CrawlTargetState.PENDING) -> CrawlTarget:
    return CrawlTarget(
        id=CrawlTargetId("ct-1"),
        run_id=IngestionRunId("run-1"),
        normalized_url="https://example.com/about",
        depth=1,
        priority=0,
        state=state,
        attempts=0,
    )


def test_crawl_target_is_frozen() -> None:
    target = _crawl_target()
    with pytest.raises(FrozenInstanceError):
        target.state = CrawlTargetState.LEASED
    with pytest.raises(FrozenInstanceError):
        target.priority = 5


def test_crawl_target_optional_fields_default_to_none() -> None:
    target = _crawl_target()
    assert target.page_type_hint is None
    assert target.lease_until is None
    assert target.next_attempt_at is None
    assert target.last_error is None


def test_crawl_target_state_covers_lease_queue_machine() -> None:
    expected = {
        "PENDING",
        "LEASED",
        "FETCHED",
        "EXTRACTED",
        "DONE",
        "FAILED_RETRYABLE",
        "FAILED",
        "SKIPPED_ROBOTS",
        "SKIPPED_UNSAFE",
        "TOO_LARGE",
        "CANCELLED",
    }
    assert {s.value for s in CrawlTargetState} == expected
