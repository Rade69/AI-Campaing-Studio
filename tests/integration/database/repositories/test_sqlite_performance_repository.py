"""Integration tests for SqlitePerformanceRepository (P1.5-G2)."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ai_campaign_studio.domain.campaign.entities import (
    Campaign,
    CampaignBrief,
    CampaignItem,
    CampaignPlan,
)
from ai_campaign_studio.domain.campaign.enums import (
    CampaignItemStatus,
    CampaignPlanStatus,
    CampaignStatus,
)
from ai_campaign_studio.domain.campaign.roles import CampaignRole
from ai_campaign_studio.domain.common.ids import (
    CampaignId,
    CampaignItemId,
    CampaignPlanId,
    DistributionInstanceId,
    PerformanceImportBatchId,
    PerformanceSnapshotId,
    PostId,
    RevisionId,
)
from ai_campaign_studio.domain.performance.entities import (
    DistributionInstance,
    PerformanceImportBatch,
    PerformanceSnapshot,
)
from ai_campaign_studio.domain.performance.enums import (
    DistributionSource,
    PerformanceSource,
)
from ai_campaign_studio.domain.performance.metrics import (
    CanonicalMetricSet,
    MetricPeriod,
)
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories import (
    SqliteCampaignRepository,
    SqlitePerformanceRepository,
)
from ai_campaign_studio.ports.repositories import PerformanceRepositoryPort

_MIGRATIONS_DIR = Path(__file__).resolve().parents[4] / "resources" / "migrations"
_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def _setup_db(tmp_path: Path) -> sqlite3.Connection:
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)
    return connection


def _seed_distribution_fk(connection: sqlite3.Connection) -> None:
    """Seed the FK chain a DistributionInstance references:
    brief -> campaign -> plan -> item -> content_piece -> revision.
    """
    repo = SqliteCampaignRepository(connection)
    repo.save_brief(
        CampaignBrief(
            id="brief-1",
            offer="Offer",
            goal="Goal",
            audience_text="Audience",
            targets=[],
            content_piece_count=1,
            content_language_context="BHS_LATIN",
            created_at=_CREATED_AT,
        )
    )
    repo.save_campaign(
        Campaign(
            id=CampaignId("campaign-1"),
            brand_id="brand-1",
            brand_snapshot_id="snap-1",
            brief_id="brief-1",
            status=CampaignStatus.DRAFT,
            created_at=_CREATED_AT,
        )
    )
    repo.save_plan(
        CampaignPlan(
            id=CampaignPlanId("plan-1"),
            campaign_id=CampaignId("campaign-1"),
            version=1,
            status=CampaignPlanStatus.DRAFT,
            created_at=_CREATED_AT,
            items=[
                CampaignItem(
                    id="item-1",
                    order=1,
                    role=CampaignRole.PROBLEM,
                    topic="Topic",
                    goal="Goal",
                    status=CampaignItemStatus.PLANNED,
                )
            ],
        )
    )
    connection.execute(
        "INSERT INTO content_pieces (id, campaign_item_id, target_channel,"
        " target_platform_code, target_format_code, payload_type, status,"
        " brand_snapshot_id, facts_allowed_json, revision_ids_json,"
        " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "piece-1",
            "item-1",
            "SOCIAL",
            "INSTAGRAM",
            "FEED_POST",
            "SOCIAL_POST",
            "DRAFT",
            "snap-1",
            "[]",
            "[]",
            _CREATED_AT.isoformat(),
            _CREATED_AT.isoformat(),
        ),
    )
    connection.execute(
        "INSERT INTO revisions (id, entity_type, entity_id, version, timestamp,"
        " origin, previous_value, new_value, provider, model, prompt_version,"
        " instruction) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "rev-1",
            "ContentPiece",
            "piece-1",
            1,
            _CREATED_AT.isoformat(),
            "AI",
            "{}",
            "{}",
            None,
            None,
            None,
            None,
        ),
    )


def _distribution_instance() -> DistributionInstance:
    return DistributionInstance(
        id=DistributionInstanceId("di-1"),
        campaign_id=CampaignId("campaign-1"),
        campaign_item_id=CampaignItemId("item-1"),
        content_piece_id=PostId("piece-1"),
        content_revision_id=RevisionId("rev-1"),
        channel_code="SOCIAL",
        platform_code="INSTAGRAM",
        format_code="FEED_POST",
        distribution_source=DistributionSource.EXPORT,
        created_at=_CREATED_AT,
    )


def _batch() -> PerformanceImportBatch:
    return PerformanceImportBatch(
        id=PerformanceImportBatchId("b-1"),
        source=PerformanceSource.CSV_IMPORT,
        imported_at=_CREATED_AT,
        row_count=10,
        matched_count=8,
        unmatched_count=2,
        mapping_version="v1",
    )


def _snapshot(metrics: CanonicalMetricSet | None = None) -> PerformanceSnapshot:
    return PerformanceSnapshot(
        id=PerformanceSnapshotId("ps-1"),
        distribution_instance_id=DistributionInstanceId("di-1"),
        period=MetricPeriod(start=_CREATED_AT, end=_CREATED_AT),
        observed_at=_CREATED_AT,
        source=PerformanceSource.CSV_IMPORT,
        metrics=metrics if metrics is not None else CanonicalMetricSet(),
        source_batch_id=PerformanceImportBatchId("b-1"),
        raw_metrics={"instagram_saves": 42},
    )


def test_repository_is_a_performance_repository_port(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqlitePerformanceRepository(connection)
    assert isinstance(repo, PerformanceRepositoryPort)
    connection.close()


def test_round_trip_distribution_instance(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    _seed_distribution_fk(connection)
    repo = SqlitePerformanceRepository(connection)

    instance = _distribution_instance()
    repo.save_distribution_instance(instance)

    assert repo.get_distribution_instance(
        DistributionInstanceId("di-1")
    ) == instance
    connection.close()


def test_round_trip_performance_import_batch(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqlitePerformanceRepository(connection)

    batch = _batch()
    repo.save_performance_import_batch(batch)

    assert repo.get_performance_import_batch(
        PerformanceImportBatchId("b-1")
    ) == batch
    connection.close()


def test_round_trip_performance_snapshot(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    _seed_distribution_fk(connection)
    repo = SqlitePerformanceRepository(connection)

    repo.save_distribution_instance(_distribution_instance())
    repo.save_performance_import_batch(_batch())

    snapshot = _snapshot(metrics=CanonicalMetricSet(reach=100, spend=1.5))
    repo.save_performance_snapshot(snapshot)

    loaded = repo.get_performance_snapshot(PerformanceSnapshotId("ps-1"))
    assert loaded == snapshot
    # nested value objects reconstructed as real types
    assert loaded is not None
    assert isinstance(loaded.period, MetricPeriod)
    assert isinstance(loaded.metrics, CanonicalMetricSet)
    assert loaded.metrics.reach == 100
    assert loaded.metrics.spend == 1.5
    assert loaded.raw_metrics == {"instagram_saves": 42}
    connection.close()


def test_round_trip_snapshot_all_none_metrics(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    _seed_distribution_fk(connection)
    repo = SqlitePerformanceRepository(connection)

    repo.save_distribution_instance(_distribution_instance())
    repo.save_performance_import_batch(_batch())

    snapshot = _snapshot(metrics=CanonicalMetricSet())
    repo.save_performance_snapshot(snapshot)

    loaded = repo.get_performance_snapshot(PerformanceSnapshotId("ps-1"))
    assert loaded == snapshot
    assert loaded is not None
    assert loaded.metrics.reach is None
    assert loaded.metrics.impressions is None
    connection.close()


def test_get_unknown_returns_none_for_all_three(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqlitePerformanceRepository(connection)
    assert repo.get_distribution_instance(
        DistributionInstanceId("missing")
    ) is None
    assert repo.get_performance_import_batch(
        PerformanceImportBatchId("missing")
    ) is None
    assert repo.get_performance_snapshot(
        PerformanceSnapshotId("missing")
    ) is None
    connection.close()


def test_distribution_instance_requires_fk_rows(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)  # migrations only, no FK seed
    repo = SqlitePerformanceRepository(connection)
    with pytest.raises(sqlite3.IntegrityError):
        repo.save_distribution_instance(_distribution_instance())
    connection.close()
