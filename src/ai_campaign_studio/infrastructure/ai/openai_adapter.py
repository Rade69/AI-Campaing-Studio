"""OpenAI-compatible Chat Completions adapter (A8).

Owns translating an ``AIRequest`` into an OpenAI-style Chat Completions call
with structured output — ``response_format`` ``json_schema`` (OpenAI default)
or ``json_object`` with the schema embedded in the prompt (OpenAI-compatible
providers such as DeepSeek that reject ``json_schema``) — plus its own simple
``test_connection()``/``discover_models()`` helpers. ``base_url``,
``provider_code``, ``provider_display`` and ``structured_output_mode`` are
constructor parameters so the same adapter serves DeepSeek/OpenRouter/
generic OpenAI-compatible providers without faking provenance. Does NOT
implement ``AIProviderConnectionPort``
(future dispatch contract) and does NOT own business logic, CampaignRole
logic, claim validation or persistence. Network/rate-limit retries are
bounded and logged; every provider error is mapped to a domain
``InfrastructureError`` (never a raw SDK exception with no context).
"""

from __future__ import annotations

import json
import logging
import re
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

JSON_SCHEMA_MODE = "json_schema"
JSON_OBJECT_MODE = "json_object"

_COUNT_LINE_RE = re.compile(
    r"(?P<name>(?:[A-Za-z][A-Za-z0-9_]*_count|\bcount\b))\s*:\s*(?P<value>\d+)",
    re.IGNORECASE,
)


def _exact_array_constraints(schema: Any) -> list[tuple[str, int]]:
    """Collect ``(path, count)`` for array fields where minItems == maxItems."""
    results: list[tuple[str, int]] = []

    def walk(node: Any, path: str, seen_refs: set[str]) -> None:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str):
                if ref in seen_refs:
                    return
                seen_refs.add(ref)
            if node.get("type") == "array":
                min_items = node.get("minItems")
                max_items = node.get("maxItems")
                if (
                    isinstance(min_items, int)
                    and isinstance(max_items, int)
                    and min_items == max_items
                ):
                    results.append((path, min_items))
            properties = node.get("properties")
            if isinstance(properties, dict):
                for name, sub in properties.items():
                    walk(sub, f"{path}.{name}" if path else name, seen_refs)
            for key in ("items", "additionalProperties", "contains"):
                if key in node:
                    walk(node[key], path, seen_refs)
            for key in ("$defs", "definitions"):
                defs = node.get(key)
                if isinstance(defs, dict):
                    for name, sub in defs.items():
                        walk(sub, name, seen_refs)
            for key in ("anyOf", "allOf", "oneOf"):
                branches = node.get(key)
                if isinstance(branches, list):
                    for index, sub in enumerate(branches):
                        walk(sub, f"{path}[{index}]", seen_refs)
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{path}[{index}]", seen_refs)

    walk(schema, "", set())
    return results


def _count_constraints_from_text(text: str) -> list[tuple[str, int]]:
    """Collect ``(field_name, exact_count)`` from ``<name>_count: N`` text."""
    return [
        (match.group("name"), int(match.group("value")))
        for match in _COUNT_LINE_RE.finditer(text)
    ]


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
        provider_code: str = "OPENAI",
        provider_display: str = "openai",
        structured_output_mode: str = JSON_SCHEMA_MODE,
    ) -> None:
        if structured_output_mode not in (JSON_SCHEMA_MODE, JSON_OBJECT_MODE):
            raise ValueError(
                f"unsupported structured_output_mode: "
                f"{structured_output_mode!r}"
            )
        self._model = model
        self._provider_code = provider_code.strip().upper()
        self._provider_display = provider_display
        self._structured_output_mode = structured_output_mode
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
        messages, response_format = self._build_messages_and_format(request)
        completion = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            response_format=response_format,
            **self._optional_generation_params(request),
        )
        latency_ms = int((time.monotonic() - start) * 1000)

        choice = completion.choices[0]
        message = choice.message
        usage = getattr(completion, "usage", None)
        input_tokens = usage.prompt_tokens if usage else None
        output_tokens = usage.completion_tokens if usage else None

        return AIResponse(
            provider=self._provider_display,
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

    def _build_messages_and_format(
        self, request: AIRequest
    ) -> tuple[list[dict[str, str]], dict[str, Any]]:
        """Build chat messages + ``response_format`` for the configured mode."""
        if self._structured_output_mode == JSON_OBJECT_MODE:
            return self._json_object_messages(request), {"type": "json_object"}

        messages = [
            {"role": "system", "content": request.system_text},
            {"role": "user", "content": request.user_text},
        ]
        response_format: dict[str, Any] = {
            "type": "json_schema",
            "json_schema": {
                "name": _JSON_SCHEMA_NAME,
                "schema": request.json_schema,
            },
        }
        return messages, response_format

    @staticmethod
    def _json_object_messages(request: AIRequest) -> list[dict[str, str]]:
        """Embed the JSON schema in the system prompt for ``json_object`` mode.

        ``json_object`` does not enforce the schema server-side, so the schema
        is passed as text plus an explicit exact-count instruction (both from
        array ``minItems == maxItems`` constraints in the schema and from
        ``<name>_count: N`` fields in the user text).
        """
        schema_text = json.dumps(
            request.json_schema, ensure_ascii=False, indent=2
        )
        lines = [
            "Respond with a single valid JSON object that conforms exactly to",
            "the JSON Schema below. Return only that JSON object and nothing",
            "else.",
            "",
            "```json",
            schema_text,
            "```",
        ]

        array_constraints = _exact_array_constraints(request.json_schema)
        count_constraints = _count_constraints_from_text(request.user_text)
        if array_constraints or count_constraints:
            lines.append("")
            lines.append("Exact count requirements — match these EXACTLY:")
            for path, count in array_constraints:
                lines.append(f"- array field `{path}`: exactly {count} item(s)")
            for name, count in count_constraints:
                lines.append(
                    f"- `{name}` = {count}: the corresponding output "
                    f"collection must contain exactly {count} item(s)"
                )
            lines.append(
                "Do not produce more or fewer items than the counts above."
            )

        system_text = request.system_text + "\n\n" + "\n".join(lines)
        return [
            {"role": "system", "content": system_text},
            {"role": "user", "content": request.user_text},
        ]

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
                provider_code=self._provider_code,
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
