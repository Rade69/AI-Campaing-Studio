"""Unit tests for the ACS-GUI-011 ``start_brand_ingestion`` bridge method.

Boundary validation only, no network — deterministic. The actual live
ingestion (real HttpFetcher against a real external URL, real JobManager
background execution, real SQLite persistence, verified via the EXISTING
``get_job_status``/``get_ingestion_review`` bridge methods) is documented as
manual evidence in agent_reports/2026-09-11-ACS-GUI-011-claude.md — the
production wiring hardcodes ``UrlSafetyPolicy()`` (correctly, no test seam
that could weaken the real SSRF guard), so hitting a real socket from this
suite would require either a live internet call or a policy test-seam this
task deliberately does not add (scope boundary, see task contract).
"""

from __future__ import annotations

from pathlib import Path

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


def test_non_dict_payload_is_validation_error(tmp_path: Path) -> None:
    bridge = _isolated_bridge(tmp_path)
    result = bridge.start_brand_ingestion("not a dict")  # type: ignore[arg-type]
    assert result["ok"] is False
    assert result["error_code"] == "VALIDATION_ERROR"
    assert result["job_id"] is None


def test_missing_urls_is_validation_error(tmp_path: Path) -> None:
    bridge = _isolated_bridge(tmp_path)
    result = bridge.start_brand_ingestion({})
    assert result["ok"] is False
    assert result["error_code"] == "VALIDATION_ERROR"


def test_empty_urls_list_is_validation_error(tmp_path: Path) -> None:
    bridge = _isolated_bridge(tmp_path)
    result = bridge.start_brand_ingestion({"urls": []})
    assert result["ok"] is False
    assert result["error_code"] == "VALIDATION_ERROR"


def test_non_string_url_item_is_validation_error(tmp_path: Path) -> None:
    bridge = _isolated_bridge(tmp_path)
    result = bridge.start_brand_ingestion({"urls": [123]})
    assert result["ok"] is False
    assert result["error_code"] == "VALIDATION_ERROR"


def test_blank_url_item_is_validation_error(tmp_path: Path) -> None:
    bridge = _isolated_bridge(tmp_path)
    result = bridge.start_brand_ingestion({"urls": ["   "]})
    assert result["ok"] is False
    assert result["error_code"] == "VALIDATION_ERROR"


def test_non_string_brand_id_is_validation_error(tmp_path: Path) -> None:
    bridge = _isolated_bridge(tmp_path)
    result = bridge.start_brand_ingestion(
        {"brand_id": 123, "urls": ["https://example.com/"]}
    )
    assert result["ok"] is False
    assert result["error_code"] == "VALIDATION_ERROR"


def test_unknown_brand_id_is_validation_error(tmp_path: Path) -> None:
    bridge = _isolated_bridge(tmp_path)
    result = bridge.start_brand_ingestion(
        {"brand_id": "brand-does-not-exist", "urls": ["https://example.com/"]}
    )
    assert result["ok"] is False
    assert result["error_code"] == "VALIDATION_ERROR"
    assert "ne postoji" in result["error_message"].lower()
