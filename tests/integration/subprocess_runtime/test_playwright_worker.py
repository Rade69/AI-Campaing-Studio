"""Subprocess runtime integration tests (S2-G8) — ``PlaywrightWorker``
parent-side manager against the real worker subprocess.

Covers the parent↔subprocess lifecycle: idempotent start, deterministic
responses, crash recovery (kill → transparent respawn) and clean stop.
Skipped when Playwright/Chromium is missing (CI installs only ``.[dev]``).
"""

from __future__ import annotations

import threading
import time
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
            if self.path == "/slow":
                time.sleep(5)
            body = b"<html><head></head><body><p>fixture page</p></body></html>"
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


def _request(port: int, request_id: str = "r", path: str = "/") -> PlaywrightRequest:
    return PlaywrightRequest(
        request_id=request_id,
        url=f"http://localhost:{port}{path}",
        timeout=20,
        max_bytes=5_000_000,
        allowed_ports=(80, 443, port),
        dns_overrides={"localhost": ("93.184.216.34",)},
    )


def test_start_is_idempotent(port: int) -> None:
    worker = PlaywrightWorker()
    try:
        worker.start()
        proc = worker._proc
        assert proc is not None
        worker.start()
        assert worker._proc is proc
        assert worker.is_alive() is True
    finally:
        worker.stop()


def test_two_fetches_are_deterministic(port: int) -> None:
    worker = PlaywrightWorker()
    try:
        worker.start()
        first = worker.send_receive(_request(port, "a"), timeout=30)
        second = worker.send_receive(_request(port, "b"), timeout=30)
        assert first.ok is True
        assert second.ok is True
        assert first.status_code == second.status_code == 200
        assert first.body_b64 == second.body_b64
    finally:
        worker.stop()


def test_crash_recovery_kill_then_fetch_succeeds(port: int) -> None:
    worker = PlaywrightWorker()
    try:
        worker.start()
        first = worker.send_receive(_request(port, "a"), timeout=30)
        assert first.ok is True

        # Kill the worker mid-session; the next request must transparently
        # respawn it and still succeed (crash recovery, G-WI-BROWSER).
        proc = worker._proc
        assert proc is not None
        proc.terminate()
        proc.wait(timeout=10)
        assert worker.is_alive() is False

        second = worker.send_receive(_request(port, "b"), timeout=30)
        assert second.ok is True
        assert second.status_code == 200
    finally:
        worker.stop()


def test_stop_terminates_worker(port: int) -> None:
    worker = PlaywrightWorker()
    worker.start()
    assert worker.is_alive() is True
    worker.stop()
    assert worker.is_alive() is False


def test_parent_watchdog_terminates_and_respawns(port: int) -> None:
    # Parent-side watchdog: if the worker does not answer within the parent's
    # timeout (here 1s, while the worker's own page timeout is 30s and the
    # server sleeps 5s), the worker is terminated and respawned (clean state,
    # F1-052) and a timeout result is returned.
    worker = PlaywrightWorker()
    try:
        worker.start()
        request = PlaywrightRequest(
            request_id="slow",
            url=f"http://localhost:{port}/slow",
            timeout=30,
            max_bytes=5_000_000,
            allowed_ports=(80, 443, port),
            dns_overrides={"localhost": ("93.184.216.34",)},
        )
        result = worker.send_receive(request, timeout=1)
        assert result.ok is False
        assert result.error_code == "timeout"
        # The worker was respawned after the watchdog fired.
        assert worker.is_alive() is True
        second = worker.send_receive(_request(port, "after"), timeout=30)
        assert second.ok is True
    finally:
        worker.stop()
