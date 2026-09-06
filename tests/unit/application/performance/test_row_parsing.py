"""Unit tests for CSV row parsing/validation (P1.5-G3 dio 1)."""

from datetime import datetime

from ai_campaign_studio.application.performance.column_mapping import (
    ColumnMatch,
    load_column_aliases,
    map_columns,
)
from ai_campaign_studio.application.performance.row_parsing import parse_rows
from ai_campaign_studio.domain.performance.metrics import (
    CanonicalMetricSet,
    MetricPeriod,
)


def _match(field: str, header: str) -> ColumnMatch:
    return ColumnMatch(field, header, "matched", (header,))


def _matches(pairs: list[tuple[str, str]]) -> tuple[ColumnMatch, ...]:
    return tuple(_match(field, header) for field, header in pairs)


def test_valid_row() -> None:
    matches = _matches(
        [
            ("period_start", "period_start"),
            ("period_end", "period_end"),
            ("reach", "reach"),
            ("spend", "spend"),
        ]
    )
    raw = (
        {
            "period_start": "2026-01-01",
            "period_end": "2026-01-31",
            "reach": "100",
            "spend": "10.5",
        },
    )
    rows = parse_rows(raw, matches)
    assert len(rows) == 1
    assert rows[0].row_number == 1
    assert rows[0].errors == ()
    assert rows[0].mapped_values == {
        "period_start": "2026-01-01",
        "period_end": "2026-01-31",
        "reach": "100",
        "spend": "10.5",
    }


def test_missing_required_period() -> None:
    matches = _matches([("period_end", "period_end"), ("reach", "reach")])
    raw = ({"period_end": "2026-01-31", "reach": "100"},)
    rows = parse_rows(raw, matches)
    assert "period_start is required" in rows[0].errors


def test_empty_required_period() -> None:
    matches = _matches(
        [("period_start", "period_start"), ("period_end", "period_end"),
         ("reach", "reach")]
    )
    raw = ({"period_start": "", "period_end": "2026-01-31", "reach": "100"},)
    rows = parse_rows(raw, matches)
    assert "period_start is required" in rows[0].errors


def test_non_numeric_metric() -> None:
    matches = _matches(
        [
            ("period_start", "period_start"),
            ("period_end", "period_end"),
            ("reach", "reach"),
        ]
    )
    raw = (
        {"period_start": "2026-01-01", "period_end": "2026-01-31", "reach": "abc"},
    )
    rows = parse_rows(raw, matches)
    assert "reach (abc) is not a number" in rows[0].errors


def test_invalid_date() -> None:
    matches = _matches(
        [
            ("period_start", "period_start"),
            ("period_end", "period_end"),
            ("reach", "reach"),
        ]
    )
    raw = (
        {"period_start": "2026-01-01", "period_end": "2026-13-40", "reach": "100"},
    )
    rows = parse_rows(raw, matches)
    assert "period_end (2026-13-40) is not a valid date" in rows[0].errors


def test_end_before_start() -> None:
    matches = _matches(
        [
            ("period_start", "period_start"),
            ("period_end", "period_end"),
            ("reach", "reach"),
        ]
    )
    raw = (
        {"period_start": "2026-02-01", "period_end": "2026-01-01", "reach": "100"},
    )
    rows = parse_rows(raw, matches)
    assert any("precedes" in error for error in rows[0].errors)


def test_negative_metric() -> None:
    matches = _matches(
        [
            ("period_start", "period_start"),
            ("period_end", "period_end"),
            ("reach", "reach"),
        ]
    )
    raw = (
        {"period_start": "2026-01-01", "period_end": "2026-01-31", "reach": "-5"},
    )
    rows = parse_rows(raw, matches)
    assert "reach (-5) cannot be negative" in rows[0].errors


def test_non_integer_int_metric() -> None:
    matches = _matches(
        [
            ("period_start", "period_start"),
            ("period_end", "period_end"),
            ("reach", "reach"),
        ]
    )
    raw = (
        {"period_start": "2026-01-01", "period_end": "2026-01-31", "reach": "100.5"},
    )
    rows = parse_rows(raw, matches)
    assert "reach (100.5) is not an integer" in rows[0].errors


def test_only_unknown_columns_invalid() -> None:
    matches: tuple[ColumnMatch, ...] = ()
    raw = ({"note": "hello", "other": "x"},)
    rows = parse_rows(raw, matches)
    assert "no numeric metric present" in rows[0].errors
    assert "period_start is required" in rows[0].errors


