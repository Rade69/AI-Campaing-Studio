"""URL safety policy (S2-G3 SSRF guard) — the safety-critical module.

Owns the allow/reject decision for ONE URL or ONE resolved IP address:
scheme allow-list, userinfo rejection, port allow-list, literal-IP parsing
(decimal / hex / octal / dotted IPv4 + IPv6 — canonical plan §6.2: a literal
private IP in the URL OR in a redirect target MUST be caught here, not only
via DNS), and hostname → DNS A/AAAA validation (every resolved address must
be globally routable, otherwise DNS-rebinding candidates are rejected).

Does NOT open sockets or perform the fetch itself — ``http_fetcher`` calls
this policy before every hop (initial URL and each redirect target).
``dns_resolver`` is injectable so the SSRF matrix can be tested offline.
"""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlsplit

DnsResolver = Callable[[str], tuple[str, ...]]


def system_dns_resolver(host: str) -> tuple[str, ...]:
    """Resolve ``host`` to its unique A/AAAA address strings (zone-stripped)."""
    addrinfos = socket.getaddrinfo(host, None)
    ips: list[str] = []
    for _family, _type, _proto, _canonname, sockaddr in addrinfos:
        ip = str(sockaddr[0])
        # IPv6 link-local answers carry a scope id ("fe80::1%eth0").
        ip = ip.split("%", 1)[0]
        if ip not in ips:
            ips.append(ip)
    return tuple(ips)


@dataclass(frozen=True)
class SafetyDecision:
    """The outcome of one SSRF check."""

    allowed: bool
    reason: str = ""


def _parse_octet(part: str) -> int | None:
    """Parse one dotted-IPv4 octet in decimal / hex / octal (inet_aton-ish)."""
    if not part:
        return None
    if part.lower().startswith("0x"):
        try:
            return int(part, 16)
        except ValueError:
            return None
    if len(part) > 1 and part.startswith("0") and all(c in "01234567" for c in part):
        try:
            return int(part, 8)
        except ValueError:
            return None
    if part.isdigit():
        return int(part, 10)
    return None


def _parse_ipv4_literal(host: str) -> ipaddress.IPv4Address | None:
    """Parse ``host`` as an IPv4 literal, including the obfuscated forms:
    decimal integer (``2130706433``), hex (``0x7f000001``), octal
    (``0177.0.0.1``) and the classic 1–4-part inet_aton forms."""
    h = host.strip()
    if not h:
        return None
    if "." not in h:
        # Single-integer forms.
        value: int | None = None
        if h.isdigit():
            value = int(h, 10)
        elif h.lower().startswith("0x"):
            try:
                value = int(h, 16)
            except ValueError:
                value = None
        elif h.startswith("0") and len(h) > 1 and all(c in "01234567" for c in h):
            value = int(h, 8)
        if value is not None and 0 <= value <= 0xFFFFFFFF:
            return ipaddress.IPv4Address(value)
        return None

    parts = h.split(".")
    if not 1 <= len(parts) <= 4:
        return None
    octets: list[int] = []
    for part in parts:
        octet = _parse_octet(part)
        if octet is None or not 0 <= octet <= 0xFF:
            return None
        octets.append(octet)

    # inet_aton semantics: a → a; a.b → a<<24 | b; a.b.c → a<<24 | b<<16 | c.
    if len(octets) == 1:
        value = octets[0]
    elif len(octets) == 2:
        value = (octets[0] << 24) | octets[1]
    elif len(octets) == 3:
        value = (octets[0] << 24) | (octets[1] << 16) | octets[2]
    else:
        value = (octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3]
    return ipaddress.IPv4Address(value)


def parse_ip_literal(host: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    """Parse ``host`` as an IPv4 or IPv6 literal, or return ``None`` if it is
    a hostname (which must then go through DNS resolution)."""
    h = host.strip().strip("[]")
    if not h:
        return None
    if ":" in h:
        try:
            return ipaddress.IPv6Address(h.split("%", 1)[0])
        except ValueError:
            return None
    return _parse_ipv4_literal(h)


def _is_global(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Strict routability test — ``is_global`` (stricter than ``not is_private``,
    it also rejects loopback, link-local, reserved, broadcast and multicast)."""
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped
    return bool(addr.is_global)


@dataclass(frozen=True)
class UrlSafetyPolicy:
    """SSRF allow/reject policy. Default allow-list: http/https, ports 80/443.

    ``dns_resolver`` is injectable (tests inject a fake resolver so the matrix
    never touches real DNS); production uses ``system_dns_resolver``.
    """

    allowed_schemes: frozenset[str] = frozenset({"http", "https"})
    allowed_ports: frozenset[int] = frozenset({80, 443})
    dns_resolver: DnsResolver = system_dns_resolver

    def validate_ip(self, ip: str) -> SafetyDecision:
        """Allow only globally-routable addresses (reject loopback/private/
        link-local/reserved/broadcast/multicast, IPv4 and IPv6)."""
        try:
            addr = ipaddress.ip_address(ip.split("%", 1)[0])
        except ValueError:
            return SafetyDecision(False, f"invalid_ip:{ip}")
        return self.validate_ip_address(addr)

    def validate_ip_address(
        self, addr: ipaddress.IPv4Address | ipaddress.IPv6Address
    ) -> SafetyDecision:
        if _is_global(addr):
            return SafetyDecision(True)
        return SafetyDecision(False, f"ip_not_global:{addr.compressed}")

    def validate_url(self, url: str) -> SafetyDecision:
        """Full SSRF check on one URL (used before every fetch hop)."""
        try:
            parts = urlsplit(url)
        except ValueError:
            return SafetyDecision(False, "invalid_url")

        scheme = parts.scheme.lower()
        if scheme not in self.allowed_schemes:
            return SafetyDecision(False, f"scheme_not_allowed:{scheme}")

        if parts.username is not None or parts.password is not None:
            return SafetyDecision(False, "userinfo_not_allowed")

        host = parts.hostname
        if host is None:
            return SafetyDecision(False, "missing_host")
        host = host.lower()

        try:
            port = parts.port
        except ValueError:
            return SafetyDecision(False, "invalid_port")
        if port is None:
            port = 443 if scheme == "https" else 80
        if port not in self.allowed_ports:
            return SafetyDecision(False, f"port_not_allowed:{port}")

        literal = parse_ip_literal(host)
        if literal is not None:
            return self.validate_ip_address(literal)

        # Hostname → IDNA → DNS; EVERY resolved address must be global.
        try:
            ascii_host = host.encode("idna").decode("ascii")
        except UnicodeError:
            return SafetyDecision(False, f"invalid_host:{host}")
        try:
            ips = self.dns_resolver(ascii_host)
        except Exception:
            return SafetyDecision(False, f"dns_resolution_failed:{ascii_host}")
        if not ips:
            return SafetyDecision(False, f"dns_no_records:{ascii_host}")
        for ip in ips:
            decision = self.validate_ip(ip)
            if not decision.allowed:
                return SafetyDecision(
                    False, f"dns_resolves_to_private:{ascii_host}->{ip}"
                )
        return SafetyDecision(True)


__all__ = [
    "DnsResolver",
    "SafetyDecision",
    "UrlSafetyPolicy",
    "parse_ip_literal",
    "system_dns_resolver",
]
