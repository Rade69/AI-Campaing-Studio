"""EditCampaignPlan use-case (A10).

Owns manual plan editing via full-list replacement: the caller sends the
entire new item list, and this use-case supersedes the old DRAFT plan with a
new DRAFT plan (version + 1) atomically. Does NOT own post generation,
CampaignRole logic, or a per-change command API (deliberately simple).
"""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from ai_campaign_studio.domain.campaign.entities import CampaignItem, CampaignPlan
from ai_campaign_studio.domain.campaign.enums import CampaignPlanStatus
from ai_campaign_studio.domain.common.errors import EntityNotFound, InvariantViolation
from ai_campaign_studio.domain.common.ids import CampaignItemId, CampaignPlanId, new_id
from ai_campaign_studio.domain.common.timestamps import utc_now
from ai_campaign_studio.ports.repositories import CampaignRepositoryPort


class _UnitOfWork(Protocol):
    """Minimal transaction boundary the use-case needs."""

    def __enter__(self) -> _UnitOfWork: ...

    def __exit__(
        self, exc_type: object, exc_value: object, traceback: object
    ) -> bool: ...

    def commit(self) -> None: ...


class EditCampaignPlan:
    """Replace a DRAFT plan's items with a new item list, versioning atomically.

    The caller supplies the complete new item list (each ``CampaignItem``
    carries its order/role/topic/goal). This use-case assigns a fresh id to
    every item (a new plan version owns new item entities) and does not
    renumber ``order`` — the caller numbers items explicitly; "add/delete/
    replace" are just caller-side list edits. Domain checks (unique order,
    non-empty topic) run before any persistence.
    """

    def __init__(
        self,
        campaign_repo: CampaignRepositoryPort,
        unit_of_work: _UnitOfWork,
    ) -> None:
        self._campaign_repo = campaign_repo
        self._unit_of_work = unit_of_work

    def execute(
        self,
        plan_id: CampaignPlanId,
        updated_items: tuple[CampaignItem, ...],
    ) -> CampaignPlan:
        old = self._campaign_repo.get_plan(plan_id)
        if old is None:
            raise EntityNotFound(f"campaign plan {plan_id} not found")

        if old.status is not CampaignPlanStatus.DRAFT:
            raise InvariantViolation(
                f"campaign plan {plan_id} is {old.status.value}; only DRAFT "
                "plans can be edited"
            )

        _validate_items(updated_items)

        # A new plan version owns new item entities: assign a fresh id to each
        # item so the globally-unique ``campaign_items.id`` is not violated by
        # the superseded plan still holding the old ids.
        new_items = tuple(
            replace(item, id=CampaignItemId(new_id())) for item in updated_items
        )

        new_plan = CampaignPlan(
            id=CampaignPlanId(new_id()),
            campaign_id=old.campaign_id,
            version=old.version + 1,
            status=CampaignPlanStatus.DRAFT,
            created_at=utc_now(),
            items=new_items,
        )
        superseded = replace(old, status=CampaignPlanStatus.SUPERSEDED)

        with self._unit_of_work:
            self._campaign_repo.save_plan(superseded)
            self._campaign_repo.save_plan(new_plan)
            self._unit_of_work.commit()

        return new_plan


def _validate_items(items: tuple[CampaignItem, ...]) -> None:
    """Domain checks on the new item list (same pattern as generate_campaign_plan)."""
    orders = [item.order for item in items]
    if len(orders) != len(set(orders)):
        raise InvariantViolation("campaign plan items must have unique order")

    for item in items:
        if not item.topic or not item.topic.strip():
            raise InvariantViolation("campaign plan item topic must be non-empty")
