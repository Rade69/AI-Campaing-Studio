"""Pydantic boundary schema for campaign plan LLM output (A4)."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ai_campaign_studio.domain.campaign.roles import CampaignRole


class CampaignPlanItemOutput(BaseModel):
    """One planned item inside a campaign plan."""

    model_config = ConfigDict(frozen=True)

    order: int
    role: CampaignRole
    topic: str = Field(min_length=1)
    goal: str
    facts_needed: list[str] = Field(default_factory=list)


class CampaignPlanOutput(BaseModel):
    """LLM output shape for a campaign plan."""

    model_config = ConfigDict(frozen=True)

    campaign_theme: str
    items: list[CampaignPlanItemOutput]

    @model_validator(mode="after")
    def _validate_items(self) -> "CampaignPlanOutput":
        orders = [item.order for item in self.items]
        if len(orders) != len(set(orders)):
            raise ValueError("order must be unique")
        if sorted(orders) != list(range(1, len(orders) + 1)):
            raise ValueError("order must be a contiguous 1-based sequence")
        return self


def validate_campaign_plan_output(
    data: dict[str, Any], content_piece_count: int
) -> CampaignPlanOutput:
    """Validate plan output and enforce the expected item count."""
    output = CampaignPlanOutput.model_validate(data)
    if len(output.items) != content_piece_count:
        raise ValueError(
            f"expected {content_piece_count} items, got {len(output.items)}"
        )
    return output
