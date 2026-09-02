"""Fact-ID claim validator (A11, plan section 35).

Owns validating a claim's fact references: a FACT claim must reference
existing, usable, allowed facts; CTA/OPINION/CREATIVE claims are always
``NON_FACTUAL``. No prohibited-term/numeric-pattern linter here — that is A12.
"""

from __future__ import annotations

from ai_campaign_studio.application.posts.select_allowed_facts import AllowedFactSet
from ai_campaign_studio.application.schemas.social_post_generation_output import (
    ContentClaimOutput,
)
from ai_campaign_studio.domain.common.ids import FactId, new_id
from ai_campaign_studio.domain.content.claims import ContentClaim
from ai_campaign_studio.domain.content.enums import ClaimStatus, ClaimType
from ai_campaign_studio.domain.facts.policies import is_fact_usable
from ai_campaign_studio.ports.repositories import FactRepositoryPort


def validate_claim(
    claim: ContentClaimOutput, allowed: AllowedFactSet, fact_repo: FactRepositoryPort
) -> ContentClaim:
    """Return a domain ``ContentClaim`` with a real ``ClaimStatus``.

    FACT rules (section 35): every referenced fact must exist
    (``get_fact``), be usable (``is_fact_usable``), and be in the allowed
    set. Any violation marks the claim ``UNSUPPORTED`` with reason codes.
    """
    if claim.type is not ClaimType.FACT:
        return ContentClaim(
            id=new_id(),
            text=claim.text,
            type=claim.type,
            status=ClaimStatus.NON_FACTUAL,
        )

    if not claim.fact_ids:
        return ContentClaim(
            id=new_id(),
            text=claim.text,
            type=claim.type,
            status=ClaimStatus.UNSUPPORTED,
            reason_codes=("missing-fact-id",),
        )

    fact_ids: list[FactId] = []
    reason_codes: list[str] = []
    for raw_id in claim.fact_ids:
        fact_id = FactId(raw_id)
        fact_ids.append(fact_id)

        fact = fact_repo.get_fact(fact_id)
        if fact is None:
            reason_codes.append("fact-not-found")
        elif not is_fact_usable(fact):
            reason_codes.append("fact-not-approved")
        elif fact_id not in allowed.fact_ids:
            reason_codes.append("fact-not-offered")

    if reason_codes:
        return ContentClaim(
            id=new_id(),
            text=claim.text,
            type=claim.type,
            status=ClaimStatus.UNSUPPORTED,
            fact_ids=tuple(fact_ids),
            reason_codes=tuple(reason_codes),
        )

    return ContentClaim(
        id=new_id(),
        text=claim.text,
        type=claim.type,
        status=ClaimStatus.VERIFIED_BY_FACT,
        fact_ids=tuple(fact_ids),
    )
