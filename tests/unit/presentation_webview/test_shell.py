"""Tests for the shared shell template and the workflow stepper helper.

Covers the two shell capabilities the campaign-workflow screens rely on:
``render_shell(crumbs=...)`` for the "Kampanje › <campaign> › <screen>"
breadcrumb chain, and ``stepper_html`` for the 5-step done/active/upcoming
stepper with its ``?campaign=`` Kalendar link.
"""

from __future__ import annotations

from ai_campaign_studio.presentation_webview.shell import (
    Breadcrumb,
    render_shell,
    stepper_html,
)


def test_render_shell_renders_crumbs_chain() -> None:
    html = render_shell(
        active_key="kampanje",
        page_title="Opis kampanje",
        body_html="<p>x</p>",
        crumbs=[
            Breadcrumb("Kampanje", "../kampanje/index.html"),
            Breadcrumb("Proljetna kolekcija", None),
            Breadcrumb("Opis kampanje", None),
        ],
    )
    assert '<a href="../kampanje/index.html">Kampanje</a>' in html
    assert "<b>Proljetna kolekcija</b>" in html
    assert "<b>Opis kampanje</b>" in html
    # Link comes before the two current-page crumbs, joined by separators.
    assert html.index("Kampanje</a>") < html.index("Proljetna kolekcija")


def test_render_shell_default_crumbs_is_current_page_title() -> None:
    html = render_shell(active_key="pocetna", page_title="Početna", body_html="")
    assert "<b>Početna</b>" in html


def test_render_shell_crumbs_escapes_labels_and_hrefs() -> None:
    html = render_shell(
        active_key="kampanje",
        page_title="X",
        body_html="",
        crumbs=[
            Breadcrumb('<a "x">', '../kampanje/index.html?campaign="1"'),
            Breadcrumb("Current", None),
        ],
    )
    assert '<a "x">' not in html
    assert "&lt;a" in html
    assert '&quot;1&quot;' in html


def test_stepper_html_step_1_active_no_done() -> None:
    body = stepper_html(1, "Proljetna kolekcija")
    assert (
        '<div class="step active"><span class="num">1</span>Opis kampanje</div>'
        in body
    )
    assert 'class="step done"' not in body
    assert (
        '<div class="step"><span class="num">2</span>Plan kampanje</div>' in body
    )


def test_stepper_html_step_2_links_back_to_step_1() -> None:
    body = stepper_html(2, "Proljetna kolekcija")
    assert (
        '<a class="step done" href="../opis_kampanje/index.html">'
        '<span class="num">1</span>Opis kampanje</a>'
    ) in body
    assert (
        '<div class="step active"><span class="num">2</span>Plan kampanje</div>'
        in body
    )


def test_stepper_html_step_4_has_calendar_done_link() -> None:
    body = stepper_html(4, "Proljetna kolekcija")
    assert (
        '<a class="step done" '
        'href="../kalendar/index.html?campaign=Proljetna%20kolekcija">'
        '<span class="num">3</span>Kalendar</a>'
    ) in body
    assert (
        '<div class="step active"><span class="num">4</span>Studio sadržaja</div>'
        in body
    )


def test_stepper_html_step_5_all_prior_done() -> None:
    body = stepper_html(5, "Proljetna kolekcija")
    assert body.count('class="step done"') == 4
    assert (
        '<div class="step active"><span class="num">5</span>Pregled i izvoz</div>'
        in body
    )


def test_stepper_html_url_encodes_campaign_name() -> None:
    body = stepper_html(4, "Kampanja & Co")
    # & -> %26, spaces -> %20
    assert "Kampanja%20%26%20Co" in body
    assert "campaign=Kampanja & Co" not in body


def test_stepper_html_has_five_separators_and_one_stepper_wrapper() -> None:
    body = stepper_html(3, "X")
    assert body.count('<div class="sep"></div>') == 4
    assert body.count('<div class="stepper">') == 1
    assert body.count("</div>") >= 5
