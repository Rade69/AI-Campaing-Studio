"""Podešavanja screen — fixture-driven body, slots into the shared shell.

Visual port of ``docs/gui-v3/screens/09_podesavanja/index.html``.
Left column = settings tab list (Opšte / Jezik / **AI provajderi**
active), right column = the AI providers panel with 6 provider rows
plus a production-tok callout. Every "Podesi" button uses
``data-action="toast"`` — the real provider configuration flow goes
through a future ``PresentationFacade`` use case, not this GUI-BASE
tier.
"""

from __future__ import annotations

import html
from dataclasses import dataclass

# Settings tab list (Opšte / Jezik / AI provajderi). "AI provajderi" is
# the default-active panel with the real provider list; "Jezik" carries
# the content-language picker (SR/HR/BS/EN); "Opšte" is a placeholder.
SETTINGS_TABS: tuple[str, ...] = ("Opšte", "Jezik", "AI provajderi")
ACTIVE_TAB_INDEX = 2  # "AI provajderi"

# Language picker order is locked by the user's explicit ask
# (2026-09-03): Srpski → Hrvatski → Bosanski → Engleski.
# Codes are short tokens the JS handler uses for the active state.
LANGUAGES: tuple[tuple[str, str], ...] = (
    ("SR", "Srpski"),
    ("HR", "Hrvatski"),
    ("BS", "Bosanski"),
    ("EN", "Engleski"),
)
DEFAULT_LANGUAGE = "SR"


@dataclass(frozen=True)
class Provider:
    code: str  # used for stable id, e.g. "openai"
    display_name: str
    logo_initials: str  # 1-2 chars shown in the colored logo box
    status_label: str  # "Nije povezano" or richer detail text


@dataclass(frozen=True)
class PodesavanjaFixture:
    intro: str  # short lead paragraph above the provider list
    providers: list[Provider]
    callout: str  # production-tok callout
    podesi_toast: str  # toast body for every "Podesi" button


DEFAULT_FIXTURE = PodesavanjaFixture(
    intro=(
        "API ključevi se čuvaju u OS keyring-u. Ne čuvaju se kao "
        "plaintext u SQLite ili konfiguracionim fajlovima."
    ),
    providers=[
        Provider(
            code="openai",
            display_name="OpenAI",
            logo_initials="OA",
            status_label="Nije povezano",
        ),
        Provider(
            code="anthropic",
            display_name="Anthropic",
            logo_initials="A",
            status_label="Nije povezano",
        ),
        Provider(
            code="google",
            display_name="Google",
            logo_initials="G",
            status_label="Nije povezano",
        ),
        Provider(
            code="deepseek",
            display_name="DeepSeek",
            logo_initials="DS",
            status_label="Nije povezano",
        ),
        Provider(
            code="openrouter",
            display_name="OpenRouter",
            logo_initials="OR",
            status_label="Nije povezano",
        ),
        Provider(
            code="openai_compatible",
            display_name="OpenAI kompatibilan",
            logo_initials="AI",
            status_label="Base URL + API ključ + model ID",
        ),
    ],
    callout=(
        "Production tok: API ključ → Testiraj vezu → Učitaj modele → "
        "Izaberi model. API ključ pripada provajderu, ne modelu."
    ),
    podesi_toast=(
        "Konfiguracija provajdera — kasnije vodi u "
        "PresentationFacade.configure_provider use-case."
    ),
)


def _settings_tabs() -> str:
    """Vertical tab list for the left settings column.

    Each tab carries ``data-tab-target="<panel-id>"`` so the static
    ``app.js`` tab handler can switch the right-column panel on click.
    Uses the ``tabs-vertical`` class instead of inline styles so the
    layout stays in CSS.
    """
    panel_ids = ("panel-opste", "panel-jezik", "panel-provajderi")
    parts = ['<div class="tabs tabs-vertical" data-tabs>']
    for idx, label in enumerate(SETTINGS_TABS):
        cls = "tab active" if idx == ACTIVE_TAB_INDEX else "tab"
        target = panel_ids[idx] if idx < len(panel_ids) else ""
        parts.append(
            f'<div class="{cls}" data-action="tab" '
            f'data-tab-target="{html.escape(target)}">'
            f"{html.escape(label)}</div>"
        )
    parts.append("</div>")
    return "".join(parts)


