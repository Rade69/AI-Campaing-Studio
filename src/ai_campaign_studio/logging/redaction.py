"""Redaction of sensitive values for log-safe payloads."""

from typing import Any

SENSITIVE_KEY_FRAGMENTS: tuple[str, ...] = (
    "api_key",
    "token",
    "secret",
    "authorization",
    "password",
    "credential",
)

REDACTED_VALUE = "<redacted>"


def _is_sensitive(key: str) -> bool:
    normalized = key.lower()
    return any(fragment in normalized for fragment in SENSITIVE_KEY_FRAGMENTS)


def redact(data: Any) -> Any:
    """Return a copy of *data* with sensitive values replaced.

    Keys whose name contains a known secret fragment (case-insensitive) have
    their values replaced by ``"<redacted>"``. Containers are traversed
    recursively; scalar values are returned unchanged.
    """
    if isinstance(data, dict):
        return {
            key: REDACTED_VALUE if _is_sensitive(str(key)) else redact(value)
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [redact(item) for item in data]
    if isinstance(data, tuple):
        return tuple(redact(item) for item in data)
    return data
