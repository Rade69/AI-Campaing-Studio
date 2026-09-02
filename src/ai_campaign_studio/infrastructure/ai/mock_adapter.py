"""Mock AI adapter (A7).

First adapter implemented, before any live provider, so application tests
never depend on the network. No business logic, no CampaignRole logic, no
claim validation, no persistence — it only transforms an ``AIRequest`` into a
simulated ``AIResponse`` (or a simulated error).
"""

from __future__ import annotations

from enum import StrEnum

from ai_campaign_studio.ports.ai import (
    AIRequest,
    AIResponse,
    AITelemetry,
    TextGenerationPort,
)


class MockRateLimitError(RuntimeError):
    """Simulated rate-limit error."""


class MockMode(StrEnum):
    """The simulation mode of a ``MockAdapter``."""

    DETERMINISTIC = "DETERMINISTIC"
    ERROR = "ERROR"
    INVALID_SCHEMA = "INVALID_SCHEMA"
    RATE_LIMIT = "RATE_LIMIT"
    TELEMETRY = "TELEMETRY"


class MockAdapter(TextGenerationPort):
    """Deterministic, network-free ``TextGenerationPort`` implementation."""

    def __init__(self, mode: MockMode = MockMode.DETERMINISTIC) -> None:
        self._mode = mode
        self._call_count = 0

    @property
    def call_count(self) -> int:
        """How many times ``generate`` has been called (for assertions)."""
        return self._call_count

    def generate(self, request: AIRequest) -> AIResponse:
        self._call_count += 1

        if self._mode is MockMode.ERROR:
            raise RuntimeError("mock network error")
        if self._mode is MockMode.RATE_LIMIT:
            raise MockRateLimitError("mock rate limit exceeded")
        if self._mode is MockMode.INVALID_SCHEMA:
            return AIResponse(
                provider="mock",
                model="mock-model",
                latency_ms=1,
                structured_payload={"unexpected_field": "not the expected schema"},
                telemetry=AITelemetry(latency_ms=1, input_tokens=1, output_tokens=1),
            )
        if self._mode is MockMode.TELEMETRY:
            return AIResponse(
                provider="mock",
                model="mock-model",
                latency_ms=123,
                raw_text="telemetry response",
                structured_payload={"result": "ok"},
                input_tokens=100,
                output_tokens=200,
                telemetry=AITelemetry(
                    latency_ms=123, input_tokens=100, output_tokens=200
                ),
            )
        # DETERMINISTIC: same request always yields the same response.
        return AIResponse(
            provider="mock",
            model="mock-model",
            latency_ms=1,
            raw_text="mock deterministic response",
            structured_payload={"result": "ok"},
            telemetry=AITelemetry(latency_ms=1, input_tokens=10, output_tokens=20),
        )
