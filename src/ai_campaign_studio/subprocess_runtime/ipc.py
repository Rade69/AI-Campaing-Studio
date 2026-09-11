"""Line-delimited JSON-RPC IPC for the Playwright worker subprocess (S2-G8).

Owns the two transport shapes exchanged over stdin/stdout between the parent
fetcher and the worker: ``PlaywrightRequest`` (what the parent sends) and
``PlaywrightResult`` (what the worker answers). The response body travels
base64-encoded (``body_b64``) so arbitrary HTML bytes survive the JSON text
transport. ``allowed_ports``/``dns_overrides`` carry a SERIALISABLE subset of
``UrlSafetyPolicy`` configuration into the worker (the full policy object and
its callable ``dns_resolver`` cannot cross a process boundary) so the SSRF
guard inside the browser uses the same policy the parent uses. Does NOT do
any I/O itself beyond pure encode/decode.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PlaywrightRequest:
    """One fetch request sent by the parent to the worker."""

    request_id: str
    url: str
    timeout: int = 20
    max_bytes: int = 5_000_000
    browser: str = "chromium"
    # Serialisable subset of ``UrlSafetyPolicy``: ``None`` → worker default.
    allowed_ports: tuple[int, ...] | None = None
    dns_overrides: dict[str, tuple[str, ...]] | None = None


@dataclass(frozen=True)
class PlaywrightResult:
    """One fetch result returned by the worker to the parent.

    ``ok`` selects between the success fields (``status_code``,
    ``final_url``, ``content_type``, ``body_b64``, ``headers``) and the
    failure fields (``error_code``, ``error_message``).
    """

    request_id: str
    ok: bool
    status_code: int = 0
    final_url: str = ""
    content_type: str | None = None
    body_b64: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None


def encode_request(request: PlaywrightRequest) -> bytes:
    """Encode a request as one JSON line (UTF-8, ``\\n``-terminated)."""
    payload: dict[str, object] = {
        "request_id": request.request_id,
        "url": request.url,
        "timeout": request.timeout,
        "max_bytes": request.max_bytes,
        "browser": request.browser,
    }
    if request.allowed_ports is not None:
        payload["allowed_ports"] = list(request.allowed_ports)
    if request.dns_overrides is not None:
        payload["dns_overrides"] = {
            host: list(ips) for host, ips in request.dns_overrides.items()
        }
    return json.dumps(payload).encode("utf-8") + b"\n"


def decode_request(line: bytes) -> PlaywrightRequest:
    """Decode one request JSON line into a ``PlaywrightRequest``."""
    data = json.loads(line.decode("utf-8"))
    allowed_ports = data.get("allowed_ports")
    dns_overrides = data.get("dns_overrides")
    return PlaywrightRequest(
        request_id=str(data["request_id"]),
        url=str(data["url"]),
        timeout=int(data.get("timeout", 20)),
        max_bytes=int(data.get("max_bytes", 5_000_000)),
        browser=str(data.get("browser", "chromium")),
        allowed_ports=(
            tuple(int(p) for p in allowed_ports) if allowed_ports is not None else None
        ),
        dns_overrides=(
            {str(h): tuple(str(ip) for ip in ips) for h, ips in dns_overrides.items()}
            if dns_overrides is not None
            else None
        ),
    )


def encode_response(result: PlaywrightResult) -> bytes:
    """Encode a result as one JSON line (UTF-8, ``\\n``-terminated)."""
    payload: dict[str, object] = {
        "request_id": result.request_id,
        "ok": result.ok,
        "status_code": result.status_code,
        "final_url": result.final_url,
        "content_type": result.content_type,
        "body_b64": result.body_b64,
        "headers": result.headers,
        "error_code": result.error_code,
        "error_message": result.error_message,
    }
    return json.dumps(payload).encode("utf-8") + b"\n"


def decode_response(line: bytes) -> PlaywrightResult:
    """Decode one result JSON line into a ``PlaywrightResult``."""
    data = json.loads(line.decode("utf-8"))
    return PlaywrightResult(
        request_id=str(data["request_id"]),
        ok=bool(data["ok"]),
        status_code=int(data.get("status_code", 0)),
        final_url=str(data.get("final_url", "")),
        content_type=data.get("content_type"),
        body_b64=str(data.get("body_b64", "")),
        headers={str(k): str(v) for k, v in data.get("headers", {}).items()},
        error_code=data.get("error_code"),
        error_message=data.get("error_message"),
    )


def decode_body(result: PlaywrightResult) -> bytes:
    """Decode the base64 response body back to raw bytes."""
    return base64.b64decode(result.body_b64)


__all__ = [
    "PlaywrightRequest",
    "PlaywrightResult",
    "decode_body",
    "decode_request",
    "decode_response",
    "encode_request",
    "encode_response",
]
