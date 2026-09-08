"""Performance metric primitives (Faza 0.7 §6, Faza 1 v1.5 §20).

``CanonicalMetricSet`` holds 9 optional raw metrics; ``DerivedMetricSet``
holds 6 optional derived metrics (CTR/CPC/CPM/CPA/ROAS/Conversion Rate).
Validation and derivation live in ``calculator.py`` (P1.5-G5), not here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ai_campaign_studio.domain.common.errors import InvariantViolation


@dataclass(frozen=True)
class CanonicalMetricSet:
    """9 platform-neutral metrics (Faza 0.7 §6).

    All optional — not every platform/source supports the same metrics.
    Value validation (e.g. negative numbers) is deliberately NOT here;
    that is P1.5-G5 Metric Calculator's job (per Faza 1 v1.5 §20).
    """

    reach: int | None = None
    impressions: int | None = None
    engagements: int | None = None
    clicks: int | None = None
    conversions: int | None = None
    spend: float | None = None
    revenue: float | None = None
    video_views: int | None = None
    watch_time_seconds: float | None = None


@dataclass(frozen=True)
class DerivedMetricSet:
    """Six derived metrics (P1.5-G5, Faza 1 v1.5 §20).

    All optional — a metric is ``None`` when any required raw input is
    missing, negative, non-finite, or its denominator is zero (see
    ``calculator.calculate_derived_metrics``). CTR and Conversion Rate are
    RATIOS (0.034 == 3.4%), not percentages — one consistent choice for both
    percent-style metrics.
    """

    ctr: float | None = None               # clicks / impressions
    cpc: float | None = None               # spend / clicks
    cpm: float | None = None               # spend / impressions * 1000
    cpa: float | None = None               # spend / conversions
    roas: float | None = None              # revenue / spend
    conversion_rate: float | None = None   # conversions / clicks


@dataclass(frozen=True)
class MetricPeriod:
    """A reporting period as one value object.

    ``end`` must not precede ``start``. ``end == start`` is a valid
    (zero-length) period, so the invariant is strictly ``<``, not ``<=``.
    """

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise InvariantViolation(
                f"MetricPeriod.end ({self.end}) cannot precede"
                f" MetricPeriod.start ({self.start})"
            )
