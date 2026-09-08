"""Unit tests for MaterializePerformanceSnapshots (P1.5-G8 prerequisite)."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from ai_campaign_studio.application.performance import materialize_performance_snapshots
from ai_campaign_studio.domain.common.ids import (
    CampaignId,
    CampaignItemId,
    DistributionInstanceId,
    PerformanceImportBatchId,
    PerformanceImportRowId,
    PerformanceSnapshotId,
    PostId,
    RevisionId,
)
from ai_campaign_studio.domain.performance.entities import (
    DistributionInstance,
    PerformanceImportBatch,
    PerformanceImportRow,
)
from ai_campaign_studio.domain.performance.enums import (
    DistributionSource,
    PerformanceSource,
)
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories import (
    SqlitePerformanceRepository,
)

_MIGRATIONS_DIR = (
    Path(__file__).resolve().parents[4] / "resources" / "migrations"
)

# Short local alias: the module name is long enough to blow the 88-col
# line limit in ``from ... import (...)`` form.
MaterializePerformanceSnapshots = (
    materialize_performance_snapshots.MaterializePerformanceSnapshots
)


def _setup(tmp_path: Path) -> tuple[SqlitePerformanceRepository, sqlite3.Connection]:
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)
    return SqlitePerformanceRepository(connection), connection


def _batch(batch_id: str = "b-1") -> PerformanceImportBatch:
    return PerformanceImportBatch(
        id=PerformanceImportBatchId(batch_id),
        source=PerformanceSource.CSV_IMPORT,
        imported_at=datetime(2026, 1, 1, tzinfo=UTC),
        row_count=1,
        matched_count=0,
        unmatched_count=0,
        mapping_version="1",
    )


def _row(
    row_id: str,
    mapped_values: dict[str, str],
    *,
    batch_id: str = "b-1",
    distribution_instance_id: DistributionInstanceId | None = None,
    match_status: str | None = None,
    errors: tuple[str, ...] = (),
) -> PerformanceImportRow:
    return PerformanceImportRow(
        id=PerformanceImportRowId(row_id),
        batch_id=PerformanceImportBatchId(batch_id),
        row_number=1,
        raw_values=dict(mapped_values),
        mapped_values=dict(mapped_values),
        errors=errors,
        distribution_instance_id=distribution_instance_id,
        match_status=match_status,  # type: ignore[arg-type]
    )


def _seed_distribution_instance(
    connection: sqlite3.Connection,
    repo: SqlitePerformanceRepository,
    *,
    campaign_id: str,
    tag: str,
) -> DistributionInstance:
    """Seed one DistributionInstance with its full FK chain (same style as
    the G4 matching tests)."""
    created_at = "2026-01-01T00:00:00+00:00"
    connection.execute(
        "INSERT OR IGNORE INTO campaign_briefs (id, offer, goal, audience_text,"
        " targets_json, content_piece_count, content_language_context,"
        " special_instructions_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (f"brief-{campaign_id}", "offer", "goal", "audience", "[]", 1,
         "BHS_LATIN", "[]", created_at),
    )
    connection.execute(
        "INSERT OR IGNORE INTO campaigns (id, brand_id, brand_snapshot_id,"
        " brief_id, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (campaign_id, "brand-1", "snap-1", f"brief-{campaign_id}", "DRAFT",
         created_at),
    )
    connection.execute(
        "INSERT INTO campaign_plans (id, campaign_id, version, status,"
        " created_at) VALUES (?, ?, ?, ?, ?)",
        (f"plan-{tag}", campaign_id, 1, "DRAFT", created_at),
    )
    connection.execute(
        "INSERT INTO campaign_items (id, plan_id, \"order\", role, topic, goal,"
        " target_audience_id, facts_needed_json, status)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (f"item-{tag}", f"plan-{tag}", 1, "PROBLEM", "topic", "goal", None,
         "[]", "PLANNED"),
    )
    connection.execute(
        "INSERT INTO content_pieces (id, campaign_item_id, target_channel,"
        " target_platform_code, target_format_code, payload_type, status,"
        " brand_snapshot_id, facts_allowed_json, revision_ids_json,"
        " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (f"piece-{tag}", f"item-{tag}", "SOCIAL", "INSTAGRAM", "FEED_POST",
         "SOCIAL_POST", "DRAFT", "snap-1", "[]", "[]", created_at, created_at),
    )
    connection.execute(
        "INSERT INTO revisions (id, entity_type, entity_id, version, timestamp,"
        " origin, previous_value, new_value, provider, model, prompt_version,"
        " instruction) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (f"rev-{tag}", "ContentPiece", f"piece-{tag}", 1, created_at, "AI",
         "{}", "{}", None, None, None, None),
    )
    instance = DistributionInstance(
        id=DistributionInstanceId(f"di-{tag}"),
        campaign_id=CampaignId(campaign_id),
        campaign_item_id=CampaignItemId(f"item-{tag}"),
        content_piece_id=PostId(f"piece-{tag}"),
        content_revision_id=RevisionId(f"rev-{tag}"),
        channel_code="SOCIAL",
        platform_code="INSTAGRAM",
        format_code="FEED_POST",
        distribution_source=DistributionSource.EXPORT,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    repo.save_distribution_instance(instance)
    return instance


_VALID_MAPPED = {
    "period_start": "2026-01-01",
    "period_end": "2026-01-31",
    "reach": "100",
    "impressions": "1000",
    "clicks": "34",
    "conversions": "5",
    "spend": "200.0",
    "revenue": "500.0",
}


def test_empty_batch_materializes_nothing(tmp_path: Path) -> None:
    repo, connection = _setup(tmp_path)
    repo.save_performance_import_batch(_batch())
    result = MaterializePerformanceSnapshots(repo).execute(
        PerformanceImportBatchId("b-1")
    )
    assert result.materialized_count == 0
    assert result.skipped_invalid_count == 0
    connection.close()


def test_matched_valid_row_creates_snapshot(tmp_path: Path) -> None:
    repo, connection = _setup(tmp_path)
    di = _seed_distribution_instance(
        connection, repo, campaign_id="campaign-a", tag="a"
    )
    repo.save_performance_import_batch(_batch())
    repo.save_performance_import_row(
        _row(
            "r-1",
            _VALID_MAPPED,
            distribution_instance_id=di.id,
            match_status="MATCHED",
        )
    )

    result = MaterializePerformanceSnapshots(repo).execute(
        PerformanceImportBatchId("b-1")
    )
    assert result.materialized_count == 1
    assert result.skipped_invalid_count == 0

    snapshot = repo.get_performance_snapshot(
        PerformanceSnapshotId("snap-r-1")
    )
    assert snapshot is not None
    assert snapshot.distribution_instance_id == di.id
    assert snapshot.period.start == datetime.fromisoformat("2026-01-01")
    assert snapshot.period.end == datetime.fromisoformat("2026-01-31")
    assert snapshot.observed_at == datetime(2026, 1, 1, tzinfo=UTC)
    assert snapshot.source is PerformanceSource.CSV_IMPORT
    assert snapshot.source_batch_id == PerformanceImportBatchId("b-1")
    assert snapshot.metrics.reach == 100
    assert snapshot.metrics.impressions == 1000
    assert snapshot.metrics.clicks == 34
    assert snapshot.metrics.conversions == 5
    assert snapshot.metrics.spend == 200.0
    assert snapshot.metrics.revenue == 500.0
    assert snapshot.metrics.engagements is None
    assert snapshot.metrics.video_views is None
    assert snapshot.metrics.watch_time_seconds is None
    assert snapshot.raw_metrics == _VALID_MAPPED
    connection.close()


def test_matched_invalid_row_is_skipped(tmp_path: Path) -> None:
    repo, connection = _setup(tmp_path)
    di = _seed_distribution_instance(
        connection, repo, campaign_id="campaign-a", tag="a"
    )
    repo.save_performance_import_batch(_batch())
    repo.save_performance_import_row(
        _row(
            "r-1",
            {"period_start": "garbage", "period_end": "2026-01-31", "reach": "x"},
            distribution_instance_id=di.id,
            match_status="MATCHED",
            errors=("period_start (garbage) is not a valid date",),
        )
    )

    result = MaterializePerformanceSnapshots(repo).execute(
        PerformanceImportBatchId("b-1")
    )
    assert result.materialized_count == 0
    assert result.skipped_invalid_count == 1
    assert repo.get_performance_snapshot(PerformanceSnapshotId("snap-r-1")) is None
    connection.close()


def test_unmatched_and_ambiguous_never_materialized(tmp_path: Path) -> None:
    repo, connection = _setup(tmp_path)
    di = _seed_distribution_instance(
        connection, repo, campaign_id="campaign-a", tag="a"
    )
    repo.save_performance_import_batch(_batch())
    repo.save_performance_import_row(
        _row(
            "r-unmatched",
            _VALID_MAPPED,
            distribution_instance_id=None,
            match_status="UNMATCHED",
        )
    )
    repo.save_performance_import_row(
        _row(
            "r-ambiguous",
            _VALID_MAPPED,
            distribution_instance_id=None,
            match_status="AMBIGUOUS",
        )
    )
    # A row with match_status None (never attempted) is also ignored.
    repo.save_performance_import_row(
        _row("r-none", _VALID_MAPPED, distribution_instance_id=di.id)
    )

    result = MaterializePerformanceSnapshots(repo).execute(
        PerformanceImportBatchId("b-1")
    )
    assert result.materialized_count == 0
    assert result.skipped_invalid_count == 0
    assert repo.get_performance_snapshot(
        PerformanceSnapshotId("snap-r-unmatched")
    ) is None
    assert repo.get_performance_snapshot(
        PerformanceSnapshotId("snap-r-ambiguous")
    ) is None
    assert repo.get_performance_snapshot(
        PerformanceSnapshotId("snap-r-none")
    ) is None
    connection.close()


def test_idempotent_second_call_does_not_duplicate(tmp_path: Path) -> None:
    repo, connection = _setup(tmp_path)
    di = _seed_distribution_instance(
        connection, repo, campaign_id="campaign-a", tag="a"
    )
    repo.save_performance_import_batch(_batch())
    repo.save_performance_import_row(
        _row(
            "r-1",
            _VALID_MAPPED,
            distribution_instance_id=di.id,
            match_status="MATCHED",
        )
    )

    use_case = MaterializePerformanceSnapshots(repo)
    first = use_case.execute(PerformanceImportBatchId("b-1"))
    second = use_case.execute(PerformanceImportBatchId("b-1"))
    assert first.materialized_count == 1
    assert second.materialized_count == 1  # re-run still "materializes" (upsert)
    count = connection.execute(
        "SELECT COUNT(*) FROM performance_snapshots"
    ).fetchone()[0]
    assert count == 1, f"expected exactly 1 snapshot row, got {count}"
    connection.close()
