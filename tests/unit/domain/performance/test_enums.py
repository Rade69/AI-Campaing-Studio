"""Unit tests for the performance domain enums (P1.5-G1)."""

from __future__ import annotations

from ai_campaign_studio.domain.performance.enums import (
    DistributionSource,
    PerformanceSource,
)


def test_distribution_source_has_exactly_four_values() -> None:
    assert {m.value for m in DistributionSource} == {
        "EXPORT",
        "MANUAL",
        "CSV_IMPORT",
        "API",
    }


def test_performance_source_has_exactly_three_values() -> None:
    assert {m.value for m in PerformanceSource} == {
        "CSV_IMPORT",
        "MANUAL",
        "API",
    }


def test_sources_are_distinct_enum_types() -> None:
    assert DistributionSource is not PerformanceSource
    assert "EXPORT" not in {m.value for m in PerformanceSource}
