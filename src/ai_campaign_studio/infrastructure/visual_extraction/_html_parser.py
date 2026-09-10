"""HTML signal parser (S2-G5).

Owns parsing an HTML string ONCE into the small, stdlib-only ``HtmlSignals``
shape that both ``asset_extractor`` and ``visual_identity_extractor`` consume:
``<base href>`` (first one wins, HTML5), ``<link rel=icon>`` targets, ``og:``/
``twitter:`` meta content, ``<style>`` text and inline ``style=`` attributes.
Does NOT resolve URLs, sanitize them, or make any visual-identity decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser


@dataclass
class HtmlSignals:
    """Raw signals extracted from one HTML document."""

    base_href: str | None = None
    icon_links: list[tuple[str, str]] = field(default_factory=list)  # (rel, href)
    og: dict[str, str] = field(default_factory=dict)  # property -> content
    twitter: dict[str, str] = field(default_factory=dict)  # name -> content
    style_blocks: list[str] = field(default_factory=list)
    inline_styles: list[str] = field(default_factory=list)


class _SignalParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.signals = HtmlSignals()
        self._in_style = False
        self._style_buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k.lower(): (v or "") for k, v in attrs}
        tag = tag.lower()

        if tag == "base" and self.signals.base_href is None:
            href = a.get("href", "").strip()
            if href:
                self.signals.base_href = href
        elif tag == "link":
            rel = a.get("rel", "").strip().lower()
            href = a.get("href", "").strip()
            if rel and href and "icon" in rel.split():
                self.signals.icon_links.append((rel, href))
        elif tag == "meta":
            prop = a.get("property", "").strip().lower()
            name = a.get("name", "").strip().lower()
            content = a.get("content", "")
            if prop.startswith("og:") and content:
                self.signals.og.setdefault(prop, content)
            if name.startswith("twitter:") and content:
                self.signals.twitter.setdefault(name, content)
        elif tag == "style":
            self._in_style = True
            self._style_buf = []

        style = a.get("style", "").strip()
        if style:
            self.signals.inline_styles.append(style)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "style" and self._in_style:
            self.signals.style_blocks.append("".join(self._style_buf))
            self._in_style = False

    def handle_data(self, data: str) -> None:
        if self._in_style:
            self._style_buf.append(data)


def parse_html(html: str) -> HtmlSignals:
    """Parse ``html`` into raw signals (never raises on malformed HTML)."""
    parser = _SignalParser()
    parser.feed(html)
    parser.close()
    return parser.signals


__all__ = ["HtmlSignals", "parse_html"]
