"""Tests for the WebView2 fail-loud policy in __main__.

Per docs/PYWEBVIEW_SECURITY.md section 1, a missing WebView2 Runtime must
raise a loud, actionable error rather than silently falling back to
mshtml. These tests use unittest.mock to simulate the absent Runtime
without touching the real registry.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from ai_campaign_studio.presentation_webview.__main__ import (
    WebView2MissingError,
    _probe_webview2,
)


class _FakeWinreg:
    """Minimal stand-in for the stdlib winreg module on non-Windows test hosts."""

    HKEY_LOCAL_MACHINE = 0

    def __init__(self, *, available: bool = False) -> None:
        self._available = available
        self.opened_paths: list[tuple[int, str]] = []

    def OpenKey(self, hive: int, path: str) -> object:
        self.opened_paths.append((hive, path))
        if self._available:
            return MagicMock()
        raise FileNotFoundError(path)

    @staticmethod
    def QueryValueEx(key: object, value_name: str) -> tuple[object, int]:
        """Mimic real ``winreg.QueryValueEx`` for the ``pv`` value.

        Returns ``(<version-string>, winreg.REG_SZ)`` when the registry key
        is opened. The real ``winreg.REG_SZ`` constant equals 1, but the
        production code only consumes the returned value, so returning a
        plain int is sufficient.
        """
        return ("120.0.0.0", 1)


def test_webview2_missing_error_is_runtime_error_subclass() -> None:
    assert issubclass(WebView2MissingError, RuntimeError)


def test_probe_returns_silently_when_webview2_is_installed() -> None:
    fake = _FakeWinreg(available=True)
    with patch.object(sys, "platform", "win32"), patch.dict(
        sys.modules, {"winreg": fake}
    ):
        _probe_webview2()
    assert fake.opened_paths, "probe did not query any registry path"


def test_probe_raises_when_webview2_is_missing() -> None:
    """Missing WebView2 -> loud, actionable WebView2MissingError with download URL."""
    fake = _FakeWinreg(available=False)
    with patch.object(sys, "platform", "win32"), patch.dict(
        sys.modules, {"winreg": fake}
    ):
        with pytest.raises(WebView2MissingError) as excinfo:
            _probe_webview2()
    msg = str(excinfo.value)
    assert "WebView2" in msg
    assert "developer.microsoft.com" in msg or "Evergreen" in msg


def test_probe_is_noop_off_windows() -> None:
    fake = _FakeWinreg(available=False)
    with patch.object(sys, "platform", "linux"), patch.dict(
        sys.modules, {"winreg": fake}
    ):
        _probe_webview2()  # no exception
    assert fake.opened_paths == [], (
        "winreg should not be touched on non-Windows platforms"
    )


def test_pywebview_start_uses_explicit_edgechromium_and_debug_false() -> None:
    """Acceptance: webview.start must pass gui='edgechromium' and debug=False.

    ACS-GUI-005 BF-2 fix: ``_open_window`` now delegates bridge
    construction to a module-level ``_build_bridge`` seam so this
    test does not silently depend on the full composition root
    (``create_bootstrap`` → DB conn, migrations, logging setup,
    SecretStore). Without the seam, the test was hermetic on a
    dev workstation but brittle across CI/sandbox environments
    (Codex caught it via PermissionError on the log file).
    """
    import pathlib
    fake_webview = MagicMock()
    fake_bridge = MagicMock()
    with patch.dict(sys.modules, {"webview": fake_webview}), patch(
        "ai_campaign_studio.presentation_webview.__main__._probe_webview2"
    ), patch(
        "ai_campaign_studio.presentation_webview.__main__._build_bridge",
        return_value=fake_bridge,
    ):
        from ai_campaign_studio.presentation_webview.__main__ import _open_window

        _open_window(
            pathlib.Path("/tmp/fake.html"),
            width=1440,
            height=900,
        )

    fake_webview.create_window.assert_called_once()
    fake_webview.start.assert_called_once()
    kwargs = fake_webview.start.call_args.kwargs
    assert kwargs.get("gui") == "edgechromium", (
        f"webview.start must pass gui='edgechromium' explicitly, got {kwargs!r}"
    )
    assert kwargs.get("debug") is False, (
        f"webview.start must pass debug=False explicitly, got {kwargs!r}"
    )
