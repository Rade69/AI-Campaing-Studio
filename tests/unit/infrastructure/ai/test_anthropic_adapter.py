"""Unit tests for AnthropicAdapter (A8, dio 4) with an injected fake client.

No real network call is made: the fake client replaces the anthropic SDK's
transport entirely, so the suite passes without ``ANTHROPIC_API_KEY``.

Fake-response fixtures are constructed from the real ``anthropic`` SDK
types (``Message``, ``TextBlock``, ``Usage``, ``ModelInfo``) so they
match the shape the adapter reads from in production. Per the BF-1
lesson from ACS-F1-016: a ``SimpleNamespace`` that fakes the right
attribute names will still let ``getattr`` succeed even if the
production code is reading from the wrong attribute on the wrong
object. The contract mandates "real SDK shape, not simplified
namespace", so these tests do exactly that.
"""

from __future__ import annotations

import datetime
from typing import Any
from unittest.mock import Mock

import anthropic
import httpx
import pytest

from ai_campaign_studio.ai_registry.model_profiles import ModelSource
from ai_campaign_studio.domain.common.errors import ErrorCode, InfrastructureError
from ai_campaign_studio.infrastructure.ai.anthropic_adapter import AnthropicAdapter
from ai_campaign_studio.ports.ai import AIRequest


def _request() -> AIRequest:
    return AIRequest(
        purpose="campaign_plan",
        prompt_name="campaign_plan",
        prompt_version="1",
        system_text="You are a campaign planner.",
        user_text="plan a campaign",
        json_schema={
            "type": "object",
            "properties": {"result": {"type": "string"}},
        },
    )


def _message(
    content_text: str, stop_reason: str = "end_turn"
) -> anthropic.types.Message:
    """Build a real anthropic.types.Message object — the same type the
    SDK returns from a live ``messages.create`` call. Constructed with
    the actual SDK pydantic model so attribute access goes through the
    real field definitions (no risk of masking a shape mismatch like
    BF-1 did for ``finish_reason`` in ACS-F1-016).
    """
    return anthropic.types.Message(
        id="msg_test_01",
        type="message",
        role="assistant",
        model="claude-sonnet-4-5",
        content=[
            anthropic.types.TextBlock(type="text", text=content_text),
        ],
        stop_reason=stop_reason,
        stop_sequence=None,
        usage=anthropic.types.Usage(input_tokens=12, output_tokens=34),
        container=None,
    )


def _model_info(model_id: str, display_name: str = "") -> anthropic.types.ModelInfo:
    return anthropic.types.ModelInfo(
        id=model_id,
        type="model",
        display_name=display_name or model_id,
        created_at=datetime.datetime(2025, 1, 1, tzinfo=datetime.UTC),
    )


def _request_obj() -> httpx.Request:
    return httpx.Request("POST", "https://api.anthropic.com/v1/messages")


def _response_obj(status_code: int) -> httpx.Response:
    return httpx.Response(status_code, request=_request_obj())


def _rate_limit_error() -> anthropic.RateLimitError:
    return anthropic.RateLimitError(
        "rate limited", response=_response_obj(429), body=None
    )


def _connection_error() -> anthropic.APIConnectionError:
    return anthropic.APIConnectionError(request=_request_obj())


def _timeout_error() -> anthropic.APITimeoutError:
    return anthropic.APITimeoutError(request=_request_obj())


def _auth_error() -> anthropic.AuthenticationError:
    return anthropic.AuthenticationError(
        "invalid key", response=_response_obj(401), body=None
    )


def _bad_request_error() -> anthropic.BadRequestError:
    return anthropic.BadRequestError(
        "bad params", response=_response_obj(400), body=None
    )


def _adapter(client: Any) -> AnthropicAdapter:
    return AnthropicAdapter(
        api_key="sk-ant-EXAMPLE-test", model="claude-sonnet-4-5", client=client
    )


# --- generate() ---

def test_generate_returns_structured_payload_from_real_message() -> None:
    client = Mock()
    client.messages.create.return_value = _message('{"result": "ok"}')
    adapter = _adapter(client)

    response = adapter.generate(_request())

    assert response.structured_payload == {"result": "ok"}
    assert response.raw_text == '{"result": "ok"}'
    assert response.provider == "anthropic"
    assert response.model == "claude-sonnet-4-5"
    # Real Usage object — adapter must read .input_tokens / .output_tokens
    # off the correct attribute (BF-1 was reading finish_reason off the
    # wrong object; this test guards the equivalent token-mapping path).
    assert response.input_tokens == 12
    assert response.output_tokens == 34
    assert response.finish_reason == "end_turn"
    assert response.request_id == "msg_test_01"
    assert response.telemetry is not None
    assert response.telemetry.retry_count == 0


