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


class ImagePosition(StrEnum):
    """Where the image sits within a layout primitive."""

    LEFT = "LEFT"
    RIGHT = "RIGHT"
    TOP = "TOP"
    BOTTOM = "BOTTOM"
    BACKGROUND = "BACKGROUND"
    NONE = "NONE"


class HeadlinePosition(StrEnum):
    """Where the headline sits within a layout primitive."""

    TOP = "TOP"
    CENTER = "CENTER"
    BOTTOM = "BOTTOM"


class HeadlineScale(StrEnum):
    """Relative headline size."""

    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    LARGE = "LARGE"


class Overlay(StrEnum):
    """Overlay treatment over the image."""

    NONE = "NONE"
    DARK = "DARK"
    LIGHT = "LIGHT"
    GRADIENT = "GRADIENT"


class LogoPosition(StrEnum):
    """Where the logo sits within a layout primitive."""

    TOP_LEFT = "TOP_LEFT"
    TOP_RIGHT = "TOP_RIGHT"
    BOTTOM_LEFT = "BOTTOM_LEFT"
    BOTTOM_RIGHT = "BOTTOM_RIGHT"
    CENTER = "CENTER"


class CtaStyle(StrEnum):
    """Visual style of the CTA element."""

    SOLID = "SOLID"
    OUTLINE = "OUTLINE"
    TEXT = "TEXT"


class ImageTreatment(StrEnum):
    """Visual treatment applied to the image."""

    NONE = "NONE"
    BORDER = "BORDER"
    SHADOW = "SHADOW"
    ROUNDED = "ROUNDED"


class LogoRule(StrEnum):
    """Whether the logo is shown."""

    SHOW = "SHOW"
    HIDE = "HIDE"


class CtaRule(StrEnum):
    """Whether the CTA element is shown."""

    SHOW = "SHOW"
    HIDE = "HIDE"
