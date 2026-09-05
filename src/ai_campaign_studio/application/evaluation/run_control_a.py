"""Control A baseline (A16, §47).

Owns the naive single-call baseline: one AI call that gets the brand, the
brief and ALL approved facts as plain context, and returns N posts directly.
No CampaignRole sequence, no allowed-fact selection, no plan review, no
per-post generation, and NO database writes.
"""

from __future__ import annotations

from ai_campaign_studio.application.evaluation.evaluation_post import EvaluationPost
from ai_campaign_studio.application.posts.claim_linter import ClaimRules, lint_claim
from ai_campaign_studio.application.schemas.ab_control_output import ControlAOutput
from ai_campaign_studio.application.schemas.social_post_generation_output import (
    ContentClaimOutput,
)
from ai_campaign_studio.domain.brand.entities import BrandSnapshot
from ai_campaign_studio.domain.campaign.entities import CampaignBrief
from ai_campaign_studio.domain.common.errors import InvariantViolation
from ai_campaign_studio.domain.common.ids import FactId, new_id
from ai_campaign_studio.domain.content.claims import ContentClaim
from ai_campaign_studio.domain.content.enums import ClaimStatus, ClaimType
from ai_campaign_studio.domain.facts.entities import ApprovedFact
from ai_campaign_studio.domain.facts.policies import is_fact_usable
from ai_campaign_studio.ports.ai import AIRequest, TextGenerationPort
from ai_campaign_studio.ports.prompts import PromptRepositoryPort

_PROMPT_NAME = "ab_control"
_PROMPT_VERSION = "1"


def run_control_a(
    brand_snapshot: BrandSnapshot,
    snapshot_facts: tuple[ApprovedFact, ...],
    brief: CampaignBrief,
    prompt_repo: PromptRepositoryPort,
    ai_port: TextGenerationPort,
    claim_rules: ClaimRules,
) -> tuple[EvaluationPost, ...]:
    prompt = prompt_repo.get(_PROMPT_NAME, _PROMPT_VERSION)
    request = AIRequest(
        purpose=_PROMPT_NAME,
        prompt_name=_PROMPT_NAME,
        prompt_version=_PROMPT_VERSION,
        system_text=prompt.instructions,
        user_text=_build_user_text(brief, brand_snapshot, snapshot_facts),
        json_schema=ControlAOutput.model_json_schema(),
    )

    response = ai_port.generate(request)
    if response.structured_payload is None:
        raise InvariantViolation("Control A response has no structured_payload")

    output = ControlAOutput.model_validate(response.structured_payload)
    usable_fact_ids = frozenset(
        fact.id for fact in snapshot_facts if is_fact_usable(fact)
    )

    posts: list[EvaluationPost] = []
    for post in output.posts:
        claims = tuple(
            lint_claim(_to_content_claim(claim, usable_fact_ids), claim_rules)
            for claim in post.claims
        )
        posts.append(
            EvaluationPost(
                role=None,
                topic=None,
                headline=post.headline,
                caption=post.caption,
                hook=post.hook,
                body=post.body,
                cta=post.cta,
                hashtags=tuple(post.hashtags),
                platform_code=None,
                format_code=None,
                claims=claims,
            )
        )
    return tuple(posts)


def _to_content_claim(
    claim: ContentClaimOutput, usable_fact_ids: frozenset[FactId]
) -> ContentClaim:
    """Map a schema claim to a domain ``ContentClaim`` (same shape as
    ``validate_claim``, but without an allowed-fact set — Control A may cite
    any usable fact, so only existence among usable facts is checked)."""
    if claim.type is not ClaimType.FACT:
        return ContentClaim(
            id=new_id(),
            text=claim.text,
            type=claim.type,
            status=ClaimStatus.NON_FACTUAL,
        )

    fact_ids = tuple(FactId(raw) for raw in claim.fact_ids)
    if not fact_ids:
        return ContentClaim(
            id=new_id(),
            text=claim.text,
            type=claim.type,
            status=ClaimStatus.UNSUPPORTED,
            fact_ids=fact_ids,
            reason_codes=("missing-fact-id",),
        )

    missing = tuple(
        "fact-not-offered" for fact_id in fact_ids if fact_id not in usable_fact_ids
    )
    if missing:
        return ContentClaim(
            id=new_id(),
            text=claim.text,
            type=claim.type,
            status=ClaimStatus.UNSUPPORTED,
            fact_ids=fact_ids,
            reason_codes=missing,
        )

    return ContentClaim(
        id=new_id(),
        text=claim.text,
        type=claim.type,
        status=ClaimStatus.VERIFIED_BY_FACT,
        fact_ids=fact_ids,
    )


def _build_user_text(
    brief: CampaignBrief,
    snapshot: BrandSnapshot,
    snapshot_facts: tuple[ApprovedFact, ...],
) -> str:
    lines = [
        "## Brand snapshot",
        f"language: {snapshot.language}",
        f"locale: {snapshot.locale}",
        f"script: {snapshot.script}",
        f"voice.formality: {snapshot.voice.formality}",
        "voice.preferred_terms: " + ", ".join(snapshot.voice.preferred_terms),
        "voice.forbidden_terms: " + ", ".join(snapshot.voice.forbidden_terms),
        "## Campaign brief",
        f"offer: {brief.offer}",
        f"goal: {brief.goal}",
        f"audience: {brief.audience_text}",
        f"content_piece_count: {brief.content_piece_count}",
        "## Approved facts",
    ]
    lines.extend(f"- {fact.content}" for fact in snapshot_facts)
    return "\n".join(lines)
