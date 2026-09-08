"""P1.5-G6 analytics read models + builders (Faza 1 v1.5 §21).

Owns the three minimal aggregation read models (Campaign/Content/Platform
``PerformanceSummary``) and the pure builder functions that compute them from
``PerformanceRepositoryPort`` reads. Derived metrics come ONLY from
``calculate_derived_metrics`` (P1.5-G5) — no formula is re-implemented here.

Aggregation semantics (documented, one consistent choice): raw metrics are
SUMMED across ALL snapshots of the matched distribution instances, with
None-propagation — a metric's aggregate is ``None`` if ANY contributing
snapshot lacks that metric (missing data is not zero, same principle as G5).
Distribution instances with zero snapshots contribute nothing to ``raw`` but
still count toward ``distribution_instance_count``. No persistence, no SQL,
no bridge.
"""

from __future__ import annotations

from dataclasses import dataclass

from ai_campaign_studio.domain.common.ids import CampaignId, PostId
from ai_campaign_studio.domain.performance.calculator import (
    calculate_derived_metrics,
)
from ai_campaign_studio.domain.performance.entities import (
    DistributionInstance,
    PerformanceSnapshot,
)
from ai_campaign_studio.domain.performance.metrics import (
    CanonicalMetricSet,
    DerivedMetricSet,
)
from ai_campaign_studio.ports.repositories import PerformanceRepositoryPort


@dataclass(frozen=True)
class CampaignPerformanceSummary:
    campaign_id: CampaignId
    derived: DerivedMetricSet
    raw: CanonicalMetricSet
    distribution_instance_count: int


@dataclass(frozen=True)
class ContentPerformanceSummary:
    content_piece_id: PostId
    derived: DerivedMetricSet
    raw: CanonicalMetricSet
    distribution_instance_count: int


@dataclass(frozen=True)
class PlatformPerformanceSummary:
    platform_code: str
    derived: DerivedMetricSet
    raw: CanonicalMetricSet
    distribution_instance_count: int


def build_campaign_performance_summary(
    repo: PerformanceRepositoryPort, campaign_id: CampaignId
) -> CampaignPerformanceSummary:
    instances = repo.list_distribution_instances_by_campaign(campaign_id)
    raw, derived, count = _aggregate(repo, instances)
    return CampaignPerformanceSummary(
        campaign_id=campaign_id,
        derived=derived,
        raw=raw,
        distribution_instance_count=count,
    )


def build_content_performance_summary(
    repo: PerformanceRepositoryPort, content_piece_id: PostId
) -> ContentPerformanceSummary:
    instances = repo.list_distribution_instances_by_content_piece(
        content_piece_id
    )
    raw, derived, count = _aggregate(repo, instances)
    return ContentPerformanceSummary(
        content_piece_id=content_piece_id,
        derived=derived,
        raw=raw,
        distribution_instance_count=count,
    )


def build_platform_performance_summary(
    repo: PerformanceRepositoryPort, platform_code: str
) -> PlatformPerformanceSummary:
    instances = repo.list_distribution_instances_by_platform(platform_code)
    raw, derived, count = _aggregate(repo, instances)
    return PlatformPerformanceSummary(
        platform_code=platform_code,
        derived=derived,
        raw=raw,
        distribution_instance_count=count,
    )


def _aggregate(
    repo: PerformanceRepositoryPort,
    instances: tuple[DistributionInstance, ...],
) -> tuple[CanonicalMetricSet, DerivedMetricSet, int]:
    """Collect all snapshots for the given instances and derive the totals.

    Returns ``(raw_sum, derived, instance_count)``. ``derived`` is always
    ``calculate_derived_metrics(raw_sum)`` — never a hand-written formula.
    """
    snapshots: list[PerformanceSnapshot] = []
    for instance in instances:
        snapshots.extend(
            repo.list_performance_snapshots_by_distribution_instance(
                instance.id
            )
        )
    raw = _sum_metrics(tuple(snapshots))
    return raw, calculate_derived_metrics(raw), len(instances)


def _sum_metrics(
    snapshots: tuple[PerformanceSnapshot, ...],
) -> CanonicalMetricSet:
    """Sum raw metrics across snapshots with None-propagation.

    Zero snapshots -> all-``None`` set. Otherwise each field is the sum of
    that field across snapshots, or ``None`` if ANY snapshot has ``None`` for
    it (we refuse to fabricate a total from incomplete data).
    """
    if not snapshots:
        return CanonicalMetricSet()
    return CanonicalMetricSet(
        reach=_sum_ints(tuple(s.metrics.reach for s in snapshots)),
        impressions=_sum_ints(tuple(s.metrics.impressions for s in snapshots)),
        engagements=_sum_ints(tuple(s.metrics.engagements for s in snapshots)),
        clicks=_sum_ints(tuple(s.metrics.clicks for s in snapshots)),
        conversions=_sum_ints(tuple(s.metrics.conversions for s in snapshots)),
        video_views=_sum_ints(tuple(s.metrics.video_views for s in snapshots)),
        spend=_sum_floats(tuple(s.metrics.spend for s in snapshots)),
        revenue=_sum_floats(tuple(s.metrics.revenue for s in snapshots)),
        watch_time_seconds=_sum_floats(
            tuple(s.metrics.watch_time_seconds for s in snapshots)
        ),
    )


def _sum_ints(values: tuple[int | None, ...]) -> int | None:
    total = 0
    for value in values:
        if value is None:
            return None
        total += value
    return total


def _sum_floats(values: tuple[float | None, ...]) -> float | None:
    total = 0.0
    for value in values:
        if value is None:
            return None
        total += value
    return total
