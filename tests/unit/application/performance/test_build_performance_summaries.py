"""Unit tests for P1.5-G6 analytics read models + builders (Faza 1 v1.5 §21)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from ai_campaign_studio.application.performance.build_performance_summaries import (
    build_campaign_performance_summary,
    build_content_performance_summary,
    build_platform_performance_summary,
)
from ai_campaign_studio.domain.common.ids import (
    CampaignId,
    CampaignItemId,
    DistributionInstanceId,
    PerformanceSnapshotId,
    PostId,
    RevisionId,
)
from ai_campaign_studio.domain.performance.calculator import (
    calculate_derived_metrics,
)
from ai_campaign_studio.domain.performance.entities import (
    DistributionInstance,
    PerformanceSnapshot,
)
from ai_campaign_studio.domain.performance.enums import (
    DistributionSource,
    PerformanceSource,
)
from ai_campaign_studio.domain.performance.metrics import (
    CanonicalMetricSet,
    DerivedMetricSet,
    MetricPeriod,
)


def _instance(
    di_id: str,
    *,
    campaign_id: str = "campaign-1",
    content_piece_id: str = "piece-1",
    platform_code: str = "INSTAGRAM",
) -> DistributionInstance:
    return DistributionInstance(
        id=DistributionInstanceId(di_id),
        campaign_id=CampaignId(campaign_id),
        campaign_item_id=CampaignItemId(f"item-{di_id}"),
        content_piece_id=PostId(content_piece_id),
        content_revision_id=RevisionId(f"rev-{di_id}"),
        channel_code="SOCIAL",
        platform_code=platform_code,
        format_code="FEED_POST",
        distribution_source=DistributionSource.EXPORT,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _snapshot(
    snap_id: str,
    *,
    di_id: str,
    metrics: CanonicalMetricSet,
) -> PerformanceSnapshot:
    observed_at = datetime(2026, 1, 1, tzinfo=UTC)
    return PerformanceSnapshot(
        id=PerformanceSnapshotId(snap_id),
        distribution_instance_id=DistributionInstanceId(di_id),
        period=MetricPeriod(start=observed_at, end=observed_at),
        observed_at=observed_at,
        source=PerformanceSource.CSV_IMPORT,
        metrics=metrics,
    )


class _FakePerformanceRepo:
    """In-memory read-only stand-in for the 4 repo methods builders use."""

    def __init__(
        self,
        instances: tuple[DistributionInstance, ...] = (),
        snapshots: dict[str, tuple[PerformanceSnapshot, ...]] | None = None,
    ) -> None:
        self._instances = list(instances)
        self._snapshots = dict(snapshots or {})

    def list_distribution_instances_by_campaign(
        self, campaign_id: CampaignId
    ) -> tuple[DistributionInstance, ...]:
        cid = str(campaign_id)
        return tuple(i for i in self._instances if str(i.campaign_id) == cid)

    def list_distribution_instances_by_content_piece(
        self, content_piece_id: PostId
    ) -> tuple[DistributionInstance, ...]:
        pid = str(content_piece_id)
        return tuple(
            i for i in self._instances if str(i.content_piece_id) == pid
        )

    def list_distribution_instances_by_platform(
        self, platform_code: str
    ) -> tuple[DistributionInstance, ...]:
        return tuple(
            i for i in self._instances if i.platform_code == platform_code
        )

    def list_performance_snapshots_by_distribution_instance(
        self, distribution_instance_id: DistributionInstanceId
    ) -> tuple[PerformanceSnapshot, ...]:
        did = str(distribution_instance_id)
        return tuple(self._snapshots.get(did, ()))


def test_campaign_summary_zero_instances_gives_empty_summary() -> None:
    repo = _FakePerformanceRepo(instances=())
    summary = build_campaign_performance_summary(repo, CampaignId("campaign-1"))
    assert summary.campaign_id == CampaignId("campaign-1")
    assert summary.distribution_instance_count == 0
    assert summary.raw == CanonicalMetricSet()
    assert summary.derived == DerivedMetricSet()


def test_campaign_summary_sums_across_instances_and_snapshots() -> None:
    inst = _instance("di-1", content_piece_id="piece-1")
    inst2 = _instance("di-2", content_piece_id="piece-2")
    repo = _FakePerformanceRepo(
        instances=(inst, inst2),
        snapshots={
            "di-1": (
                _snapshot(
                    "s1",
                    di_id="di-1",
                    metrics=CanonicalMetricSet(
                        impressions=1000, clicks=10, spend=10.0
                    ),
                ),
                _snapshot(
                    "s2",
                    di_id="di-1",
                    metrics=CanonicalMetricSet(
                        impressions=500, clicks=5, spend=5.0
                    ),
                ),
            ),
            "di-2": (
                _snapshot(
                    "s3",
                    di_id="di-2",
                    metrics=CanonicalMetricSet(
                        impressions=2000, clicks=20, spend=20.0
                    ),
                ),
            ),
        },
    )
    summary = build_campaign_performance_summary(repo, CampaignId("campaign-1"))
    assert summary.distribution_instance_count == 2
    assert summary.raw.impressions == 3500
    assert summary.raw.clicks == 35
    assert summary.raw.spend == 35.0
    # derived is exactly the G5 result of the summed raw (no duplicate formula)
    assert summary.derived == calculate_derived_metrics(summary.raw)
    assert summary.derived.ctr == pytest.approx(35 / 3500)
    assert summary.derived.cpc == pytest.approx(35.0 / 35)
    assert summary.derived.cpm == pytest.approx(35.0 / 3500 * 1000)


def test_none_propagation_when_any_snapshot_lacks_metric() -> None:
    inst = _instance("di-1")
    repo = _FakePerformanceRepo(
        instances=(inst,),
        snapshots={
            "di-1": (
                _snapshot(
                    "s1",
                    di_id="di-1",
                    metrics=CanonicalMetricSet(
                        impressions=1000, clicks=10, spend=10.0
                    ),
                ),
                _snapshot(
                    "s2",
                    di_id="di-1",
                    metrics=CanonicalMetricSet(
                        impressions=500, clicks=5, spend=None
                    ),
                ),
            ),
        },
    )
    summary = build_campaign_performance_summary(repo, CampaignId("campaign-1"))
    # impressions present in both -> summed
    assert summary.raw.impressions == 1500
    # spend missing in one snapshot -> None (not fabricated)
    assert summary.raw.spend is None
    assert summary.derived.cpc is None
    assert summary.derived.cpm is None
    assert summary.derived.roas is None


def test_instance_without_snapshots_counts_but_adds_nothing() -> None:
    inst = _instance("di-1", content_piece_id="piece-1")
    inst2 = _instance("di-2", content_piece_id="piece-2")
    repo = _FakePerformanceRepo(
        instances=(inst, inst2),
        snapshots={
            "di-1": (
                _snapshot(
                    "s1",
                    di_id="di-1",
                    metrics=CanonicalMetricSet(
                        impressions=1000, clicks=10, spend=10.0
                    ),
                ),
            ),
        },
    )
    summary = build_campaign_performance_summary(repo, CampaignId("campaign-1"))
    assert summary.distribution_instance_count == 2
    # di-2 has no snapshots -> contributes nothing to raw
    assert summary.raw.impressions == 1000
    assert summary.derived == calculate_derived_metrics(summary.raw)


def test_content_summary_scopes_by_content_piece() -> None:
    inst_a = _instance("di-a", content_piece_id="piece-a")
    inst_b = _instance("di-b", content_piece_id="piece-b")
    repo = _FakePerformanceRepo(
        instances=(inst_a, inst_b),
        snapshots={
            "di-a": (
                _snapshot(
                    "sa",
                    di_id="di-a",
                    metrics=CanonicalMetricSet(
                        impressions=100, clicks=1, spend=1.0
                    ),
                ),
            ),
            "di-b": (
                _snapshot(
                    "sb",
                    di_id="di-b",
                    metrics=CanonicalMetricSet(
                        impressions=200, clicks=2, spend=2.0
                    ),
                ),
            ),
        },
    )
    summary = build_content_performance_summary(repo, PostId("piece-a"))
    assert summary.content_piece_id == PostId("piece-a")
    assert summary.distribution_instance_count == 1
    assert summary.raw.impressions == 100
    assert summary.derived == calculate_derived_metrics(summary.raw)


def test_platform_summary_scopes_by_platform() -> None:
    inst_a = _instance("di-a", platform_code="INSTAGRAM")
    inst_b = _instance("di-b", platform_code="FACEBOOK")
    repo = _FakePerformanceRepo(
        instances=(inst_a, inst_b),
        snapshots={
            "di-a": (
                _snapshot(
                    "sa",
                    di_id="di-a",
                    metrics=CanonicalMetricSet(
                        impressions=100, clicks=1, spend=1.0
                    ),
                ),
            ),
            "di-b": (
                _snapshot(
                    "sb",
                    di_id="di-b",
                    metrics=CanonicalMetricSet(
                        impressions=200, clicks=2, spend=2.0
                    ),
                ),
            ),
        },
    )
    summary = build_platform_performance_summary(repo, "INSTAGRAM")
    assert summary.platform_code == "INSTAGRAM"
    assert summary.distribution_instance_count == 1
    assert summary.raw.impressions == 100
    assert summary.derived == calculate_derived_metrics(summary.raw)


def test_zero_denominator_yields_none_derived() -> None:
    inst = _instance("di-1")
    repo = _FakePerformanceRepo(
        instances=(inst,),
        snapshots={
            "di-1": (
                _snapshot(
                    "s1",
                    di_id="di-1",
                    metrics=CanonicalMetricSet(
                        impressions=0, clicks=5, spend=10.0
                    ),
                ),
            ),
        },
    )
    summary = build_campaign_performance_summary(repo, CampaignId("campaign-1"))
    assert summary.raw.impressions == 0
    assert summary.derived.ctr is None
    assert summary.derived.cpm is None
    assert summary.derived == calculate_derived_metrics(summary.raw)


def test_summaries_are_frozen() -> None:
    summary = build_campaign_performance_summary(
        _FakePerformanceRepo(instances=()), CampaignId("campaign-1")
    )
    with pytest.raises(FrozenInstanceError):
        summary.distribution_instance_count = 99  # type: ignore[misc]
