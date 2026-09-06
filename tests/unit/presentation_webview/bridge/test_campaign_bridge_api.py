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
from datetime import UTC, datetime
from pathlib import Path
from threading import Thread
from unittest.mock import patch

from ai_campaign_studio.config.paths import AppPaths
from ai_campaign_studio.config.settings import AppSettings
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories import (
    SqliteCampaignRepository,
    SqliteContentRepository,
    SqliteFactRepository,
    SqliteRevisionRepository,
    SqliteProviderConfigRepository,
    SqliteRevisionRepository,
)
from ai_campaign_studio.ports.ai import AIRequest, AIResponse
from ai_campaign_studio.ports.provider_config import ProviderConfig
from ai_campaign_studio.presentation_webview.bridge import CampaignBridgeApi

# --- fixtures ---


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
    ``data_dir_override`` as an env-driven field. Bridge construction
    runs migrations once; each public method opens its own connection.

    ACS-GUI-007: also passes ``settings=AppSettings(environment="development")``
    so the test bridge uses the read-only ``EnvironmentSecretStore``
    (no real keyring writes during pytest runs). Production
    ``CampaignBridgeApi()`` defaults to ``environment="production"``
    which would touch the real OS keyring — never acceptable in tests.
    """
    db_path = tmp_path / "test.db"
    paths = AppPaths(
        app_name="AI Campaign Studio (test)",
        database_filename=db_path.name,
        data_dir_override=tmp_path,
    )
    settings = AppSettings(environment="development")
    bridge = CampaignBridgeApi(paths=paths, settings=settings)
    # The bootstrap closes its startup connection in ``__init__``
    # (HOTFIX-002). Each public method opens its own connection via
    # ``_resource_scope()``. Test helpers that need direct repo
    # access (for seeding / counting) open their own connection.
    bridge._brand_fixture_path = _FIXTURE_PATH
    return bridge


def _configure_provider(
    bridge: CampaignBridgeApi, code: str, *, configured: bool = True
) -> None:
    from datetime import datetime
    connection = create_connection(bridge._bootstrap.paths.database_path)
    try:
        repo = SqliteProviderConfigRepository(connection)
        repo.save_provider_config(ProviderConfig(
            provider_code=code,
            configured=configured,
            validated=True,
            credential_ref=f"provider/{code}/api_key",
            base_url=None,
            updated_at=datetime.now(UTC),
        ))
        connection.commit()
    finally:
        connection.close()


def _scalar(bridge: CampaignBridgeApi, query: str) -> object:
    connection = create_connection(bridge._bootstrap.paths.database_path)
    try:
        return connection.execute(query).fetchone()[0]
    finally:
        connection.close()


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


def _call_on_fresh_thread(call, payload: dict) -> dict:
    """Mirror pywebview's one-new-thread-per-js_api-call dispatch."""
    results: list[dict] = []
    errors: list[BaseException] = []

    def _target() -> None:
        try:
            results.append(call(payload))
        except BaseException as exc:  # pragma: no cover - assertion aid
            errors.append(exc)

    thread = Thread(target=_target)
    thread.start()
    thread.join()

    assert not errors, f"js_api method raised from worker thread: {errors!r}"
    assert len(results) == 1
    return results[0]


def test_js_api_methods_work_from_fresh_worker_threads(tmp_path) -> None:
    """ACS-HOTFIX-002: reproduce real pywebview thread dispatch."""
    bridge = _isolated_bridge(tmp_path)

    with patch.object(bridge._bootstrap.secret_store, "set_secret"):
        configured = _call_on_fresh_thread(
            bridge.configure_provider,
            {"provider_code": "openai", "api_key": "placeholder"},
        )
    assert configured["ok"] is True, configured

    _configure_provider(bridge, "OPENAI")
    with patch.object(
        bridge._bootstrap.secret_store, "get_secret", return_value="placeholder"
    ), patch(
        "ai_campaign_studio.presentation_webview.bridge.build_text_generation_adapter",
        _fake_ai_factory(_valid_ai_payload()),
    ):
        generated = _call_on_fresh_thread(
            bridge.create_campaign_and_generate_plan,
            _valid_brief(),
        )
    assert generated["ok"] is True, generated


def test_migrations_run_once_at_bridge_startup_not_per_js_api_call(tmp_path) -> None:
    """Per-call connections reuse the schema prepared at startup."""
    with patch(
        "ai_campaign_studio.bootstrap.run_migrations", wraps=run_migrations
    ) as migration_runner:
        bridge = _isolated_bridge(tmp_path)
        with patch.object(bridge._bootstrap.secret_store, "set_secret"):
            first = bridge.configure_provider(
                {"provider_code": "openai", "api_key": "placeholder"}
            )
            second = bridge.configure_provider(
                {"provider_code": "openai", "api_key": "placeholder"}
            )

    assert first["ok"] is True
    assert second["ok"] is True
    assert migration_runner.call_count == 1


