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
        prohibited_terms=(
            "najbolji",
            "garantujemo",
            "100%",
            "jedini",
            "bez rizika",
            "potpuno sigurno",
            "vodeći",
        ),
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


def test_prohibited_term_substring_not_flagged() -> None:
    # "jedinice" contains the prohibited term "jedini" as a substring, but
    # must NOT be escalated: only the whole word "jedini" is prohibited.
    claim = _claim(
        ClaimStatus.VERIFIED_BY_FACT,
        "Ordinacija ima tri jedinice za digitalno skeniranje zuba.",
    )
    result = lint_claim(claim, _rules())
    assert result.status is ClaimStatus.VERIFIED_BY_FACT
    assert "prohibited-claim" not in result.reason_codes


def test_duration_substring_not_flagged() -> None:
    # "danas" contains the duration unit "dan", but the "1" is a generic
    # number, not a duration. It must NOT get unsupported-duration.
    claim = _claim(
        ClaimStatus.NON_FACTUAL,
        "Posjetite nas danas, mjesto broj 1 za vas osmijeh.",
    )
    result = lint_claim(claim, _rules())
    assert "unsupported-duration" not in result.reason_codes
    # The "1" is still a legitimate generic numeric signal.
    assert "unsupported-number" in result.reason_codes


def test_multiword_prohibited_terms_still_work() -> None:
    for text in (
        "Tretman je potpuno bez rizika.",
        "Naš pristup je potpuno sigurno rješenje.",
    ):
        result = lint_claim(_claim(ClaimStatus.NON_FACTUAL, text), _rules())
        assert result.status is ClaimStatus.PROHIBITED
        assert "prohibited-claim" in result.reason_codes


def test_currency_symbol_substring_not_flagged() -> None:
    # "bambus" contains the currency symbol "BAM" (casefolded "bam") as a
    # substring, but must NOT be flagged as a price signal.
    claim = _claim(
        ClaimStatus.NON_FACTUAL,
        "Koristimo 3 bambus četkice.",
    )
    result = lint_claim(claim, _rules())
    assert "unsupported-price" not in result.reason_codes


def test_non_ascii_prohibited_term_whole_word() -> None:
    # "vodeći" has a non-ASCII "ć"; word boundary must still match it as a
    # whole word.
    result = lint_claim(_claim(ClaimStatus.NON_FACTUAL, "Mi smo vodeći."), _rules())
    assert result.status is ClaimStatus.PROHIBITED
    assert "prohibited-claim" in result.reason_codes


def test_euro_symbol_price_is_still_unsupported() -> None:
    # "€" is a non-word symbol: \b cannot anchor around it, so it must fall
    # back to a plain substring match and still flag the price.
    result = lint_claim(_claim(ClaimStatus.NON_FACTUAL, "Cijena je 500€"), _rules())
    assert result.status is ClaimStatus.UNSUPPORTED
    assert "unsupported-price" in result.reason_codes


def test_percent_prohibited_term_still_works() -> None:
    # "100%" ends with a non-word "%" so \b cannot anchor after it; it must
    # still be flagged as a prohibited term via plain substring.
    result = lint_claim(_claim(ClaimStatus.NON_FACTUAL, "Uštedite 100%"), _rules())
    assert result.status is ClaimStatus.PROHIBITED
    assert "prohibited-claim" in result.reason_codes
