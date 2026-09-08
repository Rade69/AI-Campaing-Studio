"""P1.5-G8 integration acceptance — deterministic end-to-end Performance chain.

This is the LAST Slice 1.5 gate. It proves the FULL Performance lane
(create → generate → export → manifest key → synthetic CSV → import+match →
materialize → campaign aggregate → content result) over the real js_api
bridge, with a DETERMINISTIC fake ``TextGenerationPort`` dispatched on
``AIRequest.purpose`` — NO real network/AI call, NO env-var dependency.

Complements (does not replace) ``test_campaign_bridge_end_to_end.py``: that
test proves a real external provider works; THIS test proves the pipeline is
wired end-to-end, including that CSV-imported metrics stop being ``None``
after the ACS-F1-057 materialization step.
"""

from __future__ import annotations

import json
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_campaign_studio.config.paths import AppPaths
from ai_campaign_studio.config.settings import AppSettings
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.repositories import (
    SqliteProviderConfigRepository,
)
from ai_campaign_studio.ports.ai import AIRequest, AIResponse
from ai_campaign_studio.ports.provider_config import ProviderConfig
from ai_campaign_studio.presentation_webview.bridge import CampaignBridgeApi


def _isolated_bridge(tmp_path: Path) -> CampaignBridgeApi:
    """Same seam every bridge test uses: an isolated temp DB + the read-only
    ``EnvironmentSecretStore`` (never the user's real OS keyring)."""
    paths = AppPaths(data_dir_override=tmp_path)
    settings = AppSettings(environment="development")
    return CampaignBridgeApi(paths=paths, settings=settings)


def _configure_provider(bridge: CampaignBridgeApi, code: str = "MOCK") -> None:
    """Mark ``MOCK`` as configured in the DB. The secret value is irrelevant
    because ``build_text_generation_adapter`` is fully patched; ``get_secret``
    is also patched to a non-empty placeholder."""
    connection = create_connection(bridge._bootstrap.paths.database_path)
    try:
        SqliteProviderConfigRepository(connection).save_provider_config(
            ProviderConfig(
                provider_code=code,
                configured=True,
                validated=True,
                credential_ref=f"provider/{code}/api_key",
                base_url=None,
                updated_at=datetime.now(UTC),
            )
        )
        connection.commit()
    finally:
        connection.close()


def _plan_payload() -> dict:
    """A schema-valid ``CampaignPlanOutput`` for content_piece_count == 2."""
    return {
        "campaign_theme": "Dental health",
        "items": [
            {
                "order": 1,
                "role": "PROBLEM",
                "topic": "T1",
                "goal": "awareness",
                "facts_needed": [],
            },
            {
                "order": 2,
                "role": "EDUCATION",
                "topic": "T2",
                "goal": "educate",
                "facts_needed": [],
            },
        ],
    }


def _post_payload(index: int) -> dict:
    """A schema-valid ``SocialPostGenerationOutput`` (unique per piece)."""
    return {
        "headline": f"headline {index}",
        "caption": f"caption {index}",
        "hook": "hook",
        "body": "body",
        "cta": "cta",
        "hashtags": [],
        "claims": [],
    }


def _visual_payload() -> dict:
    """A schema-valid ``VisualDirectionOutput`` (system + layout)."""
    return {
        "campaign_visual_system": {
            "primary_layout_family": "HERO",
            "secondary_layout_family": None,
            "headline_scale": "LARGE",
            "image_treatment": "ROUNDED",
            "logo_rule": "SHOW",
            "cta_rule": "SHOW",
            "alignment": "CENTER",
            "style": ["clean"],
        },
        "layout_spec": {
            "primitive": "HERO",
            "image_position": "BACKGROUND",
            "headline_position": "CENTER",
            "headline_scale": "LARGE",
            "overlay": "DARK",
            "logo_position": "TOP_LEFT",
            "cta_style": "SOLID",
            "alignment": "CENTER",
            "format": "FEED_POST",
        },
    }


def _layout_payload() -> dict:
    """A schema-valid ``LayoutSpecCandidate`` for one post."""
    return {
        "primitive": "HERO",
        "image_position": "BACKGROUND",
        "headline_position": "CENTER",
        "headline_scale": "LARGE",
        "overlay": "DARK",
        "logo_position": "TOP_LEFT",
        "cta_style": "SOLID",
        "alignment": "CENTER",
        "format": "999x999",
    }


class _FakeAiAdapter:
    """Deterministic fake ``TextGenerationPort`` dispatched on ``purpose``."""

    def __init__(self) -> None:
        self._post_calls = 0

    def generate(self, request: AIRequest) -> AIResponse:
        if request.purpose == "campaign_plan":
            payload = _plan_payload()
        elif request.purpose == "post_generation":
            self._post_calls += 1
            payload = _post_payload(self._post_calls)
        elif request.purpose == "visual_direction":
            payload = _visual_payload()
        elif request.purpose == "post_layout":
            payload = _layout_payload()
        else:
            raise AssertionError(f"unexpected AI purpose: {request.purpose!r}")
        return AIResponse(
            provider="fake",
            model="fake",
            latency_ms=1,
            structured_payload=payload,
        )


def _fake_factory():
    adapter = _FakeAiAdapter()

    def _factory(provider_code: str, api_key: str, *, base_url: str | None = None):
        del provider_code, api_key, base_url
        return adapter

    return _factory


def _wait_for_job_terminal(
    bridge: CampaignBridgeApi, job_id: str, *, timeout: float = 60.0
) -> dict:
    deadline = time.monotonic() + timeout
    last: dict = {}
    while time.monotonic() < deadline:
        state = bridge.get_job_status({"job_id": job_id})
        last = state
        if state.get("status") in ("SUCCEEDED", "FAILED", "CANCELLED"):
            return state
        time.sleep(0.02)
    raise AssertionError(f"job {job_id} did not reach terminal state: {last}")


