"""Integration test for ACS-GUI-017 ``bulk_review_fact_candidates`` against
a real SQLite DB — mirrors the seeding style of
``test_ingestion_review_flow.py`` / ``test_clear_brand_ingestion_flow.py``.
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

_BRAND_ID = BrandId("brand-bulk")
_RUN_ID = IngestionRunId("run-bulk")
_URL = "https://example.com/proizvodi"
_SNAPSHOT_ID = SourceSnapshotId("snap-bulk-1")
_CAND_IDS = [FactCandidateId(f"cand-bulk-{i}") for i in range(5)]


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
        SqliteBrandRepository(connection).save_brand(
            Brand(
                id=_BRAND_ID,
                name="Bulk Test Brand",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )
        ingestion_repo = SqliteIngestionRepository(connection)
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
                    id=CrawlTargetId("target-bulk-1"),
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
                content_hash="hash-bulk",
                content_type="text/html",
                status_code=200,
            )
        )
        ingestion_repo.update_crawl_target_state(
            CrawlTargetId("target-bulk-1"),
            CrawlTargetState.FETCHED,
            snapshot_id=_SNAPSHOT_ID,
        )
        for i, cand_id in enumerate(_CAND_IDS):
            ingestion_repo.save_fact_candidate(
                FactCandidate(
                    id=cand_id,
                    snapshot_id=_SNAPSHOT_ID,
                    content=f"Stavka broj {i}.",
                    created_at=datetime(2026, 1, 1, tzinfo=UTC),
                    status=FactStatus.PROPOSED,
                )
            )
        connection.commit()
    finally:
        connection.close()


def test_non_dict_payload_is_validation_error(tmp_path: Path) -> None:
    bridge = _isolated_bridge(tmp_path)
    result = bridge.bulk_review_fact_candidates("not a dict")  # type: ignore[arg-type]
    assert result["ok"] is False
    assert result["error_code"] == "VALIDATION_ERROR"


def test_invalid_action_is_validation_error(tmp_path: Path) -> None:
    bridge = _isolated_bridge(tmp_path)
    result = bridge.bulk_review_fact_candidates(
        {"candidate_ids": ["x"], "action": "delete"}
    )
    assert result["ok"] is False
    assert result["error_code"] == "VALIDATION_ERROR"


def test_empty_candidate_ids_is_validation_error(tmp_path: Path) -> None:
    bridge = _isolated_bridge(tmp_path)
    result = bridge.bulk_review_fact_candidates(
        {"candidate_ids": [], "action": "approve"}
    )
    assert result["ok"] is False
    assert result["error_code"] == "VALIDATION_ERROR"


def test_bulk_approve_then_bulk_reject_then_idempotent_reapprove(
    tmp_path: Path,
) -> None:
    bridge = _isolated_bridge(tmp_path)
    _seed(bridge)
    ids = [str(c) for c in _CAND_IDS]

    approve_first_three = bridge.bulk_review_fact_candidates(
        {"candidate_ids": ids[:3], "action": "approve"}
    )
    assert approve_first_three == {
        "ok": True,
        "action": "approve",
        "succeeded_count": 3,
        "failed_count": 0,
        "error_code": None,
        "error_message": None,
    }

    reject_last_two = bridge.bulk_review_fact_candidates(
        {"candidate_ids": ids[3:], "action": "reject"}
    )
    assert reject_last_two == {
        "ok": True,
        "action": "reject",
        "succeeded_count": 2,
        "failed_count": 0,
        "error_code": None,
        "error_message": None,
    }

    review = bridge.get_ingestion_review({"brand_id": str(_BRAND_ID)})
    assert review["approved_count"] == 3
    assert review["rejected_count"] == 2

    # Partial-batch safety: re-approving already-decided ids must not raise —
    # each fails independently and the batch still returns ok=True with
    # accurate counts (this is exactly what a double-click / stale selection
    # in the GUI would produce).
    re_approve = bridge.bulk_review_fact_candidates(
        {"candidate_ids": ids, "action": "approve"}
    )
    assert re_approve["ok"] is True
    assert re_approve["succeeded_count"] == 0
    assert re_approve["failed_count"] == 5


def test_unknown_candidate_id_counts_as_failed_not_fatal(tmp_path: Path) -> None:
    bridge = _isolated_bridge(tmp_path)
    _seed(bridge)
    result = bridge.bulk_review_fact_candidates(
        {
            "candidate_ids": [str(_CAND_IDS[0]), "cand-does-not-exist"],
            "action": "approve",
        }
    )
    assert result["ok"] is True
    assert result["succeeded_count"] == 1
    assert result["failed_count"] == 1
