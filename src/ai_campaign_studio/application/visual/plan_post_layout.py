"""PlanPostLayout use-case (A13 dio 2b, plan section 40-41).

Owns generating and persisting a per-post ``LayoutSpec`` for one already-
generated content piece, constrained to the campaign's decided visual system.
Rejects a primitive outside the campaign's allowed set (InvariantViolation,
nothing persisted), but a headline that does not fit is persisted with
``validation_status="INVALID"`` (not fatal). ``format`` is always the Slice-1
constant, never the AI-returned value.
"""

from __future__ import annotations

from dataclasses import replace
from enum import StrEnum
from typing import Protocol

from ai_campaign_studio.application.schemas.visual_direction_output import (
    LayoutSpecCandidate,
)
from ai_campaign_studio.application.visual.validate_layout import validate_layout
from ai_campaign_studio.domain.campaign.entities import CampaignItem
from ai_campaign_studio.domain.common.errors import EntityNotFound, InvariantViolation
from ai_campaign_studio.domain.common.ids import (
    CampaignPlanId,
    LayoutSpecId,
    PostId,
    VisualSystemId,
    new_id,
)
from ai_campaign_studio.domain.content.entities import SocialPostPayload
from ai_campaign_studio.domain.visual.entities import CampaignVisualSystem
from ai_campaign_studio.domain.visual.enums import (
    Alignment,
    CtaStyle,
    HeadlinePosition,
    HeadlineScale,
    ImagePosition,
    LayoutPrimitive,
    LogoPosition,
    Overlay,
)
from ai_campaign_studio.domain.visual.layout import LayoutSpec
from ai_campaign_studio.ports.ai import AIRequest, TextGenerationPort
from ai_campaign_studio.ports.prompts import PromptRepositoryPort
from ai_campaign_studio.ports.repositories import (
    CampaignRepositoryPort,
    ContentRepositoryPort,
    VisualRepositoryPort,
)

_PROMPT_NAME = "post_layout"
_PROMPT_VERSION = "1"
_SLICE1_FORMAT = "1080x1350"


class _UnitOfWork(Protocol):
    """Minimal transaction boundary the use-case needs."""

    def __enter__(self) -> _UnitOfWork: ...

    def __exit__(
        self, exc_type: object, exc_value: object, traceback: object
    ) -> bool: ...

    def commit(self) -> None: ...


class PlanPostLayout:
    """Generate and persist a per-post layout spec."""

    def __init__(
        self,
        campaign_repo: CampaignRepositoryPort,
        content_repo: ContentRepositoryPort,
        visual_repo: VisualRepositoryPort,
        prompt_repo: PromptRepositoryPort,
        ai_port: TextGenerationPort,
        unit_of_work: _UnitOfWork,
    ) -> None:
        self._campaign_repo = campaign_repo
        self._content_repo = content_repo
        self._visual_repo = visual_repo
        self._prompt_repo = prompt_repo
        self._ai_port = ai_port
        self._unit_of_work = unit_of_work

    def execute(
        self,
        content_piece_id: PostId,
        visual_system_id: VisualSystemId,
        plan_id: CampaignPlanId,
    ) -> LayoutSpec:
        piece = self._content_repo.get_content_piece(content_piece_id)
        if piece is None:
            raise EntityNotFound(f"content piece {content_piece_id} not found")
        if piece.payload is None:
            raise InvariantViolation(
                f"content piece {content_piece_id} has no payload to lay out"
            )

        visual_system = self._visual_repo.get_visual_system(visual_system_id)
        if visual_system is None:
            raise EntityNotFound(f"visual system {visual_system_id} not found")

        plan = self._campaign_repo.get_plan(plan_id)
        if plan is None:
            raise EntityNotFound(f"campaign plan {plan_id} not found")
        item = next(
            (i for i in plan.items if i.id == piece.campaign_item_id), None
        )
        if item is None:
            raise EntityNotFound(
                f"campaign item {piece.campaign_item_id} not found in plan {plan_id}"
            )

        allowed_primitives = {visual_system.primary_layout_family}
        if visual_system.secondary_layout_family is not None:
            allowed_primitives.add(visual_system.secondary_layout_family)

        prompt = self._prompt_repo.get(_PROMPT_NAME, _PROMPT_VERSION)
        request = AIRequest(
            purpose=_PROMPT_NAME,
            prompt_name=_PROMPT_NAME,
            prompt_version=_PROMPT_VERSION,
            system_text=prompt.instructions,
            user_text=_build_user_text(
                visual_system, item, piece.payload, allowed_primitives
            ),
            json_schema=LayoutSpecCandidate.model_json_schema(),
        )

        response = self._ai_port.generate(request)
        if response.structured_payload is None:
            raise InvariantViolation("AI response has no structured_payload")

        candidate = LayoutSpecCandidate.model_validate(response.structured_payload)

        if candidate.primitive not in allowed_primitives:
            raise InvariantViolation(
                f"layout primitive {candidate.primitive.value} is not allowed "
                "for this campaign"
            )

        draft = LayoutSpec(
            primitive=candidate.primitive,
            image_position=candidate.image_position,
            headline_position=candidate.headline_position,
            headline_scale=candidate.headline_scale,
            overlay=candidate.overlay,
            logo_position=candidate.logo_position,
            cta_style=candidate.cta_style,
            alignment=candidate.alignment,
            format=_SLICE1_FORMAT,
        )
        is_valid, _reasons = validate_layout(draft, piece.payload.headline)

        layout = replace(
            draft,
            id=LayoutSpecId(new_id()),
            content_piece_id=content_piece_id,
            validation_status="VALID" if is_valid else "INVALID",
        )

        with self._unit_of_work:
            self._visual_repo.save_layout_spec(layout)
            self._unit_of_work.commit()

        return layout


def _build_user_text(
    visual_system: CampaignVisualSystem,
    item: CampaignItem,
    payload: SocialPostPayload,
    allowed_primitives: set[LayoutPrimitive],
) -> str:
    lines = [
        "## Campaign visual system (already decided)",
        f"primary_layout_family: {visual_system.primary_layout_family.value}",
        "secondary_layout_family: "
        + (
            visual_system.secondary_layout_family.value
            if visual_system.secondary_layout_family
            else "NONE"
        ),
        f"headline_scale: {visual_system.headline_scale.value}",
        f"image_treatment: {visual_system.image_treatment}",
        f"logo_rule: {visual_system.logo_rule}",
        f"cta_rule: {visual_system.cta_rule}",
        f"alignment: {visual_system.alignment.value}",
        "style: " + ", ".join(visual_system.style),
        "## Post context",
        f"role: {item.role.value}",
        f"topic: {item.topic}",
        "## Actual post text (fit target, do not rewrite)",
        f"headline: {payload.headline}",
        f"cta: {payload.cta}",
        "## Allowed primitives for THIS campaign",
        ", ".join(sorted(p.value for p in allowed_primitives)),
        "## Allowed enum values (use exactly these, do not invent)",
        "image positions: " + _enum_values(ImagePosition),
        "headline positions: " + _enum_values(HeadlinePosition),
        "headline scales: " + _enum_values(HeadlineScale),
        "overlays: " + _enum_values(Overlay),
        "logo positions: " + _enum_values(LogoPosition),
        "cta styles: " + _enum_values(CtaStyle),
        "alignments: " + _enum_values(Alignment),
    ]
    return "\n".join(lines)


def _enum_values(enum_cls: type[StrEnum]) -> str:
    return ", ".join(member.value for member in enum_cls)
