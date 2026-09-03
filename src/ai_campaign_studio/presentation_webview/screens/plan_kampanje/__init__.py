"""Plan kampanje screen — fixture-driven body, slots into the shared shell.

Owns the step-2 campaign workflow screen: the 6-row plan table (#/Uloga/
Tema/Cilj/Format/Status) plus the shared 5-step stepper (step 2 active,
step 1 done). Visual port of
``docs/gui-v3/screens/05_plan_kampanje/index.html``.

Does NOT own any real use-case wiring: "Regeneriši plan" stays a
``data-action="toast"`` stub. Two real links exist — "← Opis" back to
``../opis_kampanje/index.html`` and "Odobri plan i nastavi →" to the
already-existing Kalendar screen via its ``?campaign=`` query-param
handler (``../kalendar/index.html?campaign=<url-encoded>``).
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from urllib.parse import quote

from ...shell import stepper_html


@dataclass(frozen=True)
class PlanItem:
    """One row of the plan table."""

    index: int  # 1..N
    role_label: str
    role_variant: str  # .badge variant: danger/info/ok/warn
    theme: str
    goal: str
    format: str
    status_label: str
    status_variant: str  # .badge variant ("gray" in the mokap)


@dataclass(frozen=True)
class PlanKampanjeFixture:
    campaign_name: str
    badge_variant: str  # "info"
    badge_label: str  # "Plan v1"
    items: list[PlanItem]
    regenerisi_toast: str


DEFAULT_FIXTURE = PlanKampanjeFixture(
    campaign_name="Proljetna kolekcija",
    badge_variant="info",
    badge_label="Plan v1",
    items=[
        PlanItem(
            index=1,
            role_label="Problem",
            role_variant="danger",
            theme="Najčešća frustracija korisnika",
            goal="Prepoznati problem",
            format="Feed 4:5",
            status_label="Planirano",
            status_variant="gray",
        ),
        PlanItem(
            index=2,
            role_label="Edukacija",
            role_variant="info",
            theme="Šta korisnik treba znati prije izbora",
            goal="Objasniti bez pretjerivanja",
            format="Karusel",
            status_label="Planirano",
            status_variant="gray",
        ),
        PlanItem(
            index=3,
            role_label="Dokaz",
            role_variant="ok",
            theme="Provjerljive karakteristike proizvoda",
            goal="Povećati povjerenje",
            format="Feed 4:5",
            status_label="Planirano",
            status_variant="gray",
        ),
        PlanItem(
            index=4,
            role_label="Prigovor",
            role_variant="warn",
            theme="Čest razlog odlaganja kupovine",
            goal="Odgovoriti na prigovor",
            format="Feed 4:5",
            status_label="Planirano",
            status_variant="gray",
        ),
        PlanItem(
            index=5,
            role_label="Ponuda",
            role_variant="info",
            theme="Šta korisnik konkretno dobija",
            goal="Predstaviti ponudu",
            format="Feed 4:5",
            status_label="Planirano",
            status_variant="gray",
        ),
        PlanItem(
            index=6,
            role_label="Akcija",
            role_variant="ok",
            theme="Jasan završni poziv",
            goal="Podstaći sljedeći korak",
            format="Feed 4:5",
            status_label="Planirano",
            status_variant="gray",
        ),
    ],
    regenerisi_toast=(
        "Regenerisanje plana — kasnije vodi u GenerateCampaignPlan use-case."
    ),
)


def _row(item: PlanItem) -> str:
    return (
        "<tr>"
        f"<td>{item.index}</td>"
        f'<td><span class="badge {html.escape(item.role_variant)}">'
        f"{html.escape(item.role_label)}</span></td>"
        f"<td>{html.escape(item.theme)}</td>"
        f"<td>{html.escape(item.goal)}</td>"
        f"<td>{html.escape(item.format)}</td>"
        f'<td><span class="badge {html.escape(item.status_variant)}">'
        f"{html.escape(item.status_label)}</span></td>"
        "</tr>"
    )


def render_body(fixture: PlanKampanjeFixture | None = None) -> str:
    """Return the Plan kampanje body HTML driven by the supplied fixture."""
    fx = fixture or DEFAULT_FIXTURE
    rows = "".join(_row(i) for i in fx.items)
    kalendar_href = (
        f"../kalendar/index.html?campaign={quote(fx.campaign_name)}"
    )
    return (
        stepper_html(2, fx.campaign_name)
        + '<div class="page-head"><div>'
        "<h2>Plan kampanje</h2>"
        "<p>Uredi redoslijed, uloge i teme prije generisanja sadržaja.</p>"
        "</div>"
        f'<span class="badge {html.escape(fx.badge_variant)}">'
        f"{html.escape(fx.badge_label)}</span>"
        "</div>"
        '<div class="card">'
        '<table class="table">'
        "<thead>"
        "<tr><th>#</th><th>Uloga</th><th>Tema</th><th>Cilj</th>"
        "<th>Format</th><th>Status</th></tr>"
        "</thead>"
        f"<tbody>{rows}</tbody>"
        "</table>"
        "</div>"
        '<div class="actions">'
        '<a class="btn" href="../opis_kampanje/index.html">← Opis</a>'
        f'<button class="btn" data-action="toast" '
        f'data-message="{html.escape(fx.regenerisi_toast)}">'
        "Regeneriši plan"
        "</button>"
        f'<a class="btn primary" href="{html.escape(kalendar_href)}">'
        "Odobri plan i nastavi →</a>"
        "</div>"
    )


__all__ = [
    "DEFAULT_FIXTURE",
    "PlanItem",
    "PlanKampanjeFixture",
    "render_body",
]
