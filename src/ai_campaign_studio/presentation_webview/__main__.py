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
import atexit
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

# --- User data dir (cross-platform) -----------------------------------------
# A small, dependency-free replacement for ``platformdirs`` so the GUI has a
# stable place to remember window geometry across launches. Deliberately
# kept here (not in some utility module) so the GUI entry point stays a
# self-contained composition root.

_WINDOW_STATE_FILE = "window-state.json"


def _user_data_dir() -> Path:
    """Return the OS-conventional per-user data dir for AI Campaign Studio.

    * Windows: ``%LOCALAPPDATA%\\ai-campaign-studio`` (falls back to ``~``)
    * macOS:   ``~/Library/Application Support/ai-campaign-studio``
    * Linux:   ``$XDG_DATA_HOME/ai-campaign-studio`` (falls back to
      ``~/.local/share/ai-campaign-studio``)
    """
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return Path(base) / "ai-campaign-studio"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "ai-campaign-studio"
    xdg = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return Path(xdg) / "ai-campaign-studio"


def _load_window_state() -> dict[str, int]:
    """Return the last-saved window size, or empty dict on miss/corrupt.

    Anything outside the sane range 640..4096 is ignored — protects
    against a corrupted file with absurd values crashing the next launch.
    """
    p = _user_data_dir() / _WINDOW_STATE_FILE
    try:
        raw = p.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return {}
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, int] = {}
    for key in ("width", "height"):
        v = data.get(key)
        if isinstance(v, int) and not isinstance(v, bool) and 640 <= v <= 4096:
            out[key] = v
    return out


def _save_window_state(width: int, height: int) -> None:
    """Persist current window size to user data dir (best-effort).

    Disk errors are swallowed — the worst case is that the next launch
    falls back to defaults, which is a strictly better outcome than
    refusing to start the app.
    """
    try:
        d = _user_data_dir()
        d.mkdir(parents=True, exist_ok=True)
        (d / _WINDOW_STATE_FILE).write_text(
            json.dumps({"width": int(width), "height": int(height)}),
            encoding="utf-8",
        )
    except OSError:
        pass


def _cleanup_temp_dir(d: Path) -> None:
    """Best-effort removal of the per-launch generated-pages dir.

    Registered with :mod:`atexit` so it fires on normal interpreter
    shutdown (i.e. when ``webview.start()`` returns because the user
    closed the window). On hard crashes the dir leaks — that is the
    well-known cost of ``tempfile.mkdtemp``; periodic disk cleanup
    picks those up.
    """
    try:
        shutil.rmtree(d, ignore_errors=True)
    except Exception:  # noqa: BLE001
        pass


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


def _build_bridge() -> Any:
    """Construct the js_api bridge (ACS-GUI-005, BF-2 explicit seam).

    Extracted as a module-level helper so the unit test
    ``test_pywebview_start_uses_explicit_edgechromium_and_debug_false``
    can patch the bridge construction WITHOUT triggering the full
    composition root (``create_bootstrap`` → DB conn, migrations,
    logging, keyring). Without this seam, the test was silently
    dependent on filesystem/DB/logging side effects it never
    intended to exercise — fine on a developer workstation, but
    brittle across CI/sandbox environments (Codex caught this
    via a PermissionError on the log file in its sandbox).

    The bridge owns the full GUI→backend wiring (brand seeding +
    provider resolution + CreateCampaign + GenerateCampaignPlan)
    and exposes exactly one public method to the WebView2
    JavaScript context, per docs/PYWEBVIEW_SECURITY.md §3.
    """
    from .bridge import CampaignBridgeApi  # noqa: PLC0415  (test seam)

    return CampaignBridgeApi()


def _open_window(html_path: Path, *, width: int, height: int) -> None:
    """Create and start the pywebview window. Imports are local so the
    module can be imported on test machines without pywebview installed
    (architecture tests need this)."""
    import webview  # type: ignore[import-not-found,import-untyped]  # noqa: PLC0415

    _probe_webview2()

    bridge = _build_bridge()

    window = webview.create_window(
        title="AI Campaign Studio",
        url=html_path.resolve().as_uri(),
        width=width,
        height=height,
        resizable=True,
        js_api=bridge,
    )

    # Persist window size on every resize. We use ``resized`` rather
    # than ``closed`` because the WinForms edgechromium backend's
    # ``closed`` event fires *after* ``gui.get_size`` starts returning
    # ``None`` (the GUI is being torn down), so accessing
    # ``window.width`` / ``window.height`` from a ``closed`` handler
    # raises ``TypeError`` before we can save. ``resized`` fires while
    # the window is still alive, so the size is reliable. State
    # persistence is therefore continuous — by the time the user
    # closes the window, the last-saved size already reflects their
    # final choice.
    def _on_resized() -> None:
        try:
            _save_window_state(
                window.width,  # type: ignore[union-attr]
                window.height,  # type: ignore[union-attr]
            )
        except Exception:  # noqa: BLE001
            pass

    window.events.resized += _on_resized  # type: ignore[union-attr]

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
    # Last-saved window size becomes the default. CLI --width/--height
    # still override the saved value.
    state = _load_window_state()
    default_width = state.get("width", 1440)
    default_height = state.get("height", 900)

    parser = argparse.ArgumentParser(
        prog="ai_campaign_studio.presentation_webview",
        description="AI Campaign Studio — pywebview GUI entry point (GUI-BASE).",
    )
    parser.add_argument("--width", type=int, default=default_width)
    parser.add_argument("--height", type=int, default=default_height)
    args = parser.parse_args(argv)

    # Per-launch working dir for generated pages. We register a cleanup
    # hook so the dir is removed on normal interpreter shutdown (which
    # is what happens when the user closes the window — ``webview.start``
    # returns and ``main`` returns).
    out_dir = Path(tempfile.mkdtemp(prefix="ai_campaign_studio_gui_"))
    atexit.register(_cleanup_temp_dir, out_dir)

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
