"""System B wrapper (A16, §47).

Owns orchestrating the REAL, existing campaign pipeline in order — nothing is
reimplemented here. It persists to the database exactly like the GUI bridge
does, because System B IS the real pipeline. Includes the ``ApproveCampaignPlan``
step that the bridge does not yet call, since ``GenerateSocialPost`` requires an
APPROVED plan.
"""

from __future__ import annotations

from typing import Protocol

from ai_campaign_studio.application.campaigns.approve_campaign_plan import (
    ApproveCampaignPlan,
)
from ai_campaign_studio.application.campaigns.create_campaign import CreateCampaign
from ai_campaign_studio.application.campaigns.generate_campaign_plan import (
    GenerateCampaignPlan,
)
from ai_campaign_studio.application.evaluation.evaluation_post import EvaluationPost
from ai_campaign_studio.application.posts.generate_social_post import (
    GenerateSocialPost,
)
from ai_campaign_studio.domain.campaign.entities import CampaignItem
from ai_campaign_studio.domain.common.ids import BrandId, BrandSnapshotId
from ai_campaign_studio.domain.content.entities import CampaignTarget, ContentPiece
from ai_campaign_studio.ports.ai import TextGenerationPort
from ai_campaign_studio.ports.prompts import PromptRepositoryPort
from ai_campaign_studio.ports.repositories import (
    BrandRepositoryPort,
    CampaignRepositoryPort,
    ContentRepositoryPort,
    FactRepositoryPort,
    RevisionRepositoryPort,
)


class _UnitOfWork(Protocol):
    def __enter__(self) -> _UnitOfWork: ...

    def __exit__(
        self, exc_type: object, exc_value: object, traceback: object
    ) -> bool: ...

    def commit(self) -> None: ...


def run_system_b(
    brand_id: BrandId,
    brand_snapshot_id: BrandSnapshotId,
    raw_brief: dict,
    campaign_repo: CampaignRepositoryPort,
    brand_repo: BrandRepositoryPort,
    fact_repo: FactRepositoryPort,
    content_repo: ContentRepositoryPort,
    revision_repo: RevisionRepositoryPort,
    prompt_repo: PromptRepositoryPort,
    ai_port: TextGenerationPort,
    unit_of_work: _UnitOfWork,
) -> tuple[EvaluationPost, ...]:
    campaign = CreateCampaign(campaign_repo, unit_of_work).execute(
        brand_id, brand_snapshot_id, raw_brief
    )

    plan = GenerateCampaignPlan(
        campaign_repo, brand_repo, prompt_repo, ai_port, unit_of_work
    ).execute(campaign.id)

    approved = ApproveCampaignPlan(campaign_repo, unit_of_work).execute(plan.id)

    targets = _targets_from_brief(raw_brief)
    generator = GenerateSocialPost(
        campaign_repo,
        brand_repo,
        fact_repo,
        content_repo,
        revision_repo,
        prompt_repo,
        ai_port,
        unit_of_work,
    )

    posts: list[EvaluationPost] = []
    for index, item in enumerate(approved.items):
        target = targets[index % len(targets)] if targets else None
        if target is None:
            continue
        piece = generator.execute(campaign.id, approved.id, item.id, target)
        posts.append(_piece_to_evaluation_post(piece, item, target))
    return tuple(posts)


def _targets_from_brief(raw_brief: dict) -> list[CampaignTarget]:
    return [
        CampaignTarget(
            channel=t["channel"],
            platform_code=t["platform_code"],
            format_code=t["format_code"],
        )
        for t in raw_brief.get("targets", [])
    ]


def _piece_to_evaluation_post(
    piece: ContentPiece, item: CampaignItem, target: CampaignTarget
) -> EvaluationPost:
    payload = piece.payload
    return EvaluationPost(
        role=item.role.value,
        topic=item.topic,
        headline=payload.headline if payload else "",
        caption=payload.caption if payload else "",
        hook=payload.hook if payload else "",
        body=payload.body if payload else "",
        cta=payload.cta if payload else "",
        hashtags=payload.hashtags if payload else (),
        platform_code=target.platform_code,
        format_code=target.format_code,
        claims=piece.claims,
    )
