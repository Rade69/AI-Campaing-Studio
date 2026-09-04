"""Unit tests for the GUI→backend bridge (ACS-GUI-005).

These tests do not make any real network call. They exercise the bridge's
boundary-validation, error-mapping, brand-seeding, and provider-resolution
paths in isolation. The composition root (``create_bootstrap``) is real —
it is fast and offline — but the secret store and DB are backed by a
temp dir + in-memory-style configuration override so the test never
touches the user's real ``%LOCALAPPDATA%`` or keyring.

Heavy integration coverage (full ``CreateCampaign + GenerateCampaignPlan``
against a real SQLite DB with a fake AI port) lives in
``tests/integration/presentation_webview/bridge/test_campaign_bridge_end_to_end.py``.
"""

from __future__ import annotations

import json
from datetime import UTC
from pathlib import Path
from unittest.mock import patch

from ai_campaign_studio.config.paths import AppPaths
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories import (
    SqliteBrandRepository,
    SqliteCampaignRepository,
    SqliteFactRepository,
    SqliteProviderConfigRepository,
)
from ai_campaign_studio.infrastructure.database.unit_of_work import SqliteUnitOfWork
from ai_campaign_studio.ports.ai import AIRequest, AIResponse
from ai_campaign_studio.ports.provider_config import ProviderConfig
from ai_campaign_studio.presentation_webview.bridge import CampaignBridgeApi

# --- fixtures ---


_MIGRATIONS_DIR = (
    Path(__file__).resolve().parents[4] / "resources" / "migrations"
)
_FIXTURE_PATH = (
    Path(__file__).resolve().parents[4] / "resources" / "fixtures" / "brightsmile.json"
)


def _isolated_bridge(tmp_path: Path) -> CampaignBridgeApi:
    """Build a bridge whose AppPaths points at ``tmp_path`` (so the
    brand-seed.json file lives in the test dir, not the user's real
    ``%LOCALAPPDATA%``).

    Uses the explicit ``AppPaths(data_dir_override=tmp_path)`` seam
    that ``create_bootstrap(paths=...)`` accepts — NOT a fake env var,
    because ``AppSettings`` does not actually expose
    ``data_dir_override`` as an env-driven field. The DB connection
    is also rebuilt against the test path with migrations applied so
    every test starts from a clean schema.
    """
    db_path = tmp_path / "test.db"
    paths = AppPaths(
        app_name="AI Campaign Studio (test)",
        database_filename=db_path.name,
        data_dir_override=tmp_path,
    )
    bridge = CampaignBridgeApi(paths=paths)
    # The bootstrap's DB connection lives at ``paths.database_path``,
    # which is already inside ``tmp_path`` because we passed the override
    # in. We close it and reopen against the explicit test path so the
    # brand/campaign/provider repos share one connection, then re-run
    # migrations against a fresh schema.
    bridge._bootstrap.database_connection.close()
    conn = create_connection(db_path)
    run_migrations(conn, _MIGRATIONS_DIR)
    bridge._bootstrap.database_connection = conn
    bridge._brand_repo = SqliteBrandRepository(conn)
    bridge._fact_repo = SqliteFactRepository(conn)
    bridge._campaign_repo = SqliteCampaignRepository(conn)
    bridge._provider_config_repo = SqliteProviderConfigRepository(conn)
    bridge._uow = SqliteUnitOfWork(conn)
    bridge._brand_fixture_path = _FIXTURE_PATH
    return bridge


def _configure_provider(
    repo: SqliteProviderConfigRepository, code: str, *, configured: bool = True
) -> None:
    from datetime import datetime
    repo.save_provider_config(ProviderConfig(
        provider_code=code,
        configured=configured,
        validated=True,
        credential_ref=f"provider/{code}/api_key",
        base_url=None,
        updated_at=datetime.now(UTC),
    ))


