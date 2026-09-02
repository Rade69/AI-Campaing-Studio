"""Visual layout specification (A3)."""

from __future__ import annotations

from dataclasses import dataclass

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


@dataclass(frozen=True)
class LayoutSpec:
    """A typed raster layout specification.

    Every field is an enum (not a free string), so an arbitrary LLM output
    cannot produce an untested layout value.
    """

    primitive: LayoutPrimitive
    image_position: ImagePosition
    headline_position: HeadlinePosition
    headline_scale: HeadlineScale
    overlay: Overlay
    logo_position: LogoPosition
    cta_style: CtaStyle
    alignment: Alignment
    format: str
