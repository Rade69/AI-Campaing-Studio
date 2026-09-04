"""Opis kampanje screen — fixture-driven body, slots into the shared shell.

Owns the step-1 campaign workflow screen: a 2-column form (name/goal/offer/
audience on the left, channel/platform/format/language/instructions on the
right) plus the shared 5-step stepper (step 1 active). Visual port of
``docs/gui-v3/screens/04_opis_kampanje/index.html``.

Does NOT own any real use-case wiring: "Sačuvaj nacrt" stays a
``data-action="toast"`` stub; only "Sačuvaj i napravi plan →" is a real
``<a href>`` into the next workflow step (``../plan_kampanje/index.html``).
"""

from __future__ import annotations

import html
from dataclasses import dataclass

from ...shell import stepper_html

# Platform / format / content-language select options are structure locked
# (same discipline as WEEKDAYS in kalendar and SETTINGS_TABS in podesavanja).
PLATFORMS: tuple[str, ...] = ("Instagram", "Facebook", "LinkedIn")
FORMATS: tuple[str, ...] = ("Feed 4:5", "Kvadrat 1:1", "Priča 9:16")

# Content-language dropdown: SR/HR/BS/EN, in that order (Human Owner
# decision, 2026-09-03 -- no NEUTRAL variant, no "BHS" prefix on the
# labels; order matches the app-wide UI-language picker's SR-first
# convention from Podešavanja/ACS-GUI-004). ``jezik`` on the fixture
# holds the selected *code*; :data:`JEZICI_SADRZAJA` maps code -> label
# and also drives the rendered ``<option>`` order.
JEZICI_SADRZAJA: tuple[tuple[str, str], ...] = (
    ("SR", "Srpski"),
    ("HR", "Hrvatski"),
    ("BS", "Bosanski"),
    ("EN", "Engleski"),
)


@dataclass(frozen=True)
class OpisKampanjeFixture:
    """Every value rendered by the step-1 screen, driven from one place.

    ``platforma`` / ``format`` are the selected values; the option lists
    they belong to are the module-level :data:`PLATFORMS` / :data:`FORMATS`
    constants (the mokap's structure, not per-campaign data). ``jezik`` is
    the selected *code* from :data:`JEZICI_SADRZAJA` (e.g. ``"SR"``).
    """

    campaign_name: str  # breadcrumb + stepper `?campaign=` link
    badge_variant: str  # .badge class variant ("warn")
    badge_label: str  # "Nacrt"
    naziv: str
    cilj: str
    ponuda: str
    publika: str
    kanal: str
    platforma: str
    format: str
    jezik: str
    instrukcije: str  # may be empty -> placeholder only
    sacuvaj_nacrt_toast: str


DEFAULT_FIXTURE = OpisKampanjeFixture(
    campaign_name="Proljetna kolekcija",
    badge_variant="warn",
    badge_label="Nacrt",
    naziv="Proljetna kolekcija",
    cilj="Generisanje interesovanja i upita",
    ponuda=(
        "Predstaviti novu liniju proizvoda uz fokus na provjerljive "
        "karakteristike i jednostavan CTA."
    ),
    publika="Postojeći i novi kupci, 25–45 godina.",
    kanal="Društvene mreže",
    platforma="Instagram",
    format="Feed 4:5",
    jezik="SR",
    instrukcije="",
    sacuvaj_nacrt_toast=(
        "Nacrt kampanje — kasnije vodi u CreateCampaign use-case."
    ),
)


def _select(
    options: tuple[str, ...], selected: str, *, id_attr: str | None = None
) -> str:
    """Render a ``<select>`` with the selected option marked.

    Single-value selects (cilj/kanal) pass a one-element tuple so the
    rendered markup matches the mokap's single-option selects.

    ``id_attr`` (optional) injects ``id="..."`` onto the rendered
    ``<select>`` so the bridge ``app.js`` handler can read the chosen
    value via a stable DOM hook. Without it the rendered markup is
    identical to the pre-ACS-GUI-005 version (used by the
    ``render_body`` fallback and by tests that don't care about JS hooks).
    """
    id_html = f' id="{html.escape(id_attr)}"' if id_attr else ""
    opts = "".join(
        f"<option{' selected' if o == selected else ''}>{html.escape(o)}</option>"
        for o in options
    )
    return f'<select{id_html} class="select">{opts}</select>'


