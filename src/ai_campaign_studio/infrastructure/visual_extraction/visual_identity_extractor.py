"""Visual identity extractor (S2-G5).

Owns turning HTML + base_url into the existing ``VisualIdentity`` VO using
cheap signals only (canonical plan §10 S2-G5): logo = og:image → twitter:image
→ favicon; primary colors = hex colors found in CSS custom properties; font
families = ``font-family`` declarations. No image analysis (no Pillow/color
clustering). An empty HTML document returns a default ``VisualIdentity`` (no
raise) with a logged warning.
"""

from __future__ import annotations

import logging
import re

from ai_campaign_studio.domain.brand.value_objects import VisualIdentity
from ai_campaign_studio.infrastructure.visual_extraction._html_parser import (
    HtmlSignals,
    parse_html,
)
from ai_campaign_studio.infrastructure.visual_extraction.asset_extractor import (
    AssetExtractor,
)

logger = logging.getLogger(__name__)

_CUSTOM_PROPERTY_RE = re.compile(r"--([\w-]+)\s*:\s*([^;}]+)")
_HEX_COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}")
_FONT_FAMILY_RE = re.compile(r"font-family\s*:\s*([^;}]+)")
_GENERIC_FONTS = frozenset(
    {
        "serif",
        "sans-serif",
        "monospace",
        "cursive",
        "fantasy",
        "system-ui",
        "ui-sans-serif",
        "ui-serif",
        "ui-monospace",
        "ui-rounded",
        "emoji",
        "math",
        "fangsong",
        "inherit",
        "initial",
        "unset",
        "revert",
    }
)


def _css_sources(signals: HtmlSignals) -> list[str]:
    return [*signals.style_blocks, *signals.inline_styles]


def _extract_primary_colors(signals: HtmlSignals) -> tuple[str, ...]:
    colors: list[str] = []
    seen: set[str] = set()
    for source in _css_sources(signals):
        for _name, value in _CUSTOM_PROPERTY_RE.findall(source):
            for match in _HEX_COLOR_RE.findall(value):
                normalized = match.lower()
                if normalized not in seen:
                    seen.add(normalized)
                    colors.append(normalized)
    return tuple(colors)


def _extract_font_families(signals: HtmlSignals) -> tuple[str, ...]:
    fonts: list[str] = []
    seen: set[str] = set()
    for source in _css_sources(signals):
        for declaration in _FONT_FAMILY_RE.findall(source):
            for part in declaration.split(","):
                family = part.strip().strip("\"'")
                normalized = family.lower()
                if family and normalized not in _GENERIC_FONTS and family not in seen:
                    seen.add(family)
                    fonts.append(family)
    return tuple(fonts)


class VisualIdentityExtractor:
    """Build ``VisualIdentity`` from HTML via cheap signals."""

    def __init__(self, assets: AssetExtractor | None = None) -> None:
        self._assets = assets if assets is not None else AssetExtractor()

    def extract(self, html: str, base_url: str) -> VisualIdentity:
        signals = parse_html(html)
        assets = self._assets.extract(html, base_url)

        logo = (
            assets.get("og_image")
            or assets.get("twitter_image")
            or assets.get("favicon")
        )
        primary_colors = _extract_primary_colors(signals)
        font_families = _extract_font_families(signals)

        identity = VisualIdentity(
            logo_path=logo,
            primary_colors=primary_colors,
            secondary_colors=(),
            font_families=font_families,
            image_style_notes=(),
        )

        if not logo and not primary_colors and not font_families:
            logger.warning("visual_identity_no_signals base_url=%s", base_url)

        return identity


__all__ = ["VisualIdentityExtractor"]
