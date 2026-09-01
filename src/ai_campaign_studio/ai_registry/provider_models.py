"""Immutable AI provider definitions (P0.14)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


def _normalize_code(value: str) -> str:
    return value.strip().upper()


class AIProviderDefinition(BaseModel):
    """A data-driven AI provider entry.

    Carries only provider metadata; deliberately no secrets, no API keys and
    no hardcoded model lists (D-AI-2). ``adapter_type`` is an opaque string
    that a future adapter layer will resolve — no provider SDK is imported or
    referenced here.
    """

    model_config = ConfigDict(frozen=True)

    provider_code: str
    display_name: str
    adapter_type: str
    requires_api_key: bool = True
    supports_model_discovery: bool = False
    base_url_mode: Literal["FIXED", "USER_CONFIGURABLE", "NONE"] = "NONE"
    enabled: bool = True

    @field_validator("provider_code")
    @classmethod
    def _normalize_provider_code(cls, value: str) -> str:
        return _normalize_code(value)
