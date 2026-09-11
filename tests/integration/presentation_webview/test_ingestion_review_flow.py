"""End-to-end S2-G7b ingestion-review flow against a real SQLite DB.

Exercises the four new bridge methods through the real composition
(``CampaignBridgeApi`` + ``SqliteIngestionRepository`` + ``SqliteFactRepository``
+ ``SqliteBrandRepository``) with a manually seeded ingestion chain
(run → crawl target → source snapshot → fact candidates). Covers the
acceptance invariants: get_ingestion_review provenance, approve delegation
+ idempotency, assemble version increment + no_approved_facts error, and
G-WI-EVIDENCE (approved fact source_ref.uri traceable to the snapshot URL).
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

_BRAND_ID = BrandId("brand-review")
_RUN_ID = IngestionRunId("run-review")
_URL = "https://example.com/proizvod"
_SNAPSHOT_ID = SourceSnapshotId("snap-review-1")
_CAND_1 = FactCandidateId("cand-review-1")
_CAND_2 = FactCandidateId("cand-review-2")


def _isolated_bridge(tmp_path: Path) -> CampaignBridgeApi:
    """Bridge whose DB/seed live under ``tmp_path`` (never the real user dir)."""
    db_path = tmp_path / "test.db"
    paths = AppPaths(
        app_name="AI Campaign Studio (test)",
        database_filename=db_path.name,
        data_dir_override=tmp_path,
    )
    settings = AppSettings(environment="development")
    return CampaignBridgeApi(paths=paths, settings=settings)


def _seed_review_data(bridge: CampaignBridgeApi) -> None:
    """Seed a brand + ingestion chain + two PROPOSED candidates."""
    connection = create_connection(bridge._bootstrap.paths.database_path)
    try:
        run_migrations(connection, _MIGRATIONS_DIR)
        brand_repo = SqliteBrandRepository(connection)
        ingestion_repo = SqliteIngestionRepository(connection)

        brand_repo.save_brand(
            Brand(
                id=_BRAND_ID,
                name="Review Brand",
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
                    id=CrawlTargetId("target-review-1"),
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
                content_hash="hash-review",
                content_type="text/html",
                status_code=200,
            )
        )
        ingestion_repo.update_crawl_target_state(
            CrawlTargetId("target-review-1"),
            CrawlTargetState.FETCHED,
            snapshot_id=_SNAPSHOT_ID,
        )
        ingestion_repo.save_fact_candidate(
            FactCandidate(
                id=_CAND_1,
                snapshot_id=_SNAPSHOT_ID,
                content="Proizvod ne sadrži alkohol.",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                status=FactStatus.PROPOSED,
            )
        )
        ingestion_repo.save_fact_candidate(
            FactCandidate(
                id=_CAND_2,
                snapshot_id=_SNAPSHOT_ID,
                content="Pakovanje sadrži 500 ml.",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                status=FactStatus.PROPOSED,
            )
        )
        connection.commit()
    finally:
        connection.close()


def test_review_approve_assemble_flow(tmp_path: Path) -> None:
    bridge = _isolated_bridge(tmp_path)
    _seed_review_data(bridge)

    review = bridge.get_ingestion_review({"brand_id": str(_BRAND_ID)})
    assert review["ok"] is True, review
    assert review["brand_id"] == str(_BRAND_ID)
    assert review["approved_count"] == 0
    assert review["rejected_count"] == 0
    candidates = {c["candidate_id"]: c for c in review["candidates"]}
    assert set(candidates) == {str(_CAND_1), str(_CAND_2)}
    # G-WI-EVIDENCE (type-level read): snapshot_url is the source snapshot URL.
    assert all(c["snapshot_url"] == _URL for c in review["candidates"])
    assert all(c["status"] == "PROPOSED" for c in review["candidates"])

    # Approve delegates to G7a and returns the new ApprovedFact.
    approved = bridge.approve_fact_candidate({"candidate_id": str(_CAND_1)})
    assert approved["ok"] is True, approved
    assert approved["approved_fact_id"] is not None
    assert approved["snapshot_url"] == _URL
    assert approved["version"] == 1

    # Idempotency (G7a): double approve of the same candidate -> validation.
    double = bridge.approve_fact_candidate({"candidate_id": str(_CAND_1)})
    assert double["ok"] is False
    assert double["error_code"] == "VALIDATION_ERROR"

    # Reject delegates to G7a.
    rejected = bridge.reject_fact_candidate({"candidate_id": str(_CAND_2)})
    assert rejected["ok"] is True, rejected
    assert rejected["status"] == "REJECTED"

    # Assemble: only the APPROVED fact is included; version starts at 1.
    assembled = bridge.assemble_brand_snapshot({"brand_id": str(_BRAND_ID)})
    assert assembled["ok"] is True, assembled
    assert assembled["version"] == 1
    assert assembled["approved_fact_count"] == 1

    # Second assemble increments the version (version race).
    assembled2 = bridge.assemble_brand_snapshot({"brand_id": str(_BRAND_ID)})
    assert assembled2["ok"] is True, assembled2
    assert assembled2["version"] == 2

    # G-WI-EVIDENCE (data-level): the persisted snapshot's fact source_ref.uri
    # traces back to the source snapshot URL.
    connection = create_connection(bridge._bootstrap.paths.database_path)
    try:
        brand_repo = SqliteBrandRepository(connection)
        latest = brand_repo.get_latest_snapshot(_BRAND_ID)
        assert latest is not None
        assert latest.version == 2
        assert len(latest.approved_fact_ids) == 1
        fact_id = latest.approved_fact_ids[0]
        fact_row = connection.execute(
            "SELECT source_uri FROM approved_facts WHERE id = ?", (fact_id,)
        ).fetchone()
        assert fact_row is not None
        assert fact_row["source_uri"] == _URL
    finally:
        connection.close()


def test_assemble_without_approved_facts_is_validation_error(
    tmp_path: Path,
) -> None:
    bridge = _isolated_bridge(tmp_path)
    _seed_review_data(bridge)

    # No candidate has been approved yet.
    result = bridge.assemble_brand_snapshot({"brand_id": str(_BRAND_ID)})
    assert result["ok"] is False
    assert result["error_code"] == "VALIDATION_ERROR"
    assert "odobrenih" in result["error_message"].lower()


def test_get_ingestion_review_unknown_brand_is_validation_error(
    tmp_path: Path,
) -> None:
    bridge = _isolated_bridge(tmp_path)
    _seed_review_data(bridge)

    result = bridge.get_ingestion_review({"brand_id": "brand-does-not-exist"})
    assert result["ok"] is False
    assert result["error_code"] == "VALIDATION_ERROR"
