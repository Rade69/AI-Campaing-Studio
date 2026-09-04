"""OpenAI-compatible provider factories (A8, dio 3).

Owns thin factory functions that build an ``OpenAIAdapter`` for DeepSeek,
OpenRouter and a generic user-configurable OpenAI-compatible provider, each
with the correct fixed or user-supplied ``base_url`` and provenance
(``provider_code``/``provider_display``). Does NOT own provider discovery,
secret handling, use-case logic or bootstrap wiring — composition stays in a
future bridge task.
"""

from __future__ import annotations

from typing import Any

from ai_campaign_studio.infrastructure.ai.openai_adapter import (
    JSON_OBJECT_MODE,
    OpenAIAdapter,
)

# Base URLs verified against official documentation on 2026-09-04:
#   * DeepSeek  — https://api-docs.deepseek.com/ (Quick Start): base_url for
#     the OpenAI SDK is ``https://api.deepseek.com``.
#   * OpenRouter — https://openrouter.ai/docs/quickstart: baseURL for the
#     OpenAI SDK is ``https://openrouter.ai/api/v1``.
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def build_deepseek_adapter(
    api_key: str, model: str, client: Any = None
) -> OpenAIAdapter:
    """Build an ``OpenAIAdapter`` pinned to DeepSeek's fixed base URL.

    DeepSeek rejects OpenAI's ``json_schema`` response_format (live-verified,
    2026-09-04), so it uses ``json_object`` with the schema embedded in the
    prompt.
    """
    return OpenAIAdapter(
        api_key=api_key,
        model=model,
        base_url=DEEPSEEK_BASE_URL,
        provider_code="DEEPSEEK",
        provider_display="deepseek",
        structured_output_mode=JSON_OBJECT_MODE,
        client=client,
    )


def build_openrouter_adapter(
    api_key: str, model: str, client: Any = None
) -> OpenAIAdapter:
    """Build an ``OpenAIAdapter`` pinned to OpenRouter's fixed base URL.

    OpenRouter's ``json_schema`` support was NOT live-verified, so the default
    is conservatively ``json_object`` (schema embedded in the prompt) until a
    real call proves ``json_schema`` works.
    """
    return OpenAIAdapter(
        api_key=api_key,
        model=model,
        base_url=OPENROUTER_BASE_URL,
        provider_code="OPENROUTER",
        provider_display="openrouter",
        structured_output_mode=JSON_OBJECT_MODE,
        client=client,
    )


def build_openai_compatible_adapter(
    api_key: str,
    model: str,
    base_url: str,
    client: Any = None,
    structured_output_mode: str = JSON_OBJECT_MODE,
) -> OpenAIAdapter:
    """Build an ``OpenAIAdapter`` for a user-configured base URL.

    ``base_url`` is a required parameter because the generic
    ``OPENAI_COMPATIBLE`` provider is ``base_url_mode: USER_CONFIGURABLE`` in
    ``resources/ai_providers/openai_compatible.yaml`` — the user supplies it,
    it is never fixed here.

    The default ``structured_output_mode`` is ``json_object`` (broadest
    compatibility for arbitrary endpoints); callers who know their endpoint
    supports OpenAI's ``json_schema`` mode may pass it explicitly.
    """
    return OpenAIAdapter(
        api_key=api_key,
        model=model,
        base_url=base_url,
        provider_code="OPENAI_COMPATIBLE",
        provider_display="openai_compatible",
        structured_output_mode=structured_output_mode,
        client=client,
    )
