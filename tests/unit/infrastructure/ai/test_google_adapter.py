"""Unit tests for GoogleAdapter (A8, dio 5) with an injected fake client.

No real network call is made: the fake client replaces the Google Gen AI SDK's
transport entirely, so the suite passes without a real API key. Fake response
objects mirror the real SDK shape (``finish_reason`` on the candidate, ``text``
on ``candidate.content.parts[0]``).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from google.genai import errors

from ai_campaign_studio.ai_registry.model_profiles import ModelSource
from ai_campaign_studio.domain.common.errors import ErrorCode, InfrastructureError
from ai_campaign_studio.infrastructure.ai.google_adapter import GoogleAdapter
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


def _response(text: str, finish_reason: str = "STOP") -> SimpleNamespace:
    # Real Google SDK shape: text on part, finish_reason on candidate.
    part = SimpleNamespace(text=text)
    content = SimpleNamespace(parts=[part], role="model")
    candidate = SimpleNamespace(content=content, finish_reason=finish_reason)
    usage = SimpleNamespace(prompt_token_count=10, candidates_token_count=20)
    return SimpleNamespace(
        candidates=[candidate], usage_metadata=usage, response_id="resp-1"
    )


def _client_error(code: int) -> errors.ClientError:
    return errors.ClientError(code, {"error": {"message": "test"}})


def _server_error() -> errors.ServerError:
    return errors.ServerError(500, {})


def _adapter(client: Mock) -> GoogleAdapter:
    return GoogleAdapter(
        api_key="AIza-EXAMPLE-key", model="gemini-2.5-flash", client=client
    )


def test_generate_returns_structured_payload() -> None:
    client = Mock()
    client.models.generate_content.return_value = _response('{"result": "ok"}')
    adapter = _adapter(client)

    response = adapter.generate(_request())

    assert response.structured_payload == {"result": "ok"}
    assert response.raw_text == '{"result": "ok"}'
    assert response.input_tokens == 10
    assert response.output_tokens == 20
    assert response.finish_reason == "STOP"
    assert response.telemetry is not None
    assert response.telemetry.retry_count == 0


def test_generate_passes_json_schema() -> None:
    client = Mock()
    client.models.generate_content.return_value = _response('{"result": "ok"}')
    adapter = _adapter(client)
    request = _request()

    adapter.generate(request)

    config = client.models.generate_content.call_args.kwargs["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema == request.json_schema


def test_generate_maps_invalid_key_error() -> None:
    client = Mock()
    client.models.generate_content.side_effect = _client_error(401)
    adapter = _adapter(client)

    with pytest.raises(InfrastructureError) as exc_info:
        adapter.generate(_request())

    assert exc_info.value.error_code is ErrorCode.INVALID_API_KEY


def test_generate_maps_malformed_json() -> None:
    client = Mock()
    client.models.generate_content.return_value = _response("not-json")
    adapter = _adapter(client)

    with pytest.raises(InfrastructureError) as exc_info:
        adapter.generate(_request())

    assert exc_info.value.error_code is ErrorCode.PROVIDER_ERROR


def test_generate_retries_transient_error_then_succeeds() -> None:
    client = Mock()
    client.models.generate_content.side_effect = [
        _server_error(),
        _response('{"result": "ok"}'),
    ]
    adapter = _adapter(client)

    response = adapter.generate(_request())

    assert client.models.generate_content.call_count == 2
    assert response.structured_payload == {"result": "ok"}
    assert response.telemetry is not None
    assert response.telemetry.retry_count == 1


def test_generate_retry_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    client = Mock()
    client.models.generate_content.side_effect = [
        _server_error(),
        _response('{"result": "ok"}'),
    ]
    adapter = _adapter(client)

    with caplog.at_level("WARNING"):
        adapter.generate(_request())

    assert any("retry" in record.message.lower() for record in caplog.records)


def test_generate_stops_after_bounded_retries() -> None:
    client = Mock()
    client.models.generate_content.side_effect = _client_error(429)
    adapter = _adapter(client)

    with pytest.raises(InfrastructureError) as exc_info:
        adapter.generate(_request())

    assert exc_info.value.error_code is ErrorCode.RATE_LIMIT
    assert client.models.generate_content.call_count == GoogleAdapter._MAX_ATTEMPTS


def test_test_connection_returns_true() -> None:
    client = Mock()
    client.models.list.return_value = []
    adapter = _adapter(client)

    assert adapter.test_connection() is True


def test_test_connection_returns_false_for_bad_key() -> None:
    client = Mock()
    client.models.list.side_effect = _client_error(401)
    adapter = _adapter(client)

    assert adapter.test_connection() is False


def test_test_connection_raises_for_unexpected_error() -> None:
    client = Mock()
    client.models.list.side_effect = _client_error(429)
    adapter = _adapter(client)

    with pytest.raises(InfrastructureError) as exc_info:
        adapter.test_connection()

    assert exc_info.value.error_code is ErrorCode.RATE_LIMIT


def test_discover_models_maps_to_model_profiles() -> None:
    client = Mock()
    client.models.list.return_value = [
        SimpleNamespace(
            name="models/gemini-2.5-flash", display_name="Gemini 2.5 Flash"
        ),
        SimpleNamespace(
            name="models/gemini-2.5-pro", display_name="Gemini 2.5 Pro"
        ),
    ]
    adapter = _adapter(client)

    models = adapter.discover_models()

    assert [m.model_id for m in models] == [
        "models/gemini-2.5-flash",
        "models/gemini-2.5-pro",
    ]
    assert all(m.provider_code == "GOOGLE" for m in models)
    assert all(m.source is ModelSource.DISCOVERED for m in models)
