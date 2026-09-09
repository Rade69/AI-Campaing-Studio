"""Unit tests for the ingestion domain entities (S2-G1)."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from ai_campaign_studio.domain.common.ids import (
    BrandId,
    IngestionCheckpointId,
    IngestionRunId,
    SourceChunkId,
    SourceSnapshotId,
)
from ai_campaign_studio.domain.ingestion.entities import (
    IngestionCheckpoint,
    IngestionRun,
    IngestionRunStats,
    SourceChunk,
    SourceSnapshot,
)
from ai_campaign_studio.domain.ingestion.enums import (
    IngestionPhase,
    IngestionRunStatus,
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
    from ai_campaign_studio.domain.ingestion.enums import PageType

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
