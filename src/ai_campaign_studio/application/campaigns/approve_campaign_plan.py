"""ApproveCampaignPlan use-case (A10).

Owns approving a DRAFT campaign plan: validate it, mark the plan APPROVED and
advance the owning campaign to PLAN_APPROVED atomically. Does NOT touch posts/
ContentPiece — approving a plan does not auto-approve any post.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from ai_campaign_studio.domain.campaign.entities import CampaignPlan
from ai_campaign_studio.domain.campaign.enums import CampaignPlanStatus, CampaignStatus
from ai_campaign_studio.domain.common.errors import EntityNotFound, InvariantViolation
from ai_campaign_studio.domain.common.ids import CampaignPlanId
from ai_campaign_studio.ports.repositories import CampaignRepositoryPort


class _UnitOfWork(Protocol):
    """Minimal transaction boundary the use-case needs."""

    def __enter__(self) -> _UnitOfWork: ...

    def __exit__(
        self, exc_type: object, exc_value: object, traceback: object
    ) -> bool: ...

    def commit(self) -> None: ...


class ApproveCampaignPlan:
    """Approve a DRAFT plan and advance its campaign to PLAN_APPROVED atomically."""

    def __init__(
        self,
        campaign_repo: CampaignRepositoryPort,
        unit_of_work: _UnitOfWork,
    ) -> None:
        self._campaign_repo = campaign_repo
        self._unit_of_work = unit_of_work

    def execute(self, plan_id: CampaignPlanId) -> CampaignPlan:
        plan = self._campaign_repo.get_plan(plan_id)
        if plan is None:
            raise EntityNotFound(f"campaign plan {plan_id} not found")

        if plan.status is not CampaignPlanStatus.DRAFT:
            raise InvariantViolation(
                f"campaign plan {plan_id} is {plan.status.value}; only DRAFT "
                "plans can be approved"
            )

        _validate_approval(plan)

        approved_plan = replace(plan, status=CampaignPlanStatus.APPROVED)

        campaign = self._campaign_repo.get_campaign(plan.campaign_id)
        if campaign is None:
            raise EntityNotFound(f"campaign {plan.campaign_id} not found")
        updated_campaign = replace(campaign, status=CampaignStatus.PLAN_APPROVED)

        with self._unit_of_work:
            self._campaign_repo.save_plan(approved_plan)
            self._campaign_repo.save_campaign(updated_campaign)
            self._unit_of_work.commit()

        return approved_plan


def _validate_approval(plan: CampaignPlan) -> None:
    """Pre-approval checks (plan section 32)."""
    if len(plan.items) == 0:
        raise InvariantViolation("campaign plan must have at least one item")

    orders = [item.order for item in plan.items]
    if len(orders) != len(set(orders)):
        raise InvariantViolation("campaign plan items must have unique order")

    for item in plan.items:
        if not item.topic or not item.topic.strip():
            raise InvariantViolation("campaign plan item topic must be non-empty")
        if not item.goal or not item.goal.strip():
            raise InvariantViolation("campaign plan item goal must be non-empty")
