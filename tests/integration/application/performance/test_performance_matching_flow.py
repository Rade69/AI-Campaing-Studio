"""Integration test: ConfirmPerformanceImport -> MatchPerformanceImportBatch.

Proves the full G3→G4 chain over a REAL SQLite DB with real
``DistributionInstance`` rows and a real CSV: at least one MATCHED and at
least one UNMATCHED in the same batch.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

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


def test_confirm_then_match_produces_matched_and_unmatched(
    tmp_path: Path,
) -> None:
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)
    repo = SqlitePerformanceRepository(connection)

    di = _seed_distribution_instance(
        connection, repo, campaign_id="campaign-a", tag="a",
        external_content_id="ext-1",
    )

    csv_path = tmp_path / "perf.csv"
    csv_path.write_text(
        "external_content_id,datum_pocetka,datum_kraja,doseg\n"
        "ext-1,2026-01-01,2026-01-31,100\n"
        "nope,2026-01-01,2026-01-31,200\n",
        encoding="utf-8",
    )

    batch = ConfirmPerformanceImport(repo).execute(str(csv_path))

    result = MatchPerformanceImportBatch(repo).execute(
        batch.id, CampaignId("campaign-a")
    )

    assert result.matched_count == 1
    assert result.unmatched_count == 1
    assert result.ambiguous_count == 0
    assert result.skipped_count == 0

    rows = repo.list_performance_import_rows(batch.id)
    assert len(rows) == 2
    by_ext = {r.mapped_values["external_content_id"]: r for r in rows}

    matched = by_ext["ext-1"]
    assert matched.distribution_instance_id == di.id
    assert matched.match_status == "MATCHED"

    unmatched = by_ext["nope"]
    assert unmatched.distribution_instance_id is None
    assert unmatched.match_status == "UNMATCHED"

    connection.close()
