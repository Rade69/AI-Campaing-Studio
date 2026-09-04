"""Google (Gemini) live adapter (A8, dio 5).

Owns translating an ``AIRequest`` into a Gemini ``generate_content`` call with
structured JSON output (``response_json_schema``), plus its own simple
``test_connection()``/``discover_models()`` helpers. Does NOT implement
``AIProviderConnectionPort`` (future dispatch contract) and does NOT own
business logic, CampaignRole logic, claim validation or persistence. Network/
rate-limit retries are bounded and logged; every provider error is mapped to a
domain ``InfrastructureError`` (never a raw SDK exception with no context).

SDK: ``google-genai`` (unified Google Gen AI SDK) — chosen over the deprecated
``google-generativeai`` package (EOL Nov 30, 2025); see evidence report.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from google import genai
from google.genai import types
from google.genai.errors import APIError, ClientError, ServerError

from ai_campaign_studio.ai_registry.model_profiles import ModelProfile, ModelSource
from ai_campaign_studio.domain.common.errors import ErrorCode, InfrastructureError
from ai_campaign_studio.ports.ai import (
    AIRequest,
    AIResponse,
    AITelemetry,
    TextGenerationPort,
)


class GoogleAdapter(TextGenerationPort):
    """Google (Gemini)-backed ``TextGenerationPort`` implementation.

    ``client`` is an optional dependency-injection seam: production uses the
    default ``genai.Client`` built from ``api_key``; tests inject a fake client
    so no real network call is ever made.
    """

    _MAX_ATTEMPTS = 2

    def __init__(
        self,
        api_key: str,
        model: str,
        client: Any = None,
    ) -> None:
        self._model = model
        self._client: Any = client if client is not None else genai.Client(
            api_key=api_key
        )
        self._logger = logging.getLogger(__name__)

    # --- TextGenerationPort ---

    def generate(self, request: AIRequest) -> AIResponse:
        for attempt in range(1, self._MAX_ATTEMPTS + 1):
            try:
                return self._generate_once(request, attempt)
            except APIError as exc:
                if self._is_retryable(exc) and attempt < self._MAX_ATTEMPTS:
                    self._logger.warning(
                        "Google generate retrying (attempt %d/%d) after %s",
                        attempt,
                        self._MAX_ATTEMPTS,
                        type(exc).__name__,
                    )
                    continue
                raise self._map_error(exc) from exc
        raise AssertionError("unreachable")

    def _generate_once(self, request: AIRequest, attempt: int) -> AIResponse:
        start = time.monotonic()
        config = types.GenerateContentConfig(
            system_instruction=request.system_text,
            response_mime_type="application/json",
            response_json_schema=request.json_schema,
            **self._optional_generation_params(request),
        )
        contents = [
            types.Content(role="user", parts=[types.Part(text=request.user_text)])
        ]
        response = self._client.models.generate_content(
            model=self._model, contents=contents, config=config
        )
        latency_ms = int((time.monotonic() - start) * 1000)

        text = self._extract_text(response)
        usage = getattr(response, "usage_metadata", None)
        input_tokens = usage.prompt_token_count if usage else None
        output_tokens = usage.candidates_token_count if usage else None

        return AIResponse(
            provider="google",
            model=self._model,
            latency_ms=latency_ms,
            raw_text=text,
            structured_payload=self._parse_structured(text),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            finish_reason=self._extract_finish_reason(response),
            request_id=getattr(response, "response_id", None),
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

        Invalid credentials (``ClientError`` 401/403) are a legitimate ``False``
        result, not an exception. Unexpected failures are mapped to
        ``InfrastructureError``.
        """
        try:
            list(self._client.models.list())
        except ClientError as exc:
            if exc.code in (401, 403):
                return False
            raise self._map_error(exc) from exc
        except APIError as exc:
            raise self._map_error(exc) from exc
        return True

    def discover_models(self) -> list[ModelProfile]:
        """Discover provider models and map them to ``ModelProfile`` entries."""
        try:
            models = list(self._client.models.list())
        except APIError as exc:
            raise self._map_error(exc) from exc

        return [
            ModelProfile(
                provider_code="GOOGLE",
                model_id=model.name,
                display_name=model.display_name or model.name,
                source=ModelSource.DISCOVERED,
            )
            for model in models
        ]

    # --- helpers ---

    @staticmethod
    def _optional_generation_params(request: AIRequest) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if request.temperature is not None:
            params["temperature"] = request.temperature
        if request.max_output_tokens is not None:
            params["max_output_tokens"] = request.max_output_tokens
        return params

    @staticmethod
    def _extract_text(response: Any) -> str | None:
        candidates = getattr(response, "candidates", None)
        if not candidates:
            return None
        content = getattr(candidates[0], "content", None)
        if content is None:
            return None
        parts = getattr(content, "parts", None)
        if not parts:
            return None
        return getattr(parts[0], "text", None)

    @staticmethod
    def _extract_finish_reason(response: Any) -> str | None:
        candidates = getattr(response, "candidates", None)
        if not candidates:
            return None
        value = getattr(candidates[0], "finish_reason", None)
        if value is None:
            return None
        return value.value if hasattr(value, "value") else str(value)

    @staticmethod
    def _parse_structured(content: str | None) -> dict[str, Any] | None:
        if content is None:
            return None
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise InfrastructureError(
                "Google returned malformed JSON",
                error_code=ErrorCode.PROVIDER_ERROR,
            ) from exc

    @staticmethod
    def _is_retryable(exc: APIError) -> bool:
        if isinstance(exc, ServerError):
            return True
        return isinstance(exc, ClientError) and exc.code == 429

    @staticmethod
    def _map_error(exc: APIError) -> InfrastructureError:
        if isinstance(exc, ClientError) and exc.code in (401, 403):
            return InfrastructureError(
                "Google API key invalid", error_code=ErrorCode.INVALID_API_KEY
            )
        if isinstance(exc, ClientError) and exc.code == 429:
            return InfrastructureError(
                "Google rate limit exceeded", error_code=ErrorCode.RATE_LIMIT
            )
        if isinstance(exc, ServerError):
            return InfrastructureError(
                "Google server error", error_code=ErrorCode.PROVIDER_ERROR
            )
        return InfrastructureError(
            "Google provider error", error_code=ErrorCode.PROVIDER_ERROR
        )
