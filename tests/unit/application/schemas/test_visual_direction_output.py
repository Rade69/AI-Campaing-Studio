"""Visual direction output boundary schema tests (A4)."""

import pytest
from pydantic import ValidationError

from ai_campaign_studio.application.schemas.visual_direction_output import (
    VisualDirectionOutput,
)


def _valid_direction() -> dict:
    return {
        "campaign_visual_system": {
            "primary_layout_family": "HERO",
            "headline_scale": "LARGE",
            "image_treatment": "BORDER",
            "logo_rule": "SHOW",
            "cta_rule": "SHOW",
            "alignment": "CENTER",
        },
        "layout_spec": {
            "primitive": "HERO",
            "image_position": "BACKGROUND",
            "headline_position": "CENTER",
            "headline_scale": "LARGE",
            "overlay": "DARK",
            "logo_position": "TOP_LEFT",
            "cta_style": "SOLID",
            "alignment": "CENTER",
            "format": "FEED_POST",
        },
    }


def test_valid_direction() -> None:
    output = VisualDirectionOutput.model_validate(_valid_direction())

    assert output.campaign_visual_system.primary_layout_family.value == "HERO"
    assert output.layout_spec.primitive.value == "HERO"


def test_arbitrary_enum_string_rejected() -> None:
    data = _valid_direction()
    data["campaign_visual_system"]["headline_scale"] = "SOMETHING_WEIRD"

    with pytest.raises(ValidationError):
        VisualDirectionOutput.model_validate(data)


def test_arbitrary_image_treatment_rejected() -> None:
    data = _valid_direction()
    data["campaign_visual_system"]["image_treatment"] = "SOMETHING_WEIRD"

    with pytest.raises(ValidationError):
        VisualDirectionOutput.model_validate(data)
