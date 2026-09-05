"""Visual layout specification (A3)."""

from __future__ import annotations

from dataclasses import dataclass

from ai_campaign_studio.domain.common.ids import LayoutSpecId, PostId
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
    cannot produce an untested layout value. ``id``/``content_piece_id``/
    ``validation_status`` are ``None`` for an in-memory (not-yet-persisted)
    layout (ACS-F1-029 style) and populated for a persisted layout (A13 dio 2b).
    ``validation_status`` is a plain ``str`` (NOT an enum) on purpose for
    Slice 1: ``"VALID"``/``"INVALID"`` are a documented convention, and the
    future ``plan_post_layout.py`` decides the real values.
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
    id: LayoutSpecId | None = None
    content_piece_id: PostId | None = None
    validation_status: str | None = None
