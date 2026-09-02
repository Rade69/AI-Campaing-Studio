"""Standalone pywebview entry point for AI Campaign Studio.

Run as ``python -m ai_campaign_studio.presentation_webview`` (or via
``python -m ai_campaign_studio.presentation_webview --width 1400 --height 900``).
Does NOT touch ``bootstrap.py`` or ``main.py`` — owns its own
composition root for GUI-BASE (per ACS-GUI-001 task contract,
§"Zašto ne bootstrap.py/main.py").

Security policy enforced here
-----------------------------

Per ``docs/PYWEBVIEW_SECURITY.md`` §1 + §2, every product invocation
passes ``gui='edgechromium'`` and ``debug=False`` *explicitly*. A
missing Microsoft WebView2 Runtime is surfaced as a loud, actionable
error rather than the silent ``mshtml`` fallback pywebview performs by
default. The WebView2 probe is best-effort: if the OS lookup itself
fails (corrupt registry, missing WinDLL on Linux test machine, etc.),
the actual ``webview.start`` call is the ultimate arbiter and will
raise ``Exception`` with a pywebview-specific message which we catch
and re-raise as ``WebView2MissingError`` with installation guidance.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path


class WebView2MissingError(RuntimeError):
    """Raised when WebView2 Runtime is not present on the host."""


def _probe_webview2() -> None:
    """Verify WebView2 Runtime is installed (Windows hosts).

    On non-Windows hosts (CI matrix, dev macOS/Linux) the probe is
    skipped — pywebview picks an appropriate native backend and the
    security policy's "explicit gui='edgechromium' + fail-loud on
    missing" only matters on the actual target platform.
    """
    if sys.platform != "win32":
        return
    try:
        import winreg  # noqa: PLC0415  (Windows-only)
    except ImportError:
        # pywin32 not installed in this environment — skip probe and
        # let ``webview.start`` be the final arbiter.
        return
    registry_paths = (
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients"
         r"\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"),
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\Microsoft\EdgeUpdate\Clients"
         r"\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"),
    )
    for hive, path in registry_paths:
        try:
            with winreg.OpenKey(hive, path) as key:
                winreg.QueryValueEx(key, "pv")
                return  # found
        except FileNotFoundError:
            continue
        except OSError:
            continue
    raise WebView2MissingError(
        "Microsoft WebView2 Runtime nije pronađen na ovom računaru.\n"
        "AI Campaign Studio zahtijeva WebView2 za prikazivanje GUI-ja.\n"
        "Preuzmite i instalirajte Microsoft Edge WebView2 Runtime "
        "Evergreen Bootstrapper sa:\n"
        "  https://developer.microsoft.com/microsoft-edge/webview2/\n"
        "i pokrenite instalaciju prije ponovnog pokretanja aplikacije."
    )


def _open_window(html_path: Path, *, width: int, height: int) -> None:
    """Create and start the pywebview window. Imports are local so the
    module can be imported on test machines without pywebview installed
    (architecture tests need this)."""
    import webview  # type: ignore[import-not-found,import-untyped]  # noqa: PLC0415

    _probe_webview2()
    webview.create_window(
        title="AI Campaign Studio",
        url=html_path.resolve().as_uri(),
        width=width,
        height=height,
        resizable=True,
    )
    # ``gui='edgechromium'`` + ``debug=False`` are mandatory per the
    # security policy. Anything else is a regression.
    webview.start(gui="edgechromium", debug=False)


def _materialise_pages(out_dir: Path) -> Path:
    """Render all 5 screens into ``out_dir`` and return the Početna path.

    The shared :func:`shell.render_shell` is the only place the sidebar,
    topbar, CSS link, CSP and JS link are emitted — every screen goes
    through it, so the 4 placeholder screens (Brend / Kampanje / Kalendar
    / Podešavanja) do not duplicate any shell markup. The Početna file
    is returned because that is the entry point pywebview loads.
    """
    from .screens import write_all_pages

    pages = write_all_pages(out_dir)
    return pages["pocetna"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ai_campaign_studio.presentation_webview",
        description="AI Campaign Studio — pywebview GUI entry point (GUI-BASE).",
    )
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=900)
    args = parser.parse_args(argv)

    # Per-launch working dir for generated pages. The dir lives in the
    # system temp area; we own it for the duration of this process.
    out_dir = Path(tempfile.mkdtemp(prefix="ai_campaign_studio_gui_"))

    try:
        html_path = _materialise_pages(out_dir)
    except Exception:  # noqa: BLE001
        print(
            "Greška: nije moguće renderirati GUI ekrane.",
            file=sys.stderr,
        )
        return 1

    try:
        _open_window(html_path, width=args.width, height=args.height)
    except WebView2MissingError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        # Catch-all: if pywebview falls back to ``mshtml`` for any
        # reason, surface that loudly instead of silent degradation.
        if "mshtml" in str(exc).lower():
            print(
                "Greška: pywebview je pao na zastarjeli mshtml renderer.\n"
                "To se ne smije desiti — Edge WebView2 mora biti eksplicitno "
                "dostupan. Pokrenite 'python -m ai_campaign_studio "
                "--health-check' da potvrdite okruženje.",
                file=sys.stderr,
            )
            return 3
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
