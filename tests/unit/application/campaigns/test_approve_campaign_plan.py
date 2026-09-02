"""Unit tests for ApproveCampaignPlan (A10) with fake ports."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ai_campaign_studio.application.campaigns.approve_campaign_plan import (
    ApproveCampaignPlan,
)
from ai_campaign_studio.domain.campaign.entities import (
    Campaign,
    CampaignItem,
    CampaignPlan,
)
from ai_campaign_studio.domain.campaign.enums import (
    CampaignItemStatus,
    CampaignPlanStatus,
    CampaignStatus,
)
from ai_campaign_studio.domain.campaign.roles import CampaignRole
from ai_campaign_studio.domain.common.errors import EntityNotFound, InvariantViolation
from ai_campaign_studio.domain.common.ids import (
    BrandId,
    BrandSnapshotId,
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
        self.campaigns: dict = {}

    def get_plan(self, plan_id):  # noqa: ANN001
        return self.plans.get(plan_id)

    def save_plan(self, plan) -> None:  # noqa: ANN001
        self.plans[plan.id] = plan

    def get_campaign(self, campaign_id):  # noqa: ANN001
        return self.campaigns.get(campaign_id)

    def save_campaign(self, campaign) -> None:  # noqa: ANN001
        self.campaigns[campaign.id] = campaign


def _item(
    item_id: str,
    order: int,
    topic: str = "Topic",
    goal: str = "Goal",
) -> CampaignItem:
    return CampaignItem(
        id=CampaignItemId(item_id),
        order=order,
        role=CampaignRole.PROBLEM,
        topic=topic,
        goal=goal,
        status=CampaignItemStatus.PLANNED,
    )


def _plan(
    plan_id: str = "plan-1",
    status: CampaignPlanStatus = CampaignPlanStatus.DRAFT,
    items: tuple[CampaignItem, ...] = (),
) -> CampaignPlan:
    return CampaignPlan(
        id=CampaignPlanId(plan_id),
        campaign_id=CampaignId("campaign-1"),
        version=1,
        status=status,
        created_at=_CREATED_AT,
        items=items,
    )


def _campaign(status: CampaignStatus = CampaignStatus.PLAN_GENERATED) -> Campaign:
    return Campaign(
        id=CampaignId("campaign-1"),
        brand_id=BrandId("brand-1"),
        brand_snapshot_id=BrandSnapshotId("snap-1"),
        brief_id="brief-1",
        status=status,
        created_at=_CREATED_AT,
    )


def _make_use_case(repo: _FakeCampaignRepository) -> ApproveCampaignPlan:
    return ApproveCampaignPlan(repo, _FakeUnitOfWork())


def test_approve_marks_plan_and_campaign() -> None:
    repo = _FakeCampaignRepository()
    repo.plans[CampaignPlanId("plan-1")] = _plan(items=(_item("i1", 1),))
    repo.campaigns[CampaignId("campaign-1")] = _campaign()

    result = _make_use_case(repo).execute(CampaignPlanId("plan-1"))

    assert result.status is CampaignPlanStatus.APPROVED
    persisted_plan = repo.get_plan(CampaignPlanId("plan-1"))
    assert persisted_plan is not None
    assert persisted_plan.status is CampaignPlanStatus.APPROVED

    persisted_campaign = repo.get_campaign(CampaignId("campaign-1"))
    assert persisted_campaign is not None
    assert persisted_campaign.status is CampaignStatus.PLAN_APPROVED


def test_approve_unknown_plan_raises() -> None:
    repo = _FakeCampaignRepository()

    with pytest.raises(EntityNotFound):
        _make_use_case(repo).execute(CampaignPlanId("missing"))


def test_approve_approved_plan_raises() -> None:
    repo = _FakeCampaignRepository()
    repo.plans[CampaignPlanId("plan-1")] = _plan(
        status=CampaignPlanStatus.APPROVED, items=(_item("i1", 1),)
    )
    repo.campaigns[CampaignId("campaign-1")] = _campaign()

    with pytest.raises(InvariantViolation):
        _make_use_case(repo).execute(CampaignPlanId("plan-1"))

    assert (
        repo.get_campaign(CampaignId("campaign-1")).status
        is CampaignStatus.PLAN_GENERATED
    )


def test_approve_superseded_plan_raises() -> None:
    repo = _FakeCampaignRepository()
    repo.plans[CampaignPlanId("plan-1")] = _plan(
        status=CampaignPlanStatus.SUPERSEDED, items=(_item("i1", 1),)
    )
    repo.campaigns[CampaignId("campaign-1")] = _campaign()

    with pytest.raises(InvariantViolation):
        _make_use_case(repo).execute(CampaignPlanId("plan-1"))


def test_approve_empty_plan_rejected() -> None:
    repo = _FakeCampaignRepository()
    repo.plans[CampaignPlanId("plan-1")] = _plan(items=())
    repo.campaigns[CampaignId("campaign-1")] = _campaign()

    with pytest.raises(InvariantViolation):
        _make_use_case(repo).execute(CampaignPlanId("plan-1"))

    assert (
        repo.get_campaign(CampaignId("campaign-1")).status
        is CampaignStatus.PLAN_GENERATED
    )


def test_approve_duplicate_order_rejected() -> None:
    repo = _FakeCampaignRepository()
    repo.plans[CampaignPlanId("plan-1")] = _plan(
        items=(_item("i1", 1), _item("i2", 1))
    )
    repo.campaigns[CampaignId("campaign-1")] = _campaign()

    with pytest.raises(InvariantViolation):
        _make_use_case(repo).execute(CampaignPlanId("plan-1"))


def test_approve_empty_topic_rejected() -> None:
    repo = _FakeCampaignRepository()
    repo.plans[CampaignPlanId("plan-1")] = _plan(items=(_item("i1", 1, topic="   "),))
    repo.campaigns[CampaignId("campaign-1")] = _campaign()

    with pytest.raises(InvariantViolation):
        _make_use_case(repo).execute(CampaignPlanId("plan-1"))


def test_approve_empty_goal_rejected() -> None:
    repo = _FakeCampaignRepository()
    repo.plans[CampaignPlanId("plan-1")] = _plan(items=(_item("i1", 1, goal=""),))
    repo.campaigns[CampaignId("campaign-1")] = _campaign()

    with pytest.raises(InvariantViolation):
        _make_use_case(repo).execute(CampaignPlanId("plan-1"))


def test_approve_missing_campaign_raises() -> None:
    repo = _FakeCampaignRepository()
    repo.plans[CampaignPlanId("plan-1")] = _plan(items=(_item("i1", 1),))

    with pytest.raises(EntityNotFound):
        _make_use_case(repo).execute(CampaignPlanId("plan-1"))
