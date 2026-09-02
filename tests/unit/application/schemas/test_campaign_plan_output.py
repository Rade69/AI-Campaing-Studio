"""Campaign plan output boundary schema tests (A4)."""

import pytest
from pydantic import ValidationError

from ai_campaign_studio.application.schemas.campaign_plan_output import (
    CampaignPlanOutput,
    validate_campaign_plan_output,
)


def _valid_plan() -> dict:
    return {
        "campaign_theme": "Theme",
        "items": [
            {"order": 1, "role": "PROBLEM", "topic": "Topic", "goal": "Goal"},
            {"order": 2, "role": "EDUCATION", "topic": "Topic", "goal": "Goal"},
        ],
    }


def test_valid_plan() -> None:
    output = validate_campaign_plan_output(_valid_plan(), content_piece_count=2)

    assert len(output.items) == 2


def test_duplicate_order_rejected() -> None:
    data = _valid_plan()
    data["items"][1]["order"] = 1

    with pytest.raises(ValidationError):
        CampaignPlanOutput.model_validate(data)


def test_invalid_role_rejected() -> None:
    data = _valid_plan()
    data["items"][0]["role"] = "NOT_A_ROLE"

    with pytest.raises(ValidationError):
        CampaignPlanOutput.model_validate(data)


def test_wrong_item_count_rejected() -> None:
    with pytest.raises(ValueError):
        validate_campaign_plan_output(_valid_plan(), content_piece_count=3)


def test_empty_topic_rejected() -> None:
    data = _valid_plan()
    data["items"][0]["topic"] = ""

    with pytest.raises(ValidationError):
        CampaignPlanOutput.model_validate(data)
