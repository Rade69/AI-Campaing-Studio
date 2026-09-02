"""GenerateCampaignPlan use-case (A9).

Owns the campaign-plan generation pipeline: load persisted campaign/snapshot/
brief, build the AI request, validate the structured output (schema + domain),
then persist the plan and advance the campaign status atomically. Depends only
on ports — no SQLite, YAML or provider imports.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from ai_campaign_studio.application.schemas.campaign_plan_output import (
    CampaignPlanOutput,
    validate_campaign_plan_output,
)
from ai_campaign_studio.domain.brand.entities import BrandSnapshot
from ai_campaign_studio.domain.campaign.entities import (
    CampaignBrief,
    CampaignItem,
    CampaignPlan,
)
from ai_campaign_studio.domain.campaign.enums import (
    CampaignItemStatus,
    CampaignPlanStatus,
    CampaignStatus,
)
from ai_campaign_studio.domain.campaign.roles import CampaignRole
from ai_campaign_studio.domain.campaign.templates import (
    LEAD_GENERATION_V1,
    CampaignTemplate,
)
from ai_campaign_studio.domain.common.errors import EntityNotFound, InvariantViolation
from ai_campaign_studio.domain.common.ids import (
    CampaignId,
    CampaignItemId,
    CampaignPlanId,
    new_id,
)
from ai_campaign_studio.domain.common.timestamps import utc_now
from ai_campaign_studio.ports.ai import AIRequest, TextGenerationPort
from ai_campaign_studio.ports.prompts import PromptRepositoryPort
from ai_campaign_studio.ports.repositories import (
    BrandRepositoryPort,
    CampaignRepositoryPort,
)

_PROMPT_NAME = "campaign_plan"
_PROMPT_VERSION = "1"


class _UnitOfWork(Protocol):
    """Minimal transaction boundary the use-case needs."""

    def __enter__(self) -> _UnitOfWork: ...

    def __exit__(
        self, exc_type: object, exc_value: object, traceback: object
    ) -> bool: ...

    def commit(self) -> None: ...


class GenerateCampaignPlan:
    """Generate a campaign plan and advance the campaign to PLAN_GENERATED."""

    def __init__(
        self,
        campaign_repo: CampaignRepositoryPort,
        brand_repo: BrandRepositoryPort,
        prompt_repo: PromptRepositoryPort,
        ai_port: TextGenerationPort,
        unit_of_work: _UnitOfWork,
    ) -> None:
        self._campaign_repo = campaign_repo
        self._brand_repo = brand_repo
        self._prompt_repo = prompt_repo
        self._ai_port = ai_port
        self._unit_of_work = unit_of_work

    def execute(self, campaign_id: CampaignId) -> CampaignPlan:
        campaign = self._campaign_repo.get_campaign(campaign_id)
        if campaign is None:
            raise EntityNotFound(f"campaign {campaign_id} not found")

        snapshot = self._brand_repo.get_snapshot(campaign.brand_snapshot_id)
        if snapshot is None:
            raise EntityNotFound(
                f"brand snapshot {campaign.brand_snapshot_id} not found"
            )

        brief = self._campaign_repo.get_brief(campaign.brief_id)
        if brief is None:
            raise EntityNotFound(f"campaign brief {campaign.brief_id} not found")

        prompt = self._prompt_repo.get(_PROMPT_NAME, _PROMPT_VERSION)
        request = AIRequest(
            purpose=_PROMPT_NAME,
            prompt_name=_PROMPT_NAME,
            prompt_version=_PROMPT_VERSION,
            system_text=prompt.instructions,
            user_text=_build_user_text(brief, snapshot, LEAD_GENERATION_V1),
            json_schema=CampaignPlanOutput.model_json_schema(),
        )

        response = self._ai_port.generate(request)
        if response.structured_payload is None:
            raise InvariantViolation("AI response has no structured_payload")

        output = validate_campaign_plan_output(
            response.structured_payload, brief.content_piece_count
        )
        _validate_plan_domain(output)

        items = tuple(
            CampaignItem(
                id=CampaignItemId(new_id()),
                order=item.order,
                role=item.role,
                topic=item.topic,
                goal=item.goal,
                status=CampaignItemStatus.PLANNED,
                facts_needed=tuple(item.facts_needed),
            )
            for item in output.items
        )

        plan = CampaignPlan(
            id=CampaignPlanId(new_id()),
            campaign_id=campaign.id,
            version=1,
            status=CampaignPlanStatus.DRAFT,
            created_at=utc_now(),
            items=items,
        )

        updated_campaign = replace(campaign, status=CampaignStatus.PLAN_GENERATED)

        with self._unit_of_work:
            self._campaign_repo.save_plan(plan)
            self._campaign_repo.save_campaign(updated_campaign)
            self._unit_of_work.commit()

        return plan


def _build_user_text(
    brief: CampaignBrief, snapshot: BrandSnapshot, template: CampaignTemplate
) -> str:
    """Assemble the user-side prompt context (brief + snapshot + roles + template).

    The prompt's ``instructions`` already live in ``system_text``; this payload
    carries the concrete data. Plain text, no JSON, no LLM-dependent format.
    """
    lines = [
        "## Campaign brief",
        f"offer: {brief.offer}",
        f"goal: {brief.goal}",
        f"audience: {brief.audience_text}",
        f"content_piece_count: {brief.content_piece_count}",
        f"content_language_context: {brief.content_language_context}",
    ]
    if brief.special_instructions:
        lines.append("special_instructions:")
        lines.extend(f"- {instruction}" for instruction in brief.special_instructions)

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

    lines.append("## Campaign roles")
    lines.append(", ".join(role.value for role in CampaignRole))

    lines.append("## Template")
    lines.append(f"template: {template.id} ({template.name})")
    lines.append(
        "role_sequence: " + ", ".join(role.value for role in template.role_sequence)
    )

    return "\n".join(lines)


def _validate_plan_domain(output: CampaignPlanOutput) -> None:
    """Deterministic domain checks that the Pydantic schema does not cover.

    - no duplicate topics among items;
    - at least 2 distinct roles when the plan has 2 or more items.
    """
    topics = [item.topic for item in output.items]
    if len(topics) != len(set(topics)):
        raise InvariantViolation("campaign plan must not contain duplicate topics")

    roles = {item.role for item in output.items}
    if len(output.items) >= 2 and len(roles) < 2:
        raise InvariantViolation(
            "campaign plan must use at least 2 distinct roles"
        )
