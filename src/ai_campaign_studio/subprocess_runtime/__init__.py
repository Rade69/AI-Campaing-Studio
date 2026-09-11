"""Subprocess runtime (S2-G8).

Owns the long-lived Playwright worker subprocess and its line-delimited
JSON-RPC IPC contract. The worker runs Chromium in a SEPARATE process
(canonical plan §10 S2-G8 / Q4 decision: subprocess, never thread — the
thread + Chromium combination is proven flaky, F1-052) and is managed by
``infrastructure/web_ingestion/playwright_fetcher.py``. Nothing here is
imported by the Campaign Engine; this package is only entered via
``python -m ai_campaign_studio.subprocess_runtime.playwright_worker``.
"""

from ai_campaign_studio.subprocess_runtime.ipc import (
    PlaywrightRequest,
    PlaywrightResult,
    decode_request,
    decode_response,
    encode_request,
    encode_response,
)

__all__ = [
    "PlaywrightRequest",
    "PlaywrightResult",
    "decode_request",
    "decode_response",
    "encode_request",
    "encode_response",
]
