"""ReorderCampaignItem use-case (A10).

Owns reordering a DRAFT plan's items by permutation of existing item ids.
It validates the permutation, rebuilds the item tuple with ``order`` set to
``1..N``, then delegates the versioning/persistence to ``EditCampaignPlan``
(composition, not duplication).
"""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from ai_campaign_studio.application.campaigns.edit_campaign_plan import (
    EditCampaignPlan,
)
from ai_campaign_studio.domain.campaign.entities import CampaignItem, CampaignPlan
from ai_campaign_studio.domain.common.errors import EntityNotFound, InvariantViolation
from ai_campaign_studio.domain.common.ids import CampaignItemId, CampaignPlanId
from ai_campaign_studio.ports.repositories import CampaignRepositoryPort


class _UnitOfWork(Protocol):
    """Minimal transaction boundary the use-case needs."""

    def __enter__(self) -> _UnitOfWork: ...

    def __exit__(
        self, exc_type: object, exc_value: object, traceback: object
    ) -> bool: ...

    def commit(self) -> None: ...


class ReorderCampaignItem:
    """Reorder a DRAFT plan's items by id permutation, delegating to
    ``EditCampaignPlan``.
    """

    def __init__(
        self,
        campaign_repo: CampaignRepositoryPort,
        unit_of_work: _UnitOfWork,
    ) -> None:
        self._campaign_repo = campaign_repo
        self._edit = EditCampaignPlan(campaign_repo, unit_of_work)

    def execute(
        self,
        plan_id: CampaignPlanId,
        ordered_item_ids: tuple[CampaignItemId, ...],
    ) -> CampaignPlan:
        old = self._campaign_repo.get_plan(plan_id)
        if old is None:
            raise EntityNotFound(f"campaign plan {plan_id} not found")

        existing_ids = [item.id for item in old.items]
        if set(ordered_item_ids) != set(existing_ids) or len(ordered_item_ids) != len(
            existing_ids
        ):
            raise InvariantViolation(
                "ordered_item_ids must be a permutation of the plan's existing item ids"
            )

        by_id = {item.id: item for item in old.items}
        reordered: list[CampaignItem] = []
        for order, item_id in enumerate(ordered_item_ids, start=1):
            reordered.append(replace(by_id[item_id], order=order))

        return self._edit.execute(plan_id, tuple(reordered))
