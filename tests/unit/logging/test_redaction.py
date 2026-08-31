"""Unit tests for log redaction."""

import json

import pytest

from ai_campaign_studio.logging.redaction import REDACTED_VALUE, redact


@pytest.mark.parametrize(
    "key",
    [
        "api_key",
        "API_KEY",
        "access_token",
        "client_secret",
        "Authorization",
        "password",
        "credential",
        "credential_ref",
    ],
)
def test_redacts_sensitive_key_names(key: str) -> None:
    payload = {key: "SECRET-VALUE-123", "safe": "keep-me"}
    redacted = redact(payload)
    assert redacted[key] == REDACTED_VALUE
    assert redacted["safe"] == "keep-me"
    assert "SECRET-VALUE-123" not in json.dumps(redacted)


def test_redacts_nested_containers() -> None:
    payload = {
        "provider": {"api_key": "abc123"},
        "items": [{"token": "tok-1"}, "plain"],
    }
    redacted = redact(payload)
    assert redacted["provider"]["api_key"] == REDACTED_VALUE
    assert redacted["items"][0]["token"] == REDACTED_VALUE
    assert redacted["items"][1] == "plain"
    assert "abc123" not in json.dumps(redacted)
    assert "tok-1" not in json.dumps(redacted)


def test_non_sensitive_values_untouched() -> None:
    payload = {"provider": "openai", "count": 3, "ok": True}
    assert redact(payload) == payload


def test_scalars_pass_through() -> None:
    assert redact("api_key") == "api_key"
    assert redact(42) == 42
    assert redact(None) is None
