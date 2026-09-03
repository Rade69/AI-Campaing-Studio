"""Studio sadržaja screen — fixture-driven body, slots into the shared shell.

Owns the step-4 campaign workflow screen: 4 real tab panels (Sadržaj /
Korištene činjenice / Provjera usklađenosti / Istorija verzija) driven by
the ``data-tab-target`` → ``data-tab-panel`` pattern proven in ACS-GUI-004.

Does NOT own any real use-case wiring: every quick action, "Sačuvaj
nacrt" and "Pošalji na reviziju" is a ``data-action="toast"`` stub with a
"Bridge stub: <action>" message. The stepper carries real back-links to
steps 1–3 (step 3 = Kalendar via ``?campaign=``); "Pregled i izvoz →" is
a real forward ``<a href>`` to step 5 (Human Owner feedback, 2026-09-03
-- without it there was no way out of this screen toward export).

Deliberate deviation from the V3 mokap (documented in the task contract):
``docs/gui-v3/screens/07_studio_sadrzaja/index.html`` still uses the OLD
cosmetic-only tab markup (``data-action="tab"`` without ``data-tab-target``,
all content stacked in one ``.studio`` grid). That is NOT ported literally
— this module uses the real tab-panel switching instead, consistent with
the already-approved production pattern.
"""

from __future__ import annotations

import html
from dataclasses import dataclass

from ...shell import stepper_html

TAB_LABELS: tuple[str, ...] = (
    "Sadržaj",
    "Korištene činjenice",
    "Provjera usklađenosti",
    "Istorija verzija",
)

TAB_PANEL_IDS: tuple[str, ...] = (
    "panel-sadrzaj",
    "panel-cinjenice",
    "panel-usklađenost",
    "panel-istorija",
)

# Quick actions are fixed bridge stubs (structure, not per-campaign data):
# (label, bridge_action) -> toast message "Bridge stub: <action>".
QUICK_ACTIONS: tuple[tuple[str, str], ...] = (
    ("Prepiši", "rewrite_content"),
    ("Skrati", "shorten_content"),
    ("Poboljšaj uvod", "improve_hook"),
    ("Promijeni ton", "change_tone"),
    ("Generiši varijantu", "generate_variant"),
)


@dataclass(frozen=True)
class ApprovedFact:
    """One used fact shown in the "Korištene činjenice" panel."""

    code: str  # e.g. "F-001"
    text: str


@dataclass(frozen=True)
class StudioSadrzajaFixture:
    campaign_name: str
    badge_variant: str  # "warn"
    badge_label: str  # "Nacrt"
    item_index: int  # 1
    item_total: int  # 6
    role: str  # "Problem"
    platform: str  # "Instagram"
    format: str  # "Feed 4:5"
    planned_date: str  # "3. septembar"
    status_variant: str  # "warn"
    status_label: str  # "Nacrt"
    hook: str
    hook_char_count: int
    hook_char_limit: int
    body_text: str
    cta: str
    preview_label: str  # "Pregled · Instagram 4:5"
    facts: list[ApprovedFact]
    compliance_checks: list[str]
    sacuvaj_nacrt_toast: str
    posalji_reviziju_toast: str


DEFAULT_FIXTURE = StudioSadrzajaFixture(
    campaign_name="Proljetna kolekcija",
    badge_variant="warn",
    badge_label="Nacrt",
    item_index=1,
    item_total=6,
    role="Problem",
    platform="Instagram",
    format="Feed 4:5",
    planned_date="3. septembar",
    status_variant="warn",
    status_label="Nacrt",
    hook="Da li svakodnevna rutina može biti jednostavnija?",
    hook_char_count=52,
    hook_char_limit=90,
    body_text=(
        "Ako birate proizvod za svakodnevnu oralnu njegu, krenite od "
        "provjerljivih karakteristika umjesto velikih obećanja. "
        "BrightSmile formula u ovom primjeru ne sadrži alkohol i "
        "pakovanje ima 500 ml."
    ),
    cta="Pogledajte dostupne varijante",
    preview_label="Pregled · Instagram 4:5",
    facts=[
        ApprovedFact("F-001", "Formula ne sadrži alkohol."),
        ApprovedFact("F-002", "Pakovanje sadrži 500 ml."),
    ],
    compliance_checks=[
        "Sve faktografske tvrdnje imaju fact reference.",
        "Nema zabranjenih termina.",
        "CTA je prisutan.",
    ],
    sacuvaj_nacrt_toast=(
        "Nacrt sadržaja — kasnije vodi u save draft use-case."
    ),
    posalji_reviziju_toast=(
        "Slanje na reviziju — kasnije vodi u review tok."
    ),
)


def _tabs_row() -> str:
    """Tab strip: first tab active, each carrying ``data-tab-target``."""
    parts: list[str] = ['<div class="tabs" data-tabs>']
    for idx, label in enumerate(TAB_LABELS):
        cls = "tab active" if idx == 0 else "tab"
        target = TAB_PANEL_IDS[idx] if idx < len(TAB_PANEL_IDS) else ""
        parts.append(
            f'<div class="{cls}" data-action="tab" '
            f'data-tab-target="{html.escape(target)}">'
            f"{html.escape(label)}</div>"
        )
    parts.append("</div>")
    return "".join(parts)


