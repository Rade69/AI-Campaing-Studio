"""Campaign brief mapper (A9).

Owns ``map_campaign_brief``: converts a validated ``CampaignBriefInput`` into
the immutable domain ``CampaignBrief``. Pure in-memory transformation — no
validation (Pydantic already ran) and no persistence.
"""

from __future__ import annotations

from ai_campaign_studio.application.schemas.campaign_brief import CampaignBriefInput
from ai_campaign_studio.domain.campaign.entities import CampaignBrief
from ai_campaign_studio.domain.common.ids import new_id
from ai_campaign_studio.domain.common.timestamps import utc_now
from ai_campaign_studio.domain.content.entities import CampaignTarget


def map_campaign_brief(brief_input: CampaignBriefInput) -> CampaignBrief:
    """Map a validated brief input to the immutable domain ``CampaignBrief``."""
    return CampaignBrief(
        id=new_id(),
        offer=brief_input.offer,
        goal=brief_input.goal,
        audience_text=brief_input.audience_text,
        targets=tuple(
            CampaignTarget(
                channel=target.channel,
                platform_code=target.platform_code,
                format_code=target.format_code,
            )
            for target in brief_input.targets
        ),
        content_piece_count=brief_input.content_piece_count,
        content_language_context=brief_input.content_language_context,
        created_at=utc_now(),
        special_instructions=tuple(brief_input.special_instructions),
    )