def test_no_mapped_metric_invalid() -> None:
    matches = _matches([("period_start", "period_start"), ("period_end", "period_end")])
    raw = (
        {
            "period_start": "2026-01-01",
            "period_end": "2026-01-31",
            "note": "extra",
        },
    )
    rows = parse_rows(raw, matches)
    assert "no numeric metric present" in rows[0].errors


def test_all_mapped_metrics_empty_invalid() -> None:
    matches = _matches(
        [("period_start", "period_start"), ("period_end", "period_end"),
         ("reach", "reach")]
    )
    raw = (
        {"period_start": "2026-01-01", "period_end": "2026-01-31", "reach": ""},
    )
    rows = parse_rows(raw, matches)
    assert "no numeric metric present" in rows[0].errors


def test_raw_values_preserves_unmapped_columns() -> None:
    matches = _matches(
        [
            ("period_start", "period_start"),
            ("period_end", "period_end"),
            ("reach", "reach"),
        ]
    )
    raw = (
        {
            "period_start": "2026-01-01",
            "period_end": "2026-01-31",
            "reach": "100",
            "campaign": "cmp_1",
            "note": "x",
        },
    )
    rows = parse_rows(raw, matches)
    assert rows[0].raw_values == raw[0]
    assert rows[0].raw_values["campaign"] == "cmp_1"
    assert rows[0].raw_values["note"] == "x"
    assert "campaign" not in rows[0].mapped_values
    assert "note" not in rows[0].mapped_values


def test_invalid_row_never_dropped() -> None:
    matches = _matches(
        [
            ("period_start", "period_start"),
            ("period_end", "period_end"),
            ("reach", "reach"),
        ]
    )
    raw = (
        {"period_start": "2026-01-01", "period_end": "2026-01-31", "reach": "100"},
        {"period_start": "garbage", "period_end": "2026-01-31", "reach": "abc"},
    )
    rows = parse_rows(raw, matches)
    assert len(rows) == 2
    assert rows[0].errors == ()
    assert rows[1].errors != ()
    assert rows[1].row_number == 2
    assert "period_start (garbage) is not a valid date" in rows[1].errors
    assert "reach (abc) is not a number" in rows[1].errors


def test_mapped_values_shape_matches_domain_models() -> None:
    matches = _matches(
        [
            ("period_start", "period_start"),
            ("period_end", "period_end"),
            ("reach", "reach"),
            ("spend", "spend"),
            ("watch_time_seconds", "watch_time_seconds"),
        ]
    )
    raw = (
        {
            "period_start": "2026-01-01",
            "period_end": "2026-01-31",
            "reach": "100",
            "spend": "10.5",
            "watch_time_seconds": "30.0",
        },
    )
    row = parse_rows(raw, matches)[0]
    assert row.errors == ()

    # Prove canonical field names/types are compatible with the domain
    # models by constructing them BY HAND from mapped_values (dio 2 will do
    # this inside the real use-cases).
    metrics = CanonicalMetricSet(
        reach=int(row.mapped_values["reach"]),
        spend=float(row.mapped_values["spend"]),
        watch_time_seconds=float(row.mapped_values["watch_time_seconds"]),
    )
    assert metrics.reach == 100
    assert metrics.spend == 10.5
    assert metrics.watch_time_seconds == 30.0

    period = MetricPeriod(
        start=datetime.fromisoformat(row.mapped_values["period_start"]),
        end=datetime.fromisoformat(row.mapped_values["period_end"]),
    )
    assert period.start == datetime(2026, 1, 1)
    assert period.end == datetime(2026, 1, 31)


def test_end_to_end_bhs_headers() -> None:
    rules = load_column_aliases()
    headers = ("datum_pocetka", "datum_kraja", "doseg", "trošak", "kampanja")
    matches = map_columns(headers, rules)
    raw = (
        {
            "datum_pocetka": "2026-01-01",
            "datum_kraja": "2026-01-31",
            "doseg": "100",
            "trošak": "12.5",
            "kampanja": "cmp_1",
        },
    )
    rows = parse_rows(raw, matches)
    assert rows[0].errors == ()
    assert rows[0].mapped_values["period_start"] == "2026-01-01"
    assert rows[0].mapped_values["period_end"] == "2026-01-31"
    assert rows[0].mapped_values["reach"] == "100"
    assert rows[0].mapped_values["spend"] == "12.5"
    assert "kampanja" in rows[0].raw_values
    assert "kampanja" not in rows[0].mapped_values
