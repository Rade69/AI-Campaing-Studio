"""Anthropic (Claude) live adapter (A8, dio 4).

Owns translating an ``AIRequest`` into an Anthropic Messages API call, plus
its own simple ``test_connection()``/``discover_models()`` helpers. Does NOT
implement ``AIProviderConnectionPort`` (future dispatch contract) and does
NOT own business logic. Network/rate-limit retries are bounded and logged;
every provider error is mapped to a domain ``InfrastructureError`` (never a
raw SDK exception with no context).

Differences from OpenAI Chat Completions (intentional, not a reuse task):
- System prompt is a separate top-level parameter on ``client.messages.create``
  (not a message inside ``messages``).
- Response content is a list of content blocks (``message.content[0].text``
  for plain text), not a single string.
- Stop reason is ``message.stop_reason`` with values ``end_turn`` /
  ``max_tokens`` / ``stop_sequence`` / ``tool_use`` / ``pause_turn`` /
  ``refusal`` (different name + values from OpenAI's ``finish_reason``).
- Token usage: ``message.usage.input_tokens`` / ``output_tokens``.
- Error hierarchy: ``anthropic.APIError`` with concrete subtypes
  ``RateLimitError``/``AuthenticationError``/``APIConnectionError``/
  ``APITimeoutError``/``BadRequestError`` (all inheriting from
  ``AnthropicError``).

Structured output: we use the native ``output_config`` parameter on
``messages.create`` (anthropic >= 1.0). This is server-side
JSON-schema enforcement, functionally equivalent to OpenAI's
``response_format=json_schema``. Previous round used a prompt-based
directive injected into the system text; the BF-1 fix replaces that with
the native parameter (DeepSeek had 7 stavki umjesto traženih 3 without
an enforced schema, demonstrating the failure mode). The defensive
code-fence strip in :meth:`_parse_structured` is retained as a safety
net — with enforced output, the API guarantees JSON-only output, but
the strip still handles a model that adds stray whitespace/newlines
around the payload.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from anthropic import (
    Anthropic,
    AnthropicError,
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    RateLimitError,
)

from ai_campaign_studio.ai_registry.model_profiles import ModelProfile, ModelSource
from ai_campaign_studio.domain.common.errors import ErrorCode, InfrastructureError
from ai_campaign_studio.ports.ai import (
    AIRequest,
    AIResponse,
    AITelemetry,
    TextGenerationPort,
)


class AnthropicAdapter(TextGenerationPort):
    """Anthropic-backed ``TextGenerationPort`` implementation.

    ``client`` is an optional dependency-injection seam: production uses the
    default ``Anthropic`` client built from ``api_key``; tests inject a fake
    client so no real network call is ever made.
    """

    # Bounded retry: at most 2 attempts total (1 initial + 1 retry). Same
    # ceiling as OpenAIAdapter; we retry only the transient, recoverable
    # error classes (rate limit + connection/timeout), never auth or
    # bad-request — those will not get better on retry and only waste budget.
    _MAX_ATTEMPTS = 2

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        client: Any = None,
    ) -> None:
        self._model = model
        self._client: Any = client if client is not None else Anthropic(
            api_key=api_key, base_url=base_url
        )
        self._logger = logging.getLogger(__name__)

    # --- TextGenerationPort ---

    def generate(self, request: AIRequest) -> AIResponse:
        for attempt in range(1, self._MAX_ATTEMPTS + 1):
            try:
                return self._generate_once(request, attempt)
            except (RateLimitError, APIConnectionError, APITimeoutError) as exc:
                if attempt < self._MAX_ATTEMPTS:
                    self._logger.warning(
                        "Anthropic generate retrying (attempt %d/%d) after %s",
                        attempt,
                        self._MAX_ATTEMPTS,
                        type(exc).__name__,
                    )
                    continue
                raise self._map_error(exc) from exc
            except AnthropicError as exc:
                raise self._map_error(exc) from exc
        raise AssertionError("unreachable")

    def _generate_once(self, request: AIRequest, attempt: int) -> AIResponse:
        start = time.monotonic()
        # Anthropic Messages API: system prompt is a top-level parameter,
        # NOT a message in the list. user_text becomes the single user
        # message (we are single-turn for now; multi-turn is a future use-case).
        # ``output_config`` enforces JSON-schema output server-side; we
        # therefore pass ``request.system_text`` through unmodified (no
        # prompt-based JSON injection — see module docstring BF-1 note).
        message = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens_for(request),
            system=request.system_text,
            messages=[{"role": "user", "content": request.user_text}],
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": request.json_schema,
                }
            },
            **self._optional_generation_params(request),
        )
        latency_ms = int((time.monotonic() - start) * 1000)

        text = self._extract_text(message)
        usage = getattr(message, "usage", None)
        input_tokens = getattr(usage, "input_tokens", None) if usage else None
        output_tokens = getattr(usage, "output_tokens", None) if usage else None
        stop_reason = getattr(message, "stop_reason", None)
        request_id = getattr(message, "id", None)

        return AIResponse(
            provider="anthropic",
            model=self._model,
            latency_ms=latency_ms,
            raw_text=text,
            structured_payload=self._parse_structured(text),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            finish_reason=stop_reason,
            request_id=request_id,
            telemetry=AITelemetry(
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                retry_count=attempt - 1,
            ),
        )

    # --- connection helpers (NOT AIProviderConnectionPort) ---

    def test_connection(self) -> bool:
        """Return whether the configured API key is valid.

        Invalid credentials (``AuthenticationError``) are a legitimate ``False``
        result, not an exception. Unexpected failures (network/provider) are
        mapped to ``InfrastructureError``.
        """
        try:
            # ``models.list`` is paginated; we just need the first page to
            # verify the key. We do NOT iterate to completion (avoid network
            # amplification from a connection test).
            self._client.models.list(limit=1)
        except AuthenticationError:
            return False
        except AnthropicError as exc:
            raise self._map_error(exc) from exc
        return True

    def discover_models(self) -> list[ModelProfile]:
        """Discover provider models and map them to ``ModelProfile`` entries.

        ``client.models.list`` returns a paginated sync iterator; we drain it
        so callers get the full set in a single call. The cost of draining
        is intentional — discover is called from a non-hot path
        (``DiscoverModels`` use-case) and producing a partial list would
        be misleading.
        """
        try:
            page = self._client.models.list()
            models = list(page)
        except AnthropicError as exc:
            raise self._map_error(exc) from exc

        return [
            ModelProfile(
                provider_code="ANTHROPIC",
                model_id=model.id,
                display_name=getattr(model, "display_name", model.id) or model.id,
                source=ModelSource.DISCOVERED,
            )
            for model in models
        ]

    # --- helpers ---

    @staticmethod
    def _max_tokens_for(request: AIRequest) -> int:
        # Anthropic API requires ``max_tokens`` (no implicit default). Honour
        # the caller-supplied cap when present, otherwise fall back to a
        # conservative cap that fits a typical structured-output payload.
        if request.max_output_tokens is not None:
            return int(request.max_output_tokens)
        return 4096

    @staticmethod
    def _optional_generation_params(request: AIRequest) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if request.temperature is not None:
            params["temperature"] = request.temperature
        return params

    @staticmethod
    def _extract_text(message: Any) -> str | None:
        """Return concatenated text from a Messages API response.

        Anthropic response content is a list of blocks. For plain text
        generation (our current use-case) there is exactly one
        ``TextBlock`` with ``type='text'``; we concatenate defensively in
        case a future tool_use path produces a mixed block list.
        """
        content = getattr(message, "content", None) or []
        parts: list[str] = []
        for block in content:
            block_type = getattr(block, "type", None)
            if block_type == "text":
                text = getattr(block, "text", None)
                if text:
                    parts.append(text)
        if not parts:
            return None
        return "".join(parts)

    @staticmethod
    def _parse_structured(content: str | None) -> dict[str, Any] | None:
        if content is None:
            return None
        # With ``output_config`` enforcing JSON-schema output server-side,
        # the API guarantees the body parses as JSON. We keep the
        # code-fence strip as a defensive net (older SDK / pre-1.0
        # Anthropic models occasionally echo ````json fences) but
        # malformed-JSON is now a real anomaly and surfaces as
        # ``ErrorCode.PROVIDER_ERROR``.
        stripped = content.strip()
        if stripped.startswith("```"):
            first_newline = stripped.find("\n")
            last_fence = stripped.rfind("```")
            if first_newline != -1 and last_fence > first_newline:
                stripped = stripped[first_newline + 1 : last_fence].strip()
        try:
            return json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise InfrastructureError(
                "Anthropic returned malformed JSON", error_code=ErrorCode.PROVIDER_ERROR
            ) from exc

    @staticmethod
    def _map_error(exc: AnthropicError) -> InfrastructureError:
        if isinstance(exc, RateLimitError):
            return InfrastructureError(
                "Anthropic rate limit exceeded", error_code=ErrorCode.RATE_LIMIT
            )
        if isinstance(exc, APIConnectionError):
            return InfrastructureError(
                "Anthropic connection error", error_code=ErrorCode.NETWORK_ERROR
            )
        if isinstance(exc, APITimeoutError):
            return InfrastructureError(
                "Anthropic request timed out", error_code=ErrorCode.NETWORK_ERROR
            )
        if isinstance(exc, AuthenticationError):
            return InfrastructureError(
                "Anthropic API key invalid", error_code=ErrorCode.INVALID_API_KEY
            )
        if isinstance(exc, BadRequestError):
            return InfrastructureError(
                "Anthropic request was malformed", error_code=ErrorCode.PROVIDER_ERROR
            )
        return InfrastructureError(
            "Anthropic provider error", error_code=ErrorCode.PROVIDER_ERROR
        )
