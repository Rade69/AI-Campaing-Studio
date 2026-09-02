"""Social post generation output boundary schema tests (A4)."""

import pytest
from pydantic import ValidationError

from ai_campaign_studio.application.schemas.social_post_generation_output import (
    SocialPostGenerationOutput,
)


def _valid_post() -> dict:
    return {
        "headline": "H",
        "caption": "C",
        "hook": "Ho",
        "body": "B",
        "cta": "Cta",
        "claims": [{"text": "Claim", "type": "FACT"}],
    }


def test_valid_post() -> None:
    output = SocialPostGenerationOutput.model_validate(_valid_post())

    assert output.claims[0].type.value == "FACT"


def test_invalid_claim_type_rejected() -> None:
    data = _valid_post()
    data["claims"][0]["type"] = "NOT_A_TYPE"

    with pytest.raises(ValidationError):
        SocialPostGenerationOutput.model_validate(data)
