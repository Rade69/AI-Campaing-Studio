"""Playwright fallback fetcher (S2-G8) — ``HttpFetcherPort`` implementation.

Owns the parent side of the Playwright fallback: a long-lived worker
subprocess (``python -m ...subprocess_runtime.playwright_worker``) that owns
ONE Chromium instance and services fetch requests serially over line-delimited
JSON-RPC. This module implements the EXISTING ``HttpFetcherPort`` (no port
signature change) and maps worker results to ``FetchResult``. The top-level
URL is SSRF-validated here with the parent's policy BEFORE the subprocess is
involved; the worker re-validates every in-page/redirect request with the
same policy. Does NOT own the JS-heavy decision (``js_render_detector``) —
the caller decides when to use this fetcher vs ``HttpFetcher`` (HTTP-first).
"""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
from uuid import uuid4

import ai_campaign_studio
from ai_campaign_studio.infrastructure.web_ingestion.url_safety_policy import (
    UrlSafetyPolicy,
)
from ai_campaign_studio.ports.web_ingestion import FetchResult
from ai_campaign_studio.subprocess_runtime.ipc import (
    PlaywrightRequest,
    PlaywrightResult,
    decode_response,
    encode_request,
)

DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_MAX_BYTES = 5 * 1024 * 1024  # 5 MiB
_WORKER_GRACE_SECONDS = 10.0


