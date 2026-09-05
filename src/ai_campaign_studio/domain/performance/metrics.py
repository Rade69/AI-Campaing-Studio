"""Performance metric primitives (Faza 0.7 §6)."""

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
