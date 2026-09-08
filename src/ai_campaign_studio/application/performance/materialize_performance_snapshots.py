"""MaterializePerformanceSnapshots use-case (P1.5-G8 prerequisite).

Owns turning MATCHED + valid ``PerformanceImportRow`` rows into persisted
``PerformanceSnapshot`` rows, closing the G3/G4→G5/G6 gap: the G6 read models
(``build_campaign_performance_summary`` / ``build_content_performance_summary``)
read ONLY ``PerformanceSnapshot`` entities, never ``PerformanceImportRow``, so
without this step a successfully matched CSV import stays invisible to the
metric calculator. Does NOT own CSV reading (``ImportPerformanceCsv``),
matching (``MatchPerformanceImportBatch``), or metric derivation
(``calculate_derived_metrics``) — it is the bridge between matching and the
read models.

Idempotency: snapshot ids are DETERMINISTIC (``snap-<row_id>``), and
``SqlitePerformanceRepository.save_performance_snapshot`` is an UPSERT
(``ON CONFLICT(id) DO UPDATE``), so re-running this use-case over the same
batch rewrites the same snapshot rows instead of duplicating them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ai_campaign_studio.domain.common.ids import (
    DistributionInstanceId,
    PerformanceImportBatchId,
    PerformanceSnapshotId,
)
from ai_campaign_studio.domain.performance.entities import (
    PerformanceImportRow,
    PerformanceSnapshot,
)
from ai_campaign_studio.domain.performance.enums import PerformanceSource
from ai_campaign_studio.domain.performance.metrics import (
    CanonicalMetricSet,
    MetricPeriod,
)
from ai_campaign_studio.ports.repositories import PerformanceRepositoryPort

# Same integer/float split as ``row_parsing.py`` (single source of truth for
# which canonical metrics are whole numbers). Kept local so this use-case
# stays decoupled from the parsing module's internals.
_INT_METRIC_FIELDS = frozenset(
    {"reach", "impressions", "engagements", "clicks", "conversions", "video_views"}
)
_FLOAT_METRIC_FIELDS = frozenset({"spend", "revenue", "watch_time_seconds"})


@dataclass(frozen=True)
class MaterializeResult:
    """Outcome of one materialization run over a batch."""

    materialized_count: int
    skipped_invalid_count: int


class MaterializePerformanceSnapshots:
    """Persist one ``PerformanceSnapshot`` per MATCHED + valid import row."""

    def __init__(self, performance_repo: PerformanceRepositoryPort) -> None:
        self._repo = performance_repo

    def execute(
        self, batch_id: PerformanceImportBatchId
    ) -> MaterializeResult:
        """Materialize snapshots for the given batch.

        Only rows with ``match_status == "MATCHED"`` AND an empty ``errors``
        tuple are materialized. MATCHED rows WITH errors are skipped (they
        cannot be parsed into a ``CanonicalMetricSet`` — ``MatchPerformanceImportBatch``
        matches without checking ``row.errors``, so this case is real) and
        counted separately. UNMATCHED/AMBIGUOUS rows are never materialized.
        A defensive ``try/except`` around parsing means one bad row never
        aborts the whole batch (``row.errors == ()`` already guarantees
        parseability, but we do not rely on that blindly).
        """
        rows = self._repo.list_performance_import_rows(batch_id)
        batch = self._repo.get_performance_import_batch(batch_id)
        # ``observed_at`` = the import time (the moment this data entered the
        # system). ``period`` already carries the reporting window; falling
        # back to ``period.end`` is a defensive path for a batch row that
        # cannot be missing in practice (rows are FK-bound to their batch).
        batch_imported_at = batch.imported_at if batch is not None else None

        materialized = 0
        skipped_invalid = 0
        for row in rows:
            if row.match_status != "MATCHED":
                continue
            distribution_instance_id = row.distribution_instance_id
            if distribution_instance_id is None:
                # A MATCHED row always has a distribution_instance_id; this
                # is defensive only. Never materialize without a DI to bind to.
                skipped_invalid += 1
                continue
            if row.errors:
                skipped_invalid += 1
                continue
            try:
                snapshot = _build_snapshot(
                    batch_id, row, batch_imported_at, distribution_instance_id
                )
            except (KeyError, ValueError, TypeError):
                # Defensive: row.errors==() guarantees the values parse, but a
                # future parser change must not crash the whole batch here.
                skipped_invalid += 1
                continue
            self._repo.save_performance_snapshot(snapshot)
            materialized += 1

        return MaterializeResult(
            materialized_count=materialized,
            skipped_invalid_count=skipped_invalid,
        )


def _build_snapshot(
    batch_id: PerformanceImportBatchId,
    row: PerformanceImportRow,
    batch_imported_at: datetime | None,
    distribution_instance_id: DistributionInstanceId,
) -> PerformanceSnapshot:
    """Map one valid, MATCHED row onto a ``PerformanceSnapshot``.

    ``mapped_values`` are the ORIGINAL CSV strings keyed by canonical field
    name; ``row.errors == ()`` means every present value already parsed
    during import, so the conversions here are safe (but still wrapped by the
    caller's try/except). Empty cells map to ``None`` metrics.
    """
    mapped = row.mapped_values
    period = MetricPeriod(
        start=datetime.fromisoformat(mapped["period_start"].strip()),
        end=datetime.fromisoformat(mapped["period_end"].strip()),
    )
    observed_at = (
        batch_imported_at if batch_imported_at is not None else period.end
    )
    return PerformanceSnapshot(
        id=PerformanceSnapshotId(f"snap-{row.id}"),
        distribution_instance_id=distribution_instance_id,
        period=period,
        observed_at=observed_at,
        source=PerformanceSource.CSV_IMPORT,
        metrics=CanonicalMetricSet(
            reach=_parse_int(mapped, "reach"),
            impressions=_parse_int(mapped, "impressions"),
            engagements=_parse_int(mapped, "engagements"),
            clicks=_parse_int(mapped, "clicks"),
            conversions=_parse_int(mapped, "conversions"),
            spend=_parse_float(mapped, "spend"),
            revenue=_parse_float(mapped, "revenue"),
            video_views=_parse_int(mapped, "video_views"),
            watch_time_seconds=_parse_float(mapped, "watch_time_seconds"),
        ),
        source_batch_id=batch_id,
        # Keep the ORIGINAL raw CSV values for the audit trail (same
        # principle as ``PerformanceImportRow.raw_values``).
        raw_metrics=dict(row.raw_values),
    )


def _parse_int(mapped: dict[str, str], field: str) -> int | None:
    value = mapped.get(field)
    if value is None or not value.strip():
        return None
    # ``int(float(...))`` tolerates "100.0" (a whole number written with a
    # decimal point), which row_parsing accepts for integer fields.
    return int(float(value.strip()))


def _parse_float(mapped: dict[str, str], field: str) -> float | None:
    value = mapped.get(field)
    if value is None or not value.strip():
        return None
    return float(value.strip())


__all__ = ["MaterializePerformanceSnapshots", "MaterializeResult"]
