"""Unit tests for the S2-G3 crawl budget (per-domain cap + politeness)."""

from __future__ import annotations

import pytest

from ai_campaign_studio.infrastructure.web_ingestion.crawl_budget import CrawlBudget


class _FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class _RecordingSleeper:
    def __init__(self) -> None:
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


def test_politeness_sleeps_when_interval_too_short() -> None:
    clock = _FakeClock()
    sleeper = _RecordingSleeper()
    budget = CrawlBudget(politeness_seconds=1.0, sleeper=sleeper, clock=clock)

    budget.record_fetch("example.com")  # t=0
    clock.now = 0.4
    slept = budget.wait_politeness("example.com")  # 0.4 elapsed < 1.0
    assert slept == pytest.approx(0.6)
    assert sleeper.calls == [pytest.approx(0.6)]


def test_politeness_does_not_sleep_when_interval_elapsed() -> None:
    clock = _FakeClock()
    sleeper = _RecordingSleeper()
    budget = CrawlBudget(politeness_seconds=1.0, sleeper=sleeper, clock=clock)

    budget.record_fetch("example.com")  # t=0
    clock.now = 1.5
    slept = budget.wait_politeness("example.com")
    assert slept == 0.0
    assert sleeper.calls == []


def test_politeness_is_per_domain() -> None:
    clock = _FakeClock()
    sleeper = _RecordingSleeper()
    budget = CrawlBudget(politeness_seconds=1.0, sleeper=sleeper, clock=clock)

    budget.record_fetch("a.example")  # t=0
    clock.now = 0.1
    # Different domain → no politeness constraint.
    assert budget.wait_politeness("b.example") == 0.0
    assert sleeper.calls == []


def test_max_urls_per_domain_limits_crawl() -> None:
    budget = CrawlBudget(max_urls_per_domain=3)
    assert budget.can_crawl("example.com") is True
    budget.record_fetch("example.com")
    budget.record_fetch("example.com")
    budget.record_fetch("example.com")
    assert budget.can_crawl("example.com") is False
    # A different domain is unaffected.
    assert budget.can_crawl("other.com") is True


def test_reset_per_domain_and_global() -> None:
    budget = CrawlBudget(max_urls_per_domain=1)
    budget.record_fetch("example.com")
    assert budget.count("example.com") == 1
    budget.reset("example.com")
    assert budget.count("example.com") == 0
    budget.record_fetch("example.com")
    budget.record_fetch("other.com")
    budget.reset()
    assert budget.count("example.com") == 0
    assert budget.count("other.com") == 0


def test_invalid_configuration_raises() -> None:
    with pytest.raises(ValueError):
        CrawlBudget(max_urls_per_domain=-1)
    with pytest.raises(ValueError):
        CrawlBudget(politeness_seconds=-1)
