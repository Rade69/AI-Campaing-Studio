"""GenerateSocialPost use-case (A11).

Owns the social-post generation pipeline: load campaign/plan/item/snapshot/
facts, select allowed facts, build the AI request, validate the structured
output and its claims, then persist the ``ContentPiece`` atomically. Depends
only on ports — no channels/ai_registry/provider imports.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Protocol

from ai_campaign_studio.application.posts.claim_linter import (
    lint_claim,
    load_claim_rules,
)
from ai_campaign_studio.application.posts.claim_validator import validate_claim
from ai_campaign_studio.application.posts.content_similarity import (
    is_too_similar_to_any,
)
from ai_campaign_studio.application.posts.derive_content_status import (
    derive_content_status,
)
from ai_campaign_studio.application.posts.select_allowed_facts import (
    AllowedFactSet,
    select_allowed_facts,
)
from ai_campaign_studio.application.schemas.social_post_generation_output import (
    SocialPostGenerationOutput,
)
from ai_campaign_studio.domain.brand.entities import BrandSnapshot
from ai_campaign_studio.domain.campaign.entities import CampaignItem
from ai_campaign_studio.domain.campaign.enums import CampaignPlanStatus
from ai_campaign_studio.domain.common.errors import EntityNotFound, InvariantViolation
from ai_campaign_studio.domain.common.ids import (
    CampaignId,
    CampaignItemId,
    CampaignPlanId,
    PostId,
    RevisionId,
    new_id,
)
from ai_campaign_studio.domain.common.timestamps import utc_now
from ai_campaign_studio.domain.content.entities import (
    CampaignTarget,
    ContentPiece,
    SocialPostPayload,
)
from ai_campaign_studio.domain.content.enums import ContentPayloadType, ContentStatus
from ai_campaign_studio.domain.content.revisions import Revision, RevisionOrigin
from ai_campaign_studio.domain.facts.entities import ApprovedFact
from ai_campaign_studio.ports.ai import AIRequest, TextGenerationPort
from ai_campaign_studio.ports.prompts import PromptRepositoryPort
from ai_campaign_studio.ports.repositories import (
    BrandRepositoryPort,
    CampaignRepositoryPort,
    ContentRepositoryPort,
    FactRepositoryPort,
    RevisionRepositoryPort,
)

_PROMPT_NAME = "post_generation"
_PROMPT_VERSION = "1"
_CLAIM_RULES_PATH = (
    Path(__file__).resolve().parents[4]
    / "resources"
    / "claim_rules"
    / "default_v1.yaml"
)


class _UnitOfWork(Protocol):
    """Minimal transaction boundary the use-case needs."""

    def __enter__(self) -> _UnitOfWork: ...

    def __exit__(
        self, exc_type: object, exc_value: object, traceback: object
    ) -> bool: ...

    def commit(self) -> None: ...


class GenerateSocialPost:
    """Generate and persist one social post for a campaign item."""

    def __init__(
        self,
        campaign_repo: CampaignRepositoryPort,
        brand_repo: BrandRepositoryPort,
        fact_repo: FactRepositoryPort,
        content_repo: ContentRepositoryPort,
        revision_repo: RevisionRepositoryPort,
        prompt_repo: PromptRepositoryPort,
        ai_port: TextGenerationPort,
        unit_of_work: _UnitOfWork,
    ) -> None:
        self._campaign_repo = campaign_repo
        self._brand_repo = brand_repo
        self._fact_repo = fact_repo
        self._content_repo = content_repo
        self._revision_repo = revision_repo
        self._prompt_repo = prompt_repo
        self._ai_port = ai_port
        self._unit_of_work = unit_of_work

    def execute(
        self,
        campaign_id: CampaignId,
        plan_id: CampaignPlanId,
        campaign_item_id: CampaignItemId,
        target: CampaignTarget,
    ) -> ContentPiece:
        campaign = self._campaign_repo.get_campaign(campaign_id)
        if campaign is None:
            raise EntityNotFound(f"campaign {campaign_id} not found")

        plan = self._campaign_repo.get_plan(plan_id)
        if plan is None:
            raise EntityNotFound(f"campaign plan {plan_id} not found")

        if plan.status is not CampaignPlanStatus.APPROVED:
            raise InvariantViolation(
                f"campaign plan {plan_id} is {plan.status.value}; only an "
                "APPROVED plan can be used to generate posts"
            )

        campaign_item = next(
            (item for item in plan.items if item.id == campaign_item_id), None
        )
        if campaign_item is None:
            raise EntityNotFound(
                f"campaign item {campaign_item_id} not found in plan {plan_id}"
            )

        snapshot = self._brand_repo.get_snapshot(campaign.brand_snapshot_id)
        if snapshot is None:
            raise EntityNotFound(
                f"brand snapshot {campaign.brand_snapshot_id} not found"
            )

        snapshot_facts = self._fact_repo.list_snapshot_facts(snapshot.id)
        allowed = select_allowed_facts(campaign_item, snapshot_facts)

        prompt = self._prompt_repo.get(_PROMPT_NAME, _PROMPT_VERSION)
        request = AIRequest(
            purpose=_PROMPT_NAME,
            prompt_name=_PROMPT_NAME,
            prompt_version=_PROMPT_VERSION,
            system_text=prompt.instructions,
            user_text=_build_user_text(
                campaign_item, snapshot, allowed, snapshot_facts, target
            ),
            json_schema=SocialPostGenerationOutput.model_json_schema(),
        )

        response = self._ai_port.generate(request)
        if response.structured_payload is None:
            raise InvariantViolation("AI response has no structured_payload")

        output = SocialPostGenerationOutput.model_validate(
            response.structured_payload
        )

        validated = (
            validate_claim(claim, allowed, self._fact_repo) for claim in output.claims
        )
        rules = load_claim_rules(_CLAIM_RULES_PATH)
        claims = tuple(lint_claim(claim, rules) for claim in validated)
        status = derive_content_status(claims)

        payload = SocialPostPayload(
            headline=output.headline,
            caption=output.caption,
            hook=output.hook,
            body=output.body,
            cta=output.cta,
            hashtags=tuple(output.hashtags),
        )

        existing_texts = tuple(
            f"{piece.payload.headline} {piece.payload.caption}"
            for piece in self._content_repo.list_campaign_content(campaign_id)
            if piece.payload is not None
        )
        if is_too_similar_to_any(
            f"{output.headline} {output.caption}", existing_texts
        ):
            status = ContentStatus.NEEDS_REVIEW

        now = utc_now()
        piece_id = PostId(new_id())
        revision = Revision(
            id=RevisionId(new_id()),
            entity_type="ContentPiece",
            entity_id=str(piece_id),
            version=1,
            timestamp=now,
            origin=RevisionOrigin.AI,
            previous_value=json.dumps(None),
            new_value=json.dumps(asdict(payload)),
            provider=response.provider,
            model=response.model,
            prompt_version=_PROMPT_VERSION,
            instruction=None,
        )
        content_piece = ContentPiece(
            id=piece_id,
            campaign_item_id=campaign_item.id,
            target=target,
            payload_type=ContentPayloadType.SOCIAL_POST,
            status=status,
            brand_snapshot_id=snapshot.id,
            created_at=now,
            updated_at=now,
            facts_allowed=allowed.fact_ids,
            claims=claims,
            revision_ids=(revision.id,),
            payload=payload,
        )

        with self._unit_of_work:
            self._revision_repo.save_revision(revision)
            self._content_repo.save_content_piece(content_piece)
            self._unit_of_work.commit()

        return content_piece


def _build_user_text(
    campaign_item: CampaignItem,
    snapshot: BrandSnapshot,
    allowed: AllowedFactSet,
    snapshot_facts: tuple[ApprovedFact, ...],
    target: CampaignTarget,
) -> str:
    """Assemble the user-side prompt context.

    The prompt's ``instructions`` live in ``system_text``; this payload
    carries the concrete data (item, brand, allowed facts, target). The model
    must see the actual fact text so it can cite facts faithfully.
    """
    fact_by_id = {fact.id: fact for fact in snapshot_facts}

    lines = [
        "## Campaign item",
        f"role: {campaign_item.role.value}",
        f"topic: {campaign_item.topic}",
        f"goal: {campaign_item.goal}",
    ]
    if campaign_item.facts_needed:
        lines.append("facts_needed: " + ", ".join(campaign_item.facts_needed))

    lines.append("## Brand snapshot")
    lines.append(f"language: {snapshot.language}")
    lines.append(f"locale: {snapshot.locale}")
    lines.append(f"script: {snapshot.script}")
    lines.append(f"voice.formality: {snapshot.voice.formality}")
    lines.append(
        "voice.preferred_terms: " + ", ".join(snapshot.voice.preferred_terms)
    )
    lines.append(
        "voice.forbidden_terms: " + ", ".join(snapshot.voice.forbidden_terms)
    )
    lines.append(
        "voice.regional_vocabulary: " + ", ".join(snapshot.voice.regional_vocabulary)
    )
    lines.append("voice.tone_examples: " + "; ".join(snapshot.voice.tone_examples))

    lines.append("## Allowed facts")
    if allowed.fact_ids:
        for fact_id in allowed.fact_ids:
            fact = fact_by_id.get(fact_id)
            content = fact.content if fact is not None else "(unknown)"
            lines.append(f"- [{fact_id}] {content}")
    else:
        lines.append("(none)")

    lines.append("## Target")
    lines.append(f"channel: {target.channel}")
    lines.append(f"platform_code: {target.platform_code}")
    lines.append(f"format_code: {target.format_code}")

    return "\n".join(lines)
