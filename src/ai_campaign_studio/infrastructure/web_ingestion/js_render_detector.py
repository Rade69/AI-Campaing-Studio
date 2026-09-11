"""JavaScript-render detector (S2-G8).

Owns the deterministic heuristic that decides whether an HTTP-fetched page is
JS-heavy (client-rendered SPA or SSR shell) and therefore needs the Playwright
fallback. Input is the HTTP fetch response shape (content_type + body
preview); output is ``(is_js_heavy, reason)``. Pure string/regex heuristics
on the first bytes of the body — NEVER an LLM, NEVER a network call, NEVER a
deep HTML parse (that belongs to the G4 extractors). The 2+-marker confidence
threshold is the canonical plan §8 trade-off: false positives cost ~1-2s of
subprocess IPC, false negatives cost empty extraction.
"""

from __future__ import annotations

import re

# A marker name is the stable, sortable key of one JS-heavy signal; the order
# below is the order markers are joined into the reason string.
_SPA_ROOT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("react_root", re.compile(r"<div\s+id=[\"']root[\"']", re.IGNORECASE)),
    ("vue_root", re.compile(r"<div\s+id=[\"']app[\"']", re.IGNORECASE)),
    ("angular_root", re.compile(r"<app-root[\s>]", re.IGNORECASE)),
)
_FRAMEWORK_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("next_data", re.compile(r"__NEXT_DATA__")),
    ("nuxt", re.compile(r"__NUXT__")),
    ("initial_state", re.compile(r"window\.__INITIAL_STATE__")),
)
_OTHER_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("module", re.compile(r"<script\s+[^>]*type=[\"']module[\"']", re.IGNORECASE)),
    (
        "modulepreload",
        re.compile(r"<link\s+[^>]*rel=[\"']modulepreload[\"']", re.IGNORECASE),
    ),
    ("noscript", re.compile(r"<noscript\b", re.IGNORECASE)),
)

# ``noscript`` counts only when combined with a ``<script>`` (graceful
# degradation pattern), per canonical plan §8.
_SCRIPT_TAG = re.compile(r"<script\b", re.IGNORECASE)
_HEAD_OPEN = re.compile(r"<head\b", re.IGNORECASE)
_BODY_OPEN = re.compile(r"<body\b[^>]*>", re.IGNORECASE)
_BODY_CLOSE = re.compile(r"</body\s*>", re.IGNORECASE)

_EMPTY_BODY_CHAR_LIMIT = 100
_PREVIEW_LIMIT = 50_000  # heuristic runs on the first 50 KB only


def _looks_like_html(content_type: str | None) -> bool:
    """True when the content type is (potentially) HTML; ``None`` → assume HTML."""
    if content_type is None:
        return True
    ctype = content_type.split(";", 1)[0].strip().lower()
    return ctype in {"text/html", "application/xhtml+xml"}


def _detect_markers(body_preview: str) -> tuple[str, ...]:
    found: list[str] = []
    for name, pattern in _SPA_ROOT_PATTERNS + _FRAMEWORK_PATTERNS + _OTHER_PATTERNS:
        if pattern.search(body_preview):
            # ``noscript`` is only a marker together with a ``<script>`` tag.
            if name == "noscript" and not _SCRIPT_TAG.search(body_preview):
                continue
            found.append(name)
    return tuple(found)


def _is_empty_body_shell(body_preview: str) -> bool:
    """True when the HTML is a real document (has ``<head>``) with a
    ``<body>`` that is almost empty — content injected by JavaScript
    (canonical plan §8). Requires ``<head>`` so a bare fragment like
    ``<p>Hello world</p>`` is NOT misjudged as an empty SPA shell."""
    if _HEAD_OPEN.search(body_preview) is None:
        return False
    match = _BODY_OPEN.search(body_preview)
    if match is None:
        return False
    after_open = body_preview[match.end() :]
    close = _BODY_CLOSE.search(after_open)
    tail = after_open[: close.start()] if close else after_open
    return len(tail.strip()) < _EMPTY_BODY_CHAR_LIMIT


def _preview(body: str) -> str:
    return body[:_PREVIEW_LIMIT]


def detect_js_heavy(content_type: str | None, body_preview: str) -> tuple[bool, str]:
    """Classify one HTTP fetch response as JS-heavy or not.

    Returns ``(is_js_heavy, reason)``. Reasons: ``not_html`` (non-HTML content
    type — HTTP-only is enough), ``js_heavy_empty_body``,
    ``js_heavy_<marker>+<marker>`` (2+ markers), ``weak_signal_<marker>``
    (exactly 1 marker — do NOT activate the fallback) and ``no_js_markers``.
    """
    if not _looks_like_html(content_type):
        return False, "not_html"

    preview = _preview(body_preview)
    markers = _detect_markers(preview)

    if _is_empty_body_shell(preview):
        if markers:
            return True, "js_heavy_empty_body+" + "+".join(markers)
        return True, "js_heavy_empty_body"

    if len(markers) >= 2:
        return True, "js_heavy_" + "+".join(markers)
    if len(markers) == 1:
        return False, "weak_signal_" + markers[0]
    return False, "no_js_markers"


def has_spa_shell(body_preview: str) -> bool:
    """True when the body carries a client-rendered SPA root marker
    (React/Vue/Angular root, ``__NEXT_DATA__``, ``__NUXT__`` or
    ``__INITIAL_STATE__``). Used by ``page_classifier`` to avoid treating a
    client-routed SPA URL as a real blog/article page."""
    preview = _preview(body_preview)
    for _name, pattern in _SPA_ROOT_PATTERNS + _FRAMEWORK_PATTERNS:
        if pattern.search(preview):
            return True
    return False


__all__ = [
    "detect_js_heavy",
    "has_spa_shell",
]
