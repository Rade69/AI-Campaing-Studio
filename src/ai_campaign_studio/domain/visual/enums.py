"""Visual domain enums (A3).

``LayoutPrimitive`` is the only primitive explicitly required for Slice 1;
the remaining enums type the ``ContentSlotContract`` fields so that layout
values are validated value objects, not arbitrary LLM strings.
"""

from enum import StrEnum


class LayoutPrimitive(StrEnum):
    """A raster layout primitive.

    Only ``HERO`` and ``SPLIT`` are implemented for Slice 1, but this enum is
    not closed in a way that blocks adding ``FAQ``/``QUOTE``/``PRODUCT``/
    ``CTA``/``STAT``/``COMPARISON``/``TESTIMONIAL``/``FEATURE`` later.
    """

    HERO = "HERO"
    SPLIT = "SPLIT"


class SlotName(StrEnum):
    """The named raster slots available in Slice 1."""

    HEADLINE = "HEADLINE"
    CTA = "CTA"


class CaseStyle(StrEnum):
    """Preferred text casing for a slot."""

    UPPER = "UPPER"
    TITLE = "TITLE"
    SENTENCE = "SENTENCE"
    NONE = "NONE"


class Alignment(StrEnum):
    """Horizontal alignment for a slot."""

    LEFT = "LEFT"
    CENTER = "CENTER"
    RIGHT = "RIGHT"


class OverflowPolicy(StrEnum):
    """How to handle text that overflows a slot."""

    CLIP = "CLIP"
    ELLIPSIS = "ELLIPSIS"
    SHRINK = "SHRINK"
