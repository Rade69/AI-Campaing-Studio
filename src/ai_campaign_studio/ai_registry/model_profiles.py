"""Model profile primitives (P0.14).

A model is not just a string (D-AI-3): it carries capabilities so use-cases
can ask for a capability instead of a concrete vendor model.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, field_validator


class ModelCapability(StrEnum):
    TEXT_GENERATION = "TEXT_GENERATION"
    STRUCTURED_OUTPUT = "STRUCTURED_OUTPUT"
    VISION = "VISION"
    IMAGE_GENERATION = "IMAGE_GENERATION"
    TOOL_USE = "TOOL_USE"


class ModelSource(StrEnum):
    DISCOVERED = "DISCOVERED"
    REGISTRY = "REGISTRY"
    MANUAL = "MANUAL"


class ModelProfile(BaseModel):
    """A single model entry within a provider."""

    model_config = ConfigDict(frozen=True)

    provider_code: str
    model_id: str
    display_name: str
    capabilities: tuple[ModelCapability, ...] = ()
    context_window: int | None = None
    supports_temperature: bool | None = None
    enabled: bool = True
    source: ModelSource = ModelSource.MANUAL

    @field_validator("provider_code")
    @classmethod
    def _normalize_provider_code(cls, value: str) -> str:
        return value.strip().upper()