def _valid_brief() -> dict:
    return {
        "offer": "Test offer",
        "goal": "Test goal",
        "audience_text": "Adults 25-45",
        "targets": [
            {
                "channel": "SOCIAL",
                "platform_code": "INSTAGRAM",
                "format_code": "FEED_POST",
            }
        ],
        "content_piece_count": 3,
        "content_language_context": "SR",
    }


class _FakeAiAdapter:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def generate(self, request: AIRequest) -> AIResponse:
        del request
        return AIResponse(
            provider="fake", model="fake", latency_ms=1,
            structured_payload=self._payload,
        )


def _fake_ai_factory(payload: dict):
    """Return a function that, when called, returns a fake AI adapter."""
    fake = _FakeAiAdapter(payload)
    def _factory(provider_code: str, api_key: str, *, base_url: str | None = None):
        assert provider_code in ("OPENAI", "ANTHROPIC", "GOOGLE")
        assert api_key  # non-empty
        return fake
    return _factory


def _valid_ai_payload() -> dict:
    return {
        "campaign_theme": "Theme",
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
            {
                "order": 3,
                "role": "ACTION",
                "topic": "T3",
                "goal": "convert",
                "facts_needed": [],
            },
        ],
    }


# --- boundary validation (PYWEBVIEW_SECURITY §3) ---


def test_non_dict_payload_returns_validation_error(tmp_path) -> None:
    bridge = _isolated_bridge(tmp_path)
    result = bridge.create_campaign_and_generate_plan("not a dict")  # type: ignore[arg-type]
    assert result["ok"] is False
    assert result["error_code"] == "VALIDATION_ERROR"
    msg = result["error_message"].lower()
    assert "objekat" in msg or "dict" in msg


def test_pydantic_validation_failure_returns_validation_error(tmp_path) -> None:
    bridge = _isolated_bridge(tmp_path)
    # Missing required keys (offer/goal/audience_text/targets/...)
    result = bridge.create_campaign_and_generate_plan({"offer": "x"})
    assert result["ok"] is False
    assert result["error_code"] == "VALIDATION_ERROR"


# --- provider resolution ---


def test_no_provider_configured_returns_no_provider_error(tmp_path) -> None:
    bridge = _isolated_bridge(tmp_path)
    with patch(
        "ai_campaign_studio.presentation_webview.bridge.build_text_generation_adapter"
    ):
        result = bridge.create_campaign_and_generate_plan(_valid_brief())
    assert result["ok"] is False
    assert result["error_code"] == "NO_PROVIDER_CONFIGURED"
    assert "nijedan ai provajder" in result["error_message"].lower()


def test_configured_provider_but_no_key_returns_key_missing(tmp_path) -> None:
    bridge = _isolated_bridge(tmp_path)
    _configure_provider(bridge._provider_config_repo, "OPENAI")
    with patch.object(bridge._bootstrap.secret_store, "get_secret", return_value=""):
        result = bridge.create_campaign_and_generate_plan(_valid_brief())
    assert result["ok"] is False
    assert result["error_code"] == "PROVIDER_KEY_MISSING"


def test_provider_fallback_uses_second_when_first_has_no_key(tmp_path) -> None:
    bridge = _isolated_bridge(tmp_path)
    _configure_provider(bridge._provider_config_repo, "OPENAI")
    _configure_provider(bridge._provider_config_repo, "GOOGLE")

    def _fake_get_secret(ref: str) -> str:
        # OPENAI is higher priority but its key is missing; GOOGLE has one.
        if ref == "provider/OPENAI/api_key":
            return ""
        return "sk-google-key"

    called_with: dict[str, str] = {}

    def _recording_factory(
        provider_code: str, api_key: str, *, base_url: str | None = None
    ):
        called_with["provider_code"] = provider_code
        called_with["api_key"] = api_key
        return _FakeAiAdapter(_valid_ai_payload())

    with patch.object(
        bridge._bootstrap.secret_store, "get_secret", side_effect=_fake_get_secret
    ), patch(
        "ai_campaign_studio.presentation_webview.bridge.build_text_generation_adapter",
        _recording_factory,
    ):
        result = bridge.create_campaign_and_generate_plan(_valid_brief())

    assert result["ok"] is True, f"unexpected result: {result}"
    assert called_with["provider_code"] == "GOOGLE"


