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
            # ACS-F1-028: morphological variants of the ``garant-`` root
            # so the linter catches the cases reported during A16
            # (notably "garantovano" — the original term was
            # ``garantujemo``/1st-person plural, the production text
            # used the past-participle form and slipped through).
            "garantovano",
            "garantovan",
            "garantuje",
            "garantujem",
            "garantuju",
            "garancija",
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


def test_glued_currency_number_is_specific_price() -> None:
    # A digit glued directly to a currency symbol ("30KM") is a legitimate
    # price signal and must be flagged as unsupported-price, not the
    # generic unsupported-number.
    result = lint_claim(
        _claim(ClaimStatus.NON_FACTUAL, "Cijena je 30KM ukupno."), _rules()
    )
    assert result.status is ClaimStatus.UNSUPPORTED
    assert "unsupported-price" in result.reason_codes


def test_glued_duration_number_is_specific_duration() -> None:
    # A digit glued directly to a duration unit ("3dana") is a legitimate
    # duration signal and must be flagged as unsupported-duration, not the
    # generic unsupported-number.
    result = lint_claim(
        _claim(ClaimStatus.NON_FACTUAL, "Akcija traje 3dana."), _rules()
    )
    assert result.status is ClaimStatus.UNSUPPORTED
    assert "unsupported-duration" in result.reason_codes


def test_letter_adjacent_unit_is_not_duration() -> None:
    # Only a DIGIT adjacency is allowed for duration units; a letter glued
    # before the unit ("nedana") still means the unit is inside a larger
    # word and must NOT be flagged as a duration.
    result = lint_claim(
        _claim(ClaimStatus.NON_FACTUAL, "To je nedana 5."), _rules()
    )
    assert "unsupported-duration" not in result.reason_codes


# --- ACS-F1-028: morphological variants of the "garant-" root ---


def test_garantovano_past_participle_is_prohibited() -> None:
    """The A16 production text "Garantovano cete dobiti istu razinu..."
    was NOT caught by the linter before ACS-F1-028 because the only
    "garant-" term in the rules was "garantujemo" (1st-person
    plural). The past-participle form "garantovano" is a different
    word, so the per-term substring match missed it. After the
    morphological fix, this text MUST escalate to PROHIBITED with
    "prohibited-claim" in the reason codes."""
    result = lint_claim(
        _claim(
            ClaimStatus.NON_FACTUAL,
            "Garantovano ćete dobiti istu razinu profesionalnosti.",
        ),
        _rules(),
    )
    assert result.status is ClaimStatus.PROHIBITED
    assert "prohibited-claim" in result.reason_codes


def test_garantovan_masculine_adjective_is_prohibited() -> None:
    """Same root, masculine adjective form (used as short-form predicate)."""
    result = lint_claim(
        _claim(
            ClaimStatus.NON_FACTUAL,
            "Naš rezultat je garantovan na 5 godina.",
        ),
        _rules(),
    )
    assert result.status is ClaimStatus.PROHIBITED
    assert "prohibited-claim" in result.reason_codes


def test_garantuje_third_person_singular_is_prohibited() -> None:
    """Same root, 3rd-person singular present ("garantuje" = "he/she/it guarantees")."""
    result = lint_claim(
        _claim(
            ClaimStatus.NON_FACTUAL,
            "Naš tim garantuje potpunu sigurnost.",
        ),
        _rules(),
    )
    assert result.status is ClaimStatus.PROHIBITED
    assert "prohibited-claim" in result.reason_codes


def test_garantujem_first_person_singular_is_prohibited() -> None:
    """Same root, 1st-person singular present ("garantujem" = "I guarantee")."""
    result = lint_claim(
        _claim(
            ClaimStatus.NON_FACTUAL,
            "Garantujem vam da će sve biti u redu.",
        ),
        _rules(),
    )
    assert result.status is ClaimStatus.PROHIBITED
    assert "prohibited-claim" in result.reason_codes