def test_connection_failure_never_raises_or_leaks_secret_to_js(tmp_path) -> None:
    bridge = _isolated_bridge(tmp_path)
    sentinel_key = "test-secret-connection-failure-sentinel"

    with patch(
        "ai_campaign_studio.presentation_webview.bridge.create_connection",
        side_effect=RuntimeError(f"failed while handling {sentinel_key}"),
    ):
        configured = bridge.configure_provider(
            {"provider_code": "openai", "api_key": sentinel_key}
        )
        generated = bridge.create_campaign_and_generate_plan(_valid_brief())

    assert configured["ok"] is False
    assert configured["error_code"] == "INTERNAL_ERROR"
    assert generated["ok"] is False
    assert generated["error_code"] == "INTERNAL_ERROR"
    assert sentinel_key not in json.dumps(configured)
    assert sentinel_key not in json.dumps(generated)


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
    _configure_provider(bridge, "OPENAI")
    with patch.object(bridge._bootstrap.secret_store, "get_secret", return_value=""):
        result = bridge.create_campaign_and_generate_plan(_valid_brief())
    assert result["ok"] is False
    assert result["error_code"] == "PROVIDER_KEY_MISSING"


def test_provider_fallback_uses_second_when_first_has_no_key(tmp_path) -> None:
    bridge = _isolated_bridge(tmp_path)
    _configure_provider(bridge, "OPENAI")
    _configure_provider(bridge, "GOOGLE")

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
    _configure_provider(bridge, "OPENAI")
    _configure_provider(bridge, "ANTHROPIC")
    _configure_provider(bridge, "GOOGLE")
    with patch.object(
        bridge._bootstrap.secret_store, "get_secret", return_value=""
    ):
        result = bridge.create_campaign_and_generate_plan(_valid_brief())
    assert result["ok"] is False
    assert result["error_code"] == "PROVIDER_KEY_MISSING"


# --- happy path ---


def test_happy_path_creates_campaign_and_plan(tmp_path) -> None:
    bridge = _isolated_bridge(tmp_path)
    _configure_provider(bridge, "OPENAI")
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
    _configure_provider(bridge, "OPENAI")
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
    count = _scalar(bridge, "SELECT COUNT(*) FROM brands")
    assert count == 1, f"expected 1 brand, got {count}"
    # Same identity across both calls, not just the same row count: the
    # seed file must point at the SAME brand_id both times, and the single
    # DB row must be that same id.
    assert first_seed["brand_id"] == second_seed["brand_id"]
    db_brand_id = _scalar(bridge, "SELECT id FROM brands")
    assert db_brand_id == first_seed["brand_id"]


def test_returned_dict_is_json_serializable_and_contains_no_secrets(tmp_path) -> None:
    """PYWEBVIEW_SECURITY §3: the js_api return value must be JSON-safe
    and never contain API keys, tokens, or paths.
    """
    bridge = _isolated_bridge(tmp_path)
    _configure_provider(bridge, "OPENAI")
    sentinel_key = "sk-EXAMPLE-redacted-1234"
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
    _configure_provider(bridge, "GOOGLE")
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
    _configure_provider(bridge, "OPENAI")
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
    assert _scalar(bridge, "SELECT COUNT(*) FROM campaigns") == 0
    # Brief created by CreateCampaign is also gone (it was created
    # in the same compensating action — see the docstring on
    # delete_campaign for why this is safe in the bridge's call site).
    assert _scalar(bridge, "SELECT COUNT(*) FROM campaign_briefs") == 0


def test_orphan_campaign_deleted_on_domain_error_in_generate_plan(
    tmp_path,
) -> None:
    """Same compensating behavior for the (EntityNotFound, InvariantViolation)
    domain-error path inside ``GenerateCampaignPlan`` (separate from the
    generic Exception branch).
    """
    from ai_campaign_studio.domain.common.errors import InvariantViolation

    bridge = _isolated_bridge(tmp_path)
    _configure_provider(bridge, "OPENAI")
    with patch.object(
        bridge._bootstrap.secret_store, "get_secret", return_value="sk-test-key"
    ), patch(
        "ai_campaign_studio.presentation_webview.bridge.build_text_generation_adapter",
        _failing_ai_factory(InvariantViolation("role_sequence violated")),
    ):
        result = bridge.create_campaign_and_generate_plan(_valid_brief())

    assert result["ok"] is False
    assert result["error_code"] == "GENERATION_FAILED"
    assert _scalar(bridge, "SELECT COUNT(*) FROM campaigns") == 0


