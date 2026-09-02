"""Pydantic boundary schema for social post generation LLM output (A4)."""

from pydantic import BaseModel, ConfigDict, Field

from ai_campaign_studio.domain.content.enums import ClaimType


class ContentClaimOutput(BaseModel):
    """One claim within a social post.

    ``type`` is validated against the domain ``ClaimType`` enum, so an
    arbitrary LLM string cannot pass. ``fact_ids`` are plain strings here
    (``FactId`` is runtime ``str``); mapping to real claim objects (with
    ``id``/``status``) is use-case work outside this schema.
    """

    model_config = ConfigDict(frozen=True)

    text: str
    type: ClaimType
    fact_ids: list[str] = Field(default_factory=list)


class SocialPostGenerationOutput(BaseModel):
    """LLM output shape for a ``SOCIAL_POST`` payload."""

    model_config = ConfigDict(frozen=True)

    headline: str
    caption: str
    hook: str
    body: str
    cta: str
    hashtags: list[str] = Field(default_factory=list)
    claims: list[ContentClaimOutput] = Field(default_factory=list)