class PlaywrightWorker:
    """Parent-side manager of the long-lived worker subprocess.

    ``start()`` is idempotent (never spawns a second process); ``stop()``
    terminates; ``send_receive`` serialises requests (the worker is
    single-threaded) and transparently respawns a dead worker (crash
    recovery, canonical plan §10 S2-G8). A single daemon thread drains the
    worker's stdout into a queue so the main thread can wait with a timeout —
    this thread only moves pipe bytes, it never touches Chromium (Q4/F1-052:
    subprocess, not thread + Chromium).
    """

    def __init__(
        self,
        *,
        python: str | None = None,
        startup_grace: float = _WORKER_GRACE_SECONDS,
    ) -> None:
        self._python = python or sys.executable
        self._startup_grace = startup_grace
        self._proc: subprocess.Popen[bytes] | None = None
        self._reader: threading.Thread | None = None
        self._responses: queue.Queue[bytes] = queue.Queue()
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self._proc is not None and self._proc.poll() is None:
                return  # already running — idempotent
            self._spawn()

    def is_alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def stop(self) -> None:
        with self._lock:
            self._terminate()

    def restart(self) -> None:
        with self._lock:
            self._terminate()
            self._spawn()

    def _spawn(self) -> None:
        self._responses = queue.Queue()
        # The worker subprocess must import the SAME package the parent
        # process imports (the pytest ``pythonpath = ["src"]`` config does
        # NOT propagate to children, and the editable-install ``.pth`` can
        # point at a stale checkout — workflow §13). Pin the src root
        # explicitly via PYTHONPATH.
        env = dict(os.environ)
        src_root = str(Path(ai_campaign_studio.__file__).resolve().parent.parent)
        existing = env.get("PYTHONPATH")
        env["PYTHONPATH"] = (
            src_root if not existing else src_root + os.pathsep + existing
        )
        self._proc = subprocess.Popen(
            [
                self._python,
                "-m",
                "ai_campaign_studio.subprocess_runtime.playwright_worker",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=env,
        )
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    def _read_loop(self) -> None:
        assert self._proc is not None
        assert self._proc.stdout is not None
        # EOF (worker died) ends the loop; the queue just stays empty.
        for line in self._proc.stdout:
            self._responses.put(line)

    def _terminate(self) -> None:
        proc = self._proc
        self._proc = None
        if proc is None:
            return
        try:
            proc.terminate()
        except Exception:  # noqa: BLE001 - teardown is best-effort
            pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except Exception:  # noqa: BLE001
                pass
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass

    def send_receive(
        self, request: PlaywrightRequest, timeout: float
    ) -> PlaywrightResult:
        """Send one request and wait for its response.

        ``timeout`` is the parent-side watchdog: if the worker does not answer
        in time it is terminated and respawned (clean state, F1-052) and a
        ``timeout`` result is returned. A worker that died earlier is
        transparently respawned (crash recovery).
        """
        with self._lock:
            if not self.is_alive():
                self._spawn()
            assert self._proc is not None
            assert self._proc.stdin is not None
            try:
                self._proc.stdin.write(encode_request(request))
                self._proc.stdin.flush()
            except (BrokenPipeError, OSError):
                # Worker died between the liveness check and the write.
                self._spawn()
                return PlaywrightResult(
                    request_id=request.request_id,
                    ok=False,
                    error_code="worker_died",
                    error_message=(
                        "worker subprocess exited before accepting the request"
                    ),
                )
            try:
                line = self._responses.get(timeout=timeout)
            except queue.Empty:
                self._terminate()
                self._spawn()
                return PlaywrightResult(
                    request_id=request.request_id,
                    ok=False,
                    error_code="timeout",
                    error_message=f"worker did not respond within {timeout}s",
                )
            return decode_response(line)


def _to_fetch_result(url: str, result: PlaywrightResult) -> FetchResult:
    if result.ok:
        from ai_campaign_studio.subprocess_runtime.ipc import decode_body

        return FetchResult(
            url=url,
            final_url=result.final_url or url,
            status_code=result.status_code,
            content=decode_body(result),
            content_type=result.content_type,
        )
    if result.error_code == "unsafe_url":
        return FetchResult(
            url=url,
            final_url=url,
            status_code=0,
            error=f"unsafe:{result.error_message or ''}",
        )
    if result.error_code == "body_too_large":
        return FetchResult(url=url, final_url=url, status_code=0, error="too_large")
    if result.error_code == "timeout":
        return FetchResult(url=url, final_url=url, status_code=0, error="timeout")
    code = result.error_code or "fetch_error"
    message = result.error_message or ""
    return FetchResult(
        url=url,
        final_url=url,
        status_code=0,
        error=f"{code}:{message}",
    )


class PlaywrightFetcher:
    """``HttpFetcherPort`` implementation backed by the worker subprocess."""

    def __init__(
        self,
        *,
        policy: UrlSafetyPolicy | None = None,
        worker: PlaywrightWorker | None = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        max_bytes: int = DEFAULT_MAX_BYTES,
        dns_overrides: dict[str, tuple[str, ...]] | None = None,
        response_timeout: float | None = None,
    ) -> None:
        self._policy = policy or UrlSafetyPolicy()
        self._worker = worker or PlaywrightWorker()
        self._timeout = timeout
        self._max_bytes = max_bytes
        self._dns_overrides = dns_overrides
        self._response_timeout = (
            response_timeout
            if response_timeout is not None
            else float(timeout) + _WORKER_GRACE_SECONDS
        )

    def start(self) -> None:
        self._worker.start()

    def stop(self) -> None:
        self._worker.stop()

    def fetch(self, url: str) -> FetchResult:
        decision = self._policy.validate_url(url)
        if not decision.allowed:
            return FetchResult(
                url=url,
                final_url=url,
                status_code=0,
                error=f"unsafe:{decision.reason}",
            )
        request = PlaywrightRequest(
            request_id=uuid4().hex,
            url=url,
            timeout=self._timeout,
            max_bytes=self._max_bytes,
            allowed_ports=tuple(sorted(self._policy.allowed_ports)),
            dns_overrides=self._dns_overrides,
        )
        result = self._worker.send_receive(request, timeout=self._response_timeout)
        return _to_fetch_result(url, result)


__all__ = [
    "DEFAULT_MAX_BYTES",
    "DEFAULT_TIMEOUT_SECONDS",
    "PlaywrightFetcher",
    "PlaywrightWorker",
]
