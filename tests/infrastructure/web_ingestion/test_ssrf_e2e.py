"""End-to-end SSRF test (S2-G3) — live ``http_fetcher`` against a real local
HTTP server bound to 127.0.0.1.

The server MUST be blocked before any connection: the test proves the whole
fetch chain (policy + custom HTTPAdapter at the connection boundary), not
just the resolver, refuses loopback targets — the handler's hit counter stays
at zero for every probe.
"""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import requests

from ai_campaign_studio.infrastructure.web_ingestion.http_fetcher import (
    HttpFetcher,
    SafeHttpAdapter,
)
from ai_campaign_studio.infrastructure.web_ingestion.url_safety_policy import (
    UrlSafetyPolicy,
)


@pytest.fixture()
def local_server():
    hits = {"count": 0}
    lock = threading.Lock()

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - http.server API
            with lock:
                hits["count"] += 1
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    yield port, hits
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def _fetcher_allowing_port(port: int) -> HttpFetcher:
    policy = UrlSafetyPolicy(allowed_ports=frozenset({80, 443, port}))
    return HttpFetcher(policy=policy)


def test_literal_loopback_is_blocked_before_connection(local_server) -> None:
    port, hits = local_server
    fetcher = _fetcher_allowing_port(port)

    result = fetcher.fetch(f"http://127.0.0.1:{port}/")

    assert result.error is not None
    assert result.error.startswith("unsafe:")
    assert "127.0.0.1" in result.error
    assert hits["count"] == 0  # the server never received the request


def test_dns_loopback_is_blocked_before_connection(local_server) -> None:
    port, hits = local_server
    fetcher = _fetcher_allowing_port(port)

    result = fetcher.fetch(f"http://localhost:{port}/")

    assert result.error is not None
    assert result.error.startswith("unsafe:")
    assert hits["count"] == 0


def test_safe_adapter_blocks_at_connection_boundary(local_server) -> None:
    port, hits = local_server
    policy = UrlSafetyPolicy(allowed_ports=frozenset({80, 443, port}))
    session = requests.Session()
    session.mount("http://", SafeHttpAdapter(policy))
    session.mount("https://", SafeHttpAdapter(policy))

    with pytest.raises(Exception, match="127.0.0.1"):
        session.get(f"http://127.0.0.1:{port}/", timeout=2)

    assert hits["count"] == 0
