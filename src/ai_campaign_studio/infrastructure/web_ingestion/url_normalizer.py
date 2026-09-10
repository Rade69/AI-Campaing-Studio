"""URL normalizer (S2-G3).

Owns reducing two syntactically-equivalent URLs to ONE canonical string so
``crawl_budget``/``crawl_targets`` can deduplicate. Normalizes: scheme (lower),
host (lower + IDN→Punycode), default port removal, path (percent-encoding
normalization + RFC 3986 dot-segment removal), query (sorted key/value pairs)
and fragment (stripped). Does NOT make allow/reject decisions (scheme/port/IP
policy is ``url_safety_policy``'s job) and does NOT resolve DNS.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

_DEFAULT_PORTS: dict[str, int] = {"http": 80, "https": 443}

# RFC 3986 unreserved + sub-delims + ":" + "@" + "/" + "%" — kept literal in
# the path so an already-normalized path round-trips unchanged.
_PATH_SAFE = "/:@-._~!$&'()*+,;=%"
_UNRESERVED = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
)


def _normalize_host(host: str) -> str:
    """Lowercase and IDNA-encode a hostname; IPv6/IPv4 literals pass through."""
    lowered = host.lower()
    if ":" in lowered:
        # IPv6 literal (already stripped of brackets by urlsplit().hostname).
        return lowered
    try:
        return lowered.encode("idna").decode("ascii")
    except UnicodeError:
        return lowered


def _remove_dot_segments(path: str) -> str:
    """Collapse ``.``/``..`` path segments (RFC 3986 §5.2.4, simplified).

    Sufficient for crawl dedup: ``/a/./b`` → ``/a/b`` and ``/a/../b`` → ``/b``.
    """
    if not path:
        return path
    absolute = path.startswith("/")
    trailing_slash = path.endswith("/") and path not in ("/", "")
    segments = path.split("/")
    out: list[str] = []
    for seg in segments:
        if seg in ("", "."):
            continue
        if seg == "..":
            if out and out[-1] != "..":
                out.pop()
            elif not absolute:
                out.append("..")
        else:
            out.append(seg)
    result = "/".join(out)
    if absolute:
        result = "/" + result
    if trailing_slash and result and not result.endswith("/"):
        result += "/"
    return result or ("/" if absolute else "")


def _normalize_path(path: str) -> str:
    """Normalize percent-encoding (uppercase hex, decode unreserved), collapse
    dot segments, then re-encode any remaining non-ASCII characters."""
    # Uppercase percent-hex digits (RFC 3986 §6.2.2.1).
    path = re.sub(r"%([0-9a-fA-F]{2})", lambda m: "%" + m.group(1).upper(), path)
    # Decode percent-encoded UNRESERVED characters only (RFC 3986 §6.2.2.2);
    # reserved characters like %2F stay encoded so path semantics are kept.
    def _decode(m: re.Match[str]) -> str:
        char = chr(int(m.group(1), 16))
        return char if char in _UNRESERVED else m.group(0)

    path = re.sub(r"%([0-9A-F]{2})", _decode, path)
    collapsed = _remove_dot_segments(path)
    return quote(collapsed, safe=_PATH_SAFE)


def _normalize_query(query: str) -> str:
    """Sort query key/value pairs for deterministic dedup."""
    if query == "":
        return ""
    pairs = parse_qsl(query, keep_blank_values=True)
    pairs.sort(key=lambda kv: (kv[0], kv[1]))
    return urlencode(pairs, doseq=True)


def normalize_url(url: str) -> str:
    """Return the canonical form of ``url``.

    Raises ``ValueError`` when the URL has no host or an invalid IPv6 host
    (a scheme-only/relative URL has no canonical crawl identity).
    """
    try:
        parts = urlsplit(url)
    except ValueError as exc:
        raise ValueError(f"invalid URL: {url!r}") from exc

    scheme = parts.scheme.lower()
    host = parts.hostname
    if host is None:
        raise ValueError(f"URL has no host: {url!r}")

    normalized_host = _normalize_host(host)

    # Rebuild netloc (host + optional non-default port). userinfo is
    # preserved verbatim — url_safety_policy rejects it upstream.
    host_part = f"[{normalized_host}]" if ":" in normalized_host else normalized_host
    port = parts.port
    netloc = host_part
    if port is not None and port != _DEFAULT_PORTS.get(scheme):
        netloc = f"{host_part}:{port}"

    path = _normalize_path(parts.path)
    query = _normalize_query(parts.query)
    fragment = ""  # fragments never affect the crawl identity

    return urlunsplit((scheme, netloc, path, query, fragment))


__all__ = ["normalize_url"]