def test_garantuju_third_person_plural_is_prohibited() -> None:
    """Same root, 3rd-person plural present ("garantuju" = "they guarantee")."""
    result = lint_claim(
        _claim(
            ClaimStatus.NON_FACTUAL,
            "Naše preporuke garantuju kvalitet.",
        ),
        _rules(),
    )
    assert result.status is ClaimStatus.PROHIBITED
    assert "prohibited-claim" in result.reason_codes


def test_garancija_noun_is_prohibited() -> None:
    """The noun "garancija" is the same semantic field as the
    "garant-" verb/adjective family. Without it, a claim like
    "Ova garancija je na 5 godina" would slip through (the linter
    matches whole words with ``\\b`` boundaries, so "garancija" as
    a standalone noun does not match the unrelated verb
    "garantujemo" -- BHS naturally uses the noun in such claims,
    never "garantujemo garanciju").

    Reviewer note (per contract): the noun is one step removed from
    the originally reported past-participle case. Including it here
    because the same A16 finding discovered BOTH the past-participle
    AND the noun form slipping through, and the data-only fix is
    cheap. If a future finding shows this scope was wrong, removing
    the entry is a 1-line YAML change.
    """
    result = lint_claim(
        _claim(
            ClaimStatus.NON_FACTUAL,
            "Garancija od 5 godina je uklju\u010dena u cijenu.",
        ),
        _rules(),
    )
    assert result.status is ClaimStatus.PROHIBITED
    assert "prohibited-claim" in result.reason_codes


def test_morphological_fix_does_not_break_existing_garantujemo() -> None:
    """Regression: the original "garantujemo" term MUST still match
    (the fix added new terms, did not remove or rename the old one)."""
    result = lint_claim(
        _claim(
            ClaimStatus.NON_FACTUAL,
            "Mi garantujemo najbolji kvalitet.",
        ),
        _rules(),
    )
    assert result.status is ClaimStatus.PROHIBITED
    assert "prohibited-claim" in result.reason_codes


def test_garantujete_second_person_does_not_match() -> None:
    """The fix covers the A16-reported variants only. "garantujete"
    (2nd-person plural "you guarantee") is a different person/number
    form we have NOT added yet -- it should NOT match (this is the
    honest, explicit acknowledgement that data-only fix has a finite
    reach; stemming/lemmatization would be the next step if this
    becomes a real A17 finding)."""
    result = lint_claim(
        _claim(
            ClaimStatus.NON_FACTUAL,
            "Vi garantujete 6 godina.",
        ),
        _rules(),
    )
    # "garantujete" is NOT in the list -- the text should NOT be
    # prohibited for that reason. The duration ("6 mjeseci") will
    # still be flagged as unsupported-duration, but
    # "prohibited-claim" must be absent.
    assert "prohibited-claim" not in result.reason_codes
    assert "unsupported-duration" in result.reason_codes


def test_load_claim_rules_yaml_contains_all_morphological_variants() -> None:
    """YAML-level check: every variant added in ACS-F1-028 is present
    in the live rules file. This guards against someone editing the
    in-code ``_rules()`` helper in tests but forgetting the YAML
    (the production linter reads the YAML)."""
    rules = load_claim_rules(_RULES_PATH)
    for variant in (
        "garantovano",
        "garantovan",
        "garantuje",
        "garantujem",
        "garantuju",
        "garancija",
    ):
        assert variant in rules.prohibited_terms, (
            f"{variant!r} missing from YAML rules"
        )
    # And the original term is still there.
    assert "garantujemo" in rules.prohibited_terms


def test_garancijski_does_not_trigger_via_word_boundary() -> None:
    """The whole-word match in ``_contains_word`` uses ``\b`` boundaries
    so a derived adjective "garancijski" must NOT match the bare
    noun "garancija" -- the word "garancija" is a substring of
    "garancijski" but they are different words. The linter must stay
    precise: catching the noun does not mean catching every adjective
    that happens to share a root."""
    result = lint_claim(
        _claim(
            ClaimStatus.NON_FACTUAL,
            "Dobijate garancijski list uz svaku uslugu.",
        ),
        _rules(),
    )
    # No prohibited-claim reason code -- the "garancija" match is
    # word-bounded and does not match "garancijski".
    assert "prohibited-claim" not in result.reason_codes