def _jezik_select(selected_code: str, *, id_attr: str | None = None) -> str:
    """Render the ``<select>`` for content language (SR/HR/BS/EN).

    A real dropdown with all 4 codes as options -- consistent with the
    Kanal/Platforma/Format selects it sits next to.
    """
    id_html = f' id="{html.escape(id_attr)}"' if id_attr else ""
    opts = "".join(
        f"<option value=\"{html.escape(code)}\""
        f"{' selected' if code == selected_code else ''}>"
        f"{html.escape(label)}</option>"
        for code, label in JEZICI_SADRZAJA
    )
    return f'<select{id_html} class="select">{opts}</select>'


def render_body(fixture: OpisKampanjeFixture | None = None) -> str:
    """Return the Opis kampanje body HTML driven by the supplied fixture.

    As of ACS-GUI-005: every form field carries a stable ``id="f-..."``
    attribute (used by the ``app.js`` save-and-plan handler to read
    values back from the DOM before crossing the js_api boundary), and
    the "Sačuvaj i napravi plan →" affordance is a ``<button
    data-action="save-and-plan">`` rather than a static ``<a href>`` —
    the click now triggers a real ``CreateCampaign + GenerateCampaignPlan``
    sequence via the bridge.
    """
    fx = fixture or DEFAULT_FIXTURE
    return (
        stepper_html(1, fx.campaign_name)
        + '<div class="page-head"><div>'
        "<h2>Opis kampanje</h2>"
        "<p>Definiši cilj i kontekst. Plan se generiše tek iz odobrenog opisa.</p>"
        "</div>"
        f'<span class="badge {html.escape(fx.badge_variant)}">'
        f"{html.escape(fx.badge_label)}</span>"
        "</div>"
        '<div class="grid g2">'
        '<div class="card">'
        '<div class="field"><label>Naziv kampanje</label>'
        f'<input class="input" id="f-naziv" value="{html.escape(fx.naziv)}">'
        "</div>"
        '<div class="field"><label>Cilj kampanje</label>'
        + _select((fx.cilj,), fx.cilj, id_attr="f-cilj")
        + "</div>"
        '<div class="field"><label>Ponuda / proizvod</label>'
        f'<textarea class="textarea" id="f-ponuda">'
        f"{html.escape(fx.ponuda)}</textarea>"
        "</div>"
        '<div class="field"><label>Ciljna publika</label>'
        f'<textarea class="textarea" id="f-publika">'
        f"{html.escape(fx.publika)}</textarea>"
        "</div>"
        "</div>"
        '<div class="card"><h3>Ciljani kanal</h3>'
        '<div class="field"><label>Kanal</label>'
        + _select((fx.kanal,), fx.kanal, id_attr="f-kanal")
        + "</div>"
        '<div class="field"><label>Platforma</label>'
        + _select(PLATFORMS, fx.platforma, id_attr="f-platforma")
        + "</div>"
        '<div class="field"><label>Format</label>'
        + _select(FORMATS, fx.format, id_attr="f-format")
        + "</div>"
        '<div class="field"><label>Jezik sadržaja</label>'
        + _jezik_select(fx.jezik, id_attr="f-jezik")
        + "</div>"
        '<div class="field"><label>Posebne instrukcije</label>'
        f'<textarea class="textarea" id="f-instrukcije" placeholder="Opcionalno">'
        f"{html.escape(fx.instrukcije)}</textarea>"
        "</div>"
        "</div>"
        "</div>"
        '<div class="actions">'
        f'<button class="btn" data-action="toast" '
        f'data-message="{html.escape(fx.sacuvaj_nacrt_toast)}">'
        "Sačuvaj nacrt"
        "</button>"
        # ACS-GUI-005: real button, not a static link. The app.js
        # ``save-and-plan`` handler reads the form via stable id="..."
        # hooks, calls ``window.pywebview.api.create_campaign_and_generate_plan``,
        # and on success navigates to the plan screen with
        # ``?campaign=<id>``.
        '<button class="btn primary" id="f-save-and-plan" data-action="save-and-plan">'
        "Sačuvaj i napravi plan →</button>"
        "</div>"
    )


__all__ = [
    "DEFAULT_FIXTURE",
    "FORMATS",
    "JEZICI_SADRZAJA",
    "OpisKampanjeFixture",
    "PLATFORMS",
    "render_body",
]
