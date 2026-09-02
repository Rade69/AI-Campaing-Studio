"""Visual slot contracts (A3)."""

from dataclasses import dataclass

from ai_campaign_studio.domain.visual.enums import (
    Alignment,
    CaseStyle,
    OverflowPolicy,
    SlotName,
)


@dataclass(frozen=True)
class BoundingBox:
    """A raster bounding box in integer pixel coordinates."""

    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class ContentSlotContract:
    """Typed raster constraints for a single named slot.

    Slice 1 defines only ``headline`` and ``cta``; caption is not part of the
    first renderer's raster layout and is deliberately absent.
    """

    slot_name: SlotName
    target_chars: int
    max_chars: int
    max_lines: int
    preferred_case: CaseStyle
    allow_wrap: bool
    font_family: str
    min_font_size: float
    max_font_size: float
    bounding_box: BoundingBox
    line_height: float
    alignment: Alignment
    overflow_policy: OverflowPolicy
