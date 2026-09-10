"""Unit tests for BoilerplateFilter (S2-G4)."""

from __future__ import annotations

from ai_campaign_studio.infrastructure.extraction import BoilerplateFilter


def test_filter_removes_social_share_labels() -> None:
    text = "Stvarni sadržaj članka.\n\nPodijeli\n\nFacebook\n\nJoš teksta."
    assert BoilerplateFilter().filter(text) == "Stvarni sadržaj članka.\n\nJoš teksta."


def test_filter_removes_copyright_line() -> None:
    text = "Sadržaj.\n\n© 2026 Sva prava zadržana"
    out = BoilerplateFilter().filter(text)
    assert "Sva prava zadržana" not in out
    assert "Sadržaj." in out


def test_filter_removes_cookie_consent_line() -> None:
    text = "Sadržaj.\n\nKoristimo kolačiće za bolje iskustvo."
    out = BoilerplateFilter().filter(text)
    assert "kolačiće" not in out
    assert "Sadržaj." in out


def test_filter_preserves_legitimate_content() -> None:
    text = "Naslov vijesti\n\nPrvi paragraf sa stvarnim podacima o događaju."
    assert BoilerplateFilter().filter(text) == text


def test_filter_preserves_word_cookie_in_recipe_context() -> None:
    # "kolačić" = biscuit too; a recipe line must NOT be dropped.
    text = "Recept: umutite tijesto za kolačiće pa pecite 20 minuta."
    assert BoilerplateFilter().filter(text) == text


def test_filter_empty_text() -> None:
    assert BoilerplateFilter().filter("") == ""


def test_filter_is_deterministic() -> None:
    text = "A\n\nPodijeli\n\nB\n\nFacebook\n\nC"
    first = BoilerplateFilter().filter(text)
    second = BoilerplateFilter().filter(text)
    assert first == second == "A\n\nB\n\nC"