def test_generate_passes_system_as_separate_top_level_param() -> None:
    """Anthropic Messages API: ``system`` is top-level, NOT inside messages."""
    client = Mock()
    client.messages.create.return_value = _message('{"result": "ok"}')
    adapter = _adapter(client)
    request = _request()

    adapter.generate(request)

    kwargs = client.messages.create.call_args.kwargs
    # system is a top-level kwarg (not inside a messages entry)
    assert "system" in kwargs
    # BF-1 fix: system is passed through UNMODIFIED — no JSON-schema
    # directive is appended any more (that lived in the removed
    # _compose_system_text helper). Schema is now enforced server-side
    # via output_config (see test_generate_passes_json_schema_via_output_config).
    assert kwargs["system"] == request.system_text
    # messages contains ONLY the user turn (no system message)
    msgs = kwargs["messages"]
    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == request.user_text


def test_generate_passes_json_schema_via_output_config() -> None:
    """BF-1 fix: native server-side JSON-schema enforcement.

    The adapter must call ``messages.create`` with ``output_config`` set
    to a json_schema format referencing the caller's ``AIRequest.json_schema``
    — functionally equivalent to OpenAI's ``response_format=json_schema``.
    This is the primary guarantee that the response payload validates
    against the schema, replacing the previous prompt-based directive.
    """
    client = Mock()
    client.messages.create.return_value = _message('{"result": "ok"}')
    adapter = _adapter(client)
    request = _request()

    adapter.generate(request)

    kwargs = client.messages.create.call_args.kwargs
    assert "output_config" in kwargs, "output_config must be set on messages.create"
    # output_config shape: {"format": {"type": "json_schema", "schema": <dict>}}
    oc = kwargs["output_config"]
    assert oc["format"]["type"] == "json_schema"
    assert oc["format"]["schema"] == request.json_schema


def test_generate_does_not_inject_schema_directive_into_system() -> None:
    """BF-1 fix evidence: the previous prompt-injection path is GONE.

    Verifies the contract that ``request.system_text`` reaches the API
    unmodified — no JSON-schema directive is appended by the adapter.
    If a future refactor reintroduces the old ``_compose_system_text``
    helper, this test fails loudly.
    """
    client = Mock()
    client.messages.create.return_value = _message('{"result": "ok"}')
    adapter = _adapter(client)
    request = _request()

    adapter.generate(request)

    system = client.messages.create.call_args.kwargs["system"]
    assert "JSON Schema" not in system
    assert "json_schema" not in system
    assert "Schema:" not in system
    # and the caller's text is exactly the system text
    assert system == request.system_text


def test_generate_emits_max_tokens_when_caller_omits_it() -> None:
    """Anthropic API requires max_tokens; adapter falls back when not set."""
    client = Mock()
    client.messages.create.return_value = _message('{"result": "ok"}')
    adapter = _adapter(client)
    request = AIRequest(
        purpose="x", prompt_name="x", prompt_version="1",
        system_text="s", user_text="u", json_schema={"type": "object"},
    )

    adapter.generate(request)

    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["max_tokens"] == 4096  # the documented fallback


def test_generate_honours_caller_max_output_tokens() -> None:
    client = Mock()
    client.messages.create.return_value = _message('{"result": "ok"}')
    adapter = _adapter(client)
    request = AIRequest(
        purpose="x", prompt_name="x", prompt_version="1",
        system_text="s", user_text="u", json_schema={"type": "object"},
        max_output_tokens=512,
    )

    adapter.generate(request)

    assert client.messages.create.call_args.kwargs["max_tokens"] == 512


def test_generate_passes_temperature_when_set() -> None:
    client = Mock()
    client.messages.create.return_value = _message('{"result": "ok"}')
    adapter = _adapter(client)
    request = AIRequest(
        purpose="x", prompt_name="x", prompt_version="1",
        system_text="s", user_text="u", json_schema={"type": "object"},
        temperature=0.4,
    )

    adapter.generate(request)

    assert client.messages.create.call_args.kwargs["temperature"] == 0.4


