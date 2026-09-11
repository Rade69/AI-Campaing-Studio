"""Reproducer tests for ``js_render_detector`` (S2-G8, canonical plan §8).

Deterministic, offline: pure string heuristics, no network, no Playwright.
Covers the 0/1/2+ marker confidence threshold, the non-HTML content-type
short-circuit, the empty-body SPA shell and the weak-signal "do not activate"
rule.
"""

from __future__ import annotations

import pytest

from ai_campaign_studio.infrastructure.web_ingestion.js_render_detector import (
    detect_js_heavy,
    has_spa_shell,
)


def test_react_root_plus_module_is_js_heavy() -> None:
    html = (
        "<html><head><title>x</title></head><body>"
        "<div id=\"root\"></div>"
        "<script type=\"module\" src=\"/main.js\"></script>"
        "<p>Static fallback content, long enough that the body is clearly "
        "not an empty shell for this test case.</p>"
        "<p>More text to push the body well past the empty-body threshold.</p>"
        "</body></html>"
    )
    is_heavy, reason = detect_js_heavy("text/html", html)
    assert is_heavy is True
    assert reason == "js_heavy_react_root+module"


def test_static_html_has_no_js_markers() -> None:
    is_heavy, reason = detect_js_heavy("text/html", "<p>Hello world</p>")
    assert is_heavy is False
    assert reason == "no_js_markers"


@pytest.mark.parametrize(
    ("html", "expected_reason"),
    [
        ("<div id=\"app\"></div>", "weak_signal_vue_root"),
        ("<app-root></app-root>", "weak_signal_angular_root"),
        ("<script type=\"module\"></script>", "weak_signal_module"),
    ],
)
def test_single_marker_is_weak_signal_and_does_not_activate(
    html: str, expected_reason: str
) -> None:
    is_heavy, reason = detect_js_heavy("text/html", html)
    assert is_heavy is False
    assert reason == expected_reason


@pytest.mark.parametrize(
    "content_type",
    [
        "application/json",
        "application/xml",
        "text/plain",
        "image/png",
        "application/pdf",
    ],
)
def test_non_html_content_type_is_never_js_heavy(content_type: str) -> None:
    is_heavy, reason = detect_js_heavy(content_type, "<div id=\"root\"></div>")
    assert is_heavy is False
    assert reason == "not_html"


def test_empty_body_shell_is_js_heavy() -> None:
    html = (
        "<html><head><title>x</title></head><body>"
        '<div id="root"></div></body></html>'
    )
    is_heavy, reason = detect_js_heavy("text/html", html)
    assert is_heavy is True
    assert reason.startswith("js_heavy_empty_body")


def test_none_content_type_is_treated_as_html() -> None:
    is_heavy, reason = detect_js_heavy(None, "<p>Hello world</p>")
    assert is_heavy is False
    assert reason == "no_js_markers"


def test_spa_shell_detection_for_page_classifier() -> None:
    assert has_spa_shell("<div id=\"root\"></div>") is True
    assert has_spa_shell("__NEXT_DATA__") is True
    assert has_spa_shell("<p>static</p>") is False