def test_provider_fallback_all_missing_keys_returns_key_missing(tmp_path) -> None:
    bridge = _isolated_bridge(tmp_path)
    _configure_provider(bridge._provider_config_repo, "OPENAI")
    _configure_provider(bridge._provider_config_repo, "ANTHROPIC")
    _configure_provider(bridge._provider_config_repo, "GOOGLE")
    with patch.object(
        bridge._bootstrap.secret_store, "get_secret", return_value=""
    ):
        result = bridge.create_campaign_and_generate_plan(_valid_brief())
    assert result["ok"] is False
    assert result["error_code"] == "PROVIDER_KEY_MISSING"


# --- happy path ---


def test_happy_path_creates_campaign_and_plan(tmp_path) -> None:
    bridge = _isolated_bridge(tmp_path)
    _configure_provider(bridge._provider_config_repo, "OPENAI")
    with patch.object(
        bridge._bootstrap.secret_store, "get_secret", return_value="sk-test-key"
    ), patch(
        "ai_campaign_studio.presentation_webview.bridge.build_text_generation_adapter",
        _fake_ai_factory(_valid_ai_payload()),
    ):
        result = bridge.create_campaign_and_generate_plan(_valid_brief())
    assert result["ok"] is True, f"unexpected result: {result}"
    assert result["campaign_id"] is not None
    assert result["plan_item_count"] == 3
    assert result["error_code"] is None
    assert result["error_message"] is None
    # Brand seeding wrote brand-seed.json in the (overridden) user data dir.
    seed = json.loads((tmp_path / "brand-seed.json").read_text(encoding="utf-8"))
    assert "brand_id" in seed and "brand_snapshot_id" in seed


def test_brand_seed_reused_on_second_call(tmp_path) -> None:
    """Two consecutive clicks must NOT duplicate the brand (contract)."""
    bridge = _isolated_bridge(tmp_path)
    _configure_provider(bridge._provider_config_repo, "OPENAI")
    with patch.object(
        bridge._bootstrap.secret_store, "get_secret", return_value="sk-test-key"
    ), patch(
        "ai_campaign_studio.presentation_webview.bridge.build_text_generation_adapter",
        _fake_ai_factory(_valid_ai_payload()),
    ):
        bridge.create_campaign_and_generate_plan(_valid_brief())
        first_seed = json.loads(
            (tmp_path / "brand-seed.json").read_text(encoding="utf-8")
        )
        bridge.create_campaign_and_generate_plan(_valid_brief())
        second_seed = json.loads(
            (tmp_path / "brand-seed.json").read_text(encoding="utf-8")
        )
    # Exactly one brand in the DB.
    count = bridge._bootstrap.database_connection.execute(
        "SELECT COUNT(*) FROM brands"
    ).fetchone()[0]
    assert count == 1, f"expected 1 brand, got {count}"
    # Same identity across both calls, not just the same row count: the
    # seed file must point at the SAME brand_id both times, and the single
    # DB row must be that same id.
    assert first_seed["brand_id"] == second_seed["brand_id"]
    db_brand_id = bridge._bootstrap.database_connection.execute(
        "SELECT id FROM brands"
    ).fetchone()[0]
    assert db_brand_id == first_seed["brand_id"]


