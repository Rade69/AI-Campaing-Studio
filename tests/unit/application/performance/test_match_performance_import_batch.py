"""Unit tests for MatchPerformanceImportBatch (P1.5-G4)."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from ai_campaign_studio.application.performance.match_performance_import_batch import (
    MatchPerformanceImportBatch,
)
from ai_campaign_studio.domain.analytics.match_key import compute_analytics_match_key
from ai_campaign_studio.domain.common.ids import (
    CampaignId,
    CampaignItemId,
    DistributionInstanceId,
    PerformanceImportBatchId,
    PerformanceImportRowId,
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
    batch_id: str = "b-1",
    distribution_instance_id: DistributionInstanceId | None = None,
    match_status: str | None = None,
) -> PerformanceImportRow:
    return PerformanceImportRow(
        id=PerformanceImportRowId(row_id),
        batch_id=PerformanceImportBatchId(batch_id),
        row_number=1,
        raw_values={},
        mapped_values=mapped_values,
        errors=(),
        distribution_instance_id=distribution_instance_id,
        match_status=match_status,  # type: ignore[arg-type]
    )


def _seed_distribution_instance(
    connection: sqlite3.Connection,
    repo: SqlitePerformanceRepository,
    *,
    campaign_id: str,
    tag: str,
    external_content_id: str | None = None,
    platform_code: str = "INSTAGRAM",
    format_code: str = "FEED_POST",
) -> DistributionInstance:
    """Seed one DistributionInstance (with its full FK chain) in a campaign.

    ``campaign_id`` may be shared across several instances (multiple pieces
    in one campaign); brief/campaign rows use ``INSERT OR IGNORE`` so repeated
    seeding of the same campaign is idempotent. ``tag`` disambiguates the
    per-piece ids (plan/item/piece/revision/di).
    """
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
        (f"piece-{tag}", f"item-{tag}", "SOCIAL", platform_code, format_code,
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
        platform_code=platform_code,
        format_code=format_code,
        distribution_source=DistributionSource.EXPORT,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        external_content_id=external_content_id,
    )
    repo.save_distribution_instance(instance)
    return instance


def test_priority1_external_content_id_matches(tmp_path: Path) -> None:
    repo, connection = _setup(tmp_path)
    di = _seed_distribution_instance(
        connection, repo, campaign_id="campaign-a", tag="a",
        external_content_id="ext-123",
    )
    repo.save_performance_import_batch(_batch())
    repo.save_performance_import_row(
        _row("r-1", {"external_content_id": "ext-123"})
    )

    result = MatchPerformanceImportBatch(repo).execute(
        PerformanceImportBatchId("b-1"), CampaignId("campaign-a")
    )

    assert result.matched_count == 1
    assert result.ambiguous_count == 0
    assert result.unmatched_count == 0
    assert result.skipped_count == 0
    loaded = repo.get_performance_import_row(PerformanceImportRowId("r-1"))
    assert loaded is not None
    assert loaded.distribution_instance_id == di.id
    assert loaded.match_status == "MATCHED"
    connection.close()


def test_priority2_analytics_match_key_matches(tmp_path: Path) -> None:
    repo, connection = _setup(tmp_path)
    di = _seed_distribution_instance(
        connection, repo, campaign_id="campaign-a", tag="a"
    )
    key = compute_analytics_match_key(
        di.content_piece_id,
        di.content_revision_id,
        di.platform_code,
        di.format_code,
    )
    repo.save_performance_import_batch(_batch())
    repo.save_performance_import_row(
        _row("r-1", {"analytics_match_key": key})
    )

    result = MatchPerformanceImportBatch(repo).execute(
        PerformanceImportBatchId("b-1"), CampaignId("campaign-a")
    )

    assert result.matched_count == 1
    loaded = repo.get_performance_import_row(PerformanceImportRowId("r-1"))
    assert loaded is not None
    assert loaded.distribution_instance_id == di.id
    assert loaded.match_status == "MATCHED"
    connection.close()


def test_priority1_ambiguous_stops_and_leaves_none(tmp_path: Path) -> None:
    repo, connection = _setup(tmp_path)
    _seed_distribution_instance(
        connection, repo, campaign_id="campaign-a", tag="a1",
        external_content_id="dup",
    )
    _seed_distribution_instance(
        connection, repo, campaign_id="campaign-a", tag="a2",
        external_content_id="dup",
    )
    repo.save_performance_import_batch(_batch())
    repo.save_performance_import_row(
        _row("r-1", {"external_content_id": "dup"})
    )

    result = MatchPerformanceImportBatch(repo).execute(
        PerformanceImportBatchId("b-1"), CampaignId("campaign-a")
    )

    assert result.ambiguous_count == 1
    assert result.matched_count == 0
    loaded = repo.get_performance_import_row(PerformanceImportRowId("r-1"))
    assert loaded is not None
    assert loaded.distribution_instance_id is None
    assert loaded.match_status == "AMBIGUOUS"
    connection.close()


def test_priority1_ambiguous_does_not_fall_through_to_priority2(
    tmp_path: Path,
) -> None:
    repo, connection = _setup(tmp_path)
    di1 = _seed_distribution_instance(
        connection, repo, campaign_id="campaign-a", tag="a1",
        external_content_id="dup",
    )
    _seed_distribution_instance(
        connection, repo, campaign_id="campaign-a", tag="a2",
        external_content_id="dup",
    )
    # A CORRECT priority-2 key for di1 — must NOT rescue the row: priority 1
    # ambiguity is final and must not fall through.
    key = compute_analytics_match_key(
        di1.content_piece_id,
        di1.content_revision_id,
        di1.platform_code,
        di1.format_code,
    )
    repo.save_performance_import_batch(_batch())
    repo.save_performance_import_row(
        _row("r-1", {"external_content_id": "dup", "analytics_match_key": key})
    )

    result = MatchPerformanceImportBatch(repo).execute(
        PerformanceImportBatchId("b-1"), CampaignId("campaign-a")
    )

    assert result.ambiguous_count == 1
    assert result.matched_count == 0
    loaded = repo.get_performance_import_row(PerformanceImportRowId("r-1"))
    assert loaded is not None
    assert loaded.distribution_instance_id is None
    assert loaded.match_status == "AMBIGUOUS"
    connection.close()


def test_unmatched_when_external_content_id_absent(tmp_path: Path) -> None:
    repo, connection = _setup(tmp_path)
    _seed_distribution_instance(
        connection, repo, campaign_id="campaign-a", tag="a",
        external_content_id="ext-a",
    )
    repo.save_performance_import_batch(_batch())
    repo.save_performance_import_row(
        _row("r-1", {"external_content_id": "nope"})
    )

    result = MatchPerformanceImportBatch(repo).execute(
        PerformanceImportBatchId("b-1"), CampaignId("campaign-a")
    )

    assert result.unmatched_count == 1
    loaded = repo.get_performance_import_row(PerformanceImportRowId("r-1"))
    assert loaded is not None
    assert loaded.distribution_instance_id is None
    assert loaded.match_status == "UNMATCHED"
    connection.close()


def test_skipped_when_no_matching_data(tmp_path: Path) -> None:
    repo, connection = _setup(tmp_path)
    repo.save_performance_import_batch(_batch())
    repo.save_performance_import_row(_row("r-1", {"reach": "100"}))

    result = MatchPerformanceImportBatch(repo).execute(
        PerformanceImportBatchId("b-1"), CampaignId("campaign-a")
    )

    assert result.skipped_count == 1
    assert result.unmatched_count == 0
    loaded = repo.get_performance_import_row(PerformanceImportRowId("r-1"))
    assert loaded is not None
    assert loaded.distribution_instance_id is None
    assert loaded.match_status == "UNMATCHED"
    connection.close()


def test_idempotent_second_call_does_not_touch_matched_row(
    tmp_path: Path,
) -> None:
    repo, connection = _setup(tmp_path)
    di = _seed_distribution_instance(
        connection, repo, campaign_id="campaign-a", tag="a1",
        external_content_id="ext-a",
    )
    repo.save_performance_import_batch(_batch())
    repo.save_performance_import_row(
        _row("r-1", {"external_content_id": "ext-a"})
    )

    use_case = MatchPerformanceImportBatch(repo)
    first = use_case.execute(
        PerformanceImportBatchId("b-1"), CampaignId("campaign-a")
    )
    assert first.matched_count == 1

    # Add a SECOND instance with the SAME external_content_id. If the row
    # were re-matched, it would now become AMBIGUOUS — proving the second
    # call must leave it untouched.
    _seed_distribution_instance(
        connection, repo, campaign_id="campaign-a", tag="a2",
        external_content_id="ext-a",
    )
    second = use_case.execute(
        PerformanceImportBatchId("b-1"), CampaignId("campaign-a")
    )
    assert second.matched_count == 0
    assert second.ambiguous_count == 0
    assert second.unmatched_count == 0
    assert second.skipped_count == 0

    loaded = repo.get_performance_import_row(PerformanceImportRowId("r-1"))
    assert loaded is not None
    assert loaded.distribution_instance_id == di.id
    assert loaded.match_status == "MATCHED"
    connection.close()


def test_cross_campaign_external_content_id_does_not_match(
    tmp_path: Path,
) -> None:
    repo, connection = _setup(tmp_path)
    _seed_distribution_instance(
        connection, repo, campaign_id="campaign-a", tag="a",
        external_content_id="ext-a",
    )
    _seed_distribution_instance(
        connection, repo, campaign_id="campaign-b", tag="b",
        external_content_id="ext-b",
    )
    repo.save_performance_import_batch(_batch())
    # "ext-b" exists, but in campaign-b — matching against campaign-a must
    # NOT cross the campaign boundary.
    repo.save_performance_import_row(
        _row("r-1", {"external_content_id": "ext-b"})
    )

    result = MatchPerformanceImportBatch(repo).execute(
        PerformanceImportBatchId("b-1"), CampaignId("campaign-a")
    )

    assert result.unmatched_count == 1
    assert result.matched_count == 0
    loaded = repo.get_performance_import_row(PerformanceImportRowId("r-1"))
    assert loaded is not None
    assert loaded.distribution_instance_id is None
    assert loaded.match_status == "UNMATCHED"
    connection.close()
