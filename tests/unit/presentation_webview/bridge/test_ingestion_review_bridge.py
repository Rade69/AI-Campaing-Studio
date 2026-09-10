"""Unit tests for the S2-G7b ingestion-review bridge methods.

Boundary validation, error mapping, and the resource-lifecycle error
dispatch (which must return the exact per-method DTO shape, same rule as
every other bridge method — no other method's keys may leak through).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from ai_campaign_studio.config.paths import AppPaths
from ai_campaign_studio.config.settings import AppSettings
from ai_campaign_studio.presentation_webview.bridge import CampaignBridgeApi


def _isolated_bridge(tmp_path: Path) -> CampaignBridgeApi:
    db_path = tmp_path / "test.db"
    paths = AppPaths(
        app_name="AI Campaign Studio (test)",
        database_filename=db_path.name,
        data_dir_override=tmp_path,
    )
    settings = AppSettings(environment="development")
    return CampaignBridgeApi(paths=paths, settings=settings)


def test_non_dict_payload_returns_validation_error_for_all_four_methods(
    tmp_path: Path,
) -> None:
    bridge = _isolated_bridge(tmp_path)
    calls = [
        bridge.get_ingestion_review,
        bridge.approve_fact_candidate,
        bridge.reject_fact_candidate,
        bridge.assemble_brand_snapshot,
    ]
    for call in calls:
        result = call("not a dict")  # type: ignore[arg-type]
        assert result["ok"] is False
        assert result["error_code"] == "VALIDATION_ERROR"


def test_missing_candidate_id_is_validation_error(tmp_path: Path) -> None:
    bridge = _isolated_bridge(tmp_path)
    assert bridge.approve_fact_candidate({})["error_code"] == "VALIDATION_ERROR"
    assert bridge.reject_fact_candidate({})["error_code"] == "VALIDATION_ERROR"


def test_approve_unknown_candidate_is_validation_error(tmp_path: Path) -> None:
    bridge = _isolated_bridge(tmp_path)
    result = bridge.approve_fact_candidate({"candidate_id": "cand-missing"})
    assert result["ok"] is False
    assert result["error_code"] == "VALIDATION_ERROR"
    assert "ne postoji" in result["error_message"].lower()


def test_reject_unknown_candidate_is_validation_error(tmp_path: Path) -> None:
    bridge = _isolated_bridge(tmp_path)
    result = bridge.reject_fact_candidate({"candidate_id": "cand-missing"})
    assert result["ok"] is False
    assert result["error_code"] == "VALIDATION_ERROR"


def test_lifecycle_failure_uses_per_method_error_shape(tmp_path: Path) -> None:
    """A resource-lifecycle exception (SQLite open fails) must map to the
    exact per-method DTO shape — the same BF-5 rule as every other bridge
    method. No other method's keys may leak through.
    """
    bridge = _isolated_bridge(tmp_path)
    with patch(
        "ai_campaign_studio.presentation_webview.bridge.create_connection",
        side_effect=RuntimeError("db open failed"),
    ):
        review = bridge.get_ingestion_review({})
        approve = bridge.approve_fact_candidate({"candidate_id": "c-any"})
        reject = bridge.reject_fact_candidate({"candidate_id": "c-any"})
        assemble = bridge.assemble_brand_snapshot({})

    assert review["ok"] is False
    assert review["error_code"] == "INTERNAL_ERROR"
    assert set(review.keys()) == {
        "ok",
        "brand_id",
        "candidates",
        "approved_count",
        "rejected_count",
        "error_code",
        "error_message",
    }

    assert approve["ok"] is False
    assert approve["error_code"] == "INTERNAL_ERROR"
    assert set(approve.keys()) == {
        "ok",
        "approved_fact_id",
        "candidate_id",
        "snapshot_url",
        "version",
        "error_code",
        "error_message",
    }

    assert reject["ok"] is False
    assert reject["error_code"] == "INTERNAL_ERROR"
    assert set(reject.keys()) == {
        "ok",
        "candidate_id",
        "status",
        "error_code",
        "error_message",
    }

    assert assemble["ok"] is False
    assert assemble["error_code"] == "INTERNAL_ERROR"
    assert set(assemble.keys()) == {
        "ok",
        "snapshot_id",
        "brand_id",
        "version",
        "approved_fact_count",
        "created_at",
        "error_code",
        "error_message",
    }
