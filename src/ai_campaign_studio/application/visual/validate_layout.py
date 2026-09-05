"""Headline-fit layout validation (A13, plan section 41).

Owns a pure, deterministic, I/O-free check that a generated headline fits its
layout primitive. Slice-1 only checks the headline slot; the CTA slot is out of
scope (plan gives no CTA numeric defaults). Values are initial test parameters,
not a render-calibrated conclusion.
"""

from __future__ import annotations

from dataclasses import dataclass

from ai_campaign_studio.domain.visual.enums import LayoutPrimitive
from ai_campaign_studio.domain.visual.layout import LayoutSpec


@dataclass(frozen=True)
class _HeadlineLimits:
    target_chars: tuple[int, int]
    max_chars: int
    max_lines: int
    min_font_size: float
    max_font_size: float


_HERO_HEADLINE = _HeadlineLimits((28, 42), 55, 2, 48.0, 72.0)
_SPLIT_HEADLINE = _HeadlineLimits((24, 38), 48, 3, 42.0, 64.0)


def validate_layout(
    layout: LayoutSpec, headline_text: str
) -> tuple[bool, tuple[str, ...]]:
    """Slice-1 headline-only fit check (plan section 41).

    CTA slot check is NOT in scope. Values here are initial test parameters
    (per plan section 41: "Ovo nisu trajne dizajnerske istine"), not a final
    render-calibrated conclusion.
    """
    if layout.primitive is LayoutPrimitive.HERO:
        limits = _HERO_HEADLINE
    elif layout.primitive is LayoutPrimitive.SPLIT:
        limits = _SPLIT_HEADLINE
    else:
        return (True, ())

    if len(headline_text) > limits.max_chars:
        return (
            False,
            (
                f"{layout.primitive.value} headline is {len(headline_text)} "
                f"chars, over max {limits.max_chars}",
            ),
        )
    return (True, ())
