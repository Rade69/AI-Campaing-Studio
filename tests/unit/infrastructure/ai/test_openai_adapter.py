"""Unit tests for OpenAIAdapter (A8, dio 2) with an injected fake client.

No real network call is made: the fake client replaces the OpenAI SDK's
transport entirely, so the suite passes without ``OPENAI_API_KEY``.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import openai
import pytest

from ai_campaign_studio.ai_registry.model_profiles import ModelSource
from ai_campaign_studio.domain.common.errors import ErrorCode, InfrastructureError
from ai_campaign_studio.infrastructure.ai.openai_adapter import OpenAIAdapter
from ai_campaign_studio.ports.ai import AIRequest


def _request() -> AIRequest:
    return AIRequest(
        purpose="campaign_plan",
        prompt_name="campaign_plan",
        prompt_version="1",
        system_text="system",
        user_text="user",
        json_schema={
            "type": "object",
            "properties": {"result": {"type": "string"}},
        },
    )


def _completion(content: str) -> SimpleNamespace:
    # Real OpenAI shape: finish_reason lives on the Choice, not on the Message.
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message, finish_reason="stop")
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=20)
    return SimpleNamespace(id="cmpl-1", choices=[choice], usage=usage)


def _rate_limit_error() -> openai.RateLimitError:
    request = httpx.Request("POST", "http://test")
    response = httpx.Response(429, request=request)
    return openai.RateLimitError("rate limited", response=response, body=None)


def _connection_error() -> openai.APIConnectionError:
    request = httpx.Request("POST", "http://test")
    return openai.APIConnectionError(request=request)


def _auth_error() -> openai.AuthenticationError:
    request = httpx.Request("POST", "http://test")
    response = httpx.Response(401, request=request)
    return openai.AuthenticationError("invalid key", response=response, body=None)


def _adapter(client: Mock) -> OpenAIAdapter:
    return OpenAIAdapter(api_key="sk-EXAMPLE-test", model="gpt-4o", client=client)


def test_generate_returns_structured_payload() -> None:
    client = Mock()
    client.chat.completions.create.return_value = _completion('{"result": "ok"}')
    adapter = _adapter(client)

    response = adapter.generate(_request())

    assert response.structured_payload == {"result": "ok"}
    assert response.raw_text == '{"result": "ok"}'
    assert response.input_tokens == 10
    assert response.output_tokens == 20
    assert response.finish_reason == "stop"
    assert response.telemetry is not None
    assert response.telemetry.retry_count == 0


def test_generate_passes_json_schema_as_response_format() -> None:
    client = Mock()
    client.chat.completions.create.return_value = _completion('{"result": "ok"}')
    adapter = _adapter(client)
    request = _request()

    adapter.generate(request)

    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["response_format"]["type"] == "json_schema"
    assert kwargs["response_format"]["json_schema"]["schema"] == request.json_schema


def test_generate_maps_authentication_error() -> None:
    client = Mock()
    client.chat.completions.create.side_effect = _auth_error()
    adapter = _adapter(client)

    with pytest.raises(InfrastructureError) as exc_info:
        adapter.generate(_request())

    assert exc_info.value.error_code is ErrorCode.INVALID_API_KEY


def test_generate_maps_malformed_json() -> None:
    client = Mock()
    client.chat.completions.create.return_value = _completion("not-json")
    adapter = _adapter(client)

    with pytest.raises(InfrastructureError) as exc_info:
        adapter.generate(_request())

    assert exc_info.value.error_code is ErrorCode.PROVIDER_ERROR


def test_generate_retries_transient_error_then_succeeds() -> None:
    client = Mock()
    client.chat.completions.create.side_effect = [
        _connection_error(),
        _completion('{"result": "ok"}'),
    ]
    adapter = _adapter(client)

    response = adapter.generate(_request())

    assert client.chat.completions.create.call_count == 2
    assert response.structured_payload == {"result": "ok"}
    assert response.telemetry is not None
    assert response.telemetry.retry_count == 1


def test_generate_retry_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    client = Mock()
    client.chat.completions.create.side_effect = [
        _connection_error(),
        _completion('{"result": "ok"}'),
    ]
    adapter = _adapter(client)

    with caplog.at_level("WARNING"):
        adapter.generate(_request())

    assert any("retry" in record.message.lower() for record in caplog.records)


def test_generate_stops_after_bounded_retries() -> None:
    client = Mock()
    client.chat.completions.create.side_effect = _rate_limit_error()
    adapter = _adapter(client)

    with pytest.raises(InfrastructureError) as exc_info:
        adapter.generate(_request())

    assert exc_info.value.error_code is ErrorCode.RATE_LIMIT
    assert client.chat.completions.create.call_count == OpenAIAdapter._MAX_ATTEMPTS


def test_test_connection_returns_true() -> None:
    client = Mock()
    client.models.list.return_value = SimpleNamespace(data=[])
    adapter = _adapter(client)

    assert adapter.test_connection() is True


def test_test_connection_returns_false_for_bad_key() -> None:
    client = Mock()
    client.models.list.side_effect = _auth_error()
    adapter = _adapter(client)

    assert adapter.test_connection() is False


def test_test_connection_raises_for_unexpected_error() -> None:
    client = Mock()
    client.models.list.side_effect = _rate_limit_error()
    adapter = _adapter(client)

    with pytest.raises(InfrastructureError) as exc_info:
        adapter.test_connection()

    assert exc_info.value.error_code is ErrorCode.RATE_LIMIT


def test_discover_models_maps_to_model_profiles() -> None:
    client = Mock()
    client.models.list.return_value = SimpleNamespace(
        data=[SimpleNamespace(id="gpt-4o"), SimpleNamespace(id="gpt-4o-mini")]
    )
    adapter = _adapter(client)

    models = adapter.discover_models()

    assert [m.model_id for m in models] == ["gpt-4o", "gpt-4o-mini"]
    assert all(m.provider_code == "OPENAI" for m in models)
    assert all(m.source is ModelSource.DISCOVERED for m in models)
