"""Kampanje screen — placeholder body, full implementation in ACS-GUI-002.

Returns the body fragment that
:func:`ai_campaign_studio.presentation_webview.shell.render_shell`
slots into the shared shell.
"""
from __future__ import annotations

import html


def render_body() -> str:
    """Return the Kampanje placeholder body HTML."""
    return (
        '<div class="page-head">'
        "<div>"
        f"<h2>{html.escape('Kampanje')}</h2>"
        "<p>Lista kampanja, statusi, veze ka opisu i planu.</p>"
        "</div>"
        "</div>"
        '<div class="card" style="max-width:560px">'
        "<h3>ACS-GUI-002</h3>"
        '<p class="muted">Ovaj ekran dobija punu implementaciju u '
        "narednom GUI task-u (ACS-GUI-002). Navigacija je već ožičena "
        "(kliknite stavku u sidebaru) — to demonstrira da je shared "
        "shell funkcionalan.</p>"
        "</div>"
    )


__all__ = ["render_body"]
