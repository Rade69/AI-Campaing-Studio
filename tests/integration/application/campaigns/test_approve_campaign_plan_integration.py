"""Integration tests for ApproveCampaignPlan (A10) on a real SQLite DB."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from ai_campaign_studio.application.campaigns.approve_campaign_plan import (
    ApproveCampaignPlan,
)
from ai_campaign_studio.domain.campaign.entities import (
    Campaign,
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
from ai_campaign_studio.domain.common.ids import (
    BrandId,
    BrandSnapshotId,
    CampaignId,
    CampaignItemId,
    CampaignPlanId,
)
from ai_campaign_studio.domain.content.entities import CampaignTarget
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories import (
    SqliteCampaignRepository,
)
from ai_campaign_studio.infrastructure.database.unit_of_work import SqliteUnitOfWork

_MIGRATIONS_DIR = Path(__file__).resolve().parents[4] / "resources" / "migrations"
_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def _setup_db(tmp_path: Path):
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)
    return connection


def _item(item_id: str, order: int) -> CampaignItem:
    return CampaignItem(
        id=CampaignItemId(item_id),
        order=order,
        role=CampaignRole.PROBLEM,
        topic=f"Topic {item_id}",
        goal="Goal",
        status=CampaignItemStatus.PLANNED,
    )


def _brief() -> CampaignBrief:
    return CampaignBrief(
        id="brief-1",
        offer="Implants",
        goal="Book consultations",
        audience_text="Adults",
        targets=(
            CampaignTarget(
                channel="SOCIAL", platform_code="INSTAGRAM", format_code="FEED_POST"
            ),
        ),
        content_piece_count=2,
        content_language_context="BHS_LATIN",
        created_at=_CREATED_AT,
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


def _plan(items: tuple[CampaignItem, ...]) -> CampaignPlan:
    return CampaignPlan(
        id=CampaignPlanId("plan-1"),
        campaign_id=CampaignId("campaign-1"),
        version=1,
        status=CampaignPlanStatus.DRAFT,
        created_at=_CREATED_AT,
        items=items,
    )


class _FailingSaveCampaignRepository:
    """save_plan succeeds, save_campaign raises (mid-persist failure)."""

    def __init__(self, inner: SqliteCampaignRepository) -> None:
        self._inner = inner

    def save_plan(self, plan) -> None:  # noqa: ANN001
        self._inner.save_plan(plan)

    def save_campaign(self, campaign) -> None:  # noqa: ANN001
        raise RuntimeError("simulated mid-persist failure")

    def get_plan(self, plan_id):  # noqa: ANN001
        return self._inner.get_plan(plan_id)

    def get_campaign(self, campaign_id):  # noqa: ANN001
        return self._inner.get_campaign(campaign_id)


def test_approve_marks_plan_and_campaign_on_real_db(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteCampaignRepository(connection)
    uow = SqliteUnitOfWork(connection)

    repo.save_brief(_brief())
    repo.save_campaign(_campaign())
    repo.save_plan(_plan((_item("i1", 1), _item("i2", 2))))

    result = ApproveCampaignPlan(repo, uow).execute(CampaignPlanId("plan-1"))

    assert result.status is CampaignPlanStatus.APPROVED
    assert repo.get_plan(CampaignPlanId("plan-1")).status is CampaignPlanStatus.APPROVED
    assert (
        repo.get_campaign(CampaignId("campaign-1")).status
        is CampaignStatus.PLAN_APPROVED
    )
    connection.close()


def test_approve_is_atomic_on_mid_failure(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    inner = SqliteCampaignRepository(connection)
    uow = SqliteUnitOfWork(connection)

    inner.save_brief(_brief())
    inner.save_campaign(_campaign())
    inner.save_plan(_plan((_item("i1", 1), _item("i2", 2))))

    failing_repo = _FailingSaveCampaignRepository(inner)

    with pytest.raises(RuntimeError):
        ApproveCampaignPlan(failing_repo, uow).execute(CampaignPlanId("plan-1"))

    # Plan stayed DRAFT and campaign stayed PLAN_GENERATED (rolled back).
    assert inner.get_plan(CampaignPlanId("plan-1")).status is CampaignPlanStatus.DRAFT
    assert (
        inner.get_campaign(CampaignId("campaign-1")).status
        is CampaignStatus.PLAN_GENERATED
    )
    connection.close()
