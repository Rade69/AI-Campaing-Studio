"""Unit tests for the performance metric primitives (P1.5-G1)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from ai_campaign_studio.domain.common.errors import InvariantViolation
from ai_campaign_studio.domain.performance.metrics import (
    CanonicalMetricSet,
    DerivedMetricSet,
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


def test_derived_metric_set_all_default_none() -> None:
    derived = DerivedMetricSet()
    assert derived.ctr is None
    assert derived.cpc is None
    assert derived.cpm is None
    assert derived.cpa is None
    assert derived.roas is None
    assert derived.conversion_rate is None


def test_derived_metric_set_holds_values() -> None:
    derived = DerivedMetricSet(ctr=0.034, roas=2.5)
    assert derived.ctr == 0.034
    assert derived.roas == 2.5
    # fields not set remain None
    assert derived.cpa is None


def test_derived_metric_set_is_frozen() -> None:
    derived = DerivedMetricSet(ctr=0.034)
    with pytest.raises(FrozenInstanceError):
        derived.ctr = 0.5  # type: ignore[misc]
