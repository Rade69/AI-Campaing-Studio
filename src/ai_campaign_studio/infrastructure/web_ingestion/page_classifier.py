"""Content-aware page classifier (S2-G8, canonical plan §8).

Owns page classification from URL path PLUS cheap content signals
(content-type header + the JS-render markers already computed by
``js_render_detector``). Signal priority: (1) URL path via the existing
``UrlClassifier`` (reused, not duplicated), (2) content-type header, (3) SPA
shell markers. A client-rendered SPA URL is NEVER classified as a real
blog/article page — its "blog" path is a client route, so it collapses to
HOME. NEVER an LLM, NEVER a deep HTML parse (scope guard, canonical plan §8);
``content_type`` is accepted for signature compatibility and the one
non-HTML refinement below.
"""

from __future__ import annotations

from ai_campaign_studio.domain.ingestion.enums import PageType
from ai_campaign_studio.infrastructure.web_ingestion.js_render_detector import (
    has_spa_shell,
)
from ai_campaign_studio.infrastructure.web_ingestion.url_classifier import (
    UrlClassifier,
)

# Content types that are NOT an HTML page even when the URL path says "blog".
_NON_HTML_MIME_PREFIXES = (
    "application/json",
    "application/xml",
    "image/",
    "text/plain",
)


def _is_html_content(content_type: str | None) -> bool:
    if content_type is None:
        return True
    ctype = content_type.split(";", 1)[0].strip().lower()
    return not ctype.startswith(_NON_HTML_MIME_PREFIXES)


class PageClassifier:
    """Classify a fetched page from URL + content signals.

    Reuses ``UrlClassifier`` for the URL-path signal (the S2-G6 URL-only
    classifier) and overlays the SPA-shell rule from ``js_render_detector``.
    """

    def __init__(self, url_classifier: UrlClassifier | None = None) -> None:
        self._url_classifier = url_classifier or UrlClassifier()

    def classify(
        self, url: str, content_type: str | None, body_preview: str
    ) -> PageType:
        page_type = self._url_classifier.classify(url)

        # A non-HTML payload cannot be a blog/article page, regardless of URL.
        if page_type in (PageType.BLOG, PageType.ARTICLE) and not _is_html_content(
            content_type
        ):
            return PageType.OTHER

        # A client-rendered SPA page is a single app shell: a "/blog/x" path
        # is a client route, not a real blog post (canonical plan §8).
        if page_type in (PageType.BLOG, PageType.ARTICLE) and has_spa_shell(
            body_preview
        ):
            return PageType.HOME

        return page_type


__all__ = ["PageClassifier"]
