"""Deterministic URL classifier (S2-G6, fills the S2-G1 port gap).

Owns URL-ONLY page classification (canonical plan §8): path segments and the
query-free basename, matched against an EN + BHS_LATIN segment vocabulary
(``/about``, ``/o-nama``, ``/kontakt``, ``/vijesti`` ...). Implements the
existing S2-G1 ``UrlClassifierPort`` — no new port. NEVER uses an LLM and
NEVER fetches content; content signals (title/H1/breadcrumb/schema.org)
belong to a future content-refinement pass, not this port.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from ai_campaign_studio.domain.ingestion.enums import PageType

# BHS diacritics transliterated to ASCII so a URL may use either spelling.
_TRANSLITERATION: tuple[tuple[str, str], ...] = (
    ("č", "c"),
    ("ć", "c"),
    ("š", "s"),
    ("ž", "z"),
    ("đ", "dj"),
)

# Ordered most-specific-first; the first key that matches a path segment wins.
_PATTERNS: tuple[tuple[str, PageType], ...] = (
    # legal / policy
    ("privacy", PageType.LEGAL),
    ("privatnost", PageType.LEGAL),
    ("politika-privatnosti", PageType.LEGAL),
    ("gdpr", PageType.LEGAL),
    ("cookies", PageType.LEGAL),
    ("kolacici", PageType.LEGAL),
    ("terms", PageType.LEGAL),
    ("uslovi", PageType.LEGAL),
    ("pravila", PageType.LEGAL),
    ("impresum", PageType.LEGAL),
    ("impressum", PageType.LEGAL),
    ("imprint", PageType.LEGAL),
    ("legal", PageType.LEGAL),
    # FAQ
    ("faq", PageType.FAQ),
    ("cesta-pitanja", PageType.FAQ),
    ("cestapitanja", PageType.FAQ),
    ("ucestala-pitanja", PageType.FAQ),
    ("pitanja", PageType.FAQ),
    ("pomoc", PageType.FAQ),
    ("help", PageType.FAQ),
    # shipping / returns
    ("shipping", PageType.SHIPPING),
    ("dostava", PageType.SHIPPING),
    ("isporuka", PageType.SHIPPING),
    ("slanje", PageType.SHIPPING),
    ("returns", PageType.RETURNS),
    ("povrat", PageType.RETURNS),
    ("reklamacije", PageType.RETURNS),
    ("reklamacija", PageType.RETURNS),
    ("zamjena", PageType.RETURNS),
    ("zamena", PageType.RETURNS),
    # pricing
    ("pricing", PageType.PRICING),
    ("cenovnik", PageType.PRICING),
    ("cjenovnik", PageType.PRICING),
    ("cijene", PageType.PRICING),
    ("cene", PageType.PRICING),
    ("prices", PageType.PRICING),
    ("paketi", PageType.PRICING),
    # contact
    ("contact", PageType.CONTACT),
    ("kontakt", PageType.CONTACT),
    # about
    ("about", PageType.ABOUT),
    ("o-nama", PageType.ABOUT),
    ("onama", PageType.ABOUT),
    ("o_nama", PageType.ABOUT),
    # blog / article
    ("blog", PageType.BLOG),
    ("vijesti", PageType.BLOG),
    ("vesti", PageType.BLOG),
    ("novosti", PageType.BLOG),
    ("aktuelno", PageType.BLOG),
    ("news", PageType.BLOG),
    ("article", PageType.ARTICLE),
    ("clanak", PageType.ARTICLE),
    # service / product / category
    ("services", PageType.SERVICE),
    ("service", PageType.SERVICE),
    ("usluge", PageType.SERVICE),
    ("usluga", PageType.SERVICE),
    ("servis", PageType.SERVICE),
    ("products", PageType.PRODUCT),
    ("product", PageType.PRODUCT),
    ("proizvodi", PageType.PRODUCT),
    ("proizvod", PageType.PRODUCT),
    ("artikli", PageType.PRODUCT),
    ("artikal", PageType.PRODUCT),
    ("prodavnica", PageType.PRODUCT),
    ("shop", PageType.PRODUCT),
    ("kategorije", PageType.CATEGORY),
    ("kategorija", PageType.CATEGORY),
    ("categories", PageType.CATEGORY),
    ("category", PageType.CATEGORY),
    ("kolekcija", PageType.CATEGORY),
    ("collection", PageType.CATEGORY),
    ("katalog", PageType.CATEGORY),
    # home
    ("pocetna", PageType.HOME),
    ("naslovna", PageType.HOME),
    ("home", PageType.HOME),
)

# Pages with no path (root) are HOME regardless of the vocabulary above.
_ARTICLE_EXTENSIONS = (".html", ".htm", ".php", ".asp", ".aspx")


def _fold(text: str) -> str:
    lowered = text.lower()
    for source, target in _TRANSLITERATION:
        lowered = lowered.replace(source, target)
    return lowered


def _match_segment(segment: str) -> PageType | None:
    folded = _fold(segment)
    # Drop a trailing file extension so /o-nama.html still matches "o-nama".
    for extension in _ARTICLE_EXTENSIONS:
        if folded.endswith(extension):
            folded = folded[: -len(extension)]
            break
    for key, page_type in _PATTERNS:
        if _segment_matches_key(folded, key):
            return page_type
    return None


def _segment_matches_key(segment: str, key: str) -> bool:
    """True when ``key`` occurs in ``segment`` on an alphanumeric boundary."""
    start = 0
    while True:
        index = segment.find(key, start)
        if index == -1:
            return False
        before_ok = index == 0 or not segment[index - 1].isalnum()
        end = index + len(key)
        after_ok = end == len(segment) or not segment[end].isalnum()
        if before_ok and after_ok:
            return True
        start = index + 1


class UrlClassifier:
    """``UrlClassifierPort`` implementation — deterministic URL-only bucketing."""

    def classify(self, url: str) -> PageType:
        try:
            path = urlsplit(url).path
        except ValueError:
            return PageType.OTHER
        segments = [segment for segment in path.split("/") if segment]
        if not segments:
            return PageType.HOME
        # Basename first (most specific), then outer segments.
        for segment in reversed(segments):
            page_type = _match_segment(segment)
            if page_type is not None:
                return page_type
        return PageType.OTHER


__all__ = ["UrlClassifier"]
