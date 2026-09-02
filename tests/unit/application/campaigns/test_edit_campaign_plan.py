"""Unit tests for EditCampaignPlan (A10) with fake ports."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ai_campaign_studio.application.campaigns.edit_campaign_plan import (
    EditCampaignPlan,
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
    role: CampaignRole = CampaignRole.PROBLEM,
) -> CampaignItem:
    return CampaignItem(
        id=CampaignItemId(item_id),
        order=order,
        role=role,
        topic=topic,
        goal="Goal",
        status=CampaignItemStatus.PLANNED,
    )


def _plan(
    plan_id: str = "plan-1",
    version: int = 1,
    status: CampaignPlanStatus = CampaignPlanStatus.DRAFT,
    items: tuple[CampaignItem, ...] = (),
) -> CampaignPlan:
    return CampaignPlan(
        id=CampaignPlanId(plan_id),
        campaign_id=CampaignId("campaign-1"),
        version=version,
        status=status,
        created_at=_CREATED_AT,
        items=items,
    )


def _make_use_case(repo: _FakeCampaignRepository) -> EditCampaignPlan:
    return EditCampaignPlan(repo, _FakeUnitOfWork())


def test_edit_creates_new_draft_and_supersedes_old() -> None:
    old_items = (_item("i1", 1), _item("i2", 2))
    repo = _FakeCampaignRepository()
    repo.plans[CampaignPlanId("plan-1")] = _plan(items=old_items)
    new_items = (_item("i1", 1, topic="Changed"), _item("i2", 2))

    result = _make_use_case(repo).execute(CampaignPlanId("plan-1"), new_items)

    assert result.id != CampaignPlanId("plan-1")
    assert result.version == 2
    assert result.status is CampaignPlanStatus.DRAFT
    # fresh item ids, preserved order/topic
    assert result.items[0].id != CampaignItemId("i1")
    assert result.items[1].id != CampaignItemId("i2")
    assert [item.order for item in result.items] == [1, 2]
    assert [item.topic for item in result.items] == ["Changed", "Topic"]

    old_persisted = repo.get_plan(CampaignPlanId("plan-1"))
    assert old_persisted is not None
    assert old_persisted.status is CampaignPlanStatus.SUPERSEDED
    assert repo.get_plan(result.id) is not None


def test_edit_unknown_plan_raises() -> None:
    repo = _FakeCampaignRepository()

    with pytest.raises(EntityNotFound):
        _make_use_case(repo).execute(CampaignPlanId("missing"), ())


def test_edit_approved_plan_raises() -> None:
    repo = _FakeCampaignRepository()
    repo.plans[CampaignPlanId("plan-1")] = _plan(
        status=CampaignPlanStatus.APPROVED, items=(_item("i1", 1),)
    )

    with pytest.raises(InvariantViolation):
        _make_use_case(repo).execute(CampaignPlanId("plan-1"), (_item("i1", 1),))

    assert len(repo.plans) == 1  # nothing new persisted


def test_edit_superseded_plan_raises() -> None:
    repo = _FakeCampaignRepository()
    repo.plans[CampaignPlanId("plan-1")] = _plan(
        status=CampaignPlanStatus.SUPERSEDED, items=(_item("i1", 1),)
    )

    with pytest.raises(InvariantViolation):
        _make_use_case(repo).execute(CampaignPlanId("plan-1"), (_item("i1", 1),))

    assert len(repo.plans) == 1  # nothing new persisted


def test_duplicate_order_rejected_before_persist() -> None:
    repo = _FakeCampaignRepository()
    repo.plans[CampaignPlanId("plan-1")] = _plan(items=(_item("i1", 1),))

    with pytest.raises(InvariantViolation):
        _make_use_case(repo).execute(
            CampaignPlanId("plan-1"), (_item("i1", 1), _item("i2", 1))
        )

    # old plan untouched (still DRAFT, not superseded)
    old = repo.get_plan(CampaignPlanId("plan-1"))
    assert old is not None
    assert old.status is CampaignPlanStatus.DRAFT
    assert len(repo.plans) == 1


def test_empty_topic_rejected() -> None:
    repo = _FakeCampaignRepository()
    repo.plans[CampaignPlanId("plan-1")] = _plan(items=(_item("i1", 1),))

    with pytest.raises(InvariantViolation):
        _make_use_case(repo).execute(
            CampaignPlanId("plan-1"), (_item("i1", 1, topic="   "),)
        )

    assert len(repo.plans) == 1


def test_add_item() -> None:
    repo = _FakeCampaignRepository()
    repo.plans[CampaignPlanId("plan-1")] = _plan(items=(_item("i1", 1),))

    result = _make_use_case(repo).execute(
        CampaignPlanId("plan-1"), (_item("i1", 1), _item("i2", 2))
    )

    assert len(result.items) == 2
    assert [item.order for item in result.items] == [1, 2]


def test_delete_item() -> None:
    repo = _FakeCampaignRepository()
    repo.plans[CampaignPlanId("plan-1")] = _plan(items=(_item("i1", 1), _item("i2", 2)))

    result = _make_use_case(repo).execute(CampaignPlanId("plan-1"), (_item("i1", 1),))

    assert len(result.items) == 1
    assert [item.order for item in result.items] == [1]


def test_replace_item() -> None:
    repo = _FakeCampaignRepository()
    repo.plans[CampaignPlanId("plan-1")] = _plan(items=(_item("i1", 1), _item("i2", 2)))

    result = _make_use_case(repo).execute(
        CampaignPlanId("plan-1"),
        (_item("i1", 1, topic="Replaced"), _item("i2", 2)),
    )

    assert result.items[0].topic == "Replaced"
    assert result.items[1].topic == "Topic"