def _meta_card(fx: StudioSadrzajaFixture) -> str:
    return (
        '<div class="card meta-card">'
        f"<h3>Stavka {fx.item_index} / {fx.item_total}</h3>"
        '<div class="meta"><strong>Uloga</strong>'
        f"{html.escape(fx.role)}</div>"
        '<div class="meta"><strong>Platforma</strong>'
        f"{html.escape(fx.platform)}</div>"
        '<div class="meta"><strong>Format</strong>'
        f"{html.escape(fx.format)}</div>"
        '<div class="meta"><strong>Planirano</strong>'
        f"{html.escape(fx.planned_date)}</div>"
        '<div class="meta"><strong>Status</strong>'
        f'<span class="badge {html.escape(fx.status_variant)}">'
        f"{html.escape(fx.status_label)}</span></div>"
        "</div>"
    )


def _edit_card(fx: StudioSadrzajaFixture) -> str:
    quick = "".join(
        f'<button data-action="toast" '
        f'data-message="{html.escape(f"Bridge stub: {action}")}">'
        f"{html.escape(label)}</button>"
        for label, action in QUICK_ACTIONS
    )
    return (
        '<div class="card">'
        "<h3>Uredi sadržaj</h3>"
        '<div class="field"><label>Naslov / Hook</label>'
        f'<input class="input" value="{html.escape(fx.hook)}">'
        f'<div class="hint">{fx.hook_char_count} / {fx.hook_char_limit} '
        "znakova</div>"
        "</div>"
        '<div class="field"><label>Glavni tekst</label>'
        f'<textarea class="textarea" style="min-height:120px">'
        f"{html.escape(fx.body_text)}</textarea>"
        "</div>"
        '<div class="field"><label>CTA</label>'
        f'<input class="input" value="{html.escape(fx.cta)}">'
        "</div>"
        f'<div class="quick">{quick}</div>'
        '<div class="actions">'
        f'<button class="btn" data-action="toast" '
        f'data-message="{html.escape(fx.sacuvaj_nacrt_toast)}">'
        "Sačuvaj nacrt"
        "</button>"
        f'<button class="btn" data-action="toast" '
        f'data-message="{html.escape(fx.posalji_reviziju_toast)}">'
        "Pošalji na reviziju"
        "</button>"
        '<a class="btn primary" href="../pregled_izvoz/index.html">'
        "Pregled i izvoz →</a>"
        "</div>"
        "</div>"
    )


def _preview_card(fx: StudioSadrzajaFixture) -> str:
    return (
        '<div class="card">'
        f"<h3>{html.escape(fx.preview_label)}</h3>"
        '<div class="preview"><div>'
        "<b>Vizual još nije dostupan</b>"
        '<p class="small">Prikazaće se kada Brand ingestion dovede odobreni '
        "asset ili kada renderer dobije LayoutSpec.</p>"
        "</div></div>"
        "</div>"
    )


def _facts_panel(fx: StudioSadrzajaFixture) -> str:
    facts = "".join(
        f'<div class="fact"><b>{html.escape(f.code)}</b> '
        f"{html.escape(f.text)}</div>"
        for f in fx.facts
    )
    return (
        '<div data-tab-panel id="panel-cinjenice" hidden>'
        '<div class="card">'
        "<h3>Korištene činjenice</h3>"
        f"{facts}"
        "</div>"
        "</div>"
    )


def _compliance_panel(fx: StudioSadrzajaFixture) -> str:
    checks = "".join(
        f'<div class="check"><i>✓</i><span>{html.escape(c)}</span></div>'
        for c in fx.compliance_checks
    )
    return (
        '<div data-tab-panel id="panel-usklađenost" hidden>'
        '<div class="card">'
        "<h3>Provjera usklađenosti</h3>"
        f"{checks}"
        "</div>"
        "</div>"
    )


def _history_panel() -> str:
    return (
        '<div data-tab-panel id="panel-istorija" hidden>'
        '<div class="card">'
        "<h3>Istorija verzija</h3>"
        '<div class="callout">Istorija verzija sadržaja — dostupno u '
        "narednoj verziji.</div>"
        "</div>"
        "</div>"
    )


def render_body(fixture: StudioSadrzajaFixture | None = None) -> str:
    """Return the Studio sadržaja body HTML driven by the supplied fixture.

    Layout (ACS-GUI-004 pattern): one tab strip, four ``data-tab-panel``
    divs. "Sadržaj" (panel-sadrzaj) is default-active (no ``hidden``); the
    other three start hidden. The JS handler in ``static/app.js`` shows
    only the panel whose id matches the clicked tab's ``data-tab-target``.
    """
    fx = fixture or DEFAULT_FIXTURE
    return (
        stepper_html(4, fx.campaign_name)
        + '<div class="page-head"><div>'
        "<h2>Studio sadržaja</h2>"
        "<p>Uredi jednu stavku plana uz činjenice, AI brze akcije i "
        "provjeru usklađenosti.</p>"
        "</div>"
        f'<span class="badge {html.escape(fx.badge_variant)}">'
        f"{html.escape(fx.badge_label)}</span>"
        "</div>"
        + _tabs_row()
        # Panel 1 (default-active): Sadržaj — meta + edit + preview.
        + '<div data-tab-panel id="panel-sadrzaj">'
        '<div class="studio">'
        + _meta_card(fx)
        + _edit_card(fx)
        + _preview_card(fx)
        + "</div>"
        "</div>"
        + _facts_panel(fx)
        + _compliance_panel(fx)
        + _history_panel()
    )


__all__ = [
    "ApprovedFact",
    "DEFAULT_FIXTURE",
    "QUICK_ACTIONS",
    "StudioSadrzajaFixture",
    "TAB_LABELS",
    "TAB_PANEL_IDS",
    "render_body",
]
