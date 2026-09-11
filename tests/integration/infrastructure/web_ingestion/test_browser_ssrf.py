"""Browser SSRF reproducer (S2-G8, G-WI-BROWSER) — real Chromium in a
subprocess against a real local HTTP server.

Proves the worker's ``context.route()`` guard blocks in-page requests (iframe
and redirect hops) to literal private IPs BEFORE any connection is opened,
using a canary server hit-counter that must stay at zero. The top-level URL is
SSRF-validated by the parent fetcher's policy first; the worker re-validates
every browser-issued request with the same policy (canonical plan §6.3).

Skipped when Playwright (or its Chromium) is not installed — CI installs only
``.[dev]`` so these never run there (S2-G8 §9).
"""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

pytest.importorskip("playwright")

from ai_campaign_studio.infrastructure.web_ingestion.playwright_fetcher import (
    PlaywrightFetcher,
)
from ai_campaign_studio.infrastructure.web_ingestion.url_safety_policy import (
    UrlSafetyPolicy,
)


@pytest.fixture(scope="session", autouse=True)
def _skip_without_chromium() -> None:
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
    except Exception as exc:  # noqa: BLE001 - surface a clear skip message
        pytest.skip(
            "Playwright Chromium not available — run "
            f"`playwright install chromium`: {exc}"
        )


@pytest.fixture()
def served():
    hits = {"leak": 0}
    lock = threading.Lock()

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
                    "<html><head><title>ok</title></head><body>"
                    f'<iframe src="http://127.0.0.1:{port}/leak"></iframe>'
                    "<p>page loaded</p></body></html>"
                ).encode()
                self._respond(200, "text/html; charset=utf-8", body)
            elif self.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", f"http://127.0.0.1:{port}/leak")
                self.send_header("Content-Length", "0")
                self.end_headers()
            elif self.path == "/leak":
                with lock:
                    hits["leak"] += 1
                self._respond(200, "text/plain", b"leaked")
            else:
                self._respond(404, "text/plain", b"not found")

        def log_message(self, *args: object) -> None:  # noqa: ARG002
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield port, hits
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture()
def fetcher(served):
    port, _hits = served
    policy = UrlSafetyPolicy(
        allowed_ports=frozenset({80, 443, port}),
        dns_resolver=lambda host: ("93.184.216.34",),
    )
    fetcher = PlaywrightFetcher(
        policy=policy,
        dns_overrides={"localhost": ("93.184.216.34",)},
    )
    yield fetcher
    fetcher.stop()


def test_top_level_literal_imds_is_unsafe(fetcher: PlaywrightFetcher) -> None:
    result = fetcher.fetch("http://169.254.169.254/latest/meta-data/")
    assert result.error is not None
    assert result.error.startswith("unsafe:")
    assert "169.254.169.254" in result.error


def test_top_level_loopback_literal_is_unsafe(
    fetcher: PlaywrightFetcher, served
) -> None:
    port, _hits = served
    result = fetcher.fetch(f"http://127.0.0.1:{port}/")
    assert result.error is not None
    assert result.error.startswith("unsafe:")
    assert "127.0.0.1" in result.error


def test_iframe_to_private_ip_is_blocked(fetcher: PlaywrightFetcher, served) -> None:
    port, hits = served
    result = fetcher.fetch(f"http://localhost:{port}/")
    assert result.error is None
    assert result.status_code == 200
    # The page rendered, but the iframe request was aborted BEFORE connecting.
    assert hits["leak"] == 0
    assert b"page loaded" in (result.content or b"")


def test_redirect_to_literal_ip_is_blocked(fetcher: PlaywrightFetcher, served) -> None:
    port, hits = served
    result = fetcher.fetch(f"http://localhost:{port}/redirect")
    assert result.error is not None
    assert result.error.startswith("unsafe:")
    assert hits["leak"] == 0
