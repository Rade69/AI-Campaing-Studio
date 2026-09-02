"""Mock AI adapter tests (A7)."""

import pytest

from ai_campaign_studio.infrastructure.ai.mock_adapter import (
    MockAdapter,
    MockMode,
    MockRateLimitError,
)
from ai_campaign_studio.ports.ai import AIRequest, TextGenerationPort


def _request() -> AIRequest:
    return AIRequest(
        purpose="test",
        prompt_name="campaign_plan",
        prompt_version="1",
        system_text="system",
        user_text="user",
        json_schema={},
    )


def test_adapter_is_a_text_generation_port() -> None:
    assert isinstance(MockAdapter(), TextGenerationPort)


def test_deterministic_mode_returns_same_response() -> None:
    adapter = MockAdapter(MockMode.DETERMINISTIC)

    first = adapter.generate(_request())
    second = adapter.generate(_request())

    assert first == second


def test_error_mode_raises() -> None:
    adapter = MockAdapter(MockMode.ERROR)

    with pytest.raises(RuntimeError):
        adapter.generate(_request())


def test_invalid_schema_mode_returns_payload() -> None:
    adapter = MockAdapter(MockMode.INVALID_SCHEMA)

    response = adapter.generate(_request())

    assert response.structured_payload == {
        "unexpected_field": "not the expected schema"
    }


def test_rate_limit_mode_raises() -> None:
    adapter = MockAdapter(MockMode.RATE_LIMIT)

    with pytest.raises(MockRateLimitError):
        adapter.generate(_request())


def test_telemetry_mode_populates_telemetry() -> None:
    adapter = MockAdapter(MockMode.TELEMETRY)

    response = adapter.generate(_request())

    assert response.telemetry is not None
    assert response.telemetry.latency_ms == 123
    assert response.telemetry.input_tokens == 100
    assert response.telemetry.output_tokens == 200


def test_call_count_increments() -> None:
    adapter = MockAdapter(MockMode.DETERMINISTIC)

    adapter.generate(_request())
    adapter.generate(_request())

    assert adapter.call_count == 2
