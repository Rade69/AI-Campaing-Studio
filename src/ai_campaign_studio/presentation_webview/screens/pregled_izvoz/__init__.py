"""Pregled i izvoz screen — fixture-driven body, slots into the shared shell.

Owns the step-5 campaign workflow screen: a 3-column content-card grid
plus a 2-column grid (quality checks / export package), and the shared
5-step stepper (step 5 active, steps 1–4 done). Visual port of
``docs/gui-v3/screens/08_pregled_izvoz/index.html``.

"Odobri kampanju" is a UI-only gate (``data-action="approve-gate"``) that
enables the "Izvezi ZIP paket" button; it makes NO backend call (the plan is
already APPROVED before this screen — see ACS-GUI-008). "Izvezi ZIP paket"
(``data-action="export-campaign"``) is wired to the real
``export_campaign_package`` bridge method via ``app.js``. The export button is
ALWAYS emitted (``hidden`` by default, empty ``data-campaign-id``/
``data-plan-id``) and revealed at runtime by ``app.js`` when both ``?campaign=``
and ``?plan=`` are present (ACS-GUI-009 BF-1 equivalent).
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field

from ...shell import stepper_html


@dataclass(frozen=True)
class ContentPreviewItem:
    """One approved/under-review content card in the 3-column grid."""

    index: int  # 1..N
    role: str  # "Problem" — joined with index into the card title
    headline: str
    status_variant: str  # .badge variant: ok/warn
    status_label: str


@dataclass(frozen=True)
class ExportRow:
    """One row of the export-package list."""

    label: str
    status_variant: str  # .badge variant: ok/gray/info
    status_label: str


@dataclass(frozen=True)
class ContentPerformanceRow:
    """One placeholder row of the per-content-piece performance table.

    SSR fixture only — at runtime ``app.js`` replaces the whole tbody with
    real rows from ``get_campaign_content_performance``.
    """

    label: str
    ctr: str
    cpc: str


@dataclass(frozen=True)
class PregledIzvozFixture:
    campaign_name: str
    content_items: list[ContentPreviewItem]
    quality_checks: list[str]
    export_rows: list[ExportRow]
    export_intro: str  # G10 scope callout above the export rows
    odobri_toast: str
    izvezi_toast: str
    performance_note: str = "Nema podataka o performansama još."
    content_performance_rows: list[ContentPerformanceRow] = field(
        default_factory=list
    )


DEFAULT_FIXTURE = PregledIzvozFixture(
    campaign_name="Proljetna kolekcija",
    content_items=[
        ContentPreviewItem(
            index=1,
            role="Problem",
            headline="Da li svakodnevna rutina može biti jednostavnija?",
            status_variant="ok",
            status_label="Odobreno",
        ),
        ContentPreviewItem(
            index=2,
            role="Edukacija",
            headline="Tri stvari koje vrijedi provjeriti prije izbora.",
            status_variant="ok",
            status_label="Odobreno",
        ),
        ContentPreviewItem(
            index=3,
            role="Dokaz",
            headline="Provjerljive karakteristike, bez pretjerivanja.",
            status_variant="warn",
            status_label="Za reviziju",
        ),
    ],
    quality_checks=[
        "CTA prisutan u svim stavkama.",
        "Nema unsupported fact claims.",
        "Broj znakova je unutar formatnih ograničenja.",
        "Ton je konzistentan sa Brand Snapshotom.",
    ],
    export_rows=[
        ExportRow("Tekst objava", "ok", "Spremno"),
        ExportRow("Renderovane slike", "gray", "Čeka renderer"),
        ExportRow("manifest.json", "info", "Interno"),
    ],
    export_intro=(
        "Predviđeni rezultat za G10: tekstualni sadržaj, renderovane "
        "slike i sidecar manifest."
    ),
    odobri_toast=(
        "Sadržaj pregledan. Sada možeš izvesti ZIP paket."
    ),
    izvezi_toast=(
        "Izvoz ZIP paketa — pokreće render i pakovanje sadržaja."
    ),
    performance_note="Nema podataka o performansama još.",
    content_performance_rows=[
        ContentPerformanceRow("INSTAGRAM/FEED_POST", "—", "—"),
        ContentPerformanceRow("FACEBOOK/FEED_POST", "—", "—"),
    ],
)


def _content_card(item: ContentPreviewItem) -> str:
    return (
        '<div class="card">'
        '<div class="empty-visual">[ Vizual ]</div>'
        f'<h3 style="margin-top:12px">{item.index} · {html.escape(item.role)}</h3>'
        f'<p class="small muted">{html.escape(item.headline)}</p>'
        f'<span class="badge {html.escape(item.status_variant)}">'
        f"{html.escape(item.status_label)}</span>"
        "</div>"
    )


def _export_row(row: ExportRow) -> str:
    return (
        '<div class="row">'
        f"<span>{html.escape(row.label)}</span>"
        f'<span class="badge {html.escape(row.status_variant)}">'
        f"{html.escape(row.status_label)}</span>"
        "</div>"
    )


def _content_performance_row(row: ContentPerformanceRow) -> str:
    return (
        "<tr>"
        f"<td>{html.escape(row.label)}</td>"
        f"<td>{html.escape(row.ctr)}</td>"
        f"<td>{html.escape(row.cpc)}</td>"
        "</tr>"
    )


def _content_performance_table(rows: list[ContentPerformanceRow]) -> str:
    """Render the per-content-piece performance table.

    The tbody carries ``data-content-perf-rows`` so ``app.js`` can replace
    the SSR placeholder rows with real data at runtime. An empty fixture
    renders a single 'Nema podataka' row (offline fallback).
    """
    if rows:
        body_rows = "".join(_content_performance_row(r) for r in rows)
    else:
        body_rows = (
            '<tr><td colspan="3" class="muted">Nema podataka.</td></tr>'
        )
    return (
        '<table data-content-perf-table>'
        "<thead><tr><th>Objava</th><th>CTR</th><th>CPC</th></tr></thead>"
        f'<tbody data-content-perf-rows>{body_rows}</tbody>'
        "</table>"
    )


def render_body(fixture: PregledIzvozFixture | None = None) -> str:
    """Return the Pregled i izvoz body HTML driven by the supplied fixture."""
    fx = fixture or DEFAULT_FIXTURE
    cards = "".join(_content_card(i) for i in fx.content_items)
    checks = "".join(
        f'<div class="check"><i>✓</i><span>{html.escape(c)}</span></div>'
        for c in fx.quality_checks
    )
    rows = "".join(_export_row(r) for r in fx.export_rows)
    content_table = _content_performance_table(fx.content_performance_rows)
    return (
        stepper_html(5, fx.campaign_name)
        + '<div class="page-head"><div>'
        "<h2>Pregled i izvoz</h2>"
        "<p>Završna kontrola prije odobrenja i izvoza paketa.</p>"
        "</div>"
        f'<button class="btn success" data-action="approve-gate" '
        f'data-message="{html.escape(fx.odobri_toast)}">'
        "Odobri kampanju"
        "</button>"
        "</div>"
        f'<div class="grid g3">{cards}</div>'
        '<div class="grid g2" style="margin-top:18px">'
        '<div class="card">'
        "<h3>Provjera kvaliteta</h3>"
        f"{checks}"
        "</div>"
        '<div class="card">'
        "<h3>Izvoz paketa</h3>"
        f'<p class="muted small">{html.escape(fx.export_intro)}</p>'
        f"{rows}"
        '<div class="actions">'
        f'<button id="btn-izvezi" class="btn primary" '
        f'data-action="export-campaign" data-campaign-id="" data-plan-id="" '
        f'title="{html.escape(fx.izvezi_toast)}" hidden disabled>'
        "Izvezi ZIP paket"
        "</button>"
        "</div>"
        '<div class="callout" data-export-result hidden></div>'
        "</div>"
        "</div>"
        '<div class="grid g2" style="margin-top:18px">'
        '<div class="card" data-perf-card>'
        "<h3>Učinak kampanje</h3>"
        f'<p class="muted small" data-perf-note>'
        f"{html.escape(fx.performance_note)}</p>"
        '<div class="row"><span>CTR</span>'
        '<span data-perf-value="ctr">—</span></div>'
        '<div class="row"><span>CPC</span>'
        '<span data-perf-value="cpc">—</span></div>'
        '<div class="row"><span>CPM</span>'
        '<span data-perf-value="cpm">—</span></div>'
        '<div class="row"><span>CPA</span>'
        '<span data-perf-value="cpa">—</span></div>'
        '<div class="row"><span>ROAS</span>'
        '<span data-perf-value="roas">—</span></div>'
        '<div class="row"><span>Stopa konverzije</span>'
        '<span data-perf-value="conversion-rate">—</span></div>'
        '<div class="row"><span>Impresije</span>'
        '<span data-perf-value="impressions">—</span></div>'
        '<div class="row"><span>Klikovi</span>'
        '<span data-perf-value="clicks">—</span></div>'
        '<div class="row"><span>Potrošnja</span>'
        '<span data-perf-value="spend">—</span></div>'
        '<div class="row"><span>Distribucije</span>'
        '<span data-perf-count>—</span></div>'
        "</div>"
        '<div class="card" data-content-perf-card>'
        "<h3>Učinak po objavi</h3>"
        '<p class="muted small" data-content-perf-note>'
        f"{html.escape(fx.performance_note)}</p>"
        f"{content_table}"
        "</div>"
        "</div>"
    )


__all__ = [
    "ContentPerformanceRow",
    "ContentPreviewItem",
    "DEFAULT_FIXTURE",
    "ExportRow",
    "PregledIzvozFixture",
    "render_body",
]
