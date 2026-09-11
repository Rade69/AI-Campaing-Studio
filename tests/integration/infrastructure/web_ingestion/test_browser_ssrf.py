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
import time
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
            elif self.path == "/redirect-slow":
                # Delays the response past the redirect pre-check's read
                # timeout (F2 regression — see test below).
                time.sleep(2.0)
                self.send_response(302)
                self.send_header("Location", f"http://127.0.0.1:{port}/leak")
                self.send_header("Content-Length", "0")
                self.end_headers()
            elif self.path == "/leak":
                with lock:
                    hits["leak"] += 1
                self._respond(200, "text/plain", b"leaked")
            elif self.path == "/sw.js":
                # A real, valid Service Worker script — required so the
                # outcome can only be attributed to ``service_workers``,
                # not to a missing/broken file. Claims control immediately
                # (no reload needed) so the control test's bounded wait is
                # reliable when NOT blocked.
                self._respond(
                    200,
                    "application/javascript",
                    b"self.addEventListener('install', () => self.skipWaiting());"
                    b"self.addEventListener('activate',"
                    b" (e) => e.waitUntil(self.clients.claim()));"
                    b"self.addEventListener('fetch', () => {});",
                )
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


def test_redirect_check_failure_fails_closed(served) -> None:
    """F2 regression: a redirect target the pre-check cannot verify in time
    (timeout, connection error, ...) MUST be treated as unsafe, not "let the
    browser find out" — the browser is the ONLY thing that would actually
    reach it, since context.route does not intercept top-level navigation
    redirect hops. Previously this failed OPEN (returned "safe" on any
    requests.RequestException) and a redirect response merely slower than
    the 3s check timeout reached the loopback target live
    (agent_reports/2026-09-11-ACS-S2-017-review-claude.md, F2)."""
    port, hits = served
    policy = UrlSafetyPolicy(
        allowed_ports=frozenset({80, 443, port}),
        dns_resolver=lambda host: ("93.184.216.34",),
    )
    fetcher = PlaywrightFetcher(
        policy=policy,
        dns_overrides={"localhost": ("93.184.216.34",)},
        # Short enough that /redirect-slow's 2s delay exceeds the redirect
        # pre-check's (request-timeout-derived) read window.
        timeout=1,
    )
    try:
        result = fetcher.fetch(f"http://localhost:{port}/redirect-slow")
        assert result.error is not None
        assert result.error.startswith("unsafe:") or result.error == "timeout"
        assert hits["leak"] == 0
    finally:
        fetcher.stop()


def _attempt_service_worker(port: int, *, block: bool) -> dict[str, object]:
    """Open a context matching the worker's per-request hardening (or its
    opposite, as a control), attempt to register a real Service Worker, and
    report what actually happened.

    Playwright's own documented behaviour for ``service_workers="block"`` is
    to override ``navigator.serviceWorker.register`` so the returned promise
    still RESOLVES (does not reject) while logging a
    ``"Service Worker registration blocked by Playwright"`` console warning
    and never actually installing/activating a worker — so "did register()
    resolve" is NOT the right signal (an earlier version of this test
    asserted that and was wrong). The right signal is whether a REAL,
    active/controlling worker ever exists — checked with a bounded wait so a
    genuinely-blocked registration cannot hang the test forever.
    """
    from playwright.sync_api import sync_playwright

    console_messages: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                service_workers="block" if block else "allow"
            )
            try:
                page = context.new_page()
                page.on("console", lambda msg: console_messages.append(msg.text))
                page.goto(f"http://localhost:{port}/", wait_until="networkidle")
                outcome = page.evaluate(
                    """
                    async () => {
                        if (!('serviceWorker' in navigator)) return {support: false};
                        let registerError = null;
                        try {
                            await navigator.serviceWorker.register('/sw.js');
                        } catch (e) {
                            registerError = e.message;
                        }
                        // Bounded wait for a REAL active/controlling worker —
                        // a blocked registration must never reach this state.
                        const becameActive = await Promise.race([
                            navigator.serviceWorker.ready.then(() => true),
                            new Promise((resolve) => {
                                setTimeout(() => resolve(false), 1500);
                            }),
                        ]);
                        // clients.claim() control can land a tick after
                        // ``ready`` resolves — wait for controllerchange too
                        // (bounded), not just a synchronous check.
                        const swc = navigator.serviceWorker;
                        const hasController = await Promise.race([
                            new Promise((resolve) => {
                                if (swc.controller) return resolve(true);
                                swc.addEventListener(
                                    'controllerchange',
                                    () => resolve(!!swc.controller),
                                    {once: true},
                                );
                            }),
                            new Promise((resolve) => {
                                setTimeout(() => resolve(!!swc.controller), 1000);
                            }),
                        ]);
                        return {
                            support: true,
                            registerError,
                            becameActive,
                            hasController,
                        };
                    }
                    """
                )
            finally:
                context.close()
        finally:
            browser.close()
    outcome["console_messages"] = console_messages
    return outcome


def test_service_worker_never_becomes_active_when_blocked(served) -> None:
    """``service_workers="block"`` (canonical plan §6.3) must prevent a
    Service Worker from ever becoming an active, controlling worker in the
    worker's per-request context — the one explicit Codex-review-required
    check (Task Contract §6) never actually verified in two review rounds
    (agent_reports/2026-09-11-ACS-S2-017-review-claude.md: coordinator
    marked it 'VERIFIED' from reading the option name, not a reproducer). A
    REAL ``sw.js`` is served so the result can only be attributed to the
    context option, not to a missing/broken script.

    NOTE: ``register()`` itself does NOT reject when blocked (Playwright
    overrides it to resolve while logging a console warning) — asserting
    non-rejection would be a false negative, so this checks the actual
    security-relevant property instead: no active/controlling worker ever
    exists, so the worker can never intercept a fetch."""
    port, _hits = served
    outcome = _attempt_service_worker(port, block=True)
    assert outcome["support"] is True, (
        "Chromium build has no serviceWorker support at all — test is "
        "inconclusive"
    )
    assert outcome["becameActive"] is False, (
        f"a Service Worker became active/controlling despite service_workers="
        f"'block': {outcome!r}"
    )
    assert outcome["hasController"] is False
    assert any(
        "blocked by playwright" in m.lower() for m in outcome["console_messages"]
    ), (
        "expected Playwright's documented block warning "
        "('Service Worker registration blocked by Playwright') in console "
        f"output, got: {outcome['console_messages']!r}"
    )


def test_service_worker_activates_control_without_block(served) -> None:
    """Control for the test above: WITHOUT ``service_workers="block"`` the
    exact same registration attempt against the exact same server must
    result in a REAL active/controlling worker — proves the previous test's
    negative result is caused by the option, not by an unrelated environment
    issue (e.g. a Chromium build without Service Worker support)."""
    port, _hits = served
    outcome = _attempt_service_worker(port, block=False)
    assert outcome["support"] is True
    assert outcome["becameActive"] is True, (
        f"expected the Service Worker to become active as a control, got "
        f"{outcome!r}"
    )
    assert outcome["hasController"] is True