def _language_picker() -> str:
    """Render the language picker (SR / HR / BS / EN).

    Each row is a button with ``data-action="lang-pick"`` and
    ``data-lang="<code>"``. The row for ``DEFAULT_LANGUAGE`` starts
    with the ``lang-active`` class so the active selection is visible
    on first render. The JS handler swaps the class on click and shows
    a toast with the chosen language.
    """
    parts: list[str] = []
    for code, name in LANGUAGES:
        is_active = code == DEFAULT_LANGUAGE
        cls = "lang-row lang-active" if is_active else "lang-row"
        mark = "✓" if is_active else ""
        parts.append(
            f'<button type="button" class="{cls}" data-action="lang-pick" '
            f'data-lang="{html.escape(code)}">'
            f'<span class="lang-name">{html.escape(name)}</span>'
            f'<span class="lang-mark">{html.escape(mark)}</span>'
            f"</button>"
        )
    return "".join(parts)


def _provider_row(p: Provider, podesi_toast: str) -> str:
    return (
        '<div class="provider">'
        '<div class="left">'
        f'<div class="logo">{html.escape(p.logo_initials)}</div>'
        "<div>"
        f"<b>{html.escape(p.display_name)}</b>"
        f'<div class="small muted">{html.escape(p.status_label)}</div>'
        "</div>"
        "</div>"
        f'<button class="btn" data-action="toast" '
        f'data-message="{html.escape(podesi_toast)}">'
        "Podesi"
        "</button>"
        "</div>"
    )


def render_body(fixture: PodesavanjaFixture | None = None) -> str:
    """Return the Podešavanja body HTML driven by the supplied fixture.

    Layout (ACS-GUI-004): three vertical tabs (Opšte / Jezik / AI
    provajderi). AI provajderi is the default-active panel and carries
    the real provider list; Opšte and Jezik are placeholder callouts
    for future workspace. The JS handler in ``static/app.js`` shows
    only the panel whose id matches the clicked tab's
    ``data-tab-target``.
    """
    fx = fixture or DEFAULT_FIXTURE
    rows = "".join(_provider_row(p, fx.podesi_toast) for p in fx.providers)
    return (
        '<div class="page-head">'
        "<div>"
        "<h2>Podešavanja</h2>"
        "<p>Samo postavke koje postoje u trenutnom proizvodnom scope-u.</p>"
        "</div>"
        "</div>"
        '<div class="grid" style="grid-template-columns:220px 1fr">'
        f'<div class="card">{_settings_tabs()}</div>'
        '<div>'
        # Panel: Opšte (placeholder, hidden by default)
        '<div data-tab-panel id="panel-opste" hidden>'
        '<div class="card">'
        "<h3>Opšte</h3>"
        '<div class="callout">'
        "Opšte postavke aplikacije — dostupno u narednoj verziji."
        "</div>"
        "</div>"
        "</div>"
        # Panel: Jezik (language picker, hidden by default)
        '<div data-tab-panel id="panel-jezik" hidden>'
        '<div class="card">'
        "<h3>Jezik sadržaja</h3>"
        '<p class="muted small">'
        "Birač jezika za generisani sadržaj. "
        "Odabir se primjenjuje na naredne kampanje."
        "</p>"
        f'<div class="lang-picker">{_language_picker()}</div>'
        "</div>"
        "</div>"
        # Panel: AI provajderi (default-active, real content)
        '<div data-tab-panel id="panel-provajderi">'
        '<div class="card">'
        "<h3>AI provajderi</h3>"
        f'<p class="muted small">{html.escape(fx.intro)}</p>'
        f'<div style="margin-top:16px">{rows}</div>'
        f'<div class="callout" style="margin-top:14px">'
        f"{html.escape(fx.callout)}"
        "</div>"
        "</div>"
        "</div>"
        "</div>"
        "</div>"
    )


__all__ = [
    "ACTIVE_TAB_INDEX",
    "DEFAULT_FIXTURE",
    "DEFAULT_LANGUAGE",
    "LANGUAGES",
    "PodesavanjaFixture",
    "Provider",
    "SETTINGS_TABS",
    "render_body",
]
