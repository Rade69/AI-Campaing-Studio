"""Unit tests for the analytics match key (Faza 0.7 §16, Faza 1 v1.5 §6)."""

from __future__ import annotations

from ai_campaign_studio.domain.analytics.match_key import compute_analytics_match_key


def test_analytics_match_key_is_stable_for_same_revision() -> None:
    args = ("piece-1", "rev-1", "INSTAGRAM", "FEED_POST")
    assert compute_analytics_match_key(*args) == compute_analytics_match_key(*args)


def test_analytics_match_key_changes_on_revision_change() -> None:
    base = ("piece-1", "rev-1", "INSTAGRAM", "FEED_POST")
    changed = ("piece-1", "rev-2", "INSTAGRAM", "FEED_POST")
    assert compute_analytics_match_key(*base) != compute_analytics_match_key(*changed)


def test_analytics_match_key_changes_on_target_change() -> None:
    base = ("piece-1", "rev-1", "INSTAGRAM", "FEED_POST")
    platform_changed = ("piece-1", "rev-1", "FACEBOOK", "FEED_POST")
    format_changed = ("piece-1", "rev-1", "INSTAGRAM", "STORY_POST")
    assert compute_analytics_match_key(*base) != compute_analytics_match_key(
        *platform_changed
    )
    assert compute_analytics_match_key(*base) != compute_analytics_match_key(
        *format_changed
    )


def test_analytics_match_key_has_no_secret_shaped_output() -> None:
    key = compute_analytics_match_key("piece-1", "rev-1", "INSTAGRAM", "FEED_POST")
    # Deterministic length + pure hex, no raw UUID/registry leakage in the
    # output (it is a hash, not a concatenation).
    assert len(key) == 32
    assert all(c in "0123456789abcdef" for c in key)
    assert "piece-1" not in key
    assert "INSTAGRAM" not in key
