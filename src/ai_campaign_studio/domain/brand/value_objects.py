"""Brand domain value objects (A3).

Owns the small immutable value objects that describe a brand's voice, target
audiences, services, restrictions and visual identity. Plain frozen
dataclasses with ``tuple`` collections (never ``list``); no Pydantic and no
business policies live here.
"""

from __future__ import annotations

from dataclasses import dataclass


def _coerce_to_tuple(obj: object, *field_names: str) -> None:
    """Replace each named field with a ``tuple`` (runtime immutability).

    ``list`` inputs are coerced to ``tuple`` so a frozen dataclass can never
    hold a mutable collection (ACS-P0-004/005 lesson).
    """
    for name in field_names:
        object.__setattr__(obj, name, tuple(getattr(obj, name)))


@dataclass(frozen=True)
class BrandVoice:
    """Voice/tone rules for generated copy."""

    formality: str
    tone: tuple[str, ...] = ()
    preferred_terms: tuple[str, ...] = ()
    forbidden_terms: tuple[str, ...] = ()
    regional_vocabulary: tuple[str, ...] = ()
    tone_examples: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _coerce_to_tuple(
            self,
            "tone",
            "preferred_terms",
            "forbidden_terms",
            "regional_vocabulary",
            "tone_examples",
        )


@dataclass(frozen=True)
class Audience:
    """A target audience segment."""

    id: str
    name: str
    description: str
    needs: tuple[str, ...] = ()
    objections: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _coerce_to_tuple(self, "needs", "objections")


@dataclass(frozen=True)
class ServiceDefinition:
    """A single service the brand offers."""

    id: str
    name: str
    description: str


@dataclass(frozen=True)
class Restriction:
    """A single content restriction for the brand.

    Minimal A3 shape: the full schema (category/severity/scope) is defined
    with the A4 fixture boundary schema, not guessed here.
    """

    description: str


@dataclass(frozen=True)
class VisualIdentity:
    """Visual identity rules for the brand."""

    logo_path: str | None = None
    primary_colors: tuple[str, ...] = ()
    secondary_colors: tuple[str, ...] = ()
    font_families: tuple[str, ...] = ()
    image_style_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _coerce_to_tuple(
            self,
            "primary_colors",
            "secondary_colors",
            "font_families",
            "image_style_notes",
        )