def test_returned_dict_is_json_serializable_and_contains_no_secrets(tmp_path) -> None:
    """PYWEBVIEW_SECURITY §3: the js_api return value must be JSON-safe
    and never contain API keys, tokens, or paths.
    """
    bridge = _isolated_bridge(tmp_path)
    _configure_provider(bridge._provider_config_repo, "OPENAI")
    sentinel_key = "sk-EXAMPLE-leak-detector-1234"
    with patch.object(
        bridge._bootstrap.secret_store, "get_secret", return_value=sentinel_key
    ), patch(
        "ai_campaign_studio.presentation_webview.bridge.build_text_generation_adapter",
        _fake_ai_factory(_valid_ai_payload()),
    ):
        result = bridge.create_campaign_and_generate_plan(_valid_brief())
    blob = json.dumps(result)
    assert sentinel_key not in blob
    # No traceback-y leakage
    assert "Traceback" not in blob
    assert "Exception" not in blob


# --- error paths ---


def test_provider_adapter_construction_failure_returns_key_missing(tmp_path) -> None:
    bridge = _isolated_bridge(tmp_path)
    _configure_provider(bridge._provider_config_repo, "GOOGLE")
    with patch.object(
        bridge._bootstrap.secret_store, "get_secret", return_value="k"
    ), patch(
        "ai_campaign_studio.presentation_webview.bridge.build_text_generation_adapter",
        side_effect=ValueError("boom"),
    ):
        result = bridge.create_campaign_and_generate_plan(_valid_brief())
    assert result["ok"] is False
    assert result["error_code"] == "PROVIDER_KEY_MISSING"
    # The raw exception text must not leak to JS.
    assert "boom" not in result["error_message"]


def test_unexpected_exception_in_bridge_returns_internal_error(tmp_path) -> None:
    bridge = _isolated_bridge(tmp_path)
    # Patch _ensure_brand to raise something totally unexpected (not a
    # domain error). The bridge must catch-all and return INTERNAL_ERROR.
    with patch.object(bridge, "_ensure_brand", side_effect=RuntimeError("oops")):
        result = bridge.create_campaign_and_generate_plan(_valid_brief())
    assert result["ok"] is False
    assert result["error_code"] == "INTERNAL_ERROR"
    # No raw exception text in the user-facing message.
    assert "oops" not in result["error_message"]


# --- ACS-GUI-006: compensating delete of orphan DRAFT campaign ------------


def _failing_ai_factory(exception: Exception):
    """Return a factory whose adapter raises ``exception`` on every call.

    Used to force the ``GenerateCampaignPlan`` path to throw after
    ``CreateCampaign`` has already committed.
    """

    def _factory(provider_code: str, api_key: str, *, base_url: str | None = None):

        class _RaisingAdapter:
            def generate(self, request: AIRequest) -> AIResponse:  # noqa: ARG002
                raise exception

        return _RaisingAdapter()

    return _factory


def test_orphan_campaign_deleted_when_generate_plan_fails(tmp_path) -> None:
    """GenerateCampaignPlan fails AFTER CreateCampaign committed -> the
    orphan DRAFT campaign MUST be cleaned up before the GENERATION_FAILED
    error returns to JS.

    The exact failure path that originally motivated this task: AI
    provider returns 404 (or any network/SDK error) and the user gets
    a toast. Without the compensating delete, every retry would
    accumulate a new orphan row.
    """
    bridge = _isolated_bridge(tmp_path)
    _configure_provider(bridge._provider_config_repo, "OPENAI")
    with patch.object(
        bridge._bootstrap.secret_store, "get_secret", return_value="sk-test-key"
    ), patch(
        "ai_campaign_studio.presentation_webview.bridge.build_text_generation_adapter",
        _failing_ai_factory(RuntimeError("provider down")),
    ):
        result = bridge.create_campaign_and_generate_plan(_valid_brief())

    assert result["ok"] is False
    assert result["error_code"] == "GENERATION_FAILED"
    # The orphan row MUST be gone. We assert on the DB directly because
    # the bridge is the only API the JS caller sees, and we want to
    # prove the row is actually absent — not just that the function
    # returned a dict.
    conn = bridge._bootstrap.database_connection
    assert conn.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0] == 0
    # Brief created by CreateCampaign is also gone (it was created
    # in the same compensating action — see the docstring on
    # delete_campaign for why this is safe in the bridge's call site).
    assert conn.execute("SELECT COUNT(*) FROM campaign_briefs").fetchone()[0] == 0


