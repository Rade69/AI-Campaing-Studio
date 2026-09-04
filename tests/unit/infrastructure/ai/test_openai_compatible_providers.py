"""Unit tests for the OpenAI-compatible provider factories (A8, dio 3).

The factories build ``OpenAIAdapter`` instances; no real network call is made.
Two proof styles are used: a spy on the ``OpenAIAdapter`` constructor to assert
exactly which ``base_url``/``provider_code``/``provider_display`` each factory
passes, and an end-to-end call through an injected fake client to prove the
provenance values actually reach ``AIResponse``/``ModelProfile``.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest

from ai_campaign_studio.infrastructure.ai.openai_adapter import (
    JSON_OBJECT_MODE,
    JSON_SCHEMA_MODE,
)
from ai_campaign_studio.infrastructure.ai.openai_compatible_providers import (
    DEEPSEEK_BASE_URL,
    OPENROUTER_BASE_URL,
    build_deepseek_adapter,
    build_openai_compatible_adapter,
    build_openrouter_adapter,
)
from ai_campaign_studio.ports.ai import AIRequest


def _request() -> AIRequest:
    return AIRequest(
        purpose="campaign_plan",
        prompt_name="campaign_plan",
        prompt_version="1",
        system_text="system",
        user_text="user",
        json_schema={"type": "object"},
    )


def _completion(content: str) -> SimpleNamespace:
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message, finish_reason="stop")
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=20)
    return SimpleNamespace(id="cmpl-1", choices=[choice], usage=usage)


def test_base_url_constants_match_verified_documentation() -> None:
    assert DEEPSEEK_BASE_URL == "https://api.deepseek.com"
    assert OPENROUTER_BASE_URL == "https://openrouter.ai/api/v1"


@pytest.mark.parametrize(
    ("factory", "expected_base_url", "expected_provider_code"),
    [
        (build_deepseek_adapter, DEEPSEEK_BASE_URL, "DEEPSEEK"),
        (build_openrouter_adapter, OPENROUTER_BASE_URL, "OPENROUTER"),
    ],
)
def test_fixed_base_url_factories_pass_correct_constructor_args(
    monkeypatch: pytest.MonkeyPatch,
    factory: Any,
    expected_base_url: str,
    expected_provider_code: str,
) -> None:
    import ai_campaign_studio.infrastructure.ai.openai_compatible_providers as module

    captured: dict[str, Any] = {}

    def spy_openai_adapter(**kwargs: Any) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(module, "OpenAIAdapter", spy_openai_adapter)

    factory("sk-EXAMPLE-key", "some-model")

    assert captured["api_key"] == "sk-EXAMPLE-key"
    assert captured["model"] == "some-model"
    assert captured["base_url"] == expected_base_url
    assert captured["provider_code"] == expected_provider_code
    assert captured["provider_display"] == expected_provider_code.lower()
    assert captured["structured_output_mode"] == JSON_OBJECT_MODE
    assert captured["client"] is None


def test_build_openai_compatible_adapter_uses_user_supplied_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import ai_campaign_studio.infrastructure.ai.openai_compatible_providers as module

    captured: dict[str, Any] = {}

    def spy_openai_adapter(**kwargs: Any) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(module, "OpenAIAdapter", spy_openai_adapter)

    build_openai_compatible_adapter(
        "sk-EXAMPLE-key", "my-model", base_url="https://example.com/v1"
    )

    assert captured["base_url"] == "https://example.com/v1"
    assert captured["provider_code"] == "OPENAI_COMPATIBLE"
    assert captured["provider_display"] == "openai_compatible"
    assert captured["structured_output_mode"] == JSON_OBJECT_MODE


def test_build_openai_compatible_adapter_allows_explicit_json_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import ai_campaign_studio.infrastructure.ai.openai_compatible_providers as module

    captured: dict[str, Any] = {}

    def spy_openai_adapter(**kwargs: Any) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(module, "OpenAIAdapter", spy_openai_adapter)

    build_openai_compatible_adapter(
        "sk-EXAMPLE-key",
        "my-model",
        base_url="https://example.com/v1",
        structured_output_mode=JSON_SCHEMA_MODE,
    )

    assert captured["structured_output_mode"] == JSON_SCHEMA_MODE


def test_deepseek_factory_adapter_propagates_provenance_to_outputs() -> None:
    client = Mock()
    client.chat.completions.create.return_value = _completion('{"result": "ok"}')
    client.models.list.return_value = SimpleNamespace(
        data=[SimpleNamespace(id="deepseek-chat")]
    )

    adapter = build_deepseek_adapter(
        "sk-EXAMPLE-key", "deepseek-chat", client=client
    )

    response = adapter.generate(_request())
    models = adapter.discover_models()

    assert response.provider == "deepseek"
    assert all(m.provider_code == "DEEPSEEK" for m in models)

    # The factory must also switch the request to the json_object mode that
    # DeepSeek actually accepts (json_schema is rejected by the live API).
    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["response_format"] == {"type": "json_object"}
