"""Status-filter regression for facts used to assemble brand snapshots."""

from __future__ import annotations

from pathlib import Path

from ai_campaign_studio.domain.facts.enums import FactStatus
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.repositories import SqliteFactRepository
from tests.integration.presentation_webview.test_ingestion_review_flow import (
    _BRAND_ID,
    _CAND_1,
    _CAND_2,
    _isolated_bridge,
    _seed_review_data,
)


def test_list_approved_facts_excludes_unusable_statuses(tmp_path: Path) -> None:
    bridge = _isolated_bridge(tmp_path)
    _seed_review_data(bridge)

    first = bridge.approve_fact_candidate({"candidate_id": str(_CAND_1)})
    assert first["ok"] is True, first

    connection = create_connection(bridge._bootstrap.paths.database_path)
    try:
        repository = SqliteFactRepository(connection)
        statuses = [
            fact.status
            for fact in repository.list_approved_facts_by_brand(_BRAND_ID)
        ]
        assert statuses == [FactStatus.APPROVED]
        connection.execute(
            "UPDATE approved_facts SET status = ? WHERE id = ?",
            (FactStatus.SOFT_DELETED.value, first["approved_fact_id"]),
        )
        connection.commit()
        assert repository.list_approved_facts_by_brand(_BRAND_ID) == ()
    finally:
        connection.close()

    second = bridge.approve_fact_candidate({"candidate_id": str(_CAND_2)})
    assert second["ok"] is True, second
    connection = create_connection(bridge._bootstrap.paths.database_path)
    try:
        repository = SqliteFactRepository(connection)
        connection.execute(
            "UPDATE approved_facts SET status = ? WHERE id = ?",
            (FactStatus.SUPERSEDED.value, second["approved_fact_id"]),
        )
        connection.commit()
        assert repository.list_approved_facts_by_brand(_BRAND_ID) == ()
    finally:
        connection.close()

    assembled = bridge.assemble_brand_snapshot({"brand_id": str(_BRAND_ID)})
    assert assembled["ok"] is False
    assert assembled["error_code"] == "VALIDATION_ERROR"
    assert "odobrenih" in assembled["error_message"].lower()
