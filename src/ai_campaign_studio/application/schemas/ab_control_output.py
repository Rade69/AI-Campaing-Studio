"""Pydantic boundary schema for Control A (A/B) LLM output (A16)."""

from pydantic import BaseModel, ConfigDict

from ai_campaign_studio.application.schemas.social_post_generation_output import (
    SocialPostGenerationOutput,
)


class ControlAOutput(BaseModel):
    """LLM output shape for the Control A single-call baseline.

    Reuses the existing ``SocialPostGenerationOutput`` per post rather than
    duplicating its fields — Control A output is just a list of those posts.
    """

    model_config = ConfigDict(frozen=True)

    posts: list[SocialPostGenerationOutput]
