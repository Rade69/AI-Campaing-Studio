"""CSV row parsing + validation (P1.5-G3 dio 1, Faza 0.7 §5/§6).

Owns turning already-read ``dict[str, str]`` CSV rows into ``ParsedRow``
objects: keeps every original value (``raw_values``), maps matched columns
to canonical fields (``mapped_values``), and validates periods + metrics
without ever dropping a row silently. Pure functions only — no ``open()``,
no database, no ``DistributionInstance`` matching (that is G4 / dio 2).

Validation contract (documented, since Faza 1 v1.5 §18 is intentionally
thin):

- ``period_start``/``period_end`` are REQUIRED and must parse as an ISO 8601
  date/datetime without timezone (e.g. ``2026-01-01`` or
  ``2026-01-01T00:00:00``); ``period_end`` must not precede ``period_start``
  (consistent with ``MetricPeriod.__post_init__``).
- At least one of the nine canonical metrics must be present and parse as a
  number. Integer metrics (reach/impressions/engagements/clicks/conversions/
  video_views) must be whole numbers; the rest accept decimals.
- Negative metrics are INVALID (a metric cannot be negative). This is an
  import-time sanity rule, deliberately separate from ``CanonicalMetricSet``
  which leaves value validation to P1.5-G5 Metric Calculation.
- Every problem becomes a readable string in ``errors``; the row is NEVER
  dropped. What to do with invalid rows is dio 2's decision, not this engine's.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ai_campaign_studio.application.performance.column_mapping import (
    ColumnMatch,
)

# Canonical metric fields, in CanonicalMetricSet field order.
_METRIC_FIELDS: tuple[str, ...] = (
    "reach",
    "impressions",
    "engagements",
    "clicks",
    "conversions",
    "spend",
    "revenue",
    "video_views",
    "watch_time_seconds",
)

# CanonicalMetricSet types: these fields are int, the rest are float.
_INT_METRIC_FIELDS = frozenset(
    {"reach", "impressions", "engagements", "clicks", "conversions", "video_views"}
)


@dataclass(frozen=True)
class ParsedRow:
    """One parsed + validated CSV data row. Empty ``errors`` == valid.

    ``row_number`` is 1-based (header row is row 0). ``raw_values`` keeps the
    ORIGINAL values keyed by original header text — nothing is lost, including
    extra/unmatched columns. ``mapped_values`` maps canonical field -> string
    value for MATCHED columns only.
    """

    row_number: int
    raw_values: dict[str, str]
    mapped_values: dict[str, str]
    errors: tuple[str, ...]


def parse_rows(
    raw_rows: tuple[dict[str, str], ...],
    column_matches: tuple[ColumnMatch, ...],
) -> tuple[ParsedRow, ...]:
    """Parse/validate rows. Pure, never raises, never drops a row."""
    matched_headers: dict[str, str] = {}
    for match in column_matches:
        if match.status == "matched" and match.header is not None:
            matched_headers[match.canonical_field] = match.header

    rows: list[ParsedRow] = []
    for index, raw in enumerate(raw_rows, start=1):
        mapped = {
            field: raw[header]
            for field, header in matched_headers.items()
            if header in raw
        }
        rows.append(
            ParsedRow(
                row_number=index,
                raw_values=dict(raw),
                mapped_values=mapped,
                errors=tuple(_validate(mapped)),
            )
        )
    return tuple(rows)


def _validate(mapped: dict[str, str]) -> list[str]:
    """Return readable error messages for one mapped row (empty == valid)."""
    errors: list[str] = []

    start = _parse_period("period_start", mapped, errors)
    end = _parse_period("period_end", mapped, errors)
    if start is not None and end is not None and _comparable(end) < _comparable(start):
        errors.append(
            f"period_end ({_display(mapped, 'period_end')}) precedes "
            f"period_start ({_display(mapped, 'period_start')})"
        )

    mapped_metrics = [field for field in _METRIC_FIELDS if field in mapped]
    if not mapped_metrics:
        errors.append("no numeric metric present")
    else:
        parsed_count = 0
        for field in mapped_metrics:
            value = mapped[field].strip()
            if not value:
                # Empty cell == metric not provided for this row.
                continue
            try:
                number = float(value)
            except ValueError:
                errors.append(f"{field} ({value}) is not a number")
                continue
            if field in _INT_METRIC_FIELDS and not number.is_integer():
                errors.append(f"{field} ({value}) is not an integer")
                continue
            if number < 0:
                errors.append(f"{field} ({value}) cannot be negative")
                continue
            parsed_count += 1
        if parsed_count == 0:
            # All mapped metric columns were empty.
            errors.append("no numeric metric present")

    return errors


def _parse_period(
    field: str, mapped: dict[str, str], errors: list[str]
) -> datetime | None:
    """Parse one required period value; append an error and return None on fail."""
    if field not in mapped:
        errors.append(f"{field} is required")
        return None
    value = mapped[field].strip()
    if not value:
        errors.append(f"{field} is required")
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        errors.append(f"{field} ({value}) is not a valid date")
        return None


def _comparable(value: datetime) -> datetime:
    """Strip tzinfo so a mixed naive/aware pair still compares without raising.

    CSV period columns are expected to be naive; this only guards the order
    check against a stray timezone suffix (e.g. ``Z``) in one column, so the
    pure parse never raises on a comparison.
    """
    return value.replace(tzinfo=None) if value.tzinfo is not None else value


def _display(mapped: dict[str, str], field: str) -> str:
    """Return the stripped value for a readable error message."""
    return mapped[field].strip()
