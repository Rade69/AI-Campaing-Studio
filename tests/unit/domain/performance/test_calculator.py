"""Unit tests for the P1.5-G5 derived metric calculator (Faza 1 v1.5 §20)."""

from __future__ import annotations

import math

import pytest

from ai_campaign_studio.domain.performance.calculator import (
    calculate_derived_metrics,
)
from ai_campaign_studio.domain.performance.metrics import (
    CanonicalMetricSet,
    DerivedMetricSet,
)

_ALL_FIELD_NAMES = ("ctr", "cpc", "cpm", "cpa", "roas", "conversion_rate")


def _base() -> dict[str, int | float]:
    return {
        "impressions": 1000,
        "clicks": 10,
        "conversions": 5,
        "spend": 100.0,
        "revenue": 200.0,
    }


def _assert_nones_match(
    result_metrics: DerivedMetricSet, expected_none: set[str]
) -> None:
    values = {
        "ctr": result_metrics.ctr,
        "cpc": result_metrics.cpc,
        "cpm": result_metrics.cpm,
        "cpa": result_metrics.cpa,
        "roas": result_metrics.roas,
        "conversion_rate": result_metrics.conversion_rate,
    }
    for name in _ALL_FIELD_NAMES:
        if name in expected_none:
            assert values[name] is None, f"{name} should be None"
        else:
            assert values[name] is not None, f"{name} should be computed"


def test_all_metrics_normal_case() -> None:
    metrics = CanonicalMetricSet(
        impressions=1000,
        clicks=34,
        conversions=5,
        spend=200.0,
        revenue=500.0,
    )
    result = calculate_derived_metrics(metrics)

    # hand-computed values (not just "not None")
    assert result.ctr == pytest.approx(34 / 1000)  # 0.034
    assert result.cpc == pytest.approx(200.0 / 34)  # ~5.8824
    assert result.cpm == pytest.approx(200.0 / 1000 * 1000)  # 200.0
    assert result.cpa == pytest.approx(200.0 / 5)  # 40.0
    assert result.roas == pytest.approx(500.0 / 200.0)  # 2.5
    assert result.conversion_rate == pytest.approx(5 / 34)  # ~0.1471


def test_ctr_and_conversion_rate_are_ratios_not_percentages() -> None:
    result = calculate_derived_metrics(
        CanonicalMetricSet(impressions=1000, clicks=34, conversions=5)
    )
    # 34 clicks / 1000 impressions = 0.034 (a ratio), NOT 3.4
    assert result.ctr == pytest.approx(0.034)
    assert result.conversion_rate == pytest.approx(5 / 34)


def test_all_none_inputs_gives_all_none() -> None:
    result = calculate_derived_metrics(CanonicalMetricSet())
    assert result.ctr is None
    assert result.cpc is None
    assert result.cpm is None
    assert result.cpa is None
    assert result.roas is None
    assert result.conversion_rate is None


def test_zero_impressions_nulls_ctr_and_cpm_only() -> None:
    result = calculate_derived_metrics(
        CanonicalMetricSet(
            impressions=0, clicks=10, conversions=5, spend=100.0, revenue=200.0
        )
    )
    assert result.ctr is None
    assert result.cpm is None
    # metrics that do not need impressions still compute
    assert result.cpc == pytest.approx(100.0 / 10)
    assert result.cpa == pytest.approx(100.0 / 5)
    assert result.roas == pytest.approx(200.0 / 100.0)
    assert result.conversion_rate == pytest.approx(5 / 10)


def test_zero_clicks_nulls_cpc_and_conversion_rate() -> None:
    result = calculate_derived_metrics(
        CanonicalMetricSet(
            impressions=1000, clicks=0, conversions=5, spend=100.0, revenue=200.0
        )
    )
    assert result.cpc is None
    assert result.conversion_rate is None
    # zero numerator with positive denominator is a valid zero result
    assert result.ctr == 0.0
    assert result.cpm == pytest.approx(100.0 / 1000 * 1000)
    assert result.cpa == pytest.approx(100.0 / 5)
    assert result.roas == pytest.approx(200.0 / 100.0)


def test_zero_conversions_nulls_cpa_only() -> None:
    result = calculate_derived_metrics(
        CanonicalMetricSet(
            impressions=1000, clicks=10, conversions=0, spend=100.0, revenue=200.0
        )
    )
    assert result.cpa is None
    assert result.ctr == pytest.approx(10 / 1000)
    assert result.cpc == pytest.approx(100.0 / 10)
    assert result.cpm == pytest.approx(100.0 / 1000 * 1000)
    assert result.roas == pytest.approx(200.0 / 100.0)
    assert result.conversion_rate == 0.0


def test_zero_spend_nulls_roas_and_zeroes_cpc_cpm() -> None:
    result = calculate_derived_metrics(
        CanonicalMetricSet(
            impressions=1000, clicks=10, conversions=5, spend=0.0, revenue=200.0
        )
    )
    # spend is denominator of ROAS -> None; numerator of CPC/CPM/CPA -> 0.0
    assert result.roas is None
    assert result.cpc == 0.0
    assert result.cpm == 0.0
    assert result.cpa == 0.0
    assert result.ctr == pytest.approx(10 / 1000)
    assert result.conversion_rate == pytest.approx(5 / 10)


@pytest.mark.parametrize(
    ("field", "expected_none"),
    [("impressions", {"ctr", "cpm"}),
     ("clicks", {"ctr", "cpc", "conversion_rate"}),
     ("conversions", {"cpa", "conversion_rate"}),
     ("spend", {"cpc", "cpm", "cpa", "roas"}),
     ("revenue", {"roas"})],
)
def test_missing_input_nulls_exactly_dependent_metrics(
    field: str, expected_none: set[str]
) -> None:
    values = _base()
    del values[field]  # field falls back to its None default
    result = calculate_derived_metrics(CanonicalMetricSet(**values))
    _assert_nones_match(result, expected_none)


@pytest.mark.parametrize(
    ("field", "negative_value", "expected_none"),
    [("impressions", -1, {"ctr", "cpm"}),
     ("clicks", -10, {"ctr", "cpc", "conversion_rate"}),
     ("conversions", -5, {"cpa", "conversion_rate"}),
     ("spend", -100.0, {"cpc", "cpm", "cpa", "roas"}),
     ("revenue", -200.0, {"roas"})],
)
def test_negative_input_nulls_exactly_dependent_metrics(
    field: str, negative_value: int | float, expected_none: set[str]
) -> None:
    values = _base()
    values[field] = negative_value
    result = calculate_derived_metrics(CanonicalMetricSet(**values))
    _assert_nones_match(result, expected_none)


def test_non_finite_inputs_are_treated_as_invalid() -> None:
    result = calculate_derived_metrics(
        CanonicalMetricSet(
            impressions=1000,
            clicks=10,
            conversions=5,
            spend=float("inf"),
            revenue=float("nan"),
        )
    )
    # spend is inf -> CPC/CPM/CPA/ROAS all None; revenue nan -> ROAS None too
    assert result.cpc is None
    assert result.cpm is None
    assert result.cpa is None
    assert result.roas is None
    # metrics not using spend/revenue still compute
    assert result.ctr == pytest.approx(10 / 1000)
    assert result.conversion_rate == pytest.approx(5 / 10)


def test_no_result_is_nan_or_inf() -> None:
    result = calculate_derived_metrics(CanonicalMetricSet(**_base()))
    for value in (
        result.ctr,
        result.cpc,
        result.cpm,
        result.cpa,
        result.roas,
        result.conversion_rate,
    ):
        assert value is not None
        assert math.isfinite(value)
