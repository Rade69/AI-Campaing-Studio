"""Unit tests for campaign brief mapper (A9)."""

from ai_campaign_studio.application.mappers.campaign_brief_mapper import (
    map_campaign_brief,
)
from ai_campaign_studio.application.schemas.campaign_brief import (
    CampaignBriefInput,
    CampaignTargetInput,
)
from ai_campaign_studio.domain.content.entities import CampaignTarget


def test_map_campaign_brief_round_trip() -> None:
    brief_input = CampaignBriefInput(
        offer="Dental implants",
        goal="Book consultations",
        audience_text="Adults 25-55",
        targets=[
            CampaignTargetInput(
                channel="SOCIAL",
                platform_code="INSTAGRAM",
                format_code="FEED_POST",
            )
        ],
        content_piece_count=3,
        content_language_context="BHS_LATIN",
        special_instructions=["Keep it friendly"],
    )

    brief = map_campaign_brief(brief_input)

    assert brief.id  # non-empty string id
    assert brief.offer == "Dental implants"
    assert brief.goal == "Book consultations"
    assert brief.audience_text == "Adults 25-55"
    assert brief.targets == (
        CampaignTarget(
            channel="SOCIAL",
            platform_code="INSTAGRAM",
            format_code="FEED_POST",
        ),
    )
    assert brief.content_piece_count == 3
    assert brief.content_language_context == "BHS_LATIN"
    assert brief.special_instructions == ("Keep it friendly",)
