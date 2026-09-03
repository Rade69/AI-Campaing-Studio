"""Tests for the Kalendar screen body renderer.

Acceptance for ACS-GUI-002: the global Kalendar view mirrors the V3
reference (28-day grid, same 3 events, weekday headers
Pon-Uto-Sri-Čet-Pet-Sub-Ned). Crucially the ``?campaign=`` query
banner / stepper that the V3 reference ships is **NOT** ported here
— it points at screens (Plan kampanje / Studio sadržaja) that do
not exist in ``presentation_webview`` yet. The banner lands with the
rest of the campaign workflow in ACS-GUI-003.
"""

from __future__ import annotations

import dataclasses
import re

import pytest

from ai_campaign_studio.presentation_webview.screens.kalendar import (
    DEFAULT_FIXTURE,
    WEEKDAYS,
    CalendarEvent,
    KalendarFixture,
    render_body,
)


def test_default_fixture_total_days_is_28() -> None:
    assert DEFAULT_FIXTURE.total_days == 28


def test_default_fixture_has_three_events_on_canonical_days() -> None:
    by_day = {e.day: e for e in DEFAULT_FIXTURE.events}
    assert set(by_day) == {3, 5, 9}
    assert by_day[3].variant == ""
    assert by_day[3].label == "Proljetna kolekcija · Problem"
    assert by_day[5].variant == "green"
    assert by_day[5].label == "Lansiranje seruma · Dokaz"
    assert by_day[9].variant == "amber"
    assert by_day[9].label == "Proljetna kolekcija · Ponuda"


def test_weekdays_constant_matches_v3_order() -> None:
    assert WEEKDAYS == ("Pon", "Uto", "Sri", "Čet", "Pet", "Sub", "Ned")


def test_fixtures_are_pure_dataclasses() -> None:
    assert dataclasses.is_dataclass(CalendarEvent)
    assert dataclasses.is_dataclass(KalendarFixture)
    assert CalendarEvent.__dataclass_params__.frozen is True
    assert KalendarFixture.__dataclass_params__.frozen is True


def test_render_body_renders_28_day_cells() -> None:
    body = render_body()
    # Each day has a .day cell carrying its date number.
    day_cells = re.findall(r'<div class="day"><span class="date">(\d+)</span>', body)
    assert day_cells == [str(d) for d in range(1, 29)], (
        f"expected 28 day cells 1..28, got {day_cells[:5]}...{day_cells[-5:]}"
    )


def test_render_body_renders_7_weekday_headers() -> None:
    body = render_body()
    headers = re.findall(r'<div class="cal-head">([^<]+)</div>', body)
    assert headers == list(WEEKDAYS)


def test_render_body_emits_three_event_pills() -> None:
    body = render_body()
    for needle in (
        '<div class="event">Proljetna kolekcija · Problem</div>',
        '<div class="event green">Lansiranje seruma · Dokaz</div>',
        '<div class="event amber">Proljetna kolekcija · Ponuda</div>',
    ):
        assert needle in body, f"missing event pill: {needle!r}"


def test_render_body_uses_v3_calendar_classes() -> None:
    body = render_body()
    for needle in ("calendar", "cal-head", "day", "date", "event", "callout"):
        assert needle in body


def test_render_body_campaign_banner_hidden_by_default() -> None:
    """ACS-GUI-003: the workflow stepper + back/forward actions render but
    stay ``hidden`` -- the generic ``?campaign=`` handler in app.js
    (untouched by this task) un-hides ``[data-campaign-only]`` elements
    when Kalendar is reached from inside the campaign workflow. Nothing
    Kalendar-specific was added to app.js."""
    body = render_body()
    assert body.count("data-campaign-only") == 2  # stepper wrapper + actions
    assert '<div data-campaign-only hidden><div class="stepper">' in body
    assert '<div class="step active"><span class="num">3</span>Kalendar</div>' in body
    assert (
        '<div class="actions" data-campaign-only hidden>'
        '<a class="btn" href="../plan_kampanje/index.html">'
        "← Plan kampanje</a>"
        '<a class="btn primary" href="../studio_sadrzaja/index.html">'
        "Nastavi na Studio sadržaja →</a>"
        "</div>"
    ) in body


def test_render_body_danas_button_is_toast_stub() -> None:
    body = render_body()
    assert "Danas" in body
    assert re.search(
        r'<button class="btn" data-action="toast"[^>]*>Danas</button>', body
    ), '"Danas" must be a toast-stub button'


def test_render_body_callout_present() -> None:
    body = render_body()
    assert "<b>Napomena:</b>" in body
    # The MVP disclaimer (verbatim from V3 reference) is present.
    assert "auto-posting" in body
    assert "queue/retry" in body


def test_changing_fixture_changes_rendered_body() -> None:
    custom = KalendarFixture(
        total_days=14,
        events=[CalendarEvent(day=2, label="Custom event", variant="")],
        callout="Custom callout",
        days_button_toast="Custom toast",
    )
    body = render_body(custom)
    # 14 day cells.
    day_cells = re.findall(r'<div class="day"><span class="date">(\d+)</span>', body)
    assert len(day_cells) == 14
    # Default 28-day content must not leak.
    assert 'Proljetna kolekcija · Problem' not in body
    # Custom content is present.
    assert "Custom event" in body
    assert "Custom callout" in body


def test_render_body_escapes_xss_in_fixture() -> None:
    nasty = KalendarFixture(
        total_days=7,
        events=[CalendarEvent(day=1, label="<script>x</script>", variant="")],
        callout="<img onerror=x>",
        days_button_toast="<svg>",
    )
    body = render_body(nasty)
    assert "<script>" not in body
    assert "<img onerror" not in body
    assert "<svg>" not in body


def test_render_body_rejects_event_outside_range() -> None:
    bad = KalendarFixture(
        total_days=10,
        events=[CalendarEvent(day=99, label="x", variant="")],
        callout="x",
        days_button_toast="x",
    )
    with pytest.raises(ValueError, match="outside"):
        render_body(bad)


def test_render_body_rejects_zero_or_negative_total_days() -> None:
    with pytest.raises(ValueError):
        render_body(
            KalendarFixture(
                total_days=0,
                events=[],
                callout="x",
                days_button_toast="x",
            )
        )


def test_render_body_emits_no_remote_assets() -> None:
    body = render_body()
    for forbidden in (
        "fonts.googleapis.com",
        "cdn.tailwindcss.com",
        "unpkg.com",
    ):
        assert forbidden not in body
