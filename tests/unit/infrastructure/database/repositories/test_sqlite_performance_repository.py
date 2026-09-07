"""Unit tests for ``PerformanceImportRow`` persistence (P1.5-G3 dio 2 + G4).

Pins the ``save_performance_import_row`` / ``get_performance_import_row`` /
``list_performance_import_rows`` round-trips, JSON serialization (including
BHS Latin diacritics), the ``distribution_instance_id=None`` contract, the
``match_status`` column, and ``list_distribution_instances_by_campaign``
campaign isolation.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

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
    Path(__file__).resolve().parents[5] / "resources" / "migrations"
)


def _setup_repo(
    tmp_path: Path,
) -> tuple[SqlitePerformanceRepository, sqlite3.Connection]:
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)
    repo = SqlitePerformanceRepository(connection)
    repo.save_performance_import_batch(_batch("b-1"))
    return repo, connection


def _batch(batch_id: str) -> PerformanceImportBatch:
    return PerformanceImportBatch(
        id=PerformanceImportBatchId(batch_id),
        source=PerformanceSource.CSV_IMPORT,
        imported_at=datetime(2026, 1, 1, tzinfo=UTC),
        row_count=1,
        matched_count=1,
        unmatched_count=0,
        mapping_version="1",
    )


def _row(**overrides: object) -> PerformanceImportRow:
    fields: dict[str, object] = {
        "id": PerformanceImportRowId("row-1"),
        "batch_id": PerformanceImportBatchId("b-1"),
        "row_number": 1,
        "raw_values": {"doseg": "100", "trošak": "12.5", "kampanja": "akcija"},
        "mapped_values": {"reach": "100", "spend": "12.5"},
        "errors": (),
        "distribution_instance_id": None,
    }
    fields.update(overrides)
    return PerformanceImportRow(**fields)  # type: ignore[arg-type]


def _seed_distribution_instance(
    connection: sqlite3.Connection,
    repo: SqlitePerformanceRepository,
    *,
    tag: str,
    external_content_id: str | None = None,
    platform_code: str = "INSTAGRAM",
    format_code: str = "FEED_POST",
) -> DistributionInstance:
    """Seed the full FK chain + one DistributionInstance for one campaign."""
    created_at = "2026-01-01T00:00:00+00:00"
    connection.execute(
        "INSERT INTO campaign_briefs (id, offer, goal, audience_text,"
        " targets_json, content_piece_count, content_language_context,"
        " special_instructions_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (f"brief-{tag}", "offer", "goal", "audience", "[]", 1,
         "BHS_LATIN", "[]", created_at),
    )
    connection.execute(
        "INSERT INTO campaigns (id, brand_id, brand_snapshot_id, brief_id,"
        " status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (f"campaign-{tag}", "brand-1", "snap-1", f"brief-{tag}", "DRAFT",
         created_at),
    )
    connection.execute(
        "INSERT INTO campaign_plans (id, campaign_id, version, status,"
        " created_at) VALUES (?, ?, ?, ?, ?)",
        (f"plan-{tag}", f"campaign-{tag}", 1, "DRAFT", created_at),
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
        campaign_id=CampaignId(f"campaign-{tag}"),
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


def test_round_trip_single_row(tmp_path: Path) -> None:
    repo, connection = _setup_repo(tmp_path)
    row = _row()
    repo.save_performance_import_row(row)
    assert repo.get_performance_import_row(
        PerformanceImportRowId("row-1")
    ) == row
    connection.close()


def test_get_unknown_row_returns_none(tmp_path: Path) -> None:
    repo, connection = _setup_repo(tmp_path)
    assert repo.get_performance_import_row(
        PerformanceImportRowId("missing")
    ) is None
    connection.close()


def test_list_rows_returns_ordered_by_row_number(tmp_path: Path) -> None:
    repo, connection = _setup_repo(tmp_path)
    for row_number in (3, 1, 2):
        repo.save_performance_import_row(
            _row(
                id=PerformanceImportRowId(f"row-{row_number}"),
                row_number=row_number,
            )
        )
    rows = repo.list_performance_import_rows(PerformanceImportBatchId("b-1"))
    assert [r.row_number for r in rows] == [1, 2, 3]
    connection.close()


def test_json_round_trip_preserves_bhs_diacritics(tmp_path: Path) -> None:
    repo, connection = _setup_repo(tmp_path)
    row = _row(
        raw_values={
            "doseg": "širok",
            "trošak": "12,5",
            "napomena": "čćšđž ČĆŠĐŽ",
        },
        mapped_values={"reach": "širi", "spend": "12.5"},
        errors=("trošak (12,5) nije broj",),
    )
    repo.save_performance_import_row(row)
    loaded = repo.get_performance_import_row(PerformanceImportRowId("row-1"))
    assert loaded is not None
    assert loaded.raw_values == {
        "doseg": "širok",
        "trošak": "12,5",
        "napomena": "čćšđž ČĆŠĐŽ",
    }
    assert loaded.mapped_values == {"reach": "širi", "spend": "12.5"}
    assert loaded.errors == ("trošak (12,5) nije broj",)
    connection.close()


def test_distribution_instance_id_none_round_trip(tmp_path: Path) -> None:
    repo, connection = _setup_repo(tmp_path)
    row = _row(distribution_instance_id=None)
    repo.save_performance_import_row(row)
    loaded = repo.get_performance_import_row(PerformanceImportRowId("row-1"))
    assert loaded is not None
    assert loaded.distribution_instance_id is None
    connection.close()


def test_list_is_scoped_to_batch(tmp_path: Path) -> None:
    repo, connection = _setup_repo(tmp_path)
    repo.save_performance_import_batch(_batch("b-2"))
    repo.save_performance_import_row(_row(id=PerformanceImportRowId("row-a")))
    repo.save_performance_import_row(
        _row(
            id=PerformanceImportRowId("row-b"),
            batch_id=PerformanceImportBatchId("b-2"),
        )
    )
    assert len(
        repo.list_performance_import_rows(PerformanceImportBatchId("b-1"))
    ) == 1
    assert len(
        repo.list_performance_import_rows(PerformanceImportBatchId("b-2"))
    ) == 1
    connection.close()


def test_match_status_round_trip_none_then_value(tmp_path: Path) -> None:
    repo, connection = _setup_repo(tmp_path)
    repo.save_performance_import_row(_row(match_status=None))
    loaded = repo.get_performance_import_row(PerformanceImportRowId("row-1"))
    assert loaded is not None
    assert loaded.match_status is None

    repo.save_performance_import_row(_row(match_status="MATCHED"))
    loaded = repo.get_performance_import_row(PerformanceImportRowId("row-1"))
    assert loaded is not None
    assert loaded.match_status == "MATCHED"
    connection.close()


def test_list_distribution_instances_by_campaign_is_isolated(
    tmp_path: Path,
) -> None:
    repo, connection = _setup_repo(tmp_path)
    _seed_distribution_instance(
        connection, repo, tag="a", external_content_id="ext-a"
    )
    _seed_distribution_instance(
        connection, repo, tag="b", external_content_id="ext-b"
    )

    only_a = repo.list_distribution_instances_by_campaign(
        CampaignId("campaign-a")
    )
    only_b = repo.list_distribution_instances_by_campaign(
        CampaignId("campaign-b")
    )

    assert [str(d.id) for d in only_a] == ["di-a"]
    assert [str(d.id) for d in only_b] == ["di-b"]
    assert only_a[0].external_content_id == "ext-a"
    assert only_b[0].external_content_id == "ext-b"
    connection.close()
