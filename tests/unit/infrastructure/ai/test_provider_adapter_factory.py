"""Unit tests for the provider adapter factory (ACS-GUI-005, bridge wiring).

These tests do not make any real network call. They verify the dispatch
logic (provider_code → concrete adapter class) and the model-id
resolution. Adapters themselves are not exercised here (those have their
own unit tests in ``test_openai_adapter.py`` / ``test_anthropic_adapter.py``
/ ``test_google_adapter.py``).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from ai_campaign_studio.domain.common.errors import ConfigurationError, ErrorCode
from ai_campaign_studio.infrastructure.ai import provider_adapter_factory as factory

# --- pick_configured_provider ---

def test_pick_configured_provider_returns_none_for_empty_list() -> None:
    assert factory.pick_configured_provider([]) is None


def test_pick_configured_provider_respects_priority_order() -> None:
    # Priority order is OPENAI > ANTHROPIC > GOOGLE. When all three are
    # configured, OPENAI wins regardless of the input list's order.
    assert (
        factory.pick_configured_provider(["GOOGLE", "ANTHROPIC", "OPENAI"])
        == "OPENAI"
    )
    # ANTHROPIC beats GOOGLE when OPENAI is absent.
    assert (
        factory.pick_configured_provider(["GOOGLE", "ANTHROPIC"])
        == "ANTHROPIC"
    )


def test_pick_configured_provider_returns_first_when_no_priority_match() -> None:
    # A future provider not in our priority list is still picked (just
    # blindly takes the first entry — do not fail just because the
    # priority list is incomplete).
    assert (
        factory.pick_configured_provider(["HYPOTHETICAL_FUTURE"])
        == "HYPOTHETICAL_FUTURE"
    )


def test_pick_configured_provider_is_case_insensitive() -> None:
    assert (
        factory.pick_configured_provider(["openai", "anthropic"])
        == "OPENAI"
    )


# --- resolve_model_id ---

def test_resolve_model_id_returns_hardcoded_string_for_openai() -> None:
    assert factory.resolve_model_id("OPENAI") == "gpt-4o-mini"


def test_resolve_model_id_returns_hardcoded_string_for_anthropic() -> None:
    # The Anthropic entry is documented in the factory docstring as
    # "verified against the installed SDK Literal type" — the contract
    # allows this; only the contract forbids guessing.
    assert factory.resolve_model_id("ANTHROPIC") == "claude-3-haiku-20240307"


def test_resolve_model_id_returns_hardcoded_string_for_google() -> None:
    # Live-verified in ACS-F1-019 (see
    # `agent_reports/2026-09-04-ACS-F1-019-review-claude.md:16`).
    # NOT `gemini-1.5-flash` — that string returns 404 NOT_FOUND on the
    # real Gemini API (see ACS-GUI-005 BF-1 fix runda).
    assert factory.resolve_model_id("GOOGLE") == "gemini-2.5-flash"


def test_resolve_model_id_is_case_insensitive() -> None:
    assert factory.resolve_model_id("openai") == "gpt-4o-mini"


def test_resolve_model_id_raises_configuration_error_for_unknown_provider() -> None:
    with pytest.raises(ConfigurationError) as exc_info:
        factory.resolve_model_id("DEEPSEEK")
    assert exc_info.value.error_code is ErrorCode.CONFIGURATION_ERROR
    # Error message must NOT leak the internal model-id table.
    assert "gpt-4o" not in str(exc_info.value)
    assert "claude" not in str(exc_info.value)


# --- build_text_generation_adapter ---

# The factory uses *lazy* imports of the concrete adapter classes
# (so a test env that only has the OpenAI SDK installed can still
# import the factory module). To verify dispatch, we patch the
# adapter on its real module path — not on the factory module.


def test_build_returns_openai_adapter_with_correct_model() -> None:
    with patch(
        "ai_campaign_studio.infrastructure.ai.openai_adapter.OpenAIAdapter"
    ) as cls:
        factory.build_text_generation_adapter("OPENAI", api_key="sk-test")
    cls.assert_called_once_with(
        api_key="sk-test", model="gpt-4o-mini", base_url=None
    )


def test_build_returns_anthropic_adapter_with_correct_model() -> None:
    with patch(
        "ai_campaign_studio.infrastructure.ai.anthropic_adapter.AnthropicAdapter"
    ) as cls:
        factory.build_text_generation_adapter("ANTHROPIC", api_key="sk-ant-EXAMPLE")
    cls.assert_called_once_with(
        api_key="sk-ant-EXAMPLE", model="claude-3-haiku-20240307", base_url=None
    )


def test_build_returns_google_adapter_with_correct_model() -> None:
    with patch(
        "ai_campaign_studio.infrastructure.ai.google_adapter.GoogleAdapter"
    ) as cls:
        factory.build_text_generation_adapter("GOOGLE", api_key="goog-EXAMPLE")
    # GoogleAdapter does NOT accept base_url (Gemini SDK uses Google's
    # own endpoint; the factory explicitly drops it). The call signature
    # is therefore ``(api_key, model)`` only. The model string is the
    # one live-verified in ACS-F1-019 (NOT ``gemini-1.5-flash``).
    cls.assert_called_once_with(
        api_key="goog-EXAMPLE", model="gemini-2.5-flash"
    )


def test_build_passes_base_url_when_provided() -> None:
    with patch(
        "ai_campaign_studio.infrastructure.ai.openai_adapter.OpenAIAdapter"
    ) as cls:
        factory.build_text_generation_adapter(
            "OPENAI", api_key="sk-test", base_url="https://proxy.example/v1"
        )
    cls.assert_called_once_with(
        api_key="sk-test", model="gpt-4o-mini",
        base_url="https://proxy.example/v1",
    )


def test_build_raises_configuration_error_for_unsupported_provider() -> None:
    # DEEPSEEK / OPENROUTER would live here once ACS-F1-017 lands. Until
    # then, the factory must surface a clear error so the bridge can
    # map it to a user-facing message rather than silently picking the
    # wrong provider.
    with pytest.raises(ConfigurationError) as exc_info:
        factory.build_text_generation_adapter("DEEPSEEK", api_key="sk-test")
    assert exc_info.value.error_code is ErrorCode.CONFIGURATION_ERROR


def test_build_does_not_inspect_api_key_value() -> None:
    # The factory is dumb about secrets (per contract: receives a ready
    # string, never reads SecretStore). It must NOT reject empty/None
    # values — that is the bridge's / SDK's responsibility, and a
    # bad/missing key should surface as a real ``AuthenticationError``
    # from the live provider, not a silent config error here.
    with patch(
        "ai_campaign_studio.infrastructure.ai.openai_adapter.OpenAIAdapter"
    ) as cls:
        factory.build_text_generation_adapter("OPENAI", api_key="")
    cls.assert_called_once_with(
        api_key="", model="gpt-4o-mini", base_url=None
    )
