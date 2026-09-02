"""Kampanje screen — fixture-driven body, slots into the shared shell.

Visual port of ``docs/gui-v3/screens/03_kampanje/index.html``. Renders
a campaigns table with the same 3 rows as the V3 reference. Every
"Otvori" affordance and the "+ Nova kampanja" button use
``data-action="toast"`` — the campaign workflow screens
(Opis / Plan / Studio sadržaja / Pregled) do not exist in
``presentation_webview`` yet and land in ACS-GUI-003.
"""

from __future__ import annotations

import html
from dataclasses import dataclass


@dataclass(frozen=True)
class Campaign:
    name: str
    brand: str
    status_variant: str  # one of: warn, info, ok, danger, gray
    status_label: str
    planned_count: int  # 6 / 8 / 5 ...
    last_modified: str  # human label, e.g. "Danas 14:20"


@dataclass(frozen=True)
class KampanjeFixture:
    campaigns: list[Campaign]
    new_campaign_toast: str


DEFAULT_FIXTURE = KampanjeFixture(
    campaigns=[
        Campaign(
            name="Proljetna kolekcija",
            brand="BrightSmile",
            status_variant="warn",
            status_label="U pripremi",
            planned_count=6,
            last_modified="Danas 14:20",
        ),
        Campaign(
            name="Lansiranje seruma",
            brand="BrightSmile",
            status_variant="info",
            status_label="Planirano",
            planned_count=8,
            last_modified="Jučer",
        ),
        Campaign(
            name="Novi web-sajt",
            brand="BrightSmile",
            status_variant="ok",
            status_label="Odobreno",
            planned_count=5,
            last_modified="30. 8.",
        ),
    ],
    new_campaign_toast="Nova kampanja će se povezati sa CreateCampaign use-caseom.",
)


def _campaign_row(c: Campaign, open_toast: str) -> str:
    """One ``<tr>`` for the campaigns table.

    The "Otvori" cell is a ``<button data-action="toast">`` — NOT an
    ``<a href>`` — because the campaign workflow screen it would link
    to does not exist yet (ACS-GUI-003 scope).
    """
    return (
        "<tr>"
        f"<td><b>{html.escape(c.name)}</b></td>"
        f"<td>{html.escape(c.brand)}</td>"
        f'<td><span class="badge {html.escape(c.status_variant)}">'
        f"{html.escape(c.status_label)}</span></td>"
        f"<td>{c.planned_count} objava</td>"
        f"<td>{html.escape(c.last_modified)}</td>"
        '<td class="right">'
        f'<button class="btn" data-action="toast" '
        f'data-message="{html.escape(open_toast)}">'
        "Otvori"
        "</button>"
        "</td>"
        "</tr>"
    )


def render_body(fixture: KampanjeFixture | None = None) -> str:
    """Return the Kampanje body HTML driven by the supplied fixture."""
    fx = fixture or DEFAULT_FIXTURE
    open_toast = "Kampanja workflow ekran dolazi u ACS-GUI-003."
    rows = "".join(_campaign_row(c, open_toast) for c in fx.campaigns)
    return (
        '<div class="page-head">'
        "<div>"
        "<h2>Kampanje</h2>"
        "<p>Kreiraj, nastavi i pregledaj kampanje.</p>"
        "</div>"
        f'<button class="btn primary" data-action="toast" '
        f'data-message="{html.escape(fx.new_campaign_toast)}">'
        "+ Nova kampanja"
        "</button>"
        "</div>"
        '<div class="card">'
        '<table class="table">'
        "<thead>"
        "<tr>"
        "<th>Kampanja</th>"
        "<th>Brend</th>"
        "<th>Status</th>"
        "<th>Planirano</th>"
        "<th>Zadnja izmjena</th>"
        "<th></th>"
        "</tr>"
        "</thead>"
        f"<tbody>{rows}</tbody>"
        "</table>"
        "</div>"
    )


__all__ = [
    "Campaign",
    "DEFAULT_FIXTURE",
    "KampanjeFixture",
    "render_body",
]
