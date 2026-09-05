"""Unit tests for the performance domain entities (P1.5-G1)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from ai_campaign_studio.domain.common.ids import (
    CampaignId,
    CampaignItemId,
    DistributionInstanceId,
    PerformanceImportBatchId,
    PerformanceSnapshotId,
    PostId,
    RevisionId,
)
from ai_campaign_studio.domain.performance.entities import (
    DistributionInstance,
    PerformanceImportBatch,
    PerformanceSnapshot,
)
from ai_campaign_studio.domain.performance.enums import (
    DistributionSource,
    PerformanceSource,
)
from ai_campaign_studio.domain.performance.metrics import (
    CanonicalMetricSet,
    MetricPeriod,
)


def _dt() -> datetime:
    return datetime(2026, 1, 1, tzinfo=UTC)


def _distribution_instance() -> DistributionInstance:
    return DistributionInstance(
        id=DistributionInstanceId("di-1"),
        campaign_id=CampaignId("c-1"),
        campaign_item_id=CampaignItemId("ci-1"),
        content_piece_id=PostId("p-1"),
        content_revision_id=RevisionId("r-1"),
        channel_code="SOCIAL",
        platform_code="INSTAGRAM",
        format_code="FEED_POST",
        distribution_source=DistributionSource.EXPORT,
        created_at=_dt(),
    )


def _snapshot() -> PerformanceSnapshot:
    return PerformanceSnapshot(
        id=PerformanceSnapshotId("ps-1"),
        distribution_instance_id=DistributionInstanceId("di-1"),
        period=MetricPeriod(start=_dt(), end=_dt()),
        observed_at=_dt(),
        source=PerformanceSource.CSV_IMPORT,
        metrics=CanonicalMetricSet(),
    )


def _batch() -> PerformanceImportBatch:
    return PerformanceImportBatch(
        id=PerformanceImportBatchId("b-1"),
        source=PerformanceSource.CSV_IMPORT,
        imported_at=_dt(),
        row_count=10,
        matched_count=8,
        unmatched_count=2,
        mapping_version="v1",
    )


def test_distribution_instance_is_frozen() -> None:
    inst = _distribution_instance()
    with pytest.raises(FrozenInstanceError):
        inst.id = DistributionInstanceId("other")  # type: ignore[misc]


def test_performance_snapshot_is_frozen() -> None:
    inst = _snapshot()
    with pytest.raises(FrozenInstanceError):
        inst.source = PerformanceSource.API  # type: ignore[misc]


def test_performance_import_batch_is_frozen() -> None:
    batch = _batch()
    with pytest.raises(FrozenInstanceError):
        batch.row_count = 11  # type: ignore[misc]


def test_distribution_instance_optional_fields_default_none() -> None:
    inst = _distribution_instance()
    assert inst.external_account_id is None
    assert inst.external_content_id is None
    assert inst.published_at is None


def test_snapshot_optional_fields_default() -> None:
    snap = _snapshot()
    assert snap.source_batch_id is None
    assert snap.raw_metrics == {}


def test_raw_metrics_default_not_shared_between_instances() -> None:
    s1 = _snapshot()
    s2 = _snapshot()
    assert s1.raw_metrics is not s2.raw_metrics
    s1.raw_metrics["reach"] = 100
    assert "reach" not in s2.raw_metrics
