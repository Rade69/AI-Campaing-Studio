"""OpenAI live adapter (A8, dio 2).

Owns translating an ``AIRequest`` into an OpenAI Chat Completions call with
``response_format`` (json_schema) for structured output, plus its own simple
``test_connection()``/``discover_models()`` helpers. Does NOT implement
``AIProviderConnectionPort`` (future dispatch contract) and does NOT own
business logic, CampaignRole logic, claim validation or persistence. Network/
rate-limit retries are bounded and logged; every provider error is mapped to a
domain ``InfrastructureError`` (never a raw SDK exception with no context).
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from openai import (
    APIConnectionError,
    AuthenticationError,
    OpenAI,
    OpenAIError,
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

_JSON_SCHEMA_NAME = "structured_response"


class OpenAIAdapter(TextGenerationPort):
    """OpenAI-backed ``TextGenerationPort`` implementation.

    ``client`` is an optional dependency-injection seam: production uses the
    default ``OpenAI`` client built from ``api_key``/``base_url``; tests inject
    a fake client so no real network call is ever made.
    """

    _MAX_ATTEMPTS = 2

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        client: Any = None,
    ) -> None:
        self._model = model
        self._client: Any = client if client is not None else OpenAI(
            api_key=api_key, base_url=base_url
        )
        self._logger = logging.getLogger(__name__)

    # --- TextGenerationPort ---

    def generate(self, request: AIRequest) -> AIResponse:
        for attempt in range(1, self._MAX_ATTEMPTS + 1):
            try:
                return self._generate_once(request, attempt)
            except (RateLimitError, APIConnectionError) as exc:
                if attempt < self._MAX_ATTEMPTS:
                    self._logger.warning(
                        "OpenAI generate retrying (attempt %d/%d) after %s",
                        attempt,
                        self._MAX_ATTEMPTS,
                        type(exc).__name__,
                    )
                    continue
                raise self._map_error(exc) from exc
            except OpenAIError as exc:
                raise self._map_error(exc) from exc
        raise AssertionError("unreachable")

    def _generate_once(self, request: AIRequest, attempt: int) -> AIResponse:
        start = time.monotonic()
        messages = [
            {"role": "system", "content": request.system_text},
            {"role": "user", "content": request.user_text},
        ]
        completion = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": _JSON_SCHEMA_NAME,
                    "schema": request.json_schema,
                },
            },
            **self._optional_generation_params(request),
        )
        latency_ms = int((time.monotonic() - start) * 1000)

        choice = completion.choices[0]
        message = choice.message
        usage = getattr(completion, "usage", None)
        input_tokens = usage.prompt_tokens if usage else None
        output_tokens = usage.completion_tokens if usage else None

        return AIResponse(
            provider="openai",
            model=self._model,
            latency_ms=latency_ms,
            raw_text=message.content,
            structured_payload=self._parse_structured(message.content),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            finish_reason=getattr(choice, "finish_reason", None),
            request_id=getattr(completion, "id", None),
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
            self._client.models.list()
        except AuthenticationError:
            return False
        except OpenAIError as exc:
            raise self._map_error(exc) from exc
        return True

    def discover_models(self) -> list[ModelProfile]:
        """Discover provider models and map them to ``ModelProfile`` entries."""
        try:
            page = self._client.models.list()
        except OpenAIError as exc:
            raise self._map_error(exc) from exc

        return [
            ModelProfile(
                provider_code="OPENAI",
                model_id=model.id,
                display_name=model.id,
                source=ModelSource.DISCOVERED,
            )
            for model in page.data
        ]

    # --- helpers ---

    @staticmethod
    def _optional_generation_params(request: AIRequest) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if request.temperature is not None:
            params["temperature"] = request.temperature
        if request.max_output_tokens is not None:
            params["max_completion_tokens"] = request.max_output_tokens
        return params

    @staticmethod
    def _parse_structured(content: str | None) -> dict[str, Any] | None:
        if content is None:
            return None
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise InfrastructureError(
                "OpenAI returned malformed JSON",
                error_code=ErrorCode.PROVIDER_ERROR,
            ) from exc

    @staticmethod
    def _map_error(exc: OpenAIError) -> InfrastructureError:
        if isinstance(exc, RateLimitError):
            return InfrastructureError(
                "OpenAI rate limit exceeded", error_code=ErrorCode.RATE_LIMIT
            )
        if isinstance(exc, APIConnectionError):
            return InfrastructureError(
                "OpenAI connection error", error_code=ErrorCode.NETWORK_ERROR
            )
        if isinstance(exc, AuthenticationError):
            return InfrastructureError(
                "OpenAI API key invalid", error_code=ErrorCode.INVALID_API_KEY
            )
        return InfrastructureError(
            "OpenAI provider error", error_code=ErrorCode.PROVIDER_ERROR
        )
