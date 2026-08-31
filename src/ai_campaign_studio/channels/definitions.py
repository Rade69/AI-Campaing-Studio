"""Immutable channel/platform/format definitions (P0.13)."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ai_campaign_studio.channels.enums import Channel


def _normalize_code(value: str) -> str:
    return value.strip().upper()


class TextConstraints(BaseModel):
    """Platform/format text constraints (all optional where not confirmed)."""

    model_config = ConfigDict(frozen=True)

    max_chars: int | None = None
    max_caption_chars: int | None = None
    max_title_chars: int | None = None
    supports_hashtags: bool = False
    supports_links: bool = True


class VisualConstraints(BaseModel):
    """Platform/format visual constraints."""

    model_config = ConfigDict(frozen=True)

    supported_aspect_ratios: tuple[str, ...] = Field(default_factory=tuple)
    supports_static_image: bool = False
    supports_video: bool = False
    supports_carousel: bool = False


class FormatDefinition(BaseModel):
    """A concrete content format within a platform."""

    model_config = ConfigDict(frozen=True)

    code: str
    display_name: str
    required_fields: tuple[str, ...] = Field(default_factory=tuple)
    optional_fields: tuple[str, ...] = Field(default_factory=tuple)
    text_constraints: TextConstraints = Field(default_factory=TextConstraints)
    visual_constraints: VisualConstraints = Field(default_factory=VisualConstraints)
    enabled: bool = True

    @field_validator("code")
    @classmethod
    def _normalize_code(cls, value: str) -> str:
        return _normalize_code(value)


class PlatformDefinition(BaseModel):
    """A concrete distribution platform within a channel."""

    model_config = ConfigDict(frozen=True)

    code: str
    display_name: str
    channel: Channel
    supported_formats: tuple[str, ...] = Field(default_factory=tuple)
    content_rules: tuple[str, ...] = Field(default_factory=tuple)
    enabled: bool = True

    @field_validator("code")
    @classmethod
    def _normalize_code(cls, value: str) -> str:
        return _normalize_code(value)

    @field_validator("supported_formats", mode="before")
    @classmethod
    def _normalize_supported_formats(cls, value: object) -> tuple[str, ...]:
        if not isinstance(value, (list, tuple)):
            raise ValueError("supported_formats must be a list of codes")
        normalized = tuple(_normalize_code(str(item)) for item in value)
        if len(normalized) != len(set(normalized)):
            raise ValueError(f"duplicate supported format reference: {value}")
        return normalized
