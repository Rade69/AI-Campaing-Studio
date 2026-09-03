"""Tests for the cross-launch window-state helpers in ``__main__``.

Covers the two post-merge UX fixes:

* :func:`_load_window_state` / :func:`_save_window_state` — remember
  the last window size across launches.
* :func:`_cleanup_temp_dir` — best-effort removal of the per-launch
  generated-pages directory.

Both helpers are pure functions of the filesystem (no pywebview, no
display) so they're easy to drive from tests with ``tmp_path``.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from ai_campaign_studio.presentation_webview.__main__ import (
    _cleanup_temp_dir,
    _load_window_state,
    _save_window_state,
    _user_data_dir,
)

# ----- _user_data_dir --------------------------------------------------------


def test_user_data_dir_is_absolute_path() -> None:
    p = _user_data_dir()
    assert isinstance(p, Path)
    # On every supported platform, the resolved path is absolute.
    assert p.is_absolute()


def test_user_data_dir_platform_specific() -> None:
    """The result must follow the platform convention.

    We don't assert a full path (the test would be brittle across
    Windows versions / user names); we just verify the function picks
    the right base for the running platform.
    """
    import sys

    p = _user_data_dir()
    if sys.platform == "win32":
        assert "ai-campaign-studio" in p.parts
    elif sys.platform == "darwin":
        assert "Library" in p.parts
        assert "Application Support" in p.parts
    else:
        # Linux + others: XDG or ~/.local/share
        assert p.parent.name in {"ai-campaign-studio", "share"}


# ----- _load_window_state / _save_window_state ------------------------------


def test_load_returns_empty_when_no_state_file(tmp_path: Path) -> None:
    with patch(
        "ai_campaign_studio.presentation_webview.__main__._user_data_dir",
        return_value=tmp_path,
    ):
        assert _load_window_state() == {}


def test_load_returns_empty_on_corrupted_json(tmp_path: Path) -> None:
    state = tmp_path / "window-state.json"
    state.write_text("{not valid json", encoding="utf-8")
    with patch(
        "ai_campaign_studio.presentation_webview.__main__._user_data_dir",
        return_value=tmp_path,
    ):
        assert _load_window_state() == {}


def test_load_returns_empty_on_non_dict_payload(tmp_path: Path) -> None:
    state = tmp_path / "window-state.json"
    state.write_text("[1, 2, 3]", encoding="utf-8")
    with patch(
        "ai_campaign_studio.presentation_webview.__main__._user_data_dir",
        return_value=tmp_path,
    ):
        assert _load_window_state() == {}


def test_load_rejects_out_of_range_values(tmp_path: Path) -> None:
    state = tmp_path / "window-state.json"
    # Width too small, height too large, plus a stray string key.
    state.write_text(
        json.dumps({"width": 100, "height": 9999, "x": "abc"}),
        encoding="utf-8",
    )
    with patch(
        "ai_campaign_studio.presentation_webview.__main__._user_data_dir",
        return_value=tmp_path,
    ):
        assert _load_window_state() == {}


def test_load_ignores_bool_values_even_though_int_subclass() -> None:
    """``True``/``False`` are technically ``int`` in Python — make sure
    they don't slip through the size check (a 1x1 window would be bad).
    """
    bogus = json.dumps({"width": True, "height": False})
    with patch("pathlib.Path.read_text", return_value=bogus):
        assert _load_window_state() == {}


def test_save_then_load_round_trip(tmp_path: Path) -> None:
    with patch(
        "ai_campaign_studio.presentation_webview.__main__._user_data_dir",
        return_value=tmp_path,
    ):
        _save_window_state(1600, 1000)
        assert _load_window_state() == {"width": 1600, "height": 1000}


def test_save_creates_user_data_dir_if_missing(tmp_path: Path) -> None:
    target = tmp_path / "deep" / "nested" / "dir"
    assert not target.exists()
    with patch(
        "ai_campaign_studio.presentation_webview.__main__._user_data_dir",
        return_value=target,
    ):
        _save_window_state(1024, 768)
        assert (target / "window-state.json").exists()


def test_save_swallows_os_errors(tmp_path: Path) -> None:
    """A read-only / broken user data dir must not crash the app."""
    # A Path whose mkdir would fail because the parent is a file.
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    broken = blocker / "ai-campaign-studio"
    with patch(
        "ai_campaign_studio.presentation_webview.__main__._user_data_dir",
        return_value=broken,
    ):
        # Should NOT raise.
        _save_window_state(800, 600)
        assert not (broken / "window-state.json").exists()


def test_load_clamps_to_safe_window_range(tmp_path: Path) -> None:
    state = tmp_path / "window-state.json"
    state.write_text(
        json.dumps({"width": 1024, "height": 768}),
        encoding="utf-8",
    )
    with patch(
        "ai_campaign_studio.presentation_webview.__main__._user_data_dir",
        return_value=tmp_path,
    ):
        loaded = _load_window_state()
        assert loaded == {"width": 1024, "height": 768}
        # All loaded values are in the 640..4096 band.
        for v in loaded.values():
            assert 640 <= v <= 4096


# ----- _cleanup_temp_dir -----------------------------------------------------


def test_cleanup_temp_dir_removes_directory(tmp_path: Path) -> None:
    target = tmp_path / "ai_campaign_studio_gui_xxx"
    target.mkdir()
    (target / "screens").mkdir()
    (target / "screens" / "pocetna").mkdir()
    (target / "screens" / "pocetna" / "index.html").write_text(
        "<html></html>", encoding="utf-8"
    )
    assert target.exists()
    _cleanup_temp_dir(target)
    assert not target.exists()


def test_cleanup_temp_dir_on_nonexistent_path_is_noop(tmp_path: Path) -> None:
    ghost = tmp_path / "never-existed"
    # Should NOT raise.
    _cleanup_temp_dir(ghost)


def test_cleanup_temp_dir_survives_ignore_errors(tmp_path: Path) -> None:
    """If rmtree hits a locked file it should still terminate cleanly.

    ``ignore_errors=True`` means PermissionError on Windows is swallowed
    the same way as FileNotFoundError — we just verify the function
    returns without raising.
    """
    target = tmp_path / "ai_campaign_studio_gui_yyy"
    target.mkdir()
    _cleanup_temp_dir(target)
    # The dir is removed in the easy case.
    assert not target.exists()