def test_full_performance_chain_is_deterministic(tmp_path: Path) -> None:
    """Create → generate → export → manifest key → synthetic CSV → import+
    match+materialize → campaign aggregate → content result, all through the
    bridge with a deterministic fake adapter."""
    bridge = _isolated_bridge(tmp_path)
    _configure_provider(bridge)

    with patch.object(
        bridge._bootstrap.secret_store, "get_secret", return_value="placeholder-key"
    ), patch(
        "ai_campaign_studio.presentation_webview.bridge.build_text_generation_adapter",
        _fake_factory(),
    ):
        # -- 1. Create campaign + generate plan (fake adapter #1). --
        brief = {
            "offer": "Zubni implantati",
            "goal": "Zakazati konsultacije",
            "audience_text": "Odrasli 30-60",
            "targets": [
                {
                    "channel": "SOCIAL",
                    "platform_code": "INSTAGRAM",
                    "format_code": "FEED_POST",
                }
            ],
            "content_piece_count": 2,
            "content_language_context": "BHS_LATIN",
        }
        plan_result = bridge.create_campaign_and_generate_plan(brief)
        assert plan_result["ok"] is True, plan_result
        campaign_id = plan_result["campaign_id"]
        plan_id = plan_result["plan_id"]
        assert campaign_id and plan_id

        # -- 2. Generate content (job-backed; fake adapter #2, #3). --
        gen_result = bridge.generate_campaign_content(
            {"campaign_id": campaign_id, "plan_id": plan_id}
        )
        assert gen_result["ok"] is True, gen_result
        final_job = _wait_for_job_terminal(bridge, gen_result["job_id"])
        assert final_job["status"] == "SUCCEEDED", final_job
        assert final_job["generated_count"] == 2, final_job

        # -- 3. "approve" is a UI-only gate (no backend call) — skipped. --

        # -- 4. Export: real ZIP + manifest.json. --
        export_result = bridge.export_campaign_package(
            {"campaign_id": campaign_id, "plan_id": plan_id}
        )
        assert export_result["ok"] is True, export_result
        assert export_result["exported_count"] == 2, export_result
        zip_path = Path(export_result["zip_path"])
        assert zip_path.exists()

        # -- 5. Read manifest.json, take analytics_match_key per item. --
        with zipfile.ZipFile(zip_path) as zf:
            assert zf.testzip() is None
            manifest = json.loads(zf.read("manifest.json"))
        items = manifest["items"]
        assert len(items) == 2
        for item in items:
            assert item["analytics_match_key"]
            assert item["content_piece_id"]

        # -- 6. Synthetic CSV with the EXACT manifest keys (2 rows). --
        csv_path = tmp_path / "perf.csv"
        csv_path.write_text(
            "period_start,period_end,analytics_match_key,impressions,clicks,"
            "spend,conversions,revenue\n"
            f"2026-01-01,2026-01-31,{items[0]['analytics_match_key']},"
            "1000,34,200.0,5,500.0\n"
            f"2026-01-01,2026-01-31,{items[1]['analytics_match_key']},"
            "2000,68,400.0,10,1000.0\n",
            encoding="utf-8",
        )

        # -- 7. confirm_performance_import = import + match + materialize. --
        confirm = bridge.confirm_performance_import(
            {
                "file_path": str(csv_path),
                "campaign_id": campaign_id,
                "platform_code": None,
            }
        )
        assert confirm["ok"] is True, confirm
        # EVERY CSV row must match (the analytics_match_key chain is real).
        assert confirm["matched_count"] == 2, confirm
        assert confirm["unmatched_count"] == 0, confirm
        assert confirm["ambiguous_count"] == 0, confirm
        assert confirm["skipped_count"] == 0, confirm
        assert confirm["materialized_count"] == 2, confirm
        assert confirm["skipped_invalid_count"] == 0, confirm

        # -- 8. Campaign aggregate: hand-computed derived values. --
        # Sum of both rows: impressions 3000, clicks 102, spend 600,
        # conversions 15, revenue 1500.
        perf = bridge.get_campaign_performance({"campaign_id": campaign_id})
        assert perf["ok"] is True, perf
        assert perf["distribution_instance_count"] == 2
        assert perf["raw"]["impressions"] == 3000
        assert perf["raw"]["clicks"] == 102
        assert perf["raw"]["spend"] == 600.0
        assert perf["derived"]["ctr"] == pytest.approx(102 / 3000)
        assert perf["derived"]["cpc"] == pytest.approx(600.0 / 102)
        assert perf["derived"]["cpm"] == pytest.approx(600.0 / 3000 * 1000)
        assert perf["derived"]["cpa"] == pytest.approx(600.0 / 15)
        assert perf["derived"]["roas"] == pytest.approx(1500.0 / 600.0)
        assert perf["derived"]["conversion_rate"] == pytest.approx(15 / 102)

        # -- 9. Content result: one row per piece, correct ids. --
        content = bridge.get_campaign_content_performance(
            {"campaign_id": campaign_id}
        )
        assert content["ok"] is True, content
        assert len(content["rows"]) == 2
        piece_ids = {r["content_piece_id"] for r in content["rows"]}
        manifest_piece_ids = {item["content_piece_id"] for item in items}
        assert piece_ids == manifest_piece_ids
        # Every row now carries real (non-None) metrics — the materialization
        # step made the CSV metrics visible to the read models.
        for row in content["rows"]:
            assert row["ctr"] is not None
            assert row["cpc"] is not None
