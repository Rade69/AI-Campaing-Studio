"""Visual layout/entity tests (A3)."""

from datetime import UTC, datetime

from ai_campaign_studio.domain.visual.entities import CampaignVisualSystem
from ai_campaign_studio.domain.visual.enums import (
    Alignment,
    CtaStyle,
    HeadlinePosition,
    HeadlineScale,
    ImagePosition,
    LayoutPrimitive,
    LogoPosition,
    Overlay,
)
from ai_campaign_studio.domain.visual.layout import LayoutSpec


def test_layout_spec_fields_are_typed_enums() -> None:
    spec = LayoutSpec(
        primitive=LayoutPrimitive.HERO,
        image_position=ImagePosition.BACKGROUND,
        headline_position=HeadlinePosition.CENTER,
        headline_scale=HeadlineScale.LARGE,
        overlay=Overlay.DARK,
        logo_position=LogoPosition.TOP_LEFT,
        cta_style=CtaStyle.SOLID,
        alignment=Alignment.CENTER,
        format="FEED_POST",
    )

    assert spec.primitive is LayoutPrimitive.HERO
    assert spec.image_position is ImagePosition.BACKGROUND
    assert spec.headline_position is HeadlinePosition.CENTER
    assert spec.headline_scale is HeadlineScale.LARGE
    assert spec.overlay is Overlay.DARK
    assert spec.logo_position is LogoPosition.TOP_LEFT
    assert spec.cta_style is CtaStyle.SOLID
    assert spec.alignment is Alignment.CENTER
    # ``format`` is a data-driven registry code, not a visual enum.
    assert spec.format == "FEED_POST"


def test_layout_spec_persisted_identity_fields_default_none() -> None:
    spec = LayoutSpec(
        primitive=LayoutPrimitive.SPLIT,
        image_position=ImagePosition.LEFT,
        headline_position=HeadlinePosition.TOP,
        headline_scale=HeadlineScale.MEDIUM,
        overlay=Overlay.NONE,
        logo_position=LogoPosition.TOP_RIGHT,
        cta_style=CtaStyle.OUTLINE,
        alignment=Alignment.LEFT,
        format="STORY_POST",
    )
    assert spec.id is None
    assert spec.content_piece_id is None
    assert spec.validation_status is None


def test_layout_spec_persisted_identity_fields_hold_values() -> None:
    spec = LayoutSpec(
        primitive=LayoutPrimitive.SPLIT,
        image_position=ImagePosition.LEFT,
        headline_position=HeadlinePosition.TOP,
        headline_scale=HeadlineScale.MEDIUM,
        overlay=Overlay.NONE,
        logo_position=LogoPosition.TOP_RIGHT,
        cta_style=CtaStyle.OUTLINE,
        alignment=Alignment.LEFT,
        format="STORY_POST",
        id="ls-1",
        content_piece_id="piece-1",
        validation_status="VALID",
    )
    assert spec.id == "ls-1"
    assert spec.content_piece_id == "piece-1"
    assert spec.validation_status == "VALID"


def test_campaign_visual_system_constructs_and_coerces_style() -> None:
    system = CampaignVisualSystem(
        id="vs1",
        campaign_id="c1",
        primary_layout_family=LayoutPrimitive.HERO,
        headline_scale=HeadlineScale.LARGE,
        image_treatment="border",
        logo_rule="show",
        cta_rule="solid",
        alignment=Alignment.CENTER,
        created_at=datetime(2026, 9, 2, tzinfo=UTC),
        style=["clean"],
    )

    assert isinstance(system.style, tuple)
    assert system.style == ("clean",)
