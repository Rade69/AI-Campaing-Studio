"""Pydantic boundary schema for ``CampaignBrief`` input (A4)."""

from pydantic import BaseModel, ConfigDict, Field


class CampaignTargetInput(BaseModel):
    """Structural shape of one campaign target.

    Only structural validation here (``channel``/``platform_code``/
    ``format_code`` as strings); no lookup against the ``channels`` registry.
    """

    model_config = ConfigDict(frozen=True)

    channel: str
    platform_code: str
    format_code: str


class CampaignBriefInput(BaseModel):
    """Validated GUI/CLI input before mapping to domain ``CampaignBrief``."""

    model_config = ConfigDict(frozen=True)

    offer: str
    goal: str
    audience_text: str
    targets: list[CampaignTargetInput]
    content_piece_count: int = Field(gt=0)
    content_language_context: str
    special_instructions: list[str] = Field(default_factory=list)
