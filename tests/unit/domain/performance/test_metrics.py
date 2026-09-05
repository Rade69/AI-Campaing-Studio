"""Unit tests for the performance metric primitives (P1.5-G1)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ai_campaign_studio.domain.common.errors import InvariantViolation
from ai_campaign_studio.domain.performance.metrics import (
    CanonicalMetricSet,
    MetricPeriod,
)


def test_canonical_metric_set_all_default_none() -> None:
    metrics = CanonicalMetricSet()
    assert metrics.reach is None
    assert metrics.impressions is None
    assert metrics.engagements is None
    assert metrics.clicks is None
    assert metrics.conversions is None
    assert metrics.spend is None
    assert metrics.revenue is None
    assert metrics.video_views is None
    assert metrics.watch_time_seconds is None


def test_canonical_metric_set_holds_values() -> None:
    metrics = CanonicalMetricSet(reach=100, spend=12.5)
    assert metrics.reach == 100
    assert metrics.spend == 12.5
    # fields not set remain None
    assert metrics.clicks is None


def test_metric_period_accepts_end_equal_start() -> None:
    t = datetime(2026, 1, 1, tzinfo=UTC)
    period = MetricPeriod(start=t, end=t)
    assert period.start == period.end


def test_metric_period_accepts_end_after_start() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 1, 2, tzinfo=UTC)
    period = MetricPeriod(start=start, end=end)
    assert period.end > period.start


def test_metric_period_rejects_end_before_start() -> None:
    start = datetime(2026, 1, 2, tzinfo=UTC)
    end = datetime(2026, 1, 1, tzinfo=UTC)
    with pytest.raises(InvariantViolation):
        MetricPeriod(start=start, end=end)
