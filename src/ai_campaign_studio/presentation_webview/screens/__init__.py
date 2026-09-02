"""Fixture-driven data for the Početna (Dashboard) screen.

Plain dict literals only — no Pydantic, no domain coupling. This is
a pre-facade placeholder so the screen renders while real
``PresentationFacade`` use-cases are still in flight (see
``agent_reports/ACS-GUI-001-task-contract.md``).
"""

from __future__ import annotations

from dataclasses import dataclass

from ._static_pages import write_all_pages

__all__ = [
    "ActivityEntry",
    "DEFAULT_FIXTURE",
    "Kpi",
    "PočetnaFixture",
    "RecentCampaign",
    "write_all_pages",
]


@dataclass(frozen=True)
class Kpi:
    label: str
    value: int
    hint: str


@dataclass(frozen=True)
class RecentCampaign:
    name: str
    status: str  # matches a .badge variant below
    status_label: str


@dataclass(frozen=True)
class ActivityEntry:
    text: str
    when: str


@dataclass(frozen=True)
class PočetnaFixture:
    headline: str
    intro: str
    kpi_active_campaigns: Kpi
    kpi_posts_planned: Kpi
    kpi_drafts: Kpi
    kpi_approved: Kpi
    recent_campaigns: list[RecentCampaign]
    activity: list[ActivityEntry]


# Demo fixture. BrightSmile is the canonical sample brand from
# ``docs/gui-v3/V3_PLAN.md`` and is hard-coded here until a real
# BrandProvider exists in F1+ scope.
DEFAULT_FIXTURE = PočetnaFixture(
    headline="Početna",
    intro=(
        "Pregled trenutnog rada bez analitičkih metrika koje još nisu "
        "implementirane."
    ),
    kpi_active_campaigns=Kpi("AKTIVNE KAMPANJE", 3, "2 u pripremi"),
    kpi_posts_planned=Kpi("OBJAVE U PLANU", 18, "sljedećih 7 dana"),
    kpi_drafts=Kpi("NACRTI", 6, "čekaju doradu"),
    kpi_approved=Kpi("ODOBRENO", 12, "spremno za izvoz"),
    recent_campaigns=[
        RecentCampaign("Proljetna kolekcija", "warn", "U pripremi"),
        RecentCampaign("Lansiranje seruma", "info", "Planirano"),
        RecentCampaign("Novi web-sajt", "ok", "Odobreno"),
    ],
    activity=[
        ActivityEntry("Plan kampanje ažuriran", "prije 2 h"),
        ActivityEntry("3 objave odobrene", "jučer"),
        ActivityEntry("Brend činjenice provjerene", "jučer"),
    ],
)
