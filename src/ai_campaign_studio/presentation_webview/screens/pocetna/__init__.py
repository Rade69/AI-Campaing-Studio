"""Početna (Dashboard) screen — fixture-driven, server-rendered.

Produces the body HTML that
:func:`ai_campaign_studio.presentation_webview.shell.render_shell`
slots into the shared shell. All visible numbers, badges and
activity entries come from :class:`PočetnaFixture` — change those
values and the rendered output changes accordingly.
"""

from __future__ import annotations

import html
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .. import ActivityEntry, Kpi, PočetnaFixture, RecentCampaign


def _kpi_card(kpi: Kpi) -> str:
    return (
        '<div class="card">'
        f'<div class="muted small">{html.escape(kpi.label)}</div>'
        f'<div class="metric">{kpi.value}</div>'
        f'<div class="muted small">{html.escape(kpi.hint)}</div>'
        "</div>"
    )


def _recent_row(item: RecentCampaign) -> str:
    return (
        '<div class="row">'
        f"<b>{html.escape(item.name)}</b>"
        f'<span class="badge {html.escape(item.status)}">'
        f"{html.escape(item.status_label)}</span>"
        "</div>"
    )


def _activity_row(item: ActivityEntry) -> str:
    return (
        '<div class="row">'
        f'<span>{html.escape(item.text)}</span>'
        f'<span class="muted small">{html.escape(item.when)}</span>'
        "</div>"
    )


def render_body(fixture: PočetnaFixture | None = None) -> str:
    """Render the Početna body HTML.

    Accepts an optional ``fixture`` for tests; production code passes
    :data:`DEFAULT_FIXTURE` (or a future read-model adapter). The
    import is intentionally lazy to keep the import graph one-way:
    this module is imported at package load time by
    :mod:`._static_pages`, and a top-level ``from .. import
    DEFAULT_FIXTURE`` would cycle back through ``screens/__init__``.
    """
    from .. import DEFAULT_FIXTURE

    fx = fixture or DEFAULT_FIXTURE
    recent_html = "".join(_recent_row(r) for r in fx.recent_campaigns)
    activity_html = "".join(_activity_row(a) for a in fx.activity)
    return (
        '<div class="page-head">'
        "<div>"
        f"<h2>{html.escape(fx.headline)}</h2>"
        f"<p>{html.escape(fx.intro)}</p>"
        "</div>"
        '<button class="btn primary" data-action="toast" '
        'data-message="Nova kampanja će se povezati sa CreateCampaign use-caseom.">'
        "+ Nova kampanja"
        "</button>"
        "</div>"
        '<div class="grid g4">'
        + _kpi_card(fx.kpi_active_campaigns)
        + _kpi_card(fx.kpi_posts_planned)
        + _kpi_card(fx.kpi_drafts)
        + _kpi_card(fx.kpi_approved)
        + "</div>"
        '<div class="grid g2" style="margin-top:18px">'
        '<div class="card"><h3>Nedavne kampanje</h3>'
        f'<div class="list">{recent_html}</div></div>'
        '<div class="card"><h3>Zadnje aktivnosti</h3>'
        f'<div class="list">{activity_html}</div></div>'
        "</div>"
    )


__all__ = ["render_body"]
