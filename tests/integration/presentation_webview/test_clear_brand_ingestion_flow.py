"""Integration test for ACS-GUI-013 ``clear_brand_ingestion`` against a
real SQLite DB — mirrors the seeding style of
``test_ingestion_review_flow.py``.

Proves the acceptance invariant that actually matters here: a candidate
already APPROVED (and therefore copied into ``approved_facts``) survives
``clear_brand_ingestion`` even though its underlying raw snapshot/chunk is
deleted — only ``fact_candidates``/``source_snapshots``/etc. are cleared,
``approved_facts`` is never touched.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from ai_campaign_studio.config.paths import AppPaths
from ai_campaign_studio.config.settings import AppSettings
from ai_campaign_studio.domain.brand.entities import Brand
from ai_campaign_studio.domain.common.ids import (
    BrandId,
    CrawlTargetId,
    FactCandidateId,
    IngestionRunId,
    SourceSnapshotId,
)
from ai_campaign_studio.domain.facts.entities import FactCandidate
from ai_campaign_studio.domain.facts.enums import FactStatus
from ai_campaign_studio.domain.ingestion.entities import (
    CrawlTarget,
    IngestionRun,
    SourceSnapshot,
)
from ai_campaign_studio.domain.ingestion.enums import (
    CrawlTargetState,
    IngestionRunStatus,
)
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories import (
    SqliteBrandRepository,
    SqliteIngestionRepository,
)
from ai_campaign_studio.presentation_webview.bridge import CampaignBridgeApi

_MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "resources" / "migrations"

_BRAND_ID = BrandId("brand-clear")
_RUN_ID = IngestionRunId("run-clear")
_URL = "https://example.com/proizvod"
_SNAPSHOT_ID = SourceSnapshotId("snap-clear-1")
_CAND_PROPOSED = FactCandidateId("cand-clear-proposed")
_CAND_TO_APPROVE = FactCandidateId("cand-clear-to-approve")


def _isolated_bridge(tmp_path: Path) -> CampaignBridgeApi:
    db_path = tmp_path / "test.db"
    paths = AppPaths(
        app_name="AI Campaign Studio (test)",
        database_filename=db_path.name,
        data_dir_override=tmp_path,
    )
    settings = AppSettings(environment="development")
    return CampaignBridgeApi(paths=paths, settings=settings)


def _seed(bridge: CampaignBridgeApi) -> None:
    connection = create_connection(bridge._bootstrap.paths.database_path)
    try:
        run_migrations(connection, _MIGRATIONS_DIR)
        brand_repo = SqliteBrandRepository(connection)
        ingestion_repo = SqliteIngestionRepository(connection)

        brand_repo.save_brand(
            Brand(
                id=_BRAND_ID,
                name="Clear Test Brand",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )
        ingestion_repo.save_ingestion_run(
            IngestionRun(
                id=_RUN_ID,
                brand_id=_BRAND_ID,
                status=IngestionRunStatus.SUCCEEDED,
                started_at=datetime(2026, 1, 1, tzinfo=UTC),
                source_scope=(_URL,),
            )
        )
        ingestion_repo.register_crawl_targets(
            [
                CrawlTarget(
                    id=CrawlTargetId("target-clear-1"),
                    run_id=_RUN_ID,
                    normalized_url=_URL,
                    depth=0,
                    priority=100,
                    state=CrawlTargetState.PENDING,
                    attempts=0,
                )
            ]
        )
        ingestion_repo.save_source_snapshot(
            SourceSnapshot(
                id=_SNAPSHOT_ID,
                url=_URL,
                fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
                content_hash="hash-clear",
                content_type="text/html",
                status_code=200,
            )
        )
        ingestion_repo.update_crawl_target_state(
            CrawlTargetId("target-clear-1"),
            CrawlTargetState.FETCHED,
            snapshot_id=_SNAPSHOT_ID,
        )
        ingestion_repo.save_fact_candidate(
            FactCandidate(
                id=_CAND_PROPOSED,
                snapshot_id=_SNAPSHOT_ID,
                content="Proizvod ne sadrži alkohol.",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                status=FactStatus.PROPOSED,
            )
        )
        ingestion_repo.save_fact_candidate(
            FactCandidate(
                id=_CAND_TO_APPROVE,
                snapshot_id=_SNAPSHOT_ID,
                content="Pakovanje sadrži 500 ml.",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                status=FactStatus.PROPOSED,
            )
        )
        connection.commit()
    finally:
        connection.close()


def test_non_dict_payload_is_validation_error(tmp_path: Path) -> None:
    bridge = _isolated_bridge(tmp_path)
    result = bridge.clear_brand_ingestion("not a dict")  # type: ignore[arg-type]
    assert result["ok"] is False
    assert result["error_code"] == "VALIDATION_ERROR"


def test_unknown_brand_id_is_validation_error(tmp_path: Path) -> None:
    bridge = _isolated_bridge(tmp_path)
    result = bridge.clear_brand_ingestion({"brand_id": "brand-does-not-exist"})
    assert result["ok"] is False
    assert result["error_code"] == "VALIDATION_ERROR"


def test_clear_empties_review_list_and_keeps_approved_fact_intact(
    tmp_path: Path,
) -> None:
    bridge = _isolated_bridge(tmp_path)
    _seed(bridge)

    before = bridge.get_ingestion_review({"brand_id": str(_BRAND_ID)})
    assert before["ok"] is True
    assert len(before["candidates"]) == 2

    approve_result = bridge.approve_fact_candidate(
        {"candidate_id": str(_CAND_TO_APPROVE)}
    )
    assert approve_result["ok"] is True, approve_result
    approved_fact_id = approve_result["approved_fact_id"]

    clear_result = bridge.clear_brand_ingestion({"brand_id": str(_BRAND_ID)})
    assert clear_result == {
        "ok": True,
        "brand_id": str(_BRAND_ID),
        "deleted_run_count": 1,
        "error_code": None,
        "error_message": None,
    }

    after = bridge.get_ingestion_review({"brand_id": str(_BRAND_ID)})
    assert after["ok"] is True
    assert after["candidates"] == (), "review list must be empty after clear"

    connection = create_connection(bridge._bootstrap.paths.database_path)
    try:
        for table in (
            "fact_candidates",
            "source_chunks",
            "source_snapshots",
            "crawl_targets",
            "ingestion_checkpoints",
            "ingestion_runs",
        ):
            count = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            assert count == 0, f"{table} should be empty after clear, got {count}"
        approved_row = connection.execute(
            "SELECT id, content FROM approved_facts WHERE id = ?",
            (approved_fact_id,),
        ).fetchone()
        assert approved_row is not None, (
            "approved_facts row must survive clear_brand_ingestion "
            "(it holds its own content copy)"
        )
        assert approved_row["content"] == "Pakovanje sadrži 500 ml."
    finally:
        connection.close()

    # Idempotent: clearing an already-empty brand is a safe no-op, not an
    # error — the reset button must be clickable more than once.
    clear_again = bridge.clear_brand_ingestion({"brand_id": str(_BRAND_ID)})
    assert clear_again["ok"] is True
    assert clear_again["deleted_run_count"] == 0
