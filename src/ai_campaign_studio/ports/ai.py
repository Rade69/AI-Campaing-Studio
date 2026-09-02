"""AI port (A7) — framework-neutral text-generation contract.

Distinct from ``ports/ai_registry.py`` (the P0 provider/model registry). This
module owns the request/response models and the ``TextGenerationPort``
protocol; concrete adapters (mock first, then live providers) implement it.
No sqlite/http/provider-SDK imports live here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class AIMessage:
    """A single chat-style message.

    ``role`` + ``content`` is the standard chat-message shape (``system``/
    ``user``/``assistant`` roles). ``AIRequest`` currently uses the flattened
    ``system_text``/``user_text`` form; ``AIMessage`` remains available for
    multi-turn/chat-style callers later.
    """

    role: str
    content: str


@dataclass(frozen=True)
class AITelemetry:
    """Lightweight response-embedded telemetry snapshot.

    Deliberately NOT ``ports/telemetry.py``'s full event models (deferred to
    Performance/Analytics). Just the latency/token/retry facts one response
    carries.
    """

    latency_ms: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    retry_count: int = 0


@dataclass(frozen=True)
class AIRequest:
    """A single text-generation request."""

    purpose: str
    prompt_name: str
    prompt_version: str
    system_text: str
    user_text: str
    json_schema: dict[str, Any]
    temperature: float | None = None
    max_output_tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AIResponse:
    """A single text-generation response."""

    provider: str
    model: str
    latency_ms: int
    raw_text: str | None = None
    structured_payload: dict[str, Any] | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    finish_reason: str | None = None
    request_id: str | None = None
    telemetry: AITelemetry | None = None


@runtime_checkable
class TextGenerationPort(Protocol):
    """Framework-neutral text generation."""

    def generate(self, request: AIRequest) -> AIResponse: ...
