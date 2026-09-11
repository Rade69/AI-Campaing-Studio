"""Playwright worker subprocess entry point (S2-G8).

Owns ONE long-lived headless Chromium instance that services a SERIAL stream
of fetch requests read from stdin (one JSON line per request, one JSON line
per response on stdout). Per-request hardening (canonical plan §6.3): a fresh
``BrowserContext`` with ``service_workers="block"`` (Playwright does not
intercept Service Worker requests otherwise) and a ``context.route`` handler
that re-validates EVERY in-page request (XHR/fetch/iframe and every redirect
hop) through ``UrlSafetyPolicy`` — the same SSRF guard the HTTP fetcher uses.
The rendered DOM (``page.content()``, i.e. post-JavaScript HTML) is what is
returned, because the whole point of the fallback is content HTTP-only fetch
cannot see. Does NOT persist anything and does NOT know the Campaign Engine.

This module is entered only via ``python -m`` from the parent process; it
never runs in the application process (Q4: subprocess, not thread).
"""

from __future__ import annotations

import base64
import sys
from typing import Any
from urllib.parse import urljoin

import requests  # type: ignore[import-untyped]

from ai_campaign_studio.infrastructure.web_ingestion.url_safety_policy import (
    UrlSafetyPolicy,
    system_dns_resolver,
)
from ai_campaign_studio.subprocess_runtime.ipc import (
    PlaywrightRequest,
    PlaywrightResult,
    decode_request,
    encode_response,
)


def _build_policy(request: PlaywrightRequest) -> UrlSafetyPolicy:
    """Rebuild the worker-side SSRF policy from the serialisable subset.

    ``dns_overrides`` maps hostnames to the addresses they should resolve to
    (needed by tests that serve fixtures from ``localhost`` without weakening
    the production guard); any host not overridden falls back to the system
    resolver.
    """
    if request.allowed_ports is None and request.dns_overrides is None:
        return UrlSafetyPolicy()
    allowed_ports = (
        frozenset(request.allowed_ports)
        if request.allowed_ports is not None
        else frozenset({80, 443})
    )
    overrides = request.dns_overrides or {}

    def resolver(host: str) -> tuple[str, ...]:
        if host in overrides:
            return overrides[host]
        return system_dns_resolver(host)

    return UrlSafetyPolicy(allowed_ports=allowed_ports, dns_resolver=resolver)


_REDIRECT_STATUS_CODES = frozenset({301, 302, 303, 307, 308})
_MAX_REDIRECT_HOPS = 5
_REDIRECT_CHECK_TIMEOUT = (3.0, 3.0)


def _redirect_unsafe_reason(url: str, policy: UrlSafetyPolicy) -> str | None:
    """Pre-navigation redirect-chain SSRF validation.

    Playwright's ``context.route`` does NOT intercept redirect hops of a
    top-level navigation (verified live), so a ``302 -> 127.0.0.1`` would
    reach the private target. This follows the chain with ``requests``
    (``allow_redirects=False``) and re-validates EVERY hop through the same
    ``UrlSafetyPolicy`` BEFORE the browser navigates. Returns the unsafe
    reason, or ``None`` when no unsafe hop was found (best-effort: network
    failures/timeouts fall through to the browser's own handling).
    """
    current = url
    for _hop in range(_MAX_REDIRECT_HOPS + 1):
        decision = policy.validate_url(current)
        if not decision.allowed:
            return decision.reason
        try:
            with requests.get(
                current,
                allow_redirects=False,
                timeout=_REDIRECT_CHECK_TIMEOUT,
                stream=True,
            ) as response:
                if response.status_code not in _REDIRECT_STATUS_CODES:
                    return None  # terminal hop, no unsafe redirect
                location = response.headers.get("Location")
                if not location:
                    return None
                current = urljoin(current, location)
        except requests.RequestException:
            return None  # best-effort: let the browser surface the failure
    return "too_many_redirects"


def _content_type(response: Any) -> str | None:
    headers = response.headers if response is not None else {}
    value = headers.get("content-type") if headers else None
    return str(value) if value else None