def test_generate_omits_temperature_when_unset() -> None:
    client = Mock()
    client.messages.create.return_value = _message('{"result": "ok"}')
    adapter = _adapter(client)

    adapter.generate(_request())

    assert "temperature" not in client.messages.create.call_args.kwargs


# --- error mapping (BF-1 lesson: must read finish_reason/stop_reason from
# the correct SDK object — these tests guard the symmetric SDK-shape paths) ---

def test_generate_maps_rate_limit_error() -> None:
    client = Mock()
    client.messages.create.side_effect = _rate_limit_error()
    adapter = _adapter(client)

    with pytest.raises(InfrastructureError) as exc_info:
        adapter.generate(_request())

    assert exc_info.value.error_code is ErrorCode.RATE_LIMIT
    # human_message must NOT contain the API key (we never put the key in
    # the message anyway, but verify the message text is generic)
    assert "sk-ant" not in str(exc_info.value)


def test_generate_maps_connection_error() -> None:
    client = Mock()
    client.messages.create.side_effect = _connection_error()
    adapter = _adapter(client)

    with pytest.raises(InfrastructureError) as exc_info:
        adapter.generate(_request())

    assert exc_info.value.error_code is ErrorCode.NETWORK_ERROR


def test_generate_maps_timeout_error() -> None:
    client = Mock()
    client.messages.create.side_effect = _timeout_error()
    adapter = _adapter(client)

    with pytest.raises(InfrastructureError) as exc_info:
        adapter.generate(_request())

    assert exc_info.value.error_code is ErrorCode.NETWORK_ERROR


def test_generate_maps_authentication_error() -> None:
    client = Mock()
    client.messages.create.side_effect = _auth_error()
    adapter = _adapter(client)

    with pytest.raises(InfrastructureError) as exc_info:
        adapter.generate(_request())

    assert exc_info.value.error_code is ErrorCode.INVALID_API_KEY


def test_generate_maps_bad_request_error() -> None:
    client = Mock()
    client.messages.create.side_effect = _bad_request_error()
    adapter = _adapter(client)

    with pytest.raises(InfrastructureError) as exc_info:
        adapter.generate(_request())

    assert exc_info.value.error_code is ErrorCode.PROVIDER_ERROR


def test_generate_does_not_leak_api_key_in_any_error_message() -> None:
    """Sweep: every mapped error message must be free of the API key string."""
    client = Mock()
    adapter = _adapter(client)
    # Hard-code the same sentinel key the adapter was constructed with so
    # we can detect any leak by string match.
    secret = "sk-ant-EXAMPLE-test"
    side_effects = [
        _rate_limit_error(),
        _connection_error(),
        _timeout_error(),
        _auth_error(),
        _bad_request_error(),
    ]
    for exc in side_effects:
        client.messages.create.side_effect = exc
        with pytest.raises(InfrastructureError) as exc_info:
            adapter.generate(_request())
        assert secret not in str(exc_info.value), (
            f"API key leaked via {type(exc).__name__}: {exc_info.value!r}"
        )


# --- retry ---

def test_generate_retries_transient_error_then_succeeds() -> None:
    client = Mock()
    client.messages.create.side_effect = [
        _connection_error(),
        _message('{"result": "ok"}'),
    ]
    adapter = _adapter(client)

    response = adapter.generate(_request())

    assert client.messages.create.call_count == 2
    assert response.structured_payload == {"result": "ok"}
    assert response.telemetry is not None
    assert response.telemetry.retry_count == 1


def test_generate_retries_rate_limit_then_succeeds() -> None:
    client = Mock()
    client.messages.create.side_effect = [
        _rate_limit_error(),
        _message('{"result": "ok"}'),
    ]
    adapter = _adapter(client)

    response = adapter.generate(_request())

    assert client.messages.create.call_count == 2
    assert response.structured_payload == {"result": "ok"}


def test_generate_does_not_retry_authentication_error() -> None:
    """Auth errors are not transient — retry would just waste the key."""
    client = Mock()
    client.messages.create.side_effect = _auth_error()
    adapter = _adapter(client)

    with pytest.raises(InfrastructureError):
        adapter.generate(_request())

    assert client.messages.create.call_count == 1


