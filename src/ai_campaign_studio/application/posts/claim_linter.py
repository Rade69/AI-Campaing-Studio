"""Claim linter (A12 dio 1, plan section 36).

Owns the data-driven, deterministic linter that escalates claim status based
on prohibited/risky terms and numeric-pattern signals. Rule lists live in
``resources/claim_rules/default_v1.yaml``, not hardcoded in Python.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from ai_campaign_studio.domain.content.claims import ContentClaim
from ai_campaign_studio.domain.content.enums import ClaimStatus

_DURATION_UNITS = (
    "dan",
    "dana",
    "sedmica",
    "nedelja",
    "mjesec",
    "mesec",
    "godina",
    "minuta",
    "sat",
    "day",
    "days",
    "week",
    "weeks",
    "month",
    "months",
    "year",
    "years",
    "minute",
    "minutes",
    "hour",
    "hours",
)


@dataclass(frozen=True)
class ClaimRules:
    """Loaded linter rules (prohibited terms + currency symbols)."""

    prohibited_terms: tuple[str, ...]
    currency_symbols: tuple[str, ...]


def load_claim_rules(path: Path) -> ClaimRules:
    """Load the claim rules from a YAML file."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return ClaimRules(
        prohibited_terms=tuple(raw["prohibited_terms"]),
        currency_symbols=tuple(raw["currency_symbols"]),
    )


def _contains_word(text_folded: str, term: str) -> bool:
    """Match a term either as a whole word or as a literal substring.

    Terms whose both edges are word characters (``"jedini"``, ``"dan"``,
    ``"BAM"``, multi-word ``"bez rizika"``) use ``\b`` word boundaries so a
    term does not match inside a longer word (``"jedinice"`` must not trigger
    ``"jedini"``). Terms that start or end with a non-word character (``"€"``,
    ``"100%"``) fall back to a plain substring match: ``\b`` cannot anchor
    around a non-word character, and a symbol/percent sign cannot be "inside"
    a larger alphanumeric word, so plain substring is safe there.
    ``re.escape`` keeps multi-word terms and terms with regex-special
    characters working as literals.
    """
    folded_term = term.casefold()
    starts_word = re.match(r"\w", folded_term) is not None
    ends_word = re.search(r"\w$", folded_term) is not None
    if starts_word and ends_word:
        return re.search(rf"\b{re.escape(folded_term)}\b", text_folded) is not None
    return folded_term in text_folded


def lint_claim(claim: ContentClaim, rules: ClaimRules) -> ContentClaim:
    """Apply linter rules to one claim, possibly escalating its status.

    Applied to every claim regardless of current status. A prohibited/risky
    term always wins (``PROHIBITED`` overrides even ``VERIFIED_BY_FACT``).
    Numeric signals are only raised for claims that are NOT already
    ``VERIFIED_BY_FACT`` (a fact-backed number already passed the real check).
    """
    text_folded = claim.text.casefold()

    for term in rules.prohibited_terms:
        if _contains_word(text_folded, term):
            return replace(
                claim,
                status=ClaimStatus.PROHIBITED,
                reason_codes=(*claim.reason_codes, "prohibited-claim"),
            )

    if claim.status is ClaimStatus.VERIFIED_BY_FACT:
        return claim

    reason_code = _numeric_reason_code(text_folded, rules)
    if reason_code is not None:
        return replace(
            claim,
            status=ClaimStatus.UNSUPPORTED,
            reason_codes=(*claim.reason_codes, reason_code),
        )

    return claim


def _numeric_reason_code(text_folded: str, rules: ClaimRules) -> str | None:
    """Return the first matching numeric-signal reason code, or None.

    Checked in order: price, percent, duration, date, generic number.
    """
    has_digit = re.search(r"\d", text_folded) is not None

    for symbol in rules.currency_symbols:
        if _contains_word(text_folded, symbol) and has_digit:
            return "unsupported-price"

    if re.search(r"\d+\s*%", text_folded):
        return "unsupported-percent"

    for unit in _DURATION_UNITS:
        if _contains_word(text_folded, unit) and has_digit:
            return "unsupported-duration"

    if re.search(r"\d{1,2}\.\d{1,2}\.\d{2,4}", text_folded):
        return "unsupported-date"

    if has_digit:
        return "unsupported-number"

    return None
