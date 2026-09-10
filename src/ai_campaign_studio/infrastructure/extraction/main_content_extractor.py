"""Main-content extractor (S2-G4).

Owns reducing one fetched HTML document to its boilerplate-stripped main text
via Trafilatura (Q12 spike winner — see ``spikes/extraction-benchmark/chosen.md``).
Returns a plain ``str`` of the main content (S2-G4 contract §1); the S2-G6
pipeline adapts it to ``ContentExtractionResult`` when it materialises chunks.
Does NOT own URL fetching (S2-G3), persistence (G6 registers chunks through
``IngestionRepositoryPort``) or ``FactCandidate`` building.

Graceful fallback: if Trafilatura is unavailable, fails, or returns empty, this
falls back to the raw visible text (stdlib ``html.parser`` tag-strip) and logs
a warning — it never raises on a bad/odd page, because the G6 orchestration
must not crash on one extractor miss.
"""

from __future__ import annotations

import logging
import re
from html.parser import HTMLParser

logger = logging.getLogger(__name__)

_WHITESPACE_RE = re.compile(r"\s+")
_TAG_RE = re.compile(r"<[^>]*>")

_SKIP_TAGS = frozenset({"script", "style", "noscript", "iframe", "svg"})


def _collapse_whitespace(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip()


class _HTMLTextExtractor(HTMLParser):
    """Collect visible text from HTML, ignoring script/style/etc. blocks."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: object) -> None:
        if tag.lower() in _SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._parts.append(data)

    def get_text(self) -> str:
        return " ".join(self._parts)


class MainContentExtractor:
    """Extract main article text from one HTML document via Trafilatura."""

    def extract(self, html: str, base_url: str = "") -> str:
        """Return the boilerplate-stripped main text (never raises).

        Falls back to raw visible text (with a logged warning) when
        Trafilatura cannot produce non-empty text.
        """
        text = self._extract_with_trafilatura(html, base_url)
        if text:
            return text
        logger.warning("extraction_fallback_raw_text url=%s", base_url)
        return self._raw_text_fallback(html)

    def _extract_with_trafilatura(self, html: str, base_url: str) -> str:
        try:
            from trafilatura import (  # type: ignore[import-not-found,import-untyped]
                bare_extraction,
            )
        except ImportError as exc:
            logger.warning("trafilatura_not_installed: %s", exc)
            return ""
        try:
            result = bare_extraction(
                html,
                url=base_url or None,
                include_comments=False,
                include_tables=False,
                favor_precision=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("trafilatura_extraction_failed: %s", exc)
            return ""
        if result is None:
            return ""
        return (getattr(result, "text", "") or "").strip()

    def _raw_text_fallback(self, html: str) -> str:
        if not html or not html.strip():
            return ""
        extractor = _HTMLTextExtractor()
        try:
            extractor.feed(html)
            extractor.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning("raw_text_fallback_parse_failed: %s", exc)
            return _collapse_whitespace(_TAG_RE.sub(" ", html))
        return _collapse_whitespace(extractor.get_text())


__all__ = ["MainContentExtractor"]