def test_generate_does_not_retry_bad_request_error() -> None:
    """Malformed requests will not get better on retry."""
    client = Mock()
    client.messages.create.side_effect = _bad_request_error()
    adapter = _adapter(client)

    with pytest.raises(InfrastructureError):
        adapter.generate(_request())

    assert client.messages.create.call_count == 1


def test_generate_stops_after_bounded_retries() -> None:
    client = Mock()
    client.messages.create.side_effect = _rate_limit_error()
    adapter = _adapter(client)

    with pytest.raises(InfrastructureError) as exc_info:
        adapter.generate(_request())

    assert exc_info.value.error_code is ErrorCode.RATE_LIMIT
    assert client.messages.create.call_count == AnthropicAdapter._MAX_ATTEMPTS


def test_generate_retry_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    client = Mock()
    client.messages.create.side_effect = [
        _connection_error(),
        _message('{"result": "ok"}'),
    ]
    adapter = _adapter(client)

    with caplog.at_level("WARNING"):
        adapter.generate(_request())

    assert any("retry" in record.message.lower() for record in caplog.records)


# --- malformed JSON ---

def test_generate_maps_malformed_json_to_provider_error() -> None:
    client = Mock()
    client.messages.create.return_value = _message("not-json at all")
    adapter = _adapter(client)

    with pytest.raises(InfrastructureError) as exc_info:
        adapter.generate(_request())

    assert exc_info.value.error_code is ErrorCode.PROVIDER_ERROR


def test_generate_strips_json_code_fence_defensively() -> None:
    """Models sometimes echo ```json fences despite the in-band directive."""
    client = Mock()
    client.messages.create.return_value = _message('```json\n{"result": "ok"}\n```')
    adapter = _adapter(client)

    response = adapter.generate(_request())

    assert response.structured_payload == {"result": "ok"}


def test_generate_returns_none_payload_for_empty_text() -> None:
    """No text content (model produced only tool_use / refusal blocks).

    We construct a real Message whose content list is empty — adapter
    must not blow up and must report ``structured_payload=None`` rather
    than trying to parse empty string as JSON.
    """
    msg = anthropic.types.Message(
        id="msg_empty",
        type="message",
        role="assistant",
        model="claude-sonnet-4-5",
        content=[],
        stop_reason="end_turn",
        stop_sequence=None,
        usage=anthropic.types.Usage(input_tokens=1, output_tokens=0),
        container=None,
    )
    client = Mock()
    client.messages.create.return_value = msg
    adapter = _adapter(client)

    response = adapter.generate(_request())

    assert response.structured_payload is None
    assert response.raw_text is None
    assert response.input_tokens == 1
    assert response.output_tokens == 0


# --- test_connection ---

def test_test_connection_returns_true() -> None:
    client = Mock()
    client.models.list.return_value = iter([_model_info("claude-sonnet-4-5")])
    adapter = _adapter(client)

    assert adapter.test_connection() is True
    # Connection test must limit the page size to avoid pulling every model.
    assert client.models.list.call_args.kwargs.get("limit") == 1


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


# --- discover_models ---

def test_discover_models_maps_to_model_profiles() -> None:
    client = Mock()
    client.models.list.return_value = iter([
        _model_info("claude-sonnet-4-5", "Claude Sonnet 4.5"),
        _model_info("claude-haiku-4-5", "Claude Haiku 4.5"),
    ])
    adapter = _adapter(client)

    models = adapter.discover_models()

    assert [m.model_id for m in models] == ["claude-sonnet-4-5", "claude-haiku-4-5"]
    assert all(m.provider_code == "ANTHROPIC" for m in models)
    assert all(m.source is ModelSource.DISCOVERED for m in models)
    assert models[0].display_name == "Claude Sonnet 4.5"


def test_discover_models_uses_display_name_fallback_to_id() -> None:
    """Some SDK responses may have an empty display_name; we fall back to id."""
    client = Mock()
    client.models.list.return_value = iter([_model_info("claude-sonnet-4-5", "")])
    adapter = _adapter(client)

    models = adapter.discover_models()

    assert models[0].display_name == "claude-sonnet-4-5"


def test_discover_models_maps_provider_error() -> None:
    client = Mock()
    client.models.list.side_effect = _auth_error()
    adapter = _adapter(client)

    with pytest.raises(InfrastructureError) as exc_info:
        adapter.discover_models()

    assert exc_info.value.error_code is ErrorCode.INVALID_API_KEY
