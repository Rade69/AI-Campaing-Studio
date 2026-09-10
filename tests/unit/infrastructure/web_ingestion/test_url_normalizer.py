"""Unit tests for the S2-G3 URL normalizer (deterministic canonical form)."""

from __future__ import annotations

import pytest

from ai_campaign_studio.infrastructure.web_ingestion.url_normalizer import (
    normalize_url,
)


def test_lowercases_scheme_and_host() -> None:
    assert normalize_url("HTTP://Example.COM/Path") == "http://example.com/Path"


def test_strips_fragment() -> None:
    assert normalize_url("http://example.com/page#section") == "http://example.com/page"


def test_removes_default_port() -> None:
    assert normalize_url("http://example.com:80/x") == "http://example.com/x"
    assert normalize_url("https://example.com:443/x") == "https://example.com/x"


def test_keeps_non_default_port() -> None:
    assert normalize_url("http://example.com:8080/x") == "http://example.com:8080/x"


def test_idn_to_punycode() -> None:
    assert normalize_url("http://bücher.de/") == "http://xn--bcher-kva.de/"


def test_normalizes_percent_encoding_case() -> None:
    assert normalize_url("http://example.com/a%2fb") == "http://example.com/a%2Fb"


def test_collapses_dot_segments() -> None:
    assert normalize_url("http://example.com/a/./b") == "http://example.com/a/b"
    assert normalize_url("http://example.com/a/../b") == "http://example.com/b"


def test_sorts_query_keys() -> None:
    assert normalize_url("http://example.com/?z=1&a=2&a=1") == "http://example.com/?a=1&a=2&z=1"


def test_ipv6_literal_round_trip() -> None:
    assert normalize_url("http://[::1]:8080/x") == "http://[::1]:8080/x"


def test_empty_path_and_query() -> None:
    assert normalize_url("http://example.com") == "http://example.com"
    assert normalize_url("http://example.com?") == "http://example.com"


def test_deterministic_same_url_same_form() -> None:
    a = normalize_url("http://Example.com:80/a/../b?x=1&y=2#f")
    b = normalize_url("http://example.com/b?y=2&x=1")
    assert a == b == "http://example.com/b?x=1&y=2"


def test_no_host_raises_value_error() -> None:
    with pytest.raises(ValueError):
        normalize_url("not a url")
    with pytest.raises(ValueError):
        normalize_url("https:///path-only")
