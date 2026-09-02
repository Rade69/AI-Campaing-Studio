"""Brend screen — fixture-driven body, slots into the shared shell.

Visual port of ``docs/gui-v3/screens/02_brend/index.html`` translated
into Python: tabs row (4 tabs, first active), 2-column grid
(brand-info card + approved-facts card), 3-column brend-resursi grid.
All link/button stubs use ``data-action="toast"`` so the existing
``static/app.js`` handler can pick them up — no ``<a href>`` to
non-existent pages (campaign workflow screens land in ACS-GUI-003).
"""

from __future__ import annotations

import html
from dataclasses import dataclass


@dataclass(frozen=True)
class VoiceBadge:
    """A single glas-brenda label + variant pair (maps to a ``.badge`` class)."""

    label: str
    variant: str  # one of: info, gray, warn, ok, danger


@dataclass(frozen=True)
class BrandInfo:
    name: str
    description: str  # the demo callout text under "Opis brenda"
    primary_audience: str
    voice: list[VoiceBadge]
    last_check_label: str  # e.g. "2. 9. 2026."


@dataclass(frozen=True)
class ApprovedFact:
    code: str  # e.g. "F-001"
    text: str


@dataclass(frozen=True)
class BrandResource:
    title: str
    detail: str


@dataclass(frozen=True)
class BrendFixture:
    status_checked: bool  # drives the "✓ Provjereno i ažurno" pill
    brand: BrandInfo
    facts: list[ApprovedFact]
    resources: list[BrandResource]
    refresh_message: str  # toast body for "Osvježi podatke"


DEFAULT_FIXTURE = BrendFixture(
    status_checked=True,
    brand=BrandInfo(
        name="BrightSmile Oral Care",
        description=(
            "Demo brend za GUI. Produkcija će podatke čitati iz "
            "BrandSnapshot modela."
        ),
        primary_audience=(
            "Odrasli korisnici koji traže jednostavnu svakodnevnu "
            "oralnu njegu."
        ),
        voice=[
            VoiceBadge("Jasan", "info"),
            VoiceBadge("Pouzdan", "info"),
            VoiceBadge("Nenametljiv", "gray"),
        ],
        last_check_label="2. 9. 2026.",
    ),
    facts=[
        ApprovedFact("F-001", "Proizvod ne sadrži alkohol u formulaciji."),
        ApprovedFact("F-002", "Pakovanje sadrži 500 ml."),
        ApprovedFact("F-003", "Dostupno u tri varijante ukusa."),
    ],
    resources=[
        BrandResource("Logo", "PNG/SVG reference"),
        BrandResource("Paleta boja", "#0EA5E9 · #2563EB · #0F172A"),
        BrandResource("Izvori", "10 provjerenih izvora"),
    ],
    refresh_message="Kasnije: pokreni ingestion/review tok.",
)


def _tabs_row(active: int, labels: list[str]) -> str:
    parts: list[str] = ['<div class="tabs" data-tabs>']
    for idx, label in enumerate(labels):
        cls = "tab active" if idx == active else "tab"
        parts.append(
            f'<div class="{cls}" data-action="tab">'
            f"{html.escape(label)}</div>"
        )
    parts.append("</div>")
    return "".join(parts)


def _voice_badges(badges: list[VoiceBadge]) -> str:
    return "".join(
        f'<span class="badge {html.escape(b.variant)}">{html.escape(b.label)}</span>'
        for b in badges
    )


def _fact_row(f: ApprovedFact) -> str:
    return (
        f'<div class="fact"><b>{html.escape(f.code)}</b> — '
        f"{html.escape(f.text)}</div>"
    )


def _resource_card(r: BrandResource) -> str:
    return (
        '<div class="card">'
        f"<b>{html.escape(r.title)}</b>"
        f'<p class="muted small">{html.escape(r.detail)}</p>'
        "</div>"
    )


def render_body(fixture: BrendFixture | None = None) -> str:
    """Return the Brend body HTML driven by the supplied fixture."""
    fx = fixture or DEFAULT_FIXTURE
    fact_html = "".join(_fact_row(f) for f in fx.facts)
    resource_html = "".join(_resource_card(r) for r in fx.resources)
    status_tick = (
        '<span class="tick">✓</span>'
        if fx.status_checked
        else '<span class="tick">·</span>'
    )
    return (
        '<div class="page-head">'
        "<div>"
        f"<h2>Brend</h2>"
        "<p>Jedno mjesto za odobrene činjenice, glas brenda i resurse.</p>"
        '<div class="brand-status">'
        f"{status_tick}"
        "<b>Provjereno i ažurno</b>"
        f'<span class="muted small">Posljednja provjera: '
        f"{html.escape(fx.brand.last_check_label)}.</span>"
        "</div>"
        "</div>"
        f'<button class="btn" data-action="toast" '
        f'data-message="{html.escape(fx.refresh_message)}">'
        "Osvježi podatke"
        "</button>"
        "</div>"
        + _tabs_row(
            0,
            [
                "Osnovni podaci",
                "Odobrene činjenice",
                "Glas brenda",
                "Brend resursi",
            ],
        )
        + '<div class="grid g2">'
        '<div class="card">'
        f"<h3>{html.escape(fx.brand.name)}</h3>"
        '<div class="field"><label>Opis brenda</label>'
        f'<div class="callout">{html.escape(fx.brand.description)}</div>'
        "</div>"
        '<div class="field"><label>Primarna publika</label>'
        f"<div>{html.escape(fx.brand.primary_audience)}</div>"
        "</div>"
        '<div class="field"><label>Glas brenda</label>'
        f'<div class="statusline">{_voice_badges(fx.brand.voice)}</div>'
        "</div>"
        "</div>"
        '<div class="card">'
        "<h3>Odobrene činjenice</h3>"
        f"{fact_html}"
        '<div class="actions">'
        '<button class="btn" data-action="toast" '
        'data-message="Lista činjenica — kasnije vodi u facts workspace.">'
        "Prikaži sve činjenice"
        "</button>"
        "</div>"
        "</div>"
        "</div>"
        '<div class="section-title">'
        "<h3>Brend resursi</h3>"
        '<button class="btn" data-action="toast" '
        'data-message="Upload resursa — kasnije vodi u ingestion tok.">'
        "Dodaj resurs"
        "</button>"
        "</div>"
        f'<div class="grid g3">{resource_html}</div>'
    )


__all__ = [
    "ApprovedFact",
    "BrandInfo",
    "BrandResource",
    "BrendFixture",
    "DEFAULT_FIXTURE",
    "VoiceBadge",
    "render_body",
]