def test_compensating_delete_failure_does_not_mask_generation_error(
    tmp_path,
) -> None:
    """If ``delete_campaign`` itself raises (DB locked, disk full,
    programming error), the bridge MUST swallow it and return the
    ORIGINAL GENERATION_FAILED error to JS — not a database error
    that hides what the user actually needs to know.
    """
    bridge = _isolated_bridge(tmp_path)
    _configure_provider(bridge, "OPENAI")
    with patch.object(
        bridge._bootstrap.secret_store, "get_secret", return_value="sk-test-key"
    ), patch(
        "ai_campaign_studio.presentation_webview.bridge.build_text_generation_adapter",
        _failing_ai_factory(RuntimeError("provider down")),
    ), patch.object(
        SqliteCampaignRepository,
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
    _configure_provider(bridge, "OPENAI")
    with patch.object(
        bridge._bootstrap.secret_store, "get_secret", return_value="sk-test-key"
    ), patch.object(
        bridge, "_ensure_brand", side_effect=ValueError("brand seed boom")
    ), patch.object(
        SqliteCampaignRepository, "delete_campaign"
    ) as fake_delete:
        result = bridge.create_campaign_and_generate_plan(_valid_brief())

    # Brand seed failure -> INTERNAL_ERROR (caught by the generic
    # catch-all in the bridge).
    assert result["ok"] is False
    assert result["error_code"] == "INTERNAL_ERROR"
    # delete_campaign was NEVER called — there was nothing to delete.
    fake_delete.assert_not_called()


# --- ACS-GUI-007: configure_provider (real KeyringSecretStore wiring) -------


def test_configure_provider_non_dict_payload_returns_validation_error(
    tmp_path,
) -> None:
    """The bridge must validate the payload shape BEFORE it touches
    any secret store. A non-dict payload is a contract violation from
    JS, not a backend error."""
    bridge = _isolated_bridge(tmp_path)
    result = bridge.configure_provider("not a dict")  # type: ignore[arg-type]
    assert result["ok"] is False
    assert result["error_code"] == "VALIDATION_ERROR"
    # The api_key never even reached the bridge's namespace; no
    # possible way for the secret to be in the message.
    assert "api_key" not in result["error_message"].lower()


def test_configure_provider_missing_provider_code_returns_validation_error(
    tmp_path,
) -> None:
    bridge = _isolated_bridge(tmp_path)
    result = bridge.configure_provider({"api_key": "sk-test"})
    assert result["ok"] is False
    assert result["error_code"] == "VALIDATION_ERROR"
    # The api_key from the input must NOT appear in the error message.
    assert "sk-test" not in result["error_message"]


def test_configure_provider_missing_api_key_returns_validation_error(
    tmp_path,
) -> None:
    bridge = _isolated_bridge(tmp_path)
    result = bridge.configure_provider({"provider_code": "openai"})
    assert result["ok"] is False
    assert result["error_code"] == "VALIDATION_ERROR"


def test_configure_provider_empty_string_fields_rejected(tmp_path) -> None:
    """An empty / whitespace-only provider_code or api_key is treated
    the same as missing (the contract's ``.strip() != ""`` rule)."""
    bridge = _isolated_bridge(tmp_path)
    result = bridge.configure_provider(
        {"provider_code": "   ", "api_key": "\t\n"}
    )
    assert result["ok"] is False
    assert result["error_code"] == "VALIDATION_ERROR"


def test_configure_provider_wrong_field_types_rejected(tmp_path) -> None:
    """JS may send numbers / booleans / nulls; we only accept strings."""
    bridge = _isolated_bridge(tmp_path)
    for bad_payload in (
        {"provider_code": 123, "api_key": "sk-test"},
        {"provider_code": "openai", "api_key": None},
        {"provider_code": None, "api_key": "sk-test"},
        {"provider_code": ["openai"], "api_key": "sk-test"},
    ):
        result = bridge.configure_provider(bad_payload)
        assert result["ok"] is False
        assert result["error_code"] == "VALIDATION_ERROR"


def test_configure_provider_unknown_provider_returns_validation_error(
    tmp_path,
) -> None:
    """A code that the registry does not know is a validation error
    (the use-case raises RegistryError, which the bridge maps to
    VALIDATION_ERROR). It is NOT a backend error."""
    bridge = _isolated_bridge(tmp_path)
    result = bridge.configure_provider(
        {"provider_code": "NOT_A_PROVIDER", "api_key": "sk-test"}
    )
    assert result["ok"] is False
    assert result["error_code"] == "VALIDATION_ERROR"


def test_configure_provider_success_persists_to_secret_store(
    tmp_path,
) -> None:
    """Happy path: api_key really IS written to the configured
    SecretStore (EnvironmentSecretStore in test, since we passed
    ``settings=AppSettings(environment="development")``)."""
    bridge = _isolated_bridge(tmp_path)
    api_key = "sk-test-redacted-redacted-12345"

    captured: dict[str, str] = {}

    def fake_set_secret(credential_ref: str, value: str) -> None:
        captured["ref"] = credential_ref
        captured["value"] = value

    with patch.object(
        bridge._bootstrap.secret_store, "set_secret", side_effect=fake_set_secret
    ):
        result = bridge.configure_provider(
            {"provider_code": "openai", "api_key": api_key}
        )

    assert result["ok"] is True
    assert result["provider_code"] == "OPENAI"
    assert result["error_code"] is None
    assert result["error_message"] is None
    # Verify the value reached the store AND that the canonical
    # credential ref is used (ConfigureProvider builds the ref as
    # ``provider/<CODE>/api_key``).
    assert captured["ref"] == "provider/OPENAI/api_key"
    assert captured["value"] == api_key


def test_configure_provider_normalizes_provider_code_to_uppercase(
    tmp_path,
) -> None:
    """JS may send ``"openai"`` (lowercase, matching the screen fixture);
    the bridge normalizes to ``"OPENAI"`` (the registry convention)
    BEFORE calling the use-case."""
    bridge = _isolated_bridge(tmp_path)
    captured: dict[str, str] = {}

    def fake_set_secret(credential_ref: str, value: str) -> None:
        captured["ref"] = credential_ref

    with patch.object(
        bridge._bootstrap.secret_store, "set_secret", side_effect=fake_set_secret
    ):
        result = bridge.configure_provider(
            {"provider_code": "  openai  ", "api_key": "  sk-test  "}
        )

    assert result["ok"] is True
    assert result["provider_code"] == "OPENAI"
    # Trimming: the credential_ref is the UPPERCASE code (no spaces).
    assert captured["ref"] == "provider/OPENAI/api_key"


def test_configure_provider_never_returns_api_key_in_result(tmp_path) -> None:
    """Per docs/PYWEBVIEW_SECURITY §3: the result dict must NEVER carry
    the api_key. Sentinel value to detect even partial / masked leaks."""
    bridge = _isolated_bridge(tmp_path)
    sentinel_key = "sk-EXAMPLE-redacted-1234567890"
    with patch.object(
        bridge._bootstrap.secret_store, "set_secret"
    ):
        result = bridge.configure_provider(
            {"provider_code": "openai", "api_key": sentinel_key}
        )
    blob = json.dumps(result)
    # The raw sentinel must not appear in the result.
    assert sentinel_key not in blob
    # A substring of the sentinel must not appear either (catches masked
    # prefixes like "sk-EXAMPLE-redacted...").
    assert "redacted" not in blob
    # Traceback / Exception text also not present.
    assert "Traceback" not in blob
    assert "Exception" not in blob


def test_configure_provider_does_not_log_api_key(tmp_path, caplog) -> None:
    """The api_key MUST NOT appear in any log record emitted by the
    bridge during a configure_provider call. We assert this by scanning
    ALL log records' formatted messages."""
    import logging

    bridge = _isolated_bridge(tmp_path)
    sentinel_key = "sk-LOG-redacted-9999"

    with caplog.at_level(logging.DEBUG), patch.object(
        bridge._bootstrap.secret_store, "set_secret"
    ):
        # Happy path log lines
        bridge.configure_provider(
            {"provider_code": "openai", "api_key": sentinel_key}
        )
        # Generic exception path (provider_code IS allowed in logs;
        # api_key is NOT).
        with patch.object(
            bridge._bootstrap.secret_store,
            "set_secret",
            side_effect=RuntimeError("backend boom"),
        ):
            bridge.configure_provider(
                {"provider_code": "openai", "api_key": sentinel_key}
            )

    for record in caplog.records:
        # The api_key (full or substring) must NEVER appear in any
        # log line. provider_code is fine.
        assert "redacted" not in record.getMessage(), (
            f"api_key leaked into log: {record.getMessage()!r}"
        )


def test_configure_provider_log_does_not_include_exception_message_with_api_key(
    tmp_path, caplog
) -> None:
    """ACS-GUI-007 BF-3 regression: even if the SecretStore backend (or
    a test double / future adapter / a buggy ``ConfigureProvider``
    change) accidentally inlines the api_key into the exception
    message, the LOG FILE must not contain it.

    Prior to the BF-3 fix, the generic exception branch used
    ``logger.exception(...)`` which logs the FULL traceback + exception
    text — so a backend that included the key in its ``str(exc)``
    would leak it to ``ai_campaign_studio.log``. The fix replaces
    ``logger.exception`` with ``logger.error(format, *args)`` so only
    the formatted message + the (safe) args are written; the
    exception object itself never reaches the handler.

    The previous test (``test_configure_provider_does_not_log_api_key``)
    used a sanitized ``RuntimeError("backend boom")`` whose message
    did NOT contain the key — so it could not catch this scenario.
    This test uses a deliberately poisoned exception message.
    """
    import logging

    bridge = _isolated_bridge(tmp_path)
    sentinel_key = "sk-LOG-LEAK-POISONED-99999"
    poisoned_message = (
        f"keyring backend rejected credential that started with {sentinel_key}"
    )
    with caplog.at_level(logging.DEBUG), patch.object(
        bridge._bootstrap.secret_store,
        "set_secret",
        side_effect=RuntimeError(poisoned_message),
    ):
        result = bridge.configure_provider(
            {"provider_code": "openai", "api_key": sentinel_key}
        )

    # The result dict is still safe (we already tested this).
    assert result["ok"] is False
    assert result["error_code"] == "INTERNAL_ERROR"
    assert "sk-LOG-LEAK-POISONED" not in json.dumps(result)

    # The CRITICAL assertion: no log record (formatted message) may
    # contain the api_key or the poisoned exception text.
    for record in caplog.records:
        msg = record.getMessage()
        assert "sk-LOG-LEAK-POISONED" not in msg, (
            f"api_key leaked into log: {msg!r}"
        )
        # Also verify the exception traceback itself is not part of
        # the formatted message (``logger.error`` does NOT include
        # traceback; ``logger.exception`` WOULD). The test would FAIL
        # under the pre-BF-3 code with the same poisoned message.
        assert "keyring backend rejected" not in msg, (
            f"exception text leaked into log: {msg!r}"
        )


def test_configure_provider_secret_store_error_returns_internal_error(
    tmp_path,
) -> None:
    """If the secret store itself raises (keyring locked, no backend,
    permission denied), the user sees ``INTERNAL_ERROR`` and a SAFE
    message — NOT the SDK / backend exception text (which could
    theoretically contain backend-specific details)."""
    bridge = _isolated_bridge(tmp_path)
    with patch.object(
        bridge._bootstrap.secret_store,
        "set_secret",
        side_effect=RuntimeError("keyring backend unreachable: detailed reason"),
    ):
        result = bridge.configure_provider(
            {"provider_code": "openai", "api_key": "sk-test"}
        )
    assert result["ok"] is False
    assert result["error_code"] == "INTERNAL_ERROR"
    # The raw backend message must NOT leak to JS.
    assert "keyring backend unreachable" not in result["error_message"]
    assert "detailed reason" not in result["error_message"]
    # And the api_key is still not in the message.
    assert "sk-test" not in result["error_message"]


# --- ACS-GUI-007 BF-1 fix: error-path SHAPE is exactly ProviderConfigResultUiModel


def test_configure_provider_error_shape_has_no_campaign_flow_keys(tmp_path) -> None:
    """BF-1 regression: every ``configure_provider`` error path MUST
    return the exact ``ProviderConfigResultUiModel`` shape —
    ``{ok, provider_code, error_code, error_message}`` and NOTHING
    else. In particular, no ``campaign_id`` / ``plan_item_count``
    leakage from the campaign flow's shared ``_err()`` helper.

    The previous version routed all configure_provider errors through
    ``_err()`` (hard-coded to ``CampaignPlanResultUiModel``), so every
    error came back with ``campaign_id`` and ``plan_item_count`` keys
    (both ``None``). That violated the contract for the JS caller
    (which keys to read) AND the structural no-``api_key``-field
    guarantee for the new DTO.
    """
    bridge = _isolated_bridge(tmp_path)
    expected_keys = {"ok", "provider_code", "error_code", "error_message"}

    # Path 1: non-dict payload.
    r1 = bridge.configure_provider("not a dict")  # type: ignore[arg-type]
    assert set(r1) == expected_keys, f"non-dict: got keys {set(r1)}"
    assert r1["ok"] is False
    assert r1["provider_code"] is None
    assert r1["error_code"] == "VALIDATION_ERROR"
    # Critical: NO campaign-flow keys.
    assert "campaign_id" not in r1
    assert "plan_item_count" not in r1

    # Path 2: missing provider_code.
    r2 = bridge.configure_provider({"api_key": "sk-test"})
    assert set(r2) == expected_keys
    assert "campaign_id" not in r2
    assert "plan_item_count" not in r2

    # Path 3: missing api_key.
    r3 = bridge.configure_provider({"provider_code": "openai"})
    assert set(r3) == expected_keys
    assert "campaign_id" not in r3
    assert "plan_item_count" not in r3

    # Path 4: empty-string fields.
    r4 = bridge.configure_provider(
        {"provider_code": "   ", "api_key": "\t\n"}
    )
    assert set(r4) == expected_keys
    assert "campaign_id" not in r4
    assert "plan_item_count" not in r4

    # Path 5: wrong field types.
    r5 = bridge.configure_provider(
        {"provider_code": 123, "api_key": "sk-test"}
    )
    assert set(r5) == expected_keys
    assert "campaign_id" not in r5
    assert "plan_item_count" not in r5

    # Path 6: unknown provider_code (RegistryError path).
    r6 = bridge.configure_provider(
        {"provider_code": "NOT_A_PROVIDER", "api_key": "sk-test"}
    )
    assert set(r6) == expected_keys
    assert "campaign_id" not in r6
    assert "plan_item_count" not in r6

    # Path 7: generic exception in the use-case (e.g. SecretStoreError).
    with patch.object(
        bridge._bootstrap.secret_store,
        "set_secret",
        side_effect=RuntimeError("keyring backend unreachable"),
    ):
        r7 = bridge.configure_provider(
            {"provider_code": "openai", "api_key": "sk-test"}
        )
    assert set(r7) == expected_keys, f"INTERNAL_ERROR: got keys {set(r7)}"
    assert r7["error_code"] == "INTERNAL_ERROR"
    assert "campaign_id" not in r7
    assert "plan_item_count" not in r7


def test_configure_provider_is_a_js_api_surface(tmp_path) -> None:
    """The new method is part of the bridge's public surface (like
    ``create_campaign_and_generate_plan``), so its signature must be
    a single positional ``raw_payload: dict`` parameter and a
    JSON-serializable dict return — the same rule as ACS-GUI-005.

    Inspect the UNBOUND method (class attribute) so ``self`` is in
    ``sig.parameters``; on a bound instance method, Python 3.14 hides
    ``self``.
    """
    import inspect

    sig = inspect.signature(CampaignBridgeApi.configure_provider)
    assert list(sig.parameters) == ["self", "raw_payload"]


# --- ACS-GUI-008: generate_campaign_content ---------------------------------
#
# These tests pin the bulk-content-generation path. The bridge composes
# ApproveCampaignPlan (idempotent) + GenerateSocialPost (per CampaignItem
# with round-robin target assignment), and never raises into JS.
# Partial-failure handling is the key difference from the all-or-nothing
# ``create_campaign_and_generate_plan`` flow.


def _valid_social_payload() -> dict:
    """One ``SocialPostGenerationOutput``-shaped payload (per item)."""
    return {
        "headline": "h",
        "caption": "c",
        "hook": "k",
        "body": "b",
        "cta": "ct",
        "hashtags": [],
        "claims": [],
    }


def _seed_brand_and_campaign(
    bridge: CampaignBridgeApi,
    *,
    num_items: int = 3,
    num_targets: int = 1,
    item_topic_prefix: str = "T",
) -> tuple[str, str]:
    """Seed a fresh brand + campaign + DRAFT plan with N items.

    Mirrors the steps the real bridge takes in
    ``create_campaign_and_generate_plan`` but bypasses the
    ``CreateCampaign + GenerateCampaignPlan`` orchestration in the
    bridge itself — we need the campaign_id to pass into
    ``generate_campaign_content`` and a plan the bridge can approve.
    """
    from ai_campaign_studio.application.campaigns.create_campaign import (
        CreateCampaign,
    )
    from ai_campaign_studio.domain.campaign.entities import (
        CampaignItem,
        CampaignPlan,
    )
    from ai_campaign_studio.domain.campaign.enums import (
        CampaignItemStatus,
        CampaignPlanStatus,
    )
    from ai_campaign_studio.domain.campaign.roles import CampaignRole
    from ai_campaign_studio.domain.common.ids import CampaignItemId

    # 1. Brand fixture (real; we exercise the same path the live app uses).
    brand_id, snapshot_id = bridge._ensure_brand()

    # 2. Campaign with N target variants (round-robin will pick from
    #    this list). Default 1 target = the typical Instagram-FEED_POST
    #    brief; bump to 2+ for the round-robin test.
    targets = [
        {
            "channel": "SOCIAL",
            "platform_code": "INSTAGRAM" if i == 0 else "FACEBOOK",
            "format_code": "FEED_POST",
        }
        for i in range(num_targets)
    ]

    raw_brief = {
        "offer": "Test offer",
        "goal": "Test goal",
        "audience_text": "Adults 25-45",
        "targets": targets,
        "content_piece_count": num_items,
        "content_language_context": "BHS_LATIN",
    }
    campaign = CreateCampaign(
        campaign_repo=bridge._campaign_repo,
        unit_of_work=bridge._uow,
    ).execute(brand_id, snapshot_id, raw_brief)

    # 3. Plan with N items (DRAFT — the bridge approves it).
    plan_items: list[CampaignItem] = []
    for i in range(num_items):
        plan_items.append(
            CampaignItem(
                id=CampaignItemId(f"item-{i+1}"),
                order=i + 1,
                role=CampaignRole.PROBLEM if i == 0 else CampaignRole.EDUCATION,
                topic=f"{item_topic_prefix}{i+1}",
                goal="awareness",
                status=CampaignItemStatus.PLANNED,
            )
        )
    plan = CampaignPlan(
        id="plan-1",
        campaign_id=campaign.id,
        version=1,
        status=CampaignPlanStatus.DRAFT,
        created_at=datetime.now(UTC),
        items=tuple(plan_items),
    )
    bridge._campaign_repo.save_plan(plan)

    return str(campaign.id), str(plan.id)


def _approve_plan(bridge: CampaignBridgeApi, plan_id: str) -> None:
    """Manually mark a plan as APPROVED (simulates a prior
    ``create_campaign_and_generate_plan`` + manual approval)."""
    from ai_campaign_studio.application.campaigns.approve_campaign_plan import (
        ApproveCampaignPlan,
    )

    # The plan id is a string in the fake seed; convert back to the
    # type ApproveCampaignPlan expects.
    from ai_campaign_studio.domain.common.ids import CampaignPlanId

    ApproveCampaignPlan(
        campaign_repo=bridge._campaign_repo,
        unit_of_work=bridge._uow,
    ).execute(CampaignPlanId(plan_id))


def _count_content_pieces(bridge: CampaignBridgeApi, campaign_id_str: str) -> int:
    """Direct DB count of content_pieces for a campaign — the strongest
    evidence the bridge actually wrote the rows (not just returned
    them in the result dict)."""
    row = bridge._bootstrap.database_connection.execute(
        "SELECT COUNT(*) AS c FROM content_pieces WHERE campaign_item_id IN"
        " (SELECT id FROM campaign_items WHERE plan_id IN"
        "  (SELECT id FROM campaign_plans WHERE campaign_id = ?))",
        (campaign_id_str,),
    ).fetchone()
    return int(row["c"])


def test_generate_content_happy_path_creates_all_pieces(tmp_path) -> None:
    """2+ items, all AI calls succeed -> ``ok=True``, all pieces in DB."""
    bridge = _isolated_bridge(tmp_path)
    _configure_provider(bridge._provider_config_repo, "OPENAI")
    campaign_id, _plan_id = _seed_brand_and_campaign(bridge, num_items=3)

    with patch.object(
        bridge._bootstrap.secret_store, "get_secret", return_value="sk-test"
    ), patch(
        "ai_campaign_studio.presentation_webview.bridge.build_text_generation_adapter",
        _fake_ai_factory(_valid_social_payload()),
    ):
        result = bridge.generate_campaign_content({"campaign_id": campaign_id})

    assert result["ok"] is True
    assert result["campaign_id"] == campaign_id
    assert result["generated_count"] == 3
    assert result["failed_count"] == 0
    assert len(result["content_piece_ids"]) == 3
    assert result["error_code"] is None
    assert result["error_message"] is None
    # The strongest evidence: actual rows in the DB.
    assert _count_content_pieces(bridge, campaign_id) == 3


def test_generate_content_partial_failure_ok_true(tmp_path) -> None:
    """1 of 2 AI calls raise -> ``ok=True``, ``generated_count=1``,
    ``failed_count=1``. The user can retry for the failed item."""
    bridge = _isolated_bridge(tmp_path)
    _configure_provider(bridge._provider_config_repo, "OPENAI")
    campaign_id, _plan_id = _seed_brand_and_campaign(bridge, num_items=2)

    class _FailOnSecondItem:
        """Adapter that raises on the 2nd call, succeeds on the 1st."""

        def __init__(self) -> None:
            self.calls = 0

        def generate(self, request: AIRequest) -> AIResponse:
            del request
            self.calls += 1
            if self.calls == 2:
                raise RuntimeError("simulated AI timeout")
            return AIResponse(
                provider="fake", model="fake", latency_ms=1,
                structured_payload=_valid_social_payload(),
            )

    fail_adapter = _FailOnSecondItem()

    def _factory(
        provider_code: str, api_key: str, *, base_url: str | None = None
    ):
        del provider_code, api_key, base_url
        return fail_adapter

    with patch.object(
        bridge._bootstrap.secret_store, "get_secret", return_value="sk-test"
    ), patch(
        "ai_campaign_studio.presentation_webview.bridge.build_text_generation_adapter",
        _factory,
    ):
        result = bridge.generate_campaign_content({"campaign_id": campaign_id})

    assert result["ok"] is True
    assert result["generated_count"] == 1
    assert result["failed_count"] == 1
    assert len(result["content_piece_ids"]) == 1
    # Real evidence: only the FIRST item got persisted.
    assert _count_content_pieces(bridge, campaign_id) == 1


def test_generate_content_idempotent_re_click_does_not_duplicate(tmp_path) -> None:
    """Second click on an already-generated campaign does NOT
    duplicate ContentPiece rows. ``ok=True`` with both counts at 0
    and a friendly 'already done' message is the contract.
    """
    bridge = _isolated_bridge(tmp_path)
    _configure_provider(bridge._provider_config_repo, "OPENAI")
    campaign_id, _plan_id = _seed_brand_and_campaign(bridge, num_items=3)

    with patch.object(
        bridge._bootstrap.secret_store, "get_secret", return_value="sk-test"
    ), patch(
        "ai_campaign_studio.presentation_webview.bridge.build_text_generation_adapter",
        _fake_ai_factory(_valid_social_payload()),
    ):
        first = bridge.generate_campaign_content({"campaign_id": campaign_id})
        assert first["generated_count"] == 3
        second = bridge.generate_campaign_content({"campaign_id": campaign_id})
    # Second click: nothing to do.
    assert second["ok"] is True
    assert second["generated_count"] == 0
    assert second["failed_count"] == 0
    assert second["content_piece_ids"] == ()
    # Real evidence: still exactly 3 rows, no duplicates.
    assert _count_content_pieces(bridge, campaign_id) == 3


def test_generate_content_already_approved_plan_works(tmp_path) -> None:
    """A plan the user already approved (or the bridge pre-approved
    during a previous click) does not blow up. The bridge
    re-approves; that's idempotent at the domain level."""
    bridge = _isolated_bridge(tmp_path)
    _configure_provider(bridge._provider_config_repo, "OPENAI")
    campaign_id, plan_id = _seed_brand_and_campaign(bridge, num_items=2)
    _approve_plan(bridge, plan_id)

    with patch.object(
        bridge._bootstrap.secret_store, "get_secret", return_value="sk-test"
    ), patch(
        "ai_campaign_studio.presentation_webview.bridge.build_text_generation_adapter",
        _fake_ai_factory(_valid_social_payload()),
    ):
        result = bridge.generate_campaign_content({"campaign_id": campaign_id})

    assert result["ok"] is True
    assert result["generated_count"] == 2
    assert _count_content_pieces(bridge, campaign_id) == 2


def test_generate_content_campaign_not_found_returns_validation_error(
    tmp_path,
) -> None:
    bridge = _isolated_bridge(tmp_path)
    _configure_provider(bridge._provider_config_repo, "OPENAI")
    result = bridge.generate_campaign_content({"campaign_id": "non-existent"})
    assert result["ok"] is False
    assert result["error_code"] == "VALIDATION_ERROR"
    assert "ne postoji" in result["error_message"].lower()


def test_generate_content_no_provider_returns_no_provider_error(
    tmp_path,
) -> None:
    """Same error code as ``create_campaign_and_generate_plan`` when
    no provider is configured: NO_PROVIDER_CONFIGURED. This is the
    failure mode a fresh install hits on the very first click.

    The campaign+plan MUST exist so the bridge reaches the provider
    resolution step (a non-existent campaign returns VALIDATION_ERROR
    first; see the dedicated test above). The seed helper gives us
    both.
    """
    bridge = _isolated_bridge(tmp_path)
    campaign_id, _plan_id = _seed_brand_and_campaign(bridge, num_items=2)
    result = bridge.generate_campaign_content({"campaign_id": campaign_id})
    assert result["ok"] is False
    assert result["error_code"] == "NO_PROVIDER_CONFIGURED"


def test_generate_content_non_dict_payload_returns_validation_error(
    tmp_path,
) -> None:
    bridge = _isolated_bridge(tmp_path)
    result = bridge.generate_campaign_content("not a dict")  # type: ignore[arg-type]
    assert result["ok"] is False
    assert result["error_code"] == "VALIDATION_ERROR"


def test_generate_content_missing_campaign_id_returns_validation_error(
    tmp_path,
) -> None:
    bridge = _isolated_bridge(tmp_path)
    result = bridge.generate_campaign_content({})
    assert result["ok"] is False
    assert result["error_code"] == "VALIDATION_ERROR"
    assert "campaign_id" in result["error_message"]


def test_generate_content_carries_no_api_key_in_result(tmp_path) -> None:
    """PYWEBVIEW_SECURITY §3: the return dict never contains the
    API key. Even on a 100-piece success run with a sentinel key,
    the result blob is key-free."""
    bridge = _isolated_bridge(tmp_path)
    _configure_provider(bridge._provider_config_repo, "OPENAI")
    campaign_id, _plan_id = _seed_brand_and_campaign(bridge, num_items=2)
    sentinel_key = "sk-SENTINEL-EXAMPLE-redacted-9999"

    with patch.object(
        bridge._bootstrap.secret_store, "get_secret", return_value=sentinel_key
    ), patch(
        "ai_campaign_studio.presentation_webview.bridge.build_text_generation_adapter",
        _fake_ai_factory(_valid_social_payload()),
    ):
        result = bridge.generate_campaign_content({"campaign_id": campaign_id})

    blob = json.dumps(result)
    assert sentinel_key not in blob
    # No exception class leakage either.
    assert "Traceback" not in blob
    assert "RuntimeError" not in blob


def test_generate_content_round_robin_assignment_matches_run_system_b(
    tmp_path,
) -> None:
    """Pin the round-robin assignment to the same shape as
    ``application/evaluation/run_system_b.py:86``. With 1 target
    and 3 items, every item should use target[0] (= modulo 0 for
    all indices 0, 1, 2). The contract is implicit but the test
    documents it for future maintainers."""
    bridge = _isolated_bridge(tmp_path)
    _configure_provider(bridge._provider_config_repo, "OPENAI")
    campaign_id, _plan_id = _seed_brand_and_campaign(bridge, num_items=3, num_targets=1)

    captured_targets: list[tuple[str, str, str]] = []   # (channel, platform, format)

    class _RecordingAdapter:
        def generate(self, request: AIRequest) -> AIResponse:
            del request
            # The generator passes the target into the AI request via
            # the system prompt / facts, but the public surface is
            # the request object. We don't have a clean hook to read
            # the target off the request, so we assert a different
            # observable: the underlying ``ContentPiece.target``
            # field after the call.
            return AIResponse(
                provider="fake", model="fake", latency_ms=1,
                structured_payload=_valid_social_payload(),
            )

    def _factory(
        provider_code: str, api_key: str, *, base_url: str | None = None
    ):
        del provider_code, api_key, base_url
        return _RecordingAdapter()

    with patch.object(
        bridge._bootstrap.secret_store, "get_secret", return_value="sk-test"
    ), patch(
        "ai_campaign_studio.presentation_webview.bridge.build_text_generation_adapter",
        _factory,
    ):
        bridge.generate_campaign_content({"campaign_id": campaign_id})

    # Pull back the persisted ContentPiece rows and check the
    # ``target`` column on each one. All 3 should be the same (the
    # only target in the brief).
    rows = bridge._bootstrap.database_connection.execute(
        "SELECT target_channel, target_platform_code, target_format_code"
        " FROM content_pieces ORDER BY created_at"
    ).fetchall()
    del captured_targets  # (suppress lint: used only for the comment)
    assert len(rows) == 3
    expected = ("SOCIAL", "INSTAGRAM", "FEED_POST")
    for row in rows:
        assert (row[0], row[1], row[2]) == expected


def test_generate_content_unexpected_exception_in_adapter_factory(
    tmp_path,
) -> None:
    """An unexpected exception during adapter construction (NOT
    one of the known domain errors) maps to a safe result —
    ``ok=False`` with a stable error code and NO raw exception text
    in the user-facing message. The exact code is
    implementation-defined (today: ``KEY_MISSING``, mirroring
    ``create_campaign_and_generate_plan``); what matters is that
    the caller never sees the SDK exception text.
    """
    bridge = _isolated_bridge(tmp_path)
    _configure_provider(bridge._provider_config_repo, "OPENAI")
    campaign_id, _plan_id = _seed_brand_and_campaign(bridge, num_items=2)

    with patch.object(
        bridge._bootstrap.secret_store, "get_secret", return_value="sk-test"
    ), patch(
        "ai_campaign_studio.presentation_webview.bridge.build_text_generation_adapter",
        side_effect=RuntimeError("factory exploded unexpectedly"),
    ):
        result = bridge.generate_campaign_content({"campaign_id": campaign_id})

    assert result["ok"] is False
    # The exact code is implementation-defined; what matters is
    # that it is NOT VALIDATION_ERROR (the input was valid) and
    # that the raw SDK text is scrubbed.
    assert result["error_code"] != "VALIDATION_ERROR"
    assert "factory exploded unexpectedly" not in result["error_message"]
    assert "RuntimeError" not in result["error_message"]
