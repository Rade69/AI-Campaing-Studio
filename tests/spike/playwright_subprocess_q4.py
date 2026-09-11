"""Q4 spike reproducer (S2-G8) — proves the SUBPROCESS (not thread) Playwright
pattern actually works on this machine.

Runs the real worker subprocess, fetches the same URL twice (deterministic
body hash), kills the worker mid-session and proves transparent crash
recovery. Prints human-readable evidence to stdout. This is the evidence the
Q4 decision ("subprocess, never thread — F1-052") is correct; if it fails,
S2-G8 §10 requires a follow-up THREAD-BASED contract, not a silent switch.

Skipped when Playwright/Chromium is missing (CI never runs this).
"""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

pytest.importorskip("playwright")

from ai_campaign_studio.infrastructure.web_ingestion.playwright_fetcher import (
    PlaywrightWorker,
)
from ai_campaign_studio.subprocess_runtime.ipc import PlaywrightRequest


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
def port():
    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - http.server API
            body = (
                b"<html><head><title>q4</title></head><body>"
                b"<p>spike page</p></body></html>"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: object) -> None:  # noqa: ARG002
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _request(port: int, request_id: str) -> PlaywrightRequest:
    return PlaywrightRequest(
        request_id=request_id,
        url=f"http://localhost:{port}/",
        timeout=20,
        max_bytes=5_000_000,
        allowed_ports=(80, 443, port),
        dns_overrides={"localhost": ("93.184.216.34",)},
    )


def test_q4_subprocess_pattern_proven(port: int) -> None:
    worker = PlaywrightWorker()
    try:
        worker.start()
        print(f"[Q4] worker subprocess started (pid={worker._proc.pid})")

        first = worker.send_receive(_request(port, "a"), timeout=30)
        second = worker.send_receive(_request(port, "b"), timeout=30)
        assert first.ok and second.ok
        assert first.status_code == second.status_code == 200
        assert first.body_b64 == second.body_b64
        print(
            "[Q4] two fetches of the same URL -> deterministic: "
            f"status={first.status_code}, "
            f"body_b64 identical={first.body_b64 == second.body_b64}"
        )

        # Kill the worker; the NEXT request must transparently respawn it.
        proc = worker._proc
        assert proc is not None
        proc.terminate()
        proc.wait(timeout=10)
        print("[Q4] worker killed mid-session; parent detected death")

        third = worker.send_receive(_request(port, "c"), timeout=30)
        assert third.ok and third.status_code == 200
        print(
            "[Q4] crash recovery: next fetch succeeded after respawn "
            f"(status={third.status_code}, "
            f"body identical to first={third.body_b64 == first.body_b64})"
        )
    finally:
        worker.stop()
        print("[Q4] worker stopped cleanly")
