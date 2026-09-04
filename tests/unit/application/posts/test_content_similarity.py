"""Unit tests for cross-post text similarity (A11, dio 2)."""

from __future__ import annotations

from ai_campaign_studio.application.posts.content_similarity import (
    SIMILARITY_THRESHOLD,
    is_too_similar_to_any,
    jaccard_similarity,
)


def test_identical_text_is_1() -> None:
    assert jaccard_similarity("hello world", "hello world") == 1.0
    assert is_too_similar_to_any("hello world", ("hello world",)) is True


def test_disjoint_text_is_0() -> None:
    assert jaccard_similarity("hello world", "foo bar baz") == 0.0
    assert is_too_similar_to_any("hello world", ("foo bar baz",)) is False


def test_threshold_exact_boundary() -> None:
    # {a,b,c} intersection over {a,b,c,d,e} union = 3/5 = 0.6 (== threshold)
    assert jaccard_similarity("a b c d", "a b c e") == 0.6
    assert is_too_similar_to_any("a b c d", ("a b c e",)) is True


def test_just_below_threshold_is_not_too_similar() -> None:
    # {a,b} over {a,b,c,d,e,f} = 2/6 ≈ 0.333 (< threshold)
    assert jaccard_similarity("a b c d", "a b e f") < SIMILARITY_THRESHOLD
    assert is_too_similar_to_any("a b c d", ("a b e f",)) is False


def test_empty_text_returns_zero() -> None:
    assert jaccard_similarity("", "hello world") == 0.0
    assert jaccard_similarity("hello world", "") == 0.0
    assert jaccard_similarity("", "") == 0.0
    assert is_too_similar_to_any("", ("hello world",)) is False


def test_casefold_normalizes() -> None:
    assert jaccard_similarity("Hello WORLD", "hello world") == 1.0


def test_punctuation_only_difference_is_identical() -> None:
    assert jaccard_similarity("Naručite danas.", "Naručite danas!") == 1.0


def test_bhs_paraphrase_reflects_similarity() -> None:
    a = "Posjetite nas danas i zakažite pregled zuba."
    b = "Zakažite pregled zuba već danas kod nas."
    assert jaccard_similarity(a, b) > 0.5


def test_diacritics_match_themselves() -> None:
    assert jaccard_similarity("Zakažite č š ž đ", "zakažite č š ž đ") == 1.0
