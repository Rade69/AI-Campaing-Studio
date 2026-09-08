"""Integration test: the full import→match→materialize→aggregate chain.

This is the task-defining acceptance for ACS-F1-057: BEFORE
``MaterializePerformanceSnapshots`` the G6 summary returns ``None`` derived
metrics even after a successful match (the gap); AFTER materialization the
same summary returns REAL, hand-computed derived values.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ai_campaign_studio.application.performance import materialize_performance_snapshots
from ai_campaign_studio.application.performance.build_performance_summaries import (
    build_campaign_performance_summary,
)
from ai_campaign_studio.application.performance.confirm_performance_import import (
    ConfirmPerformanceImport,
)
from ai_campaign_studio.application.performance.match_performance_import_batch import (
    MatchPerformanceImportBatch,
)
from ai_campaign_studio.domain.common.ids import (
    CampaignId,
    CampaignItemId,
    DistributionInstanceId,
    PostId,
    RevisionId,
)
from ai_campaign_studio.domain.performance.entities import DistributionInstance
from ai_campaign_studio.domain.performance.enums import DistributionSource
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories import (
    SqlitePerformanceRepository,
)

_MIGRATIONS_DIR = (
    Path(__file__).resolve().parents[4] / "resources" / "migrations"
)


def _seed_distribution_instance(
    connection: sqlite3.Connection,
    repo: SqlitePerformanceRepository,
    *,
    campaign_id: str,
    tag: str,
    external_content_id: str | None,
) -> DistributionInstance:
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
        external_content_id=external_content_id,
    )
    repo.save_distribution_instance(instance)
    return instance


def test_full_chain_yields_real_derived_metrics(tmp_path: Path) -> None:
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)
    repo = SqlitePerformanceRepository(connection)
    campaign_id = CampaignId("campaign-a")

    _seed_distribution_instance(
        connection, repo, campaign_id="campaign-a", tag="a",
        external_content_id="ext-1",
    )

    # Two CSV rows: one matches ext-1, one does not match (ext-2).
    csv_path = tmp_path / "perf.csv"
    csv_path.write_text(
        "external_content_id,period_start,period_end,impressions,clicks,"
        "spend,conversions,revenue\n"
        "ext-1,2026-01-01,2026-01-31,1000,34,200.0,5,500.0\n"
        "ext-2,2026-01-01,2026-01-31,2000,68,400.0,10,1000.0\n",
        encoding="utf-8",
    )

    batch = ConfirmPerformanceImport(repo).execute(str(csv_path))
    match_result = MatchPerformanceImportBatch(repo).execute(
        batch.id, campaign_id
    )
    assert match_result.matched_count == 1
    assert match_result.unmatched_count == 1

    # BEFORE materialization: the G6 summary sees the distribution instance
    # but NO snapshots, so derived metrics are None — this is the exact gap
    # ACS-F1-057 closes.
    before = build_campaign_performance_summary(repo, campaign_id)
    assert before.distribution_instance_count == 1
    assert before.derived.ctr is None
    assert before.derived.cpc is None

    materialize_result = (
        materialize_performance_snapshots.MaterializePerformanceSnapshots(repo)
    ).execute(batch.id)
    assert materialize_result.materialized_count == 1
    assert materialize_result.skipped_invalid_count == 0

    # AFTER materialization: real, hand-computed derived metrics from the
    # SINGLE matched row (ext-1; the unmatched ext-2 row never materializes).
    after = build_campaign_performance_summary(repo, campaign_id)
    assert after.distribution_instance_count == 1
    assert after.raw.impressions == 1000
    assert after.raw.clicks == 34
    assert after.raw.spend == 200.0
    assert after.raw.conversions == 5
    assert after.raw.revenue == 500.0
    assert after.derived.ctr == pytest.approx(34 / 1000)
    assert after.derived.cpc == pytest.approx(200.0 / 34)
    assert after.derived.cpm == pytest.approx(200.0 / 1000 * 1000)
    assert after.derived.cpa == pytest.approx(200.0 / 5)
    assert after.derived.roas == pytest.approx(500.0 / 200.0)
    assert after.derived.conversion_rate == pytest.approx(5 / 34)

    connection.close()
