"""spike_content_studio.py -- SPIKE-001 Content Studio spike entrypoint.

Owns:
  - Rendering the Content Studio HTML for EN or BHS by injecting the
    translations table and the initial language code into the template.
  - Server-side rendering (SSR) of the same template so the page is
    fully populated even before app.js runs (needed for Edge headless
    screenshot, which captures before JS evaluate finishes).
  - Three sub-commands:
        run          open the real pywebview window
        dump         write EN + BHS preview HTMLs to screenshots/
        screenshot   dump + capture PNG screenshots via Edge headless
  - No wiring to bootstrap.py / JobManager / AI providers (per SPIKE_NOTES).

Does not own:
  - Any production-grade packaging, theming, or i18n framework.
  - Any state persistence between runs.

Usage:
  python spike_content_studio.py run               # open pywebview window
  python spike_content_studio.py dump              # write EN + BHS HTMLs
  python spike_content_studio.py screenshot        # dump + capture PNGs
  python spike_content_studio.py screenshot --viewport 1280 800
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

from bs4 import BeautifulSoup  # type: ignore

HERE = pathlib.Path(__file__).resolve().parent
TEMPLATE = HERE / "templates" / "content_studio.html"
SCREENSHOTS = HERE / "screenshots"

# Make `from data.translations import TRANSLATIONS` work whether this
# module is run as a script or imported.
sys.path.insert(0, str(HERE))
from data.translations import TRANSLATIONS  # noqa: E402


# -- rendering ---------------------------------------------------------


def _ssr_apply(soup: BeautifulSoup, lang: str) -> None:
    """Populate the BeautifulSoup tree with the chosen language's strings.

    Mutates the soup in place. Handles:
        [data-i18n]                 -> text content of any element
        [data-i18n-bind]            -> value of <input>, text of <textarea>/<div>
        [data-i18n-bind-placeholder]-> placeholder attribute
        [data-counter]              -> adjacent <span id="{name}-counter">
                                      gets "len / max" text
        #facts-list                 -> <li> children rendered from t['facts']
        active language button      -> adds .bg-slate-900 .text-white
    """
    t = TRANSLATIONS[lang]
    # 1. text content for elements with data-i18n
    for el in soup.select("[data-i18n]"):
        key = el.get("data-i18n")
        if key in t and isinstance(t[key], str):
            for child in list(el.children):
                if isinstance(child, str):
                    child.replace_with("")
            el.append(t[key])
    # 2. value/content binding
    for el in soup.select("[data-i18n-bind]"):
        key = el.get("data-i18n-bind")
        if key not in t:
            continue
        value = t[key]
        if el.name == "input":
            el["value"] = value
        elif el.name == "textarea":
            for child in list(el.children):
                if isinstance(child, str):
                    child.replace_with("")
            el.append(value)
        else:
            for child in list(el.children):
                if isinstance(child, str):
                    child.replace_with("")
            el.append(value)
    # 2b. placeholder binding
    for el in soup.select("[data-i18n-bind-placeholder]"):
        key = el.get("data-i18n-bind-placeholder")
        if key in t and isinstance(t[key], str):
            el["placeholder"] = t[key]
    # 2c. character counters (headline + caption)
    for el in soup.select("[data-counter]"):
        name = el.get("data-counter")
        max_key = el.get("data-counter-max")
        max_val = t.get(max_key, 0) if max_key else 0
        # current value: prefer the just-bound value attribute or text
        if el.name == "textarea":
            current = "".join(el.strings)
        elif el.name == "input":
            current = el.get("value", "")
        else:
            current = "".join(el.strings)
        length = len(current)
        counter = soup.find(id=f"{name}-counter")
        if counter is not None:
            counter.string = f"{length} / {max_val}"
            if length > max_val:
                # add a "text-red-500" class if not present
                classes = counter.get("class", [])
                if isinstance(classes, str):
                    classes = classes.split()
                if "text-red-500" not in classes:
                    classes.append("text-red-500")
                counter["class"] = " ".join(classes)
    # 3. facts list
    facts_list = soup.find(id="facts-list")
    if facts_list is not None and isinstance(t.get("facts"), list):
        facts_list.clear()
        for f in t["facts"]:
            li = soup.new_tag("li")
            li["class"] = (
                "text-[11px] text-slate-700 border-l-2 border-emerald-300 "
                "pl-2 py-1 break-words leading-relaxed"
            )
            div_text = soup.new_tag("div")
            div_text["class"] = "break-words"
            div_text.string = f["text"]
            div_src = soup.new_tag("div")
            div_src["class"] = "text-slate-400 mt-0.5 text-[9px] uppercase tracking-wide"
            div_src.string = f["source"]
            li.append(div_text)
            li.append(div_src)
            facts_list.append(li)
    # 4. active language button
    for btn in soup.select(".lang-btn"):
        is_active = btn.get("data-lang") == lang
        classes = btn.get("class", [])
        if isinstance(classes, str):
            classes = classes.split()
        for marker in ("bg-slate-900", "text-white", "text-slate-700", "hover:bg-slate-200"):
            if marker in classes and not (
                (marker == "bg-slate-900" or marker == "text-white") == is_active
            ):
                classes.remove(marker)
        if is_active and "bg-slate-900" not in classes:
            classes.append("bg-slate-900")
        if is_active and "text-white" not in classes:
            classes.append("text-white")
        if not is_active and "text-slate-700" not in classes:
            classes.append("text-slate-700")
        if not is_active and "hover:bg-slate-200" not in classes:
            classes.append("hover:bg-slate-200")
        btn["class"] = " ".join(classes)
    # 5. <html lang> + <title>
    soup.find("html")["lang"] = "bs" if lang == "bs" else "en"
    title_tag = soup.find("title")
    if title_tag is not None:
        title_tag.string = f"{t['title']} - {t['post_counter']}"


def render_html(lang: str, *, ssr: bool = False) -> str:
    """Render the Content Studio HTML for the given language code.

    Args:
        lang: "en" or "bs"
        ssr:  if True, do server-side rendering so the page is fully
              populated without running app.js. Used for headless
              screenshots. Strips the i18n data + app.js script tag.

    The template contains two placeholders:
        __I18N_DATA__     -> JSON object with all translations
        __INITIAL_LANG__  -> "en" or "bs"
    """
    if lang not in TRANSLATIONS:
        raise ValueError(f"unknown lang: {lang!r}; expected one of {list(TRANSLATIONS)}")
    html = TEMPLATE.read_text(encoding="utf-8")
    if ssr:
        soup = BeautifulSoup(html, "html.parser")
        _ssr_apply(soup, lang)
        # Strip the SPA block: window.__I18N__/window.__LANG__ + app.js.
        for tag in soup.find_all("script", src=re.compile(r"app\.js$")):
            tag.decompose()
        for tag in soup.find_all("script"):
            text = (tag.string or "")
            if "__I18N__" in text or "__LANG__" in text:
                tag.decompose()
        return str(soup)
    i18n_json = json.dumps(TRANSLATIONS, ensure_ascii=False)
    html = html.replace("__I18N_DATA__", i18n_json)
    html = html.replace("__INITIAL_LANG__", lang)
    return html


# -- sub-commands ------------------------------------------------------


def cmd_dump(_args) -> int:
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    for lang in ("en", "bs"):
        out = SCREENSHOTS / f"preview_{lang}.html"
        out.write_text(render_html(lang, ssr=True), encoding="utf-8")
        size = out.stat().st_size
        print(f"  wrote {out}  ({size} bytes)")
    return 0


def find_edge() -> str | None:
    """Return the first existing Microsoft Edge executable, or None."""
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for c in candidates:
        if pathlib.Path(c).exists():
            return c
    return None


def cmd_screenshot(args) -> int:
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    edge = find_edge()
    if not edge:
        print("ERROR: Microsoft Edge not found in standard locations.", file=sys.stderr)
        return 1

    # 1. dump HTMLs (SSR mode, so the page is fully populated without JS)
    for lang in ("en", "bs"):
        (SCREENSHOTS / f"preview_{lang}.html").write_text(
            render_html(lang, ssr=True), encoding="utf-8"
        )

    # 2. capture PNGs
    w, h = args.viewport
    print(f"[spike] Edge: {edge}")
    print(f"[spike] viewport: {w}x{h}")
    for lang in ("en", "bs"):
        html_path = SCREENSHOTS / f"preview_{lang}.html"
        png_path = SCREENSHOTS / f"screenshot_{lang}.png"
        url = html_path.resolve().as_uri()
        cmd = [
            edge,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--hide-scrollbars",
            f"--window-size={w},{h}",
            f"--screenshot={png_path}",
            url,
        ]
        print(f"[spike] capture {lang}: {png_path.name}")
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            print(f"ERROR: Edge exited {proc.returncode} for {lang}", file=sys.stderr)
            print("--- stdout ---", file=sys.stderr)
            print(proc.stdout, file=sys.stderr)
            print("--- stderr ---", file=sys.stderr)
            print(proc.stderr, file=sys.stderr)
            return proc.returncode
        if not png_path.exists():
            print(f"ERROR: {png_path} was not produced", file=sys.stderr)
            return 1
        size = png_path.stat().st_size
        print(f"  -> {png_path}  ({size} bytes)")
    return 0


def cmd_run(args) -> int:
    """Open a real pywebview window. Requires a display session."""
    try:
        import webview  # type: ignore
    except ImportError:
        print("ERROR: pywebview is not installed in this venv.", file=sys.stderr)
        print("       Run: pip install pywebview pywin32", file=sys.stderr)
        return 1

    # Use SSR for the pywebview window too -- it removes a flash of
    # untranslated content and works even if app.js is slow to load.
    html = render_html(args.lang, ssr=True)
    # Write to a file and load via file:// -- this is the most portable
    # approach across pywebview versions on Windows.
    tmp = HERE / "_spike_preview.html"
    tmp.write_text(html, encoding="utf-8")
    try:
        window = webview.create_window(
            title=f"Content Studio (SPIKE-001) -- {args.lang.upper()}",
            url=str(tmp),
            width=args.width,
            height=args.height,
            resizable=True,
        )
        webview.start()
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="spike_content_studio.py",
        description="SPIKE-001 Content Studio spike runner.",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="open the pywebview window")
    p_run.add_argument("--lang", choices=list(TRANSLATIONS), default="en")
    p_run.add_argument("--width", type=int, default=1400)
    p_run.add_argument("--height", type=int, default=900)
    p_run.set_defaults(func=cmd_run)

    p_dump = sub.add_parser("dump", help="write EN + BHS preview HTMLs to screenshots/")
    p_dump.set_defaults(func=cmd_dump)

    p_shot = sub.add_parser(
        "screenshot",
        help="dump + capture EN + BHS PNG screenshots via Edge headless",
    )
    p_shot.add_argument(
        "--viewport",
        type=int,
        nargs=2,
        default=[1400, 900],
        metavar=("W", "H"),
        help="viewport size for Edge headless capture (default: 1400 900)",
    )
    p_shot.set_defaults(func=cmd_screenshot)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
