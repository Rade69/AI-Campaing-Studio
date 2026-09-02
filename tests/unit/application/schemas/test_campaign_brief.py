"""Campaign brief boundary schema tests (A4)."""

import pytest
from pydantic import ValidationError

from ai_campaign_studio.application.schemas.campaign_brief import CampaignBriefInput


def _valid_brief() -> dict:
    return {
        "offer": "Offer",
        "goal": "Goal",
        "audience_text": "Audience",
        "targets": [
            {
                "channel": "SOCIAL",
                "platform_code": "INSTAGRAM",
                "format_code": "FEED_POST",
            }
        ],
        "content_piece_count": 6,
        "content_language_context": "BHS_LATIN",
    }


def test_valid_brief() -> None:
    brief = CampaignBriefInput.model_validate(_valid_brief())

    assert brief.content_piece_count == 6
    assert brief.targets[0].platform_code == "INSTAGRAM"


def test_content_piece_count_must_be_positive() -> None:
    data = _valid_brief()
    data["content_piece_count"] = 0

    with pytest.raises(ValidationError):
        CampaignBriefInput.model_validate(data)