def test_orphan_campaign_deleted_on_domain_error_in_generate_plan(
    tmp_path,
) -> None:
    """Same compensating behavior for the (EntityNotFound, InvariantViolation)
    domain-error path inside ``GenerateCampaignPlan`` (separate from the
    generic Exception branch).
    """
    from ai_campaign_studio.domain.common.errors import InvariantViolation

    bridge = _isolated_bridge(tmp_path)
    _configure_provider(bridge._provider_config_repo, "OPENAI")
    with patch.object(
        bridge._bootstrap.secret_store, "get_secret", return_value="sk-test-key"
    ), patch(
        "ai_campaign_studio.presentation_webview.bridge.build_text_generation_adapter",
        _failing_ai_factory(InvariantViolation("role_sequence violated")),
    ):
        result = bridge.create_campaign_and_generate_plan(_valid_brief())

    assert result["ok"] is False
    assert result["error_code"] == "GENERATION_FAILED"
    conn = bridge._bootstrap.database_connection
    assert conn.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0] == 0


def test_compensating_delete_failure_does_not_mask_generation_error(
    tmp_path,
) -> None:
    """If ``delete_campaign`` itself raises (DB locked, disk full,
    programming error), the bridge MUST swallow it and return the
    ORIGINAL GENERATION_FAILED error to JS — not a database error
    that hides what the user actually needs to know.
    """
    bridge = _isolated_bridge(tmp_path)
    _configure_provider(bridge._provider_config_repo, "OPENAI")
    with patch.object(
        bridge._bootstrap.secret_store, "get_secret", return_value="sk-test-key"
    ), patch(
        "ai_campaign_studio.presentation_webview.bridge.build_text_generation_adapter",
        _failing_ai_factory(RuntimeError("provider down")),
    ), patch.object(
        bridge._campaign_repo,
        "delete_campaign",
        side_effect=RuntimeError("DB locked"),
    ):
        result = bridge.create_campaign_and_generate_plan(_valid_brief())

    # The user-facing result is the AI error, NOT the DB error.
    assert result["ok"] is False
    assert result["error_code"] == "GENERATION_FAILED"
    assert "DB locked" not in result["error_message"]
    # The user-facing message must talk about the AI generation failure,
    # not the database error. "AI generisanje plana" is the bridge's
    # stable BHS message for the SDK exception branch.
    assert "ai generisanje plana" in result["error_message"].lower()


def test_create_campaign_failure_does_not_call_delete(tmp_path) -> None:
    """If ``CreateCampaign`` itself fails (validation, DB error during
    brand seed), there is nothing to compensate — no row was ever
    committed. The bridge MUST NOT call ``delete_campaign`` in that
    path (would be a no-op at best, masking the real error at worst).
    """
    bridge = _isolated_bridge(tmp_path)
    _configure_provider(bridge._provider_config_repo, "OPENAI")
    with patch.object(
        bridge._bootstrap.secret_store, "get_secret", return_value="sk-test-key"
    ), patch.object(
        bridge, "_ensure_brand", side_effect=ValueError("brand seed boom")
    ), patch.object(
        bridge._campaign_repo, "delete_campaign"
    ) as fake_delete:
        result = bridge.create_campaign_and_generate_plan(_valid_brief())

    # Brand seed failure -> INTERNAL_ERROR (caught by the generic
    # catch-all in the bridge).
    assert result["ok"] is False
    assert result["error_code"] == "INTERNAL_ERROR"
    # delete_campaign was NEVER called — there was nothing to delete.
    fake_delete.assert_not_called()
