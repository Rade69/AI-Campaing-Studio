"""Unit tests for validate_layout (A13, plan section 41)."""

from __future__ import annotations

from ai_campaign_studio.application.visual.validate_layout import validate_layout
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


def _layout(primitive: LayoutPrimitive) -> LayoutSpec:
    return LayoutSpec(
        primitive=primitive,
        image_position=ImagePosition.BACKGROUND,
        headline_position=HeadlinePosition.CENTER,
        headline_scale=HeadlineScale.LARGE,
        overlay=Overlay.NONE,
        logo_position=LogoPosition.TOP_LEFT,
        cta_style=CtaStyle.SOLID,
        alignment=Alignment.CENTER,
        format="1080x1350",
    )


def test_hero_within_limit() -> None:
    assert validate_layout(_layout(LayoutPrimitive.HERO), "x" * 55) == (True, ())


def test_hero_over_limit() -> None:
    is_valid, reasons = validate_layout(_layout(LayoutPrimitive.HERO), "x" * 56)
    assert is_valid is False
    assert len(reasons) == 1
    assert "HERO" in reasons[0]
    assert "56" in reasons[0]


def test_split_within_limit() -> None:
    assert validate_layout(_layout(LayoutPrimitive.SPLIT), "x" * 48) == (True, ())


def test_split_over_limit() -> None:
    is_valid, reasons = validate_layout(_layout(LayoutPrimitive.SPLIT), "x" * 49)
    assert is_valid is False
    assert "SPLIT" in reasons[0]


def test_boundary_exactly_max_chars_is_valid() -> None:
    assert validate_layout(_layout(LayoutPrimitive.HERO), "x" * 55) == (True, ())
    assert validate_layout(_layout(LayoutPrimitive.SPLIT), "x" * 48) == (True, ())
