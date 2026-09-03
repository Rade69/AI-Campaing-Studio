"""Generate static HTML files for all 9 screens (5 sidebar + 4 workflow).

The shared shell (:mod:`presentation_webview.shell`) is the single
source of truth for sidebar / topbar / CSS / JS — every screen, real or
placeholder, is rendered through :func:`render_shell`. This module
materialises the resulting HTML pages to disk so pywebview can load
them via ``file://`` URLs.

The function takes the target directory as a parameter so tests and
``__main__`` can both drive it without coupling to a hard-coded path.
"""
from __future__ import annotations

import importlib
import shutil
from pathlib import Path

from ..shell import SIDEBAR_ITEMS, Breadcrumb, render_shell
from .pocetna import render_body as render_pocetna_body

# The 4 campaign-workflow screens are NOT sidebar items — they are reached
# via Kampanje → "Otvori" and the in-page stepper. Each keeps the Kampanje
# sidebar link highlighted (active_key="kampanje") and carries an explicit
# breadcrumb chain "Kampanje › <campaign> › <screen>".
WORKFLOW_ITEMS: tuple[tuple[str, str], ...] = (
    ("opis_kampanje", "Opis kampanje"),
    ("plan_kampanje", "Plan kampanje"),
    ("studio_sadrzaja", "Studio sadržaja"),
    ("pregled_izvoz", "Pregled i izvoz"),
)

# Package-relative source of the shared CSS/JS/logo this module vendors into
# every generated ``target_dir``. Every generated page links to
# ``../static/app.css``/``../static/app.js``/``brand-logo.png`` (see
# shell.render_shell) -- without this copy step those links 404 and
# pywebview renders bare, incomplete HTML.
_STATIC_SRC = Path(__file__).resolve().parent.parent / "static"


def _body_for(key: str) -> str:
    """Return the body HTML fragment for the given screen key."""
    if key == "pocetna":
        # render_pocetna_body() uses DEFAULT_FIXTURE when no argument is
        # passed — that keeps the import graph one-directional and
        # avoids a circular import through screens/__init__.py.
        return render_pocetna_body()
    module = importlib.import_module(
        f"ai_campaign_studio.presentation_webview.screens.{key}"
    )
    return module.render_body()


def _write_screen(target_dir: Path, key: str, html: str) -> Path:
    """Write one rendered page to ``target_dir/screens/{key}/index.html``."""
    page_dir = target_dir / "screens" / key
    page_dir.mkdir(parents=True, exist_ok=True)
    page_path = page_dir / "index.html"
    page_path.write_text(html, encoding="utf-8")
    return page_path


def _copy_static_assets(target_dir: Path) -> None:
    """Copy the package's static assets into target_dir/static/.

    Every generated screen references these via a relative ``../static/``
    link, so they must exist alongside the generated ``screens/`` tree,
    not just in the source package.
    """
    dest = target_dir / "static"
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("app.css", "app.js", "brand-logo.png"):
        shutil.copyfile(_STATIC_SRC / name, dest / name)


def write_all_pages(target_dir: Path) -> dict[str, Path]:
    """Render every screen through ``render_shell`` into ``target_dir``.

    Writes ``target_dir/screens/{key}/index.html`` for each screen in
    :data:`shell.SIDEBAR_ITEMS` (Početna, Brend, Kampanje, Kalendar,
    Podešavanja) *and* each screen in :data:`WORKFLOW_ITEMS` (Opis
    kampanje, Plan kampanje, Studio sadržaja, Pregled i izvoz), and copies
    the shared CSS/JS/logo assets into ``target_dir/static/`` so the
    relative links in each page actually resolve. Returns a mapping
    ``{key: file_path}`` for callers that need the entry-point URL
    (pywebview).
    """
    target_dir = Path(target_dir)
    _copy_static_assets(target_dir)
    out: dict[str, Path] = {}
    for key, label, _icon, _href in SIDEBAR_ITEMS:
        body = _body_for(key)
        html = render_shell(active_key=key, page_title=label, body_html=body)
        out[key] = _write_screen(target_dir, key, html)
    for key, label in WORKFLOW_ITEMS:
        module = importlib.import_module(
            f"ai_campaign_studio.presentation_webview.screens.{key}"
        )
        body = module.render_body()
        campaign_name = module.DEFAULT_FIXTURE.campaign_name
        crumbs = [
            Breadcrumb("Kampanje", "../kampanje/index.html"),
            Breadcrumb(campaign_name, None),
            Breadcrumb(label, None),
        ]
        html = render_shell(
            active_key="kampanje",
            page_title=label,
            body_html=body,
            crumbs=crumbs,
        )
        out[key] = _write_screen(target_dir, key, html)
    return out


__all__ = ["WORKFLOW_ITEMS", "write_all_pages"]
