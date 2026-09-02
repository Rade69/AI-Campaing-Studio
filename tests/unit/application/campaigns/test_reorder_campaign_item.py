"""Unit tests for ReorderCampaignItem (A10) with fake ports."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ai_campaign_studio.application.campaigns.reorder_campaign_item import (
    ReorderCampaignItem,
)
from ai_campaign_studio.domain.campaign.entities import CampaignItem, CampaignPlan
from ai_campaign_studio.domain.campaign.enums import (
    CampaignItemStatus,
    CampaignPlanStatus,
)
from ai_campaign_studio.domain.campaign.roles import CampaignRole
from ai_campaign_studio.domain.common.errors import EntityNotFound, InvariantViolation
from ai_campaign_studio.domain.common.ids import (
    CampaignId,
    CampaignItemId,
    CampaignPlanId,
)

_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


class _FakeUnitOfWork:
    def __init__(self) -> None:
        self.committed = False

    def __enter__(self) -> _FakeUnitOfWork:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:  # noqa: ANN001
        return False

    def commit(self) -> None:
        self.committed = True


class _FakeCampaignRepository:
    def __init__(self) -> None:
        self.plans: dict = {}

    def get_plan(self, plan_id):  # noqa: ANN001
        return self.plans.get(plan_id)

    def save_plan(self, plan) -> None:  # noqa: ANN001
        self.plans[plan.id] = plan

    def get_campaign(self, campaign_id):  # noqa: ANN001
        del campaign_id
        return None

    def save_campaign(self, campaign) -> None:  # noqa: ANN001
        del campaign


def _item(item_id: str, order: int) -> CampaignItem:
    return CampaignItem(
        id=CampaignItemId(item_id),
        order=order,
        role=CampaignRole.PROBLEM,
        topic=f"Topic {item_id}",
        goal="Goal",
        status=CampaignItemStatus.PLANNED,
    )


def _plan(items: tuple[CampaignItem, ...]) -> CampaignPlan:
    return CampaignPlan(
        id=CampaignPlanId("plan-1"),
        campaign_id=CampaignId("campaign-1"),
        version=1,
        status=CampaignPlanStatus.DRAFT,
        created_at=_CREATED_AT,
        items=items,
    )


def _make_use_case(repo: _FakeCampaignRepository) -> ReorderCampaignItem:
    return ReorderCampaignItem(repo, _FakeUnitOfWork())


def test_reorder_builds_new_version_with_1_to_n_order() -> None:
    repo = _FakeCampaignRepository()
    repo.plans[CampaignPlanId("plan-1")] = _plan(
        (_item("i1", 1), _item("i2", 2), _item("i3", 3))
    )

    result = _make_use_case(repo).execute(
        CampaignPlanId("plan-1"),
        (CampaignItemId("i3"), CampaignItemId("i1"), CampaignItemId("i2")),
    )

    assert [item.topic for item in result.items] == [
        "Topic i3",
        "Topic i1",
        "Topic i2",
    ]
    assert [item.order for item in result.items] == [1, 2, 3]
    assert result.version == 2
    assert result.status is CampaignPlanStatus.DRAFT

    old = repo.get_plan(CampaignPlanId("plan-1"))
    assert old is not None
    assert old.status is CampaignPlanStatus.SUPERSEDED


def test_missing_item_id_rejected_before_change() -> None:
    repo = _FakeCampaignRepository()
    repo.plans[CampaignPlanId("plan-1")] = _plan((_item("i1", 1), _item("i2", 2)))

    with pytest.raises(InvariantViolation):
        _make_use_case(repo).execute(
            CampaignPlanId("plan-1"), (CampaignItemId("i1"),)
        )

    old = repo.get_plan(CampaignPlanId("plan-1"))
    assert old is not None
    assert old.status is CampaignPlanStatus.DRAFT
    assert len(repo.plans) == 1


def test_unknown_item_id_rejected_before_change() -> None:
    repo = _FakeCampaignRepository()
    repo.plans[CampaignPlanId("plan-1")] = _plan((_item("i1", 1), _item("i2", 2)))

    with pytest.raises(InvariantViolation):
        _make_use_case(repo).execute(
            CampaignPlanId("plan-1"),
            (CampaignItemId("i1"), CampaignItemId("i99")),
        )

    old = repo.get_plan(CampaignPlanId("plan-1"))
    assert old is not None
    assert old.status is CampaignPlanStatus.DRAFT
    assert len(repo.plans) == 1


def test_duplicate_item_id_rejected() -> None:
    repo = _FakeCampaignRepository()
    repo.plans[CampaignPlanId("plan-1")] = _plan((_item("i1", 1), _item("i2", 2)))

    with pytest.raises(InvariantViolation):
        _make_use_case(repo).execute(
            CampaignPlanId("plan-1"),
            (CampaignItemId("i1"), CampaignItemId("i1")),
        )

    assert len(repo.plans) == 1


def test_unknown_plan_raises() -> None:
    repo = _FakeCampaignRepository()

    with pytest.raises(EntityNotFound):
        _make_use_case(repo).execute(CampaignPlanId("missing"), ())
