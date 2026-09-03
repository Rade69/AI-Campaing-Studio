"""Shared shell template for pywebview screens.

Every screen renders through :func:`render_shell` which injects the same
sidebar / topbar / content-slot markup. The only screen-specific piece
is the ``body_html`` argument; everything else is DRY-ified here.

The HTML structure mirrors ``docs/gui-v3/screens/*/index.html`` so the
production package and the design reference stay visually aligned.
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from urllib.parse import quote

_ICON_POCETNA = "M3 11.5 12 4l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"
_ICON_BREND = "M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5zM4 5.5v15"
_ICON_KAMPANJE = "M4 6h16M7 3v6m10-6v6M5 9h14v11H5z"
_ICON_KALENDAR = "M5 5h14v15H5zM8 3v4m8-4v4M5 9h14"
_ICON_PODESAVANJA = (
    "M12 15.5A3.5 3.5 0 1 0 12 8a3.5 3.5 0 0 0 0 7.5zM19.4 15a1.7 1.7 0 0 0 .3 1.8"
    "l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0"
    "-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0"
    "-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8"
    " 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1A1.7 1.7 0 0 0 4.6 9"
    "a1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0"
    " 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5"
    " 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0"
    "-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"
)


# Canonical sidebar order is locked by V3_PLAN.md. ``active_key`` selects
# which link renders the ``.active`` class.
SIDEBAR_ITEMS: tuple[tuple[str, str, str, str], ...] = (
    (
        "pocetna",
        "Početna",
        _ICON_POCETNA,
        "../pocetna/index.html",
    ),
    (
        "brend",
        "Brend",
        _ICON_BREND,
        "../brend/index.html",
    ),
    (
        "kampanje",
        "Kampanje",
        _ICON_KAMPANJE,
        "../kampanje/index.html",
    ),
    (
        "kalendar",
        "Kalendar",
        _ICON_KALENDAR,
        "../kalendar/index.html",
    ),
    (
        "podesavanja",
        "Podešavanja",
        _ICON_PODESAVANJA,
        "../podesavanja/index.html",
    ),
)


@dataclass(frozen=True)
class Breadcrumb:
    """A single breadcrumb segment. ``href`` may be ``None`` for the current page."""

    label: str
    href: str | None


def _nav_html(active_key: str) -> str:
    parts: list[str] = []
    for key, label, icon_path, href in SIDEBAR_ITEMS:
        active_cls = "active" if key == active_key else ""
        parts.append(
            f'<a class="{active_cls}" href="{html.escape(href)}">'
            f'<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" '
            f'stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" '
            f'd="{html.escape(icon_path)}"/></svg>'
            f"<span>{html.escape(label)}</span></a>"
        )
    return "\n".join(parts)


def _crumbs_html(crumbs: list[Breadcrumb]) -> str:
    if not crumbs:
        return ""
    parts: list[str] = []
    for i, c in enumerate(crumbs):
        if i > 0:
            parts.append('<span class="sep">/</span>')
        if c.href and i != len(crumbs) - 1:
            parts.append(
                f'<a href="{html.escape(c.href)}">{html.escape(c.label)}</a>'
            )
        else:
            parts.append(f"<b>{html.escape(c.label)}</b>")
    return "".join(parts)


def stepper_html(active_step: int, campaign_name: str) -> str:
    """Render the 5-step campaign workflow stepper.

    Steps before ``active_step`` are ``<a class="step done">`` links,
    the active step is a ``<div class="step active">`` (no link), and
    upcoming steps are plain ``<div class="step">``. Step 3 (Kalendar)
    always links to ``../kalendar/index.html?campaign=<url-encoded>``
    because the Kalendar screen exists as its own sidebar page — it is
    never the ``active`` step, but can be a ``done`` link from steps
    4/5. All five screens live side-by-side under ``screens/``, so the
    relative links are ``../<key>/index.html`` from every workflow page.
    """
    steps: tuple[tuple[int, str, str], ...] = (
        (1, "Opis kampanje", "../opis_kampanje/index.html"),
        (2, "Plan kampanje", "../plan_kampanje/index.html"),
        (
            3,
            "Kalendar",
            f"../kalendar/index.html?campaign={quote(campaign_name)}",
        ),
        (4, "Studio sadržaja", "../studio_sadrzaja/index.html"),
        (5, "Pregled i izvoz", "../pregled_izvoz/index.html"),
    )
    parts: list[str] = ['<div class="stepper">']
    for idx, (num, label, href) in enumerate(steps):
        if idx:
            parts.append('<div class="sep"></div>')
        if num < active_step:
            parts.append(
                f'<a class="step done" href="{html.escape(href)}">'
                f'<span class="num">{num}</span>{html.escape(label)}</a>'
            )
        elif num == active_step:
            parts.append(
                f'<div class="step active">'
                f'<span class="num">{num}</span>{html.escape(label)}</div>'
            )
        else:
            parts.append(
                f'<div class="step">'
                f'<span class="num">{num}</span>{html.escape(label)}</div>'
            )
    parts.append("</div>")
    return "".join(parts)


def render_shell(
    *,
    active_key: str,
    page_title: str,
    body_html: str,
    crumbs: list[Breadcrumb] | None = None,
) -> str:
    """Return a complete HTML page rendered into the shared shell.

    ``body_html`` is inserted as-is into the ``.content`` slot — callers
    are responsible for producing well-formed HTML (typically via
    :mod:`screens.pocetna.ssr`).
    """
    nav = _nav_html(active_key)
    crumbs_block = _crumbs_html(crumbs or [Breadcrumb(page_title, None)])
    return (
        "<!doctype html><html lang=\"sr-Latn\"><head>"
        "<meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        f"<title>{html.escape(page_title)} — AI Campaign Studio</title>"
        "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'self'; "
        "script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "connect-src 'self'; font-src 'self'\">"
        "<link rel=\"stylesheet\" href=\"../../static/app.css\">"
        "</head><body><div class=\"app\">"
        '<aside class="sidebar"><div class="brand">'
        '<img class="brand-logo" src="../../static/brand-logo.png" '
        'alt="AI Campaign Studio"></div>'
        f'<nav class="nav">{nav}</nav>'
        '<div class="local"><span class="dot"></span>Lokalno</div>'
        "</aside>"
        '<div class="main">'
        '<div class="topbar">'
        f'<div class="crumbs">{crumbs_block}</div>'
        "</div>"
        f'<div class="content">{body_html}</div>'
        "</div>"
        "</div>"
        '<script src="../../static/app.js"></script>'
        "</body></html>"
    )
