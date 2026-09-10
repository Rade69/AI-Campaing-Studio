"""Unit tests for the S2-G3 RFC 9309 robots.txt reader."""

from __future__ import annotations

from ai_campaign_studio.infrastructure.web_ingestion.robots_reader import (
    RobotsReader,
    robots_url_for,
)
from ai_campaign_studio.ports.web_ingestion import FetchResult

USER_AGENT = "test-bot"


def _reader(fetcher, *, clock=None) -> RobotsReader:
    return RobotsReader(fetcher, user_agent=USER_AGENT, clock=clock)


def test_robots_url_for_builds_origin_robots_path() -> None:
    assert robots_url_for("http://example.com/a/b") == "http://example.com/robots.txt"
    assert robots_url_for("https://example.com:8443/x") == "https://example.com:8443/robots.txt"


def test_disallow_rule_is_respected(fake_fetcher) -> None:
    fake_fetcher.set_ok(
        "http://example.com/robots.txt", b"User-agent: *\nDisallow: /private/\n"
    )
    reader = _reader(fake_fetcher)
    assert reader.can_fetch("http://example.com/private/x") is False
    assert reader.can_fetch("http://example.com/public") is True


def test_allow_rule_overrides_disallow(fake_fetcher) -> None:
    fake_fetcher.set_ok(
        "http://example.com/robots.txt",
        b"User-agent: *\nDisallow: /private/\nAllow: /private/public.html\n",
    )
    reader = _reader(fake_fetcher)
    assert reader.can_fetch("http://example.com/private/public.html") is True
    assert reader.can_fetch("http://example.com/private/x") is False


def test_404_means_unavailable_therefore_allow(fake_fetcher) -> None:
    fake_fetcher.set(
        "http://example.com/robots.txt",
        FetchResult(
            url="http://example.com/robots.txt",
            final_url="http://example.com/robots.txt",
            status_code=404,
            content=b"",
        ),
    )
    reader = _reader(fake_fetcher)
    assert reader.can_fetch("http://example.com/anything") is True


def test_500_means_unreachable_therefore_disallow(fake_fetcher) -> None:
    fake_fetcher.set(
        "http://example.com/robots.txt",
        FetchResult(
            url="http://example.com/robots.txt",
            final_url="http://example.com/robots.txt",
            status_code=500,
            content=b"",
        ),
    )
    reader = _reader(fake_fetcher)
    assert reader.can_fetch("http://example.com/anything") is False


def test_network_error_means_unreachable_therefore_disallow(
    fake_fetcher,
) -> None:
    fake_fetcher.set(
        "http://example.com/robots.txt",
        FetchResult(
            url="http://example.com/robots.txt",
            final_url="http://example.com/robots.txt",
            status_code=0,
            error="fetch_error:ConnectionError",
        ),
    )
    reader = _reader(fake_fetcher)
    assert reader.can_fetch("http://example.com/anything") is False


def test_429_means_unreachable_therefore_disallow(fake_fetcher) -> None:
    fake_fetcher.set(
        "http://example.com/robots.txt",
        FetchResult(
            url="http://example.com/robots.txt",
            final_url="http://example.com/robots.txt",
            status_code=429,
            content=b"",
        ),
    )
    reader = _reader(fake_fetcher)
    assert reader.can_fetch("http://example.com/anything") is False


def test_malformed_robots_is_parsed_tolerantly(fake_fetcher) -> None:
    fake_fetcher.set_ok(
        "http://example.com/robots.txt",
        b"User-agent: *\nDisallow: /private/\n"
        b"THIS IS NOT A VALID DIRECTIVE\n"
        b"Disallow: /also-private/\n",
    )
    reader = _reader(fake_fetcher)
    # Valid lines still apply; garbage lines are ignored (RFC 9309 tolerant).
    assert reader.can_fetch("http://example.com/private/x") is False
    assert reader.can_fetch("http://example.com/also-private/x") is False
    assert reader.can_fetch("http://example.com/public") is True


def test_sitemap_directive_is_extracted(fake_fetcher) -> None:
    fake_fetcher.set_ok(
        "http://example.com/robots.txt",
        b"Sitemap: https://example.com/sitemap.xml\nUser-agent: *\nDisallow:\n",
    )
    reader = _reader(fake_fetcher)
    assert reader.sitemaps("http://example.com/") == ("https://example.com/sitemap.xml",)


def test_cache_within_ttl_avoids_refetch(fake_fetcher) -> None:
    fake_fetcher.set_ok(
        "http://example.com/robots.txt", b"User-agent: *\nDisallow: /private/\n"
    )
    clock_state = {"now": 0.0}

    def clock() -> float:
        return clock_state["now"]

    reader = _reader(fake_fetcher, clock=clock)
    assert reader.can_fetch("http://example.com/private/x") is False
    assert reader.can_fetch("http://example.com/public") is True
    assert fake_fetcher.calls.count("http://example.com/robots.txt") == 1
    # Advance well within the 24h TTL — still cached.
    clock_state["now"] = 60 * 60
    assert reader.can_fetch("http://example.com/public") is True
    assert fake_fetcher.calls.count("http://example.com/robots.txt") == 1


def test_cache_expires_after_24h(fake_fetcher) -> None:
    fake_fetcher.set_ok(
        "http://example.com/robots.txt", b"User-agent: *\nDisallow: /private/\n"
    )
    clock_state = {"now": 0.0}

    def clock() -> float:
        return clock_state["now"]

    reader = _reader(fake_fetcher, clock=clock)
    reader.can_fetch("http://example.com/public")
    assert fake_fetcher.calls.count("http://example.com/robots.txt") == 1
    # Just past 24h — must refetch.
    clock_state["now"] = 24 * 60 * 60 + 1
    reader.can_fetch("http://example.com/public")
    assert fake_fetcher.calls.count("http://example.com/robots.txt") == 2
