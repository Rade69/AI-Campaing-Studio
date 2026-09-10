"""Asset extractor (S2-G5).

Owns extracting brand asset URLs/titles from HTML with stdlib only:
``favicon`` (``<link rel="icon">`` → ``shortcut icon`` → ``/favicon.ico``),
``og_image``/``og_title``/``og_description`` (OpenGraph meta), and
``twitter_image``/``twitter_card`` (Twitter meta). All asset URLs are resolved
against the ``<base href>`` tag when present (HTML5), else the caller's
``base_url``, and ONLY http/https URLs are kept (``javascript:``/``data:``/
``file:`` are dropped). Does not interpret the assets (logo/color policy is
``visual_identity_extractor``'s job).
"""

from __future__ import annotations

from urllib.parse import urljoin, urlsplit

from ai_campaign_studio.infrastructure.visual_extraction._html_parser import (
    HtmlSignals,
    parse_html,
)

_ALLOWED_SCHEMES = frozenset({"http", "https"})
_BLOCKED_SCHEMES = ("javascript:", "data:", "vbscript:", "file:")


def _safe_url(raw: str, base: str) -> str | None:
    """Resolve ``raw`` against ``base`` and keep only http/https results."""
    value = raw.strip()
    if not value:
        return None
    low = value.lower()
    if any(low.startswith(scheme) for scheme in _BLOCKED_SCHEMES):
        return None
    if any(ch in value for ch in "\x00\n\r\t<>\"'"):
        return None
    try:
        joined = urljoin(base, value)
    except ValueError:
        return None
    if urlsplit(joined).scheme.lower() not in _ALLOWED_SCHEMES:
        return None
    return joined


def _effective_base(signals: HtmlSignals, base_url: str) -> str:
    if signals.base_href:
        try:
            return urljoin(base_url, signals.base_href)
        except ValueError:
            return base_url
    return base_url


def _pick_icon(icon_links: list[tuple[str, str]]) -> str | None:
    """Choose the best favicon href: exact ``icon``, then ``shortcut icon``,
    then any rel containing ``icon``."""
    for rel, href in icon_links:
        if rel == "icon":
            return href
    for rel, href in icon_links:
        if rel == "shortcut icon":
            return href
    for rel, href in icon_links:
        if "icon" in rel.split():
            return href
    return None


class AssetExtractor:
    """Extract brand asset signals from one HTML document."""

    def extract(self, html: str, base_url: str) -> dict[str, str]:
        signals = parse_html(html)
        effective_base = _effective_base(signals, base_url)
        assets: dict[str, str] = {}

        icon = _pick_icon(signals.icon_links)
        resolved_icon = _safe_url(icon, effective_base) if icon else None
        if resolved_icon:
            assets["favicon"] = resolved_icon
        elif html.strip():
            fallback = _safe_url("/favicon.ico", effective_base)
            if fallback:
                assets["favicon"] = fallback

        og = signals.og
        for key, meta_key in (
            ("og_image", "og:image"),
            ("og_title", "og:title"),
            ("og_description", "og:description"),
        ):
            value = og.get(meta_key)
            if not value:
                continue
            if key == "og_image":
                resolved = _safe_url(value, effective_base)
                if resolved:
                    assets[key] = resolved
            else:
                assets[key] = value.strip()

        twitter = signals.twitter
        if twitter.get("twitter:image"):
            resolved = _safe_url(twitter["twitter:image"], effective_base)
            if resolved:
                assets["twitter_image"] = resolved
        if twitter.get("twitter:card"):
            assets["twitter_card"] = twitter["twitter:card"].strip()

        return assets


__all__ = ["AssetExtractor"]
