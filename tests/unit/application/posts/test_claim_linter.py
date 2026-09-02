"""Unit tests for the claim linter (A12 dio 1)."""

from pathlib import Path

from ai_campaign_studio.application.posts.claim_linter import (
    ClaimRules,
    lint_claim,
    load_claim_rules,
)
from ai_campaign_studio.domain.content.claims import ContentClaim
from ai_campaign_studio.domain.content.enums import ClaimStatus, ClaimType

_RULES_PATH = (
    Path(__file__).resolve().parents[4]
    / "resources"
    / "claim_rules"
    / "default_v1.yaml"
)


def _rules() -> ClaimRules:
    return ClaimRules(
        prohibited_terms=("najbolji", "garantujemo", "100%"),
        currency_symbols=("KM", "BAM", "EUR", "€", "RSD"),
    )


def _claim(status: ClaimStatus, text: str) -> ContentClaim:
    return ContentClaim(
        id="c1", text=text, type=ClaimType.FACT, status=status
    )


def test_load_claim_rules_reads_default_yaml() -> None:
    rules = load_claim_rules(_RULES_PATH)
    assert "najbolji" in rules.prohibited_terms
    assert "100%" in rules.prohibited_terms
    assert "certifikovan" in rules.prohibited_terms
    assert "KM" in rules.currency_symbols
    assert "€" in rules.currency_symbols


def test_prohibited_term_overrides_any_status() -> None:
    for status in (
        ClaimStatus.VERIFIED_BY_FACT,
        ClaimStatus.UNSUPPORTED,
        ClaimStatus.NON_FACTUAL,
    ):
        result = lint_claim(_claim(status, "Mi smo najbolji izbor"), _rules())
        assert result.status is ClaimStatus.PROHIBITED
        assert "prohibited-claim" in result.reason_codes


def test_numeric_price_is_unsupported() -> None:
    result = lint_claim(_claim(ClaimStatus.NON_FACTUAL, "Cijena je 500 KM"), _rules())
    assert result.status is ClaimStatus.UNSUPPORTED
    assert "unsupported-price" in result.reason_codes


def test_numeric_percent_is_unsupported() -> None:
    result = lint_claim(_claim(ClaimStatus.NON_FACTUAL, "Uštedite 20%"), _rules())
    assert result.status is ClaimStatus.UNSUPPORTED
    assert "unsupported-percent" in result.reason_codes


def test_numeric_duration_is_unsupported() -> None:
    result = lint_claim(_claim(ClaimStatus.NON_FACTUAL, "Traje 3 dana"), _rules())
    assert result.status is ClaimStatus.UNSUPPORTED
    assert "unsupported-duration" in result.reason_codes


def test_numeric_date_is_unsupported() -> None:
    result = lint_claim(_claim(ClaimStatus.NON_FACTUAL, "Od 01.01.2026"), _rules())
    assert result.status is ClaimStatus.UNSUPPORTED
    assert "unsupported-date" in result.reason_codes


def test_generic_number_is_unsupported() -> None:
    result = lint_claim(
        _claim(ClaimStatus.NON_FACTUAL, "Imamo 10 stomatologa"), _rules()
    )
    assert result.status is ClaimStatus.UNSUPPORTED
    assert "unsupported-number" in result.reason_codes


def test_verified_by_fact_claim_with_number_stays_verified() -> None:
    result = lint_claim(_claim(ClaimStatus.VERIFIED_BY_FACT, "500 KM"), _rules())
    assert result.status is ClaimStatus.VERIFIED_BY_FACT


def test_clean_claim_is_unchanged() -> None:
    claim = _claim(ClaimStatus.NON_FACTUAL, "Nudimo zubne implantate")
    result = lint_claim(claim, _rules())
    assert result == claim
