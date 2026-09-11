"""End-to-end ``PlaywrightFetcher`` reproducer (S2-G8, G-WI-BROWSER).

Drives the REAL worker subprocess (real headless Chromium) against a local
HTTP server. Proves the core value of the fallback — content rendered by
JavaScript that HTTP-only fetch cannot see — plus status/content-type mapping,
the response body cap and the worker-side navigation timeout. Skipped when
Playwright/Chromium is missing (CI installs only ``.[dev]``, S2-G8 §9).
"""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

pytest.importorskip("playwright")

from ai_campaign_studio.infrastructure.web_ingestion.http_fetcher import HttpFetcher
from ai_campaign_studio.infrastructure.web_ingestion.playwright_fetcher import (
    PlaywrightFetcher,
)
from ai_campaign_studio.infrastructure.web_ingestion.url_safety_policy import (
    UrlSafetyPolicy,
)

_RENDERED_MARKER = "Rendered by JavaScript: actual content"


@pytest.fixture(scope="session", autouse=True)
def _skip_without_chromium() -> None:
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(
            "Playwright Chromium not available — run "
            f"`playwright install chromium`: {exc}"
        )


@pytest.fixture()
def served():
    class _Handler(BaseHTTPRequestHandler):
        def _respond(self, status: int, ctype: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 - http.server API
            if self.path == "/":
                body = (
                    b"<html><head><title>spa</title></head><body>"
                    b'<div id="root"></div>'
                    b"<script>document.getElementById('root').textContent = "
                    b"'Rendered by ' + 'JavaScript: actual content';</script>"
                    b"</body></html>"
                )
                self._respond(200, "text/html; charset=utf-8", body)
            elif self.path == "/big":
                body = (b"<html><body><p>" + b"x" * 200_000 + b"</p></body></html>")
                self._respond(200, "text/html; charset=utf-8", body)
            elif self.path == "/slow":
                import time

                time.sleep(10)
                self._respond(200, "text/html", b"<html><body>late</body></html>")
            else:
                self._respond(404, "text/plain", b"not found")

        def log_message(self, *args: object) -> None:  # noqa: ARG002
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    server.daemon_threads = True
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield port
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _policy_for(port: int) -> UrlSafetyPolicy:
    return UrlSafetyPolicy(
        allowed_ports=frozenset({80, 443, port}),
        dns_resolver=lambda host: ("93.184.216.34",),
    )


def _browser_fetcher(port: int, **kwargs: object) -> PlaywrightFetcher:
    return PlaywrightFetcher(
        policy=_policy_for(port),
        dns_overrides={"localhost": ("93.184.216.34",)},
        **kwargs,
    )


def test_renders_content_http_cannot_see(served) -> None:
    port = served
    url = f"http://localhost:{port}/"

    http_only = HttpFetcher(policy=_policy_for(port)).fetch(url)
    assert http_only.error is None
    assert _RENDERED_MARKER.encode("utf-8") not in (http_only.content or b"")

    fetcher = _browser_fetcher(port)
    try:
        rendered = fetcher.fetch(url)
        assert rendered.error is None
        assert rendered.status_code == 200
        assert _RENDERED_MARKER.encode("utf-8") in (rendered.content or b"")
    finally:
        fetcher.stop()


def test_returns_status_content_type_and_final_url(served) -> None:
    port = served
    fetcher = _browser_fetcher(port)
    try:
        result = fetcher.fetch(f"http://localhost:{port}/")
        assert result.error is None
        assert result.status_code == 200
        assert result.content_type is not None
        assert "text/html" in result.content_type
        assert result.final_url == f"http://localhost:{port}/"
    finally:
        fetcher.stop()


def test_body_over_limit_returns_too_large(served) -> None:
    port = served
    fetcher = _browser_fetcher(port, max_bytes=50_000)
    try:
        result = fetcher.fetch(f"http://localhost:{port}/big")
        assert result.error == "too_large"
        assert result.content is None
    finally:
        fetcher.stop()


def test_worker_side_timeout_returns_timeout_error(served) -> None:
    port = served
    fetcher = _browser_fetcher(port, timeout=2)
    try:
        result = fetcher.fetch(f"http://localhost:{port}/slow")
        assert result.error == "timeout"
    finally:
        fetcher.stop()