def _process_one(browser: Any, request: PlaywrightRequest) -> PlaywrightResult:
    # Playwright is imported lazily so ``mypy`` does not require it installed
    # (it is an optional ``renderer-spike`` extra, never a hard dependency).
    from playwright.sync_api import (  # type: ignore[import-not-found]
        Error as PlaywrightError,
    )
    from playwright.sync_api import (
        TimeoutError as PlaywrightTimeoutError,
    )

    policy = _build_policy(request)
    decision = policy.validate_url(request.url)
    if not decision.allowed:
        return PlaywrightResult(
            request_id=request.request_id,
            ok=False,
            error_code="unsafe_url",
            error_message=decision.reason,
        )

    # Validate the whole redirect chain BEFORE the browser navigates —
    # ``context.route`` does not intercept top-level redirect hops.
    redirect_reason = _redirect_unsafe_reason(request.url, policy)
    if redirect_reason is not None:
        return PlaywrightResult(
            request_id=request.request_id,
            ok=False,
            error_code="unsafe_url",
            error_message=redirect_reason,
        )

    blocked_reasons: list[str] = []

    def route_handler(route: Any) -> None:
        # Re-validate every request the page issues (XHR/fetch/iframe and
        # every redirect hop). Blocked requests are aborted BEFORE any
        # connection is opened.
        route_decision = policy.validate_url(route.request.url)
        if route_decision.allowed:
            route.continue_()
        else:
            blocked_reasons.append(route_decision.reason)
            route.abort()

    context = browser.new_context(service_workers="block")
    context.route("**/*", route_handler)
    try:
        timeout_ms = request.timeout * 1000
        context.set_default_timeout(timeout_ms)
        page = context.new_page()
        response = page.goto(
            request.url, timeout=timeout_ms, wait_until="networkidle"
        )
        body_html = page.content()
        body_bytes = body_html.encode("utf-8")
        if len(body_bytes) > request.max_bytes:
            return PlaywrightResult(
                request_id=request.request_id,
                ok=False,
                error_code="body_too_large",
                error_message=(
                    f"body {len(body_bytes)} bytes exceeds {request.max_bytes}"
                ),
            )
        return PlaywrightResult(
            request_id=request.request_id,
            ok=True,
            status_code=int(response.status),
            final_url=str(response.url),
            content_type=_content_type(response),
            body_b64=base64.b64encode(body_bytes).decode("ascii"),
            headers={str(k): str(v) for k, v in dict(response.headers).items()},
        )
    except PlaywrightTimeoutError:
        return PlaywrightResult(
            request_id=request.request_id,
            ok=False,
            error_code="timeout",
            error_message=f"navigation timeout after {request.timeout}s",
        )
    except PlaywrightError as exc:
        if blocked_reasons:
            return PlaywrightResult(
                request_id=request.request_id,
                ok=False,
                error_code="unsafe_url",
                error_message=blocked_reasons[-1],
            )
        return PlaywrightResult(
            request_id=request.request_id,
            ok=False,
            error_code="fetch_error",
            error_message=str(exc),
        )
    finally:
        # Full cleanup between requests — even on errors (Q4 requirement).
        try:
            context.close()
        except Exception:  # noqa: BLE001 - cleanup must never mask the result
            pass


def serve(browser: Any) -> int:
    """Read requests from stdin and answer on stdout until EOF.

    A failure in one request (unsafe URL, timeout, oversized body) yields an
    error response and the loop continues — the worker survives transient
    per-request failures and only exits when the parent closes stdin or the
    process is killed.
    """
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    for raw in stdin:
        line = raw.strip()
        if not line:
            continue
        try:
            request = decode_request(line)
        except Exception as exc:  # noqa: BLE001 - malformed line must not kill the worker
            result = PlaywrightResult(
                request_id="",
                ok=False,
                error_code="bad_request",
                error_message=str(exc),
            )
        else:
            result = _process_one(browser, request)
        stdout.write(encode_response(result))
        stdout.flush()
    return 0


def main() -> int:
    from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            return serve(browser)
        finally:
            try:
                browser.close()
            except Exception:  # noqa: BLE001 - teardown must not mask the result
                pass


if __name__ == "__main__":
    sys.exit(main())
