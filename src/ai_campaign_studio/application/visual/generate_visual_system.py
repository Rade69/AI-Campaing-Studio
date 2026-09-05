"""GenerateVisualSystem use-case (A13, plan section 39).

Owns turning an APPROVED campaign plan into a ``CampaignVisualSystem``
(persisted) plus an in-memory ``LayoutSpec`` (NOT persisted — the
``layout_specs`` table does not exist yet; per-post layout is A13 part 2),
via one AI call over ``resources/prompts/visual_direction/v1.yaml``. Depends
only on existing ports; does NOT own the visual-direction boundary schema,
the prompt YAML, or any per-post layout/validation logic.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from ai_campaign_studio.application.schemas.visual_direction_output import (
    VisualDirectionOutput,
)
from ai_campaign_studio.domain.brand.entities import BrandSnapshot
from ai_campaign_studio.domain.campaign.entities import CampaignBrief, CampaignPlan
from ai_campaign_studio.domain.campaign.enums import CampaignPlanStatus
from ai_campaign_studio.domain.common.errors import EntityNotFound, InvariantViolation
from ai_campaign_studio.domain.common.ids import CampaignPlanId, VisualSystemId, new_id
from ai_campaign_studio.domain.common.timestamps import utc_now
from ai_campaign_studio.domain.visual.entities import CampaignVisualSystem
from ai_campaign_studio.domain.visual.enums import (
    Alignment,
    CtaRule,
    CtaStyle,
    HeadlinePosition,
    HeadlineScale,
    ImagePosition,
    ImageTreatment,
    LayoutPrimitive,
    LogoPosition,
    LogoRule,
    Overlay,
)
from ai_campaign_studio.domain.visual.layout import LayoutSpec
from ai_campaign_studio.ports.ai import AIRequest, TextGenerationPort
from ai_campaign_studio.ports.prompts import PromptRepositoryPort
from ai_campaign_studio.ports.repositories import (
    BrandRepositoryPort,
    CampaignRepositoryPort,
    VisualRepositoryPort,
)

_PROMPT_NAME = "visual_direction"
_PROMPT_VERSION = "1"

# Plan section 39 example vocabulary, case-sensitive. The boundary schema
# types ``style`` as ``list[str]`` (not an enum), so membership is enforced
# at code level by ``_validate_visual_domain``.
_ALLOWED_STYLES = (
    "clean",
    "clinical",
    "calm",
    "warm",
    "bold",
    "minimal",
    "editorial",
)


class _UnitOfWork(Protocol):
    """Minimal transaction boundary the use-case needs."""

    def __enter__(self) -> _UnitOfWork: ...

    def __exit__(
        self, exc_type: object, exc_value: object, traceback: object
    ) -> bool: ...

    def commit(self) -> None: ...


class GenerateVisualSystem:
    """Generate and persist a campaign visual system (plus an in-memory layout)."""

    def __init__(
        self,
        campaign_repo: CampaignRepositoryPort,
        brand_repo: BrandRepositoryPort,
        visual_repo: VisualRepositoryPort,
        prompt_repo: PromptRepositoryPort,
        ai_port: TextGenerationPort,
        unit_of_work: _UnitOfWork,
    ) -> None:
        self._campaign_repo = campaign_repo
        self._brand_repo = brand_repo
        self._visual_repo = visual_repo
        self._prompt_repo = prompt_repo
        self._ai_port = ai_port
        self._unit_of_work = unit_of_work

    def execute(
        self, plan_id: CampaignPlanId
    ) -> tuple[CampaignVisualSystem, LayoutSpec]:
        plan = self._campaign_repo.get_plan(plan_id)
        if plan is None:
            raise EntityNotFound(f"campaign plan {plan_id} not found")

        if plan.status is not CampaignPlanStatus.APPROVED:
            raise InvariantViolation(
                f"campaign plan {plan_id} is {plan.status.value}; only an "
                "APPROVED plan can be used to generate a visual system"
            )

        campaign = self._campaign_repo.get_campaign(plan.campaign_id)
        if campaign is None:
            raise EntityNotFound(f"campaign {plan.campaign_id} not found")

        brief = self._campaign_repo.get_brief(campaign.brief_id)
        if brief is None:
            raise EntityNotFound(f"campaign brief {campaign.brief_id} not found")

        snapshot = self._brand_repo.get_snapshot(campaign.brand_snapshot_id)
        if snapshot is None:
            raise EntityNotFound(
                f"brand snapshot {campaign.brand_snapshot_id} not found"
            )

        prompt = self._prompt_repo.get(_PROMPT_NAME, _PROMPT_VERSION)
        request = AIRequest(
            purpose=_PROMPT_NAME,
            prompt_name=_PROMPT_NAME,
            prompt_version=_PROMPT_VERSION,
            system_text=prompt.instructions,
            user_text=_build_user_text(brief, snapshot, plan),
            json_schema=VisualDirectionOutput.model_json_schema(),
        )

        response = self._ai_port.generate(request)
        if response.structured_payload is None:
            raise InvariantViolation("AI response has no structured_payload")

        output = VisualDirectionOutput.model_validate(response.structured_payload)
        _validate_visual_domain(output)

        system_candidate = output.campaign_visual_system
        visual_system = CampaignVisualSystem(
            id=VisualSystemId(new_id()),
            campaign_id=campaign.id,
            primary_layout_family=system_candidate.primary_layout_family,
            secondary_layout_family=system_candidate.secondary_layout_family,
            headline_scale=system_candidate.headline_scale,
            image_treatment=system_candidate.image_treatment.value,
            logo_rule=system_candidate.logo_rule.value,
            cta_rule=system_candidate.cta_rule.value,
            alignment=system_candidate.alignment,
            created_at=utc_now(),
            style=tuple(system_candidate.style),
        )

        layout_candidate = output.layout_spec
        layout_spec = LayoutSpec(
            primitive=layout_candidate.primitive,
            image_position=layout_candidate.image_position,
            headline_position=layout_candidate.headline_position,
            headline_scale=layout_candidate.headline_scale,
            overlay=layout_candidate.overlay,
            logo_position=layout_candidate.logo_position,
            cta_style=layout_candidate.cta_style,
            alignment=layout_candidate.alignment,
            format=layout_candidate.format,
        )

        with self._unit_of_work:
            self._visual_repo.save_visual_system(visual_system)
            self._unit_of_work.commit()

        return visual_system, layout_spec


def _build_user_text(
    brief: CampaignBrief, snapshot: BrandSnapshot, plan: CampaignPlan
) -> str:
    """Assemble the user-side prompt context for a visual direction.

    The prompt's ``instructions`` live in ``system_text``; this payload
    carries the concrete data plus the CLOSED vocabularies for every enum
    field (the prompt YAML says "do not invent values" but does not enumerate
    them, so the enumeration must happen here).
    """
    lines = [
        "## Campaign brief",
        f"offer: {brief.offer}",
        f"goal: {brief.goal}",
        f"content_language_context: {brief.content_language_context}",
    ]

    lines.append("## Brand snapshot")
    lines.append(f"voice.formality: {snapshot.voice.formality}")
    lines.append(
        "voice.preferred_terms: " + ", ".join(snapshot.voice.preferred_terms)
    )
    lines.append(
        "voice.forbidden_terms: " + ", ".join(snapshot.voice.forbidden_terms)
    )

    lines.append("## Plan items (context for STYLE, not content to reproduce)")
    for item in plan.items:
        lines.append(f"- role: {item.role.value}; topic: {item.topic}")

    lines.append("## Allowed enum values (use exactly these, do not invent)")
    lines.append("layout primitives: " + _enum_values(LayoutPrimitive))
    lines.append("headline scales: " + _enum_values(HeadlineScale))
    lines.append("alignments: " + _enum_values(Alignment))
    lines.append("image positions: " + _enum_values(ImagePosition))
    lines.append("headline positions: " + _enum_values(HeadlinePosition))
    lines.append("overlays: " + _enum_values(Overlay))
    lines.append("logo positions: " + _enum_values(LogoPosition))
    lines.append("cta styles: " + _enum_values(CtaStyle))
    lines.append("image treatments: " + _enum_values(ImageTreatment))
    lines.append("logo rules: " + _enum_values(LogoRule))
    lines.append("cta rules: " + _enum_values(CtaRule))
    lines.append("allowed styles: " + ", ".join(_ALLOWED_STYLES))

    return "\n".join(lines)


def _validate_visual_domain(output: VisualDirectionOutput) -> None:
    """Deterministic domain checks the Pydantic schema does not cover.

    ``style`` is typed as ``list[str]`` (not an enum) in the boundary schema,
    so membership in the allowed vocabulary is enforced here, CASE-SENSITIVELY
    (the plan's example values are lowercase; normalizing would silently
    accept "BOLD" which the prompt vocabulary does not list).
    """
    style_values = output.campaign_visual_system.style
    unknown = sorted({s for s in style_values if s not in _ALLOWED_STYLES})
    if unknown:
        raise InvariantViolation(
            "visual system style contains unrecognized values: "
            + ", ".join(unknown)
        )


def _enum_values(enum_cls: type[StrEnum]) -> str:
    """Comma-join the string values of one enum, for the prompt vocabulary."""
    return ", ".join(member.value for member in enum_cls)
