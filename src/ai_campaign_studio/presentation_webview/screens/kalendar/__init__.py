"""Kalendar screen — fixture-driven body, slots into the shared shell.

Visual port of ``docs/gui-v3/screens/06_kalendar/index.html`` (the
*global* view). 28-day grid, 3 weekday headers (Pon–Ned) and 3 events
on the same days as the V3 reference.

The V3 reference carries a ``?campaign=`` query-param banner with
"Plan kampanje" / "Studio sadržaja" affordances. That banner is
**deliberately omitted** here: the screens it would link to are part
of the campaign workflow (ACS-GUI-003) and do not exist in
``presentation_webview`` yet. The banner lands together with that
workflow in ACS-GUI-003.
"""

from __future__ import annotations

import html
from dataclasses import dataclass

# Weekday header order locked by the V3 reference.
WEEKDAYS: tuple[str, ...] = ("Pon", "Uto", "Sri", "Čet", "Pet", "Sub", "Ned")


@dataclass(frozen=True)
class CalendarEvent:
    """A single planned publication on a calendar day.

    ``day`` is 1-based (1..28) and ``variant`` maps to a CSS class
    (empty string -> default ``.event``, otherwise ``.event.<variant>``).
    """

    day: int
    label: str
    variant: str = ""  # "", "green", "amber"


@dataclass(frozen=True)
class KalendarFixture:
    total_days: int  # 28 in the V3 reference
    events: list[CalendarEvent]
    callout: str
    days_button_toast: str


DEFAULT_FIXTURE = KalendarFixture(
    total_days=28,
    events=[
        CalendarEvent(day=3, label="Proljetna kolekcija · Problem"),
        CalendarEvent(
            day=5, label="Lansiranje seruma · Dokaz", variant="green"
        ),
        CalendarEvent(
            day=9, label="Proljetna kolekcija · Ponuda", variant="amber"
        ),
    ],
    callout=(
        "Napomena: kalendar čuva planirane datume unutar aplikacije. "
        "Nema povezivanja naloga društvenih mreža, objave „odmah“, "
        "queue/retry mehanizma ili automatskog publishovanja u MVP-u."
    ),
    days_button_toast="Skok na današnji datum — kasnije vodi u day view.",
)


def _event_html(ev: CalendarEvent) -> str:
    cls = "event" if not ev.variant else f"event {ev.variant}"
    return f'<div class="{cls}">{html.escape(ev.label)}</div>'


def _day_cell(day: int, events_for_day: list[CalendarEvent]) -> str:
    events_html = "".join(_event_html(e) for e in events_for_day)
    return (
        f'<div class="day"><span class="date">{day}</span>{events_html}</div>'
    )


def render_body(fixture: KalendarFixture | None = None) -> str:
    """Return the Kalendar body HTML driven by the supplied fixture."""
    fx = fixture or DEFAULT_FIXTURE
    if fx.total_days < 1:
        raise ValueError("total_days must be >= 1")
    by_day: dict[int, list[CalendarEvent]] = {
        d: [] for d in range(1, fx.total_days + 1)
    }
    for ev in fx.events:
        if ev.day not in by_day:
            raise ValueError(
                f"CalendarEvent.day={ev.day} is outside 1..{fx.total_days}"
            )
        by_day[ev.day].append(ev)
    cells = "".join(
        _day_cell(d, by_day[d]) for d in range(1, fx.total_days + 1)
    )
    heads = "".join(f'<div class="cal-head">{w}</div>' for w in WEEKDAYS)
    return (
        '<div class="page-head">'
        "<div>"
        "<h2>Kalendar</h2>"
        "<p>Globalni pregled planiranih objava. Ovo nije social "
        "publishing niti auto-posting.</p>"
        "</div>"
        "<div>"
        f'<button class="btn" data-action="toast" '
        f'data-message="{html.escape(fx.days_button_toast)}">'
        "Danas"
        "</button>"
        "</div>"
        "</div>"
        f'<div class="calendar">{heads}{cells}</div>'
        f'<div class="callout" style="margin-top:18px">'
        f"<b>Napomena:</b> {html.escape(fx.callout)}"
        "</div>"
    )


__all__ = [
    "CalendarEvent",
    "DEFAULT_FIXTURE",
    "KalendarFixture",
    "WEEKDAYS",
    "render_body",
]
