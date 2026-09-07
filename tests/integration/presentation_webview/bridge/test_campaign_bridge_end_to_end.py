"""Real, live vertical-slice test of the js_api bridge (all four
merged read/write paths) against a genuine external AI provider.

Owns: the ONE test in this repo that calls the real DeepSeek API
through the actual production code path (``CampaignBridgeApi`` ->
``JobManager`` -> ``provider_adapter_factory`` -> real HTTP call).
Does not own: any application/use-case logic (covered by
``tests/integration/application/*``); does not own mocked/fixture
bridge behaviour (covered by
``tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py``).

Every prior "requires real API keys, not run" reference to this exact
file path across several evidence reports (ACS-GUI-005, ACS-F1-047,
ACS-GUI-009) was aspirational -- the file never actually existed until
now (2026-09-07), after ACS-F1-046 (list_campaigns) and ACS-GUI-009
(export_campaign_package) landed and made the full loop observable
for the first time: create -> plan -> approve -> generate content ->
SEE it in the list -> export a real ZIP.

Requires ``AI_CAMPAIGN_STUDIO_DEEPSEEK_API_KEY`` in the environment (a
real DeepSeek API key). Skipped entirely otherwise -- this is
deliberately NOT part of the default ``pytest -q`` run's assumptions;
CI does not set this variable, so CI runs it as a skip, never a
failure. Uses a ``tmp_path``-isolated SQLite DB + ``EnvironmentSecretStore``
(the same seam every other bridge test uses) -- it NEVER touches the
user's real ``%LOCALAPPDATA%`` database or OS keyring, even though the
API call itself is 100% real.
"""

from __future__ import annotations

import json
import os
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ai_campaign_studio.config.paths import AppPaths
from ai_campaign_studio.config.settings import AppSettings
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.repositories import (
    SqliteProviderConfigRepository,
)
from ai_campaign_studio.ports.provider_config import ProviderConfig
from ai_campaign_studio.presentation_webview.bridge import CampaignBridgeApi

pytestmark = pytest.mark.skipif(
    not os.environ.get("AI_CAMPAIGN_STUDIO_DEEPSEEK_API_KEY"),
    reason=(
        "AI_CAMPAIGN_STUDIO_DEEPSEEK_API_KEY not set -- live vertical-slice "
        "test skipped (needs a real DeepSeek API key; see EnvironmentSecretStore)"
    ),
)


def _isolated_bridge(tmp_path: Path) -> CampaignBridgeApi:
    """Same seam every other bridge test uses: an isolated temp DB +
    the read-only, env-var-backed ``EnvironmentSecretStore`` (never
    the user's real OS keyring)."""
    paths = AppPaths(data_dir_override=tmp_path)
    settings = AppSettings(environment="development")
    return CampaignBridgeApi(paths=paths, settings=settings)


def _configure_deepseek(bridge: CampaignBridgeApi) -> None:
    """Mark DEEPSEEK as configured in the DB. The actual secret value
    is read from ``AI_CAMPAIGN_STUDIO_DEEPSEEK_API_KEY`` by
    ``EnvironmentSecretStore.get_secret`` at call time -- this helper
    never sees or touches the key itself."""
    connection = create_connection(bridge._bootstrap.paths.database_path)
    try:
        SqliteProviderConfigRepository(connection).save_provider_config(
            ProviderConfig(
                provider_code="DEEPSEEK",
                configured=True,
                validated=True,
                credential_ref="provider/DEEPSEEK/api_key",
                base_url=None,
                updated_at=datetime.now(UTC),
            )
        )
        connection.commit()
    finally:
        connection.close()


def _wait_for_job_terminal(
    bridge: CampaignBridgeApi, job_id: str, *, timeout: float = 180.0
) -> dict:
    """Real AI calls take real time -- a generous timeout, not the 5s
    used by the mocked-adapter unit tests."""
    deadline = time.monotonic() + timeout
    last: dict = {}
    while time.monotonic() < deadline:
        state = bridge.get_job_status({"job_id": job_id})
        last = state
        if state.get("status") in ("SUCCEEDED", "FAILED", "CANCELLED"):
            return state
        time.sleep(0.5)
    raise AssertionError(f"job {job_id} did not reach terminal state: {last}")


def test_full_vertical_slice_against_real_deepseek(tmp_path: Path) -> None:
    """Create -> plan -> approve -> generate -> list -> export, all
    through the real js_api bridge, against the real DeepSeek API.

    This is the live counterpart to the mocked-adapter unit tests --
    it proves the ACTUAL wiring (JobManager, provider_adapter_factory,
    the OpenAI-SDK-compatible DeepSeek adapter, list_campaigns,
    export_campaign_package) works end-to-end with a genuine external
    call, not just with a fake AI port standing in for one.
    """
    bridge = _isolated_bridge(tmp_path)
    _configure_deepseek(bridge)

    # -- 1. Create campaign + generate plan (real AI call #1). --
    brief = {
        "offer": "Zubni implantati -- proljetna promocija",
        "goal": "Zakazati besplatne konsultacije",
        "audience_text": "Odrasli 30-60 godina koji razmatraju zubne implantate",
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
    assert plan_result["ok"] is True, (
        f"create_campaign_and_generate_plan failed against real DeepSeek: "
        f"{plan_result}"
    )
    campaign_id = plan_result["campaign_id"]
    plan_id = plan_result["plan_id"]
    assert campaign_id and plan_id

    # -- 2. Generate content (real AI call #2, #3 -- one per item; the
    #    plan is DRAFT so this also exercises the auto-approve dance). --
    gen_result = bridge.generate_campaign_content(
        {"campaign_id": campaign_id, "plan_id": plan_id}
    )
    assert gen_result["ok"] is True, gen_result
    job_id = gen_result["job_id"]
    final_job = _wait_for_job_terminal(bridge, job_id)
    assert final_job["status"] == "SUCCEEDED", (
        f"generate_campaign_content job did not succeed against real "
        f"DeepSeek: {final_job}"
    )
    assert final_job["generated_count"] >= 1, (
        f"expected at least 1 real generated piece, got: {final_job}"
    )

    # -- 3. list_campaigns: the campaign must be genuinely visible,
    #    not just present in the DB. This is the exact read path
    #    ACS-F1-046 added -- proves the GUI can actually SHOW what
    #    step 1-2 just created. --
    list_result = bridge.list_campaigns({})
    assert list_result["ok"] is True, list_result
    matching = [
        c for c in list_result["campaigns"] if c["id"] == campaign_id
    ]
    assert len(matching) == 1, (
        f"campaign {campaign_id} not found via list_campaigns: "
        f"{list_result['campaigns']}"
    )
    assert matching[0]["plan_item_count"] == 2

    # -- 4. export_campaign_package: a real ZIP must land on disk with
    #    a valid manifest -- the exact path ACS-GUI-009 added. --
    export_result = bridge.export_campaign_package(
        {"campaign_id": campaign_id, "plan_id": plan_id}
    )
    assert export_result["ok"] is True, export_result
    zip_path = Path(export_result["zip_path"])
    assert zip_path.exists(), f"export claimed success but no ZIP at {zip_path}"
    with zipfile.ZipFile(zip_path) as zf:
        assert zf.testzip() is None, "exported ZIP is corrupt"
        names = zf.namelist()
        assert "manifest.json" in names
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest.get("campaign_id") == campaign_id

    print(
        f"\n[LIVE E2E] campaign_id={campaign_id} plan_id={plan_id} "
        f"generated={final_job['generated_count']} zip={zip_path}"
    )
