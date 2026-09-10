"""Unit tests for the S2-G3 SSRF URL safety policy.

The full canonical-plan §6 matrix (loopback/private/link-local/broadcast,
IPv6, obfuscated literal IPs, userinfo, ports, DNS-rebinding hostnames) plus
a few extra edge cases. DNS is injected (never a real lookup) so the matrix
is deterministic and offline.
"""

from __future__ import annotations

import pytest

from ai_campaign_studio.infrastructure.web_ingestion.url_safety_policy import (
    UrlSafetyPolicy,
)


def _default_dns(host: str) -> tuple[str, ...]:
    if host in ("localhost", "localtest.me", "127-0-0-1.nip.io"):
        return ("127.0.0.1",)
    return ("93.184.216.34",)  # example.com (public)


@pytest.fixture()
def policy() -> UrlSafetyPolicy:
    return UrlSafetyPolicy(dns_resolver=_default_dns)


# (url, expected_allowed, label)
SSRF_TEST_CASES: list[tuple[str, bool, str]] = [
    # Direct loopback / private / link-local / wildcard / broadcast.
    ("http://127.0.0.1/", False, "loopback IPv4"),
    ("http://localhost/", False, "DNS loopback"),
    ("http://10.0.0.1/", False, "private 10/8"),
    ("http://192.168.1.1/", False, "private 192.168/16"),
    ("http://172.16.0.1/", False, "private 172.16/12"),
    ("http://169.254.169.254/latest/meta-data/", False, "link-local AWS IMDS"),
    ("http://[::1]/", False, "loopback IPv6"),
    ("http://[fc00::1]/", False, "private IPv6"),
    ("http://[fe80::1]/", False, "link-local IPv6"),
    ("http://0.0.0.0/", False, "wildcard IPv4"),
    ("http://255.255.255.255/", False, "broadcast IPv4"),
    ("http://100.64.0.1/", False, "CGNAT shared address space"),
    # userinfo (credentials leak).
    ("http://user:pass@example.com/", False, "userinfo"),
    ("http://user@example.com/", False, "userinfo (no password)"),
    # Unapproved ports.
    ("http://example.com:22/", False, "SSH port"),
    ("http://example.com:23/", False, "telnet port"),
    ("http://example.com:25/", False, "SMTP port"),
    ("http://example.com:3306/", False, "MySQL port"),
    ("http://example.com:5432/", False, "PostgreSQL port"),
    ("http://example.com:6379/", False, "Redis port"),
    ("http://example.com:27017/", False, "MongoDB port"),
    ("http://example.com:8080/", False, "unapproved dev port (default policy)"),
    # Obfuscated literal IPv4 (§6.2 — must be caught without DNS).
    ("http://2130706433/", False, "decimal literal IP = 127.0.0.1"),
    ("http://0x7f000001/", False, "hex literal IP = 127.0.0.1"),
    ("http://0177.0.0.1/", False, "octal literal IP = 127.0.0.1"),
    ("http://0x7f.0.0.1/", False, "hex-in-dotted IP = 127.0.0.1"),
    ("http://[::ffff:127.0.0.1]/", False, "IPv4-mapped loopback"),
    # DNS rebinding hostnames.
    ("http://localtest.me/", False, "DNS resolves to 127.0.0.1"),
    ("http://127-0-0-1.nip.io/", False, "DNS wildcard nip.io"),
    # Non-http schemes.
    ("ftp://example.com/", False, "scheme not allowed"),
    ("file:///etc/passwd", False, "file scheme not allowed"),
    # Public targets (allowed).
    ("http://example.com/", True, "public"),
    ("https://example.com/", True, "public HTTPS"),
    ("http://8.8.8.8/", True, "public IPv4 literal"),
    ("http://93.184.216.34/", True, "public IPv4 literal"),
]


@pytest.mark.parametrize("url,expected,label", SSRF_TEST_CASES)
def test_validate_url_matrix(
    policy: UrlSafetyPolicy, url: str, expected: bool, label: str
) -> None:
    decision = policy.validate_url(url)
    assert decision.allowed is expected, f"{label}: {url} -> {decision}"


def test_dns_rebinding_mixed_public_and_private_is_rejected() -> None:
    """If ANY resolved address is non-global the host is rejected (TOCTOU)."""
    policy = UrlSafetyPolicy(dns_resolver=lambda host: ("93.184.216.34", "127.0.0.1"))
    decision = policy.validate_url("http://rebind.example/")
    assert decision.allowed is False
    assert "127.0.0.1" in decision.reason


def test_dns_no_records_is_rejected() -> None:
    policy = UrlSafetyPolicy(dns_resolver=lambda host: ())
    decision = policy.validate_url("http://nope.example/")
    assert decision.allowed is False


def test_dns_resolution_failure_is_rejected() -> None:
    def boom(host: str) -> tuple[str, ...]:
        raise OSError("no network")

    policy = UrlSafetyPolicy(dns_resolver=boom)
    decision = policy.validate_url("http://example.com/")
    assert decision.allowed is False
    assert decision.reason.startswith("dns_resolution_failed")


def test_validate_ip_rejects_private_and_allows_public() -> None:
    policy = UrlSafetyPolicy(dns_resolver=_default_dns)
    assert policy.validate_ip("127.0.0.1").allowed is False
    assert policy.validate_ip("169.254.169.254").allowed is False
    assert policy.validate_ip("::1").allowed is False
    assert policy.validate_ip("fe80::1").allowed is False
    assert policy.validate_ip("8.8.8.8").allowed is True


def test_validate_url_rejects_missing_host() -> None:
    policy = UrlSafetyPolicy(dns_resolver=_default_dns)
    assert policy.validate_url("http:///path").allowed is False


def test_validate_url_rejects_invalid_port() -> None:
    policy = UrlSafetyPolicy(dns_resolver=_default_dns)
    assert policy.validate_url("http://example.com:99999/").allowed is False


def test_extra_allowed_ports_can_be_enabled_for_dev() -> None:
    policy = UrlSafetyPolicy(
        allowed_ports=frozenset({80, 443, 8080, 8443}),
        dns_resolver=_default_dns,
    )
    assert policy.validate_url("http://example.com:8080/").allowed is True
    # Privileged ports stay rejected even when the dev ports are enabled.
    assert policy.validate_url("http://example.com:22/").allowed is False
