"""Unit tests for CSV column mapping (P1.5-G3 dio 1)."""

from ai_campaign_studio.application.performance.column_mapping import (
    ColumnAliasRules,
    load_column_aliases,
    map_columns,
)


def _rules() -> ColumnAliasRules:
    """Small hand-built rule set so unit tests do not depend on YAML."""
    return ColumnAliasRules(
        version="1",
        column_aliases={
            "platform_code": ("platform_code", "platform"),
            "period_start": ("period_start", "start"),
            "period_end": ("period_end", "end"),
            "reach": ("reach",),
            "impressions": ("impressions",),
            "spend": ("spend", "cost"),
        },
    )


def test_load_column_aliases_reads_default_yaml() -> None:
    rules = load_column_aliases()  # bundled default path
    assert rules.version == "1"
    assert "spend" in rules.column_aliases
    assert "period_start" in rules.column_aliases
    assert "watch_time_seconds" in rules.column_aliases


def test_default_yaml_contains_bhs_aliases() -> None:
    rules = load_column_aliases()
    aliases = rules.column_aliases
    # BHS Latin aliases exist across the metrics (spot checks).
    assert "trošak" in aliases["spend"]
    assert "potrošnja" in aliases["spend"]
    assert "prikazi" in aliases["impressions"]
    assert "doseg" in aliases["reach"]
    assert "klikovi" in aliases["clicks"]
    assert "konverzije" in aliases["conversions"]
    assert "prihod" in aliases["revenue"]
    assert "pregledi_videa" in aliases["video_views"]
    assert "angažmani" in aliases["engagements"]
    assert "datum_pocetka" in aliases["period_start"]
    assert "datum_kraja" in aliases["period_end"]


def test_map_columns_all_matched() -> None:
    rules = _rules()
    matches = map_columns(
        ("platform_code", "period_start", "period_end", "reach",
         "impressions", "spend"),
        rules,
    )
    assert [m.canonical_field for m in matches] == list(rules.column_aliases)
    assert all(m.status == "matched" for m in matches)
    spend = next(m for m in matches if m.canonical_field == "spend")
    assert spend.header == "spend"
    assert spend.candidates == ("spend",)


def test_map_columns_ambiguous_two_headers_same_field() -> None:
    rules = _rules()
    matches = map_columns(("spend", "cost"), rules)
    spend = next(m for m in matches if m.canonical_field == "spend")
    assert spend.status == "ambiguous"
    assert spend.header is None
    assert spend.candidates == ("spend", "cost")


def test_map_columns_unmatched_field() -> None:
    rules = _rules()
    matches = map_columns(("reach", "platform_code"), rules)
    impressions = next(m for m in matches if m.canonical_field == "impressions")
    assert impressions.status == "unmatched"
    assert impressions.header is None
    assert impressions.candidates == ()


def test_map_columns_ignores_extra_columns_without_error() -> None:
    rules = _rules()
    matches = map_columns(("note", "reach", "other"), rules)
    # One match per canonical field, none for the unknown headers, no error.
    assert len(matches) == len(rules.column_aliases)
    assert {m.canonical_field for m in matches} == set(rules.column_aliases)
    assert all(m.header not in {"note", "other"} for m in matches)
    reach = next(m for m in matches if m.canonical_field == "reach")
    assert reach.status == "matched"
    assert reach.header == "reach"


def test_map_columns_is_case_insensitive() -> None:
    rules = _rules()
    matches = map_columns(("SPEND", "Reach"), rules)
    spend = next(m for m in matches if m.canonical_field == "spend")
    reach = next(m for m in matches if m.canonical_field == "reach")
    assert spend.status == "matched"
    assert spend.header == "SPEND"  # original casing preserved
    assert reach.status == "matched"
    assert reach.header == "Reach"


def test_map_columns_is_deterministic() -> None:
    rules = _rules()
    headers = ("spend", "cost", "reach", "platform_code")
    assert map_columns(headers, rules) == map_columns(headers, rules)
