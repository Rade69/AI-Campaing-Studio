"""Integration tests for EditCampaignPlan (A10) on a real SQLite DB."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from ai_campaign_studio.application.campaigns.edit_campaign_plan import (
    EditCampaignPlan,
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


def _item(item_id: str, order: int, topic: str = "Topic") -> CampaignItem:
    return CampaignItem(
        id=CampaignItemId(item_id),
        order=order,
        role=CampaignRole.PROBLEM,
        topic=topic,
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


def _campaign() -> Campaign:
    return Campaign(
        id=CampaignId("campaign-1"),
        brand_id=BrandId("brand-1"),
        brand_snapshot_id=BrandSnapshotId("snap-1"),
        brief_id="brief-1",
        status=CampaignStatus.PLAN_GENERATED,
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


class _FailingSecondSavePlanRepository:
    """First save_plan succeeds, second save_plan raises (mid-persist failure)."""

    def __init__(self, inner: SqliteCampaignRepository) -> None:
        self._inner = inner
        self._save_plan_calls = 0

    def save_plan(self, plan) -> None:  # noqa: ANN001
        self._save_plan_calls += 1
        if self._save_plan_calls == 2:
            raise RuntimeError("simulated mid-persist failure")
        self._inner.save_plan(plan)

    def get_plan(self, plan_id):  # noqa: ANN001
        return self._inner.get_plan(plan_id)

    def get_campaign(self, campaign_id):  # noqa: ANN001
        return self._inner.get_campaign(campaign_id)

    def save_campaign(self, campaign) -> None:  # noqa: ANN001
        self._inner.save_campaign(campaign)


def test_edit_versions_plan_on_real_db(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteCampaignRepository(connection)
    uow = SqliteUnitOfWork(connection)

    repo.save_brief(_brief())
    repo.save_campaign(_campaign())
    repo.save_plan(_plan((_item("i1", 1), _item("i2", 2))))

    use_case = EditCampaignPlan(repo, uow)
    result = use_case.execute(
        CampaignPlanId("plan-1"),
        (_item("i1", 1, topic="Changed"), _item("i2", 2)),
    )

    assert result.version == 2
    assert result.status is CampaignPlanStatus.DRAFT

    old = repo.get_plan(CampaignPlanId("plan-1"))
    assert old is not None
    assert old.status is CampaignPlanStatus.SUPERSEDED

    new = repo.get_plan(result.id)
    assert new is not None
    assert new.status is CampaignPlanStatus.DRAFT
    assert new.items[0].topic == "Changed"
    connection.close()


def test_edit_is_atomic_on_mid_failure(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    inner = SqliteCampaignRepository(connection)
    uow = SqliteUnitOfWork(connection)

    inner.save_brief(_brief())
    inner.save_campaign(_campaign())
    inner.save_plan(_plan((_item("i1", 1), _item("i2", 2))))

    failing_repo = _FailingSecondSavePlanRepository(inner)
    use_case = EditCampaignPlan(failing_repo, uow)

    with pytest.raises(RuntimeError):
        use_case.execute(
            CampaignPlanId("plan-1"),
            (_item("i1", 1, topic="Changed"), _item("i2", 2)),
        )

    # Old plan stayed DRAFT (rolled back), and no new plan was persisted.
    old = inner.get_plan(CampaignPlanId("plan-1"))
    assert old is not None
    assert old.status is CampaignPlanStatus.DRAFT
    assert connection.execute("SELECT COUNT(*) FROM campaign_plans").fetchone()[0] == 1
    connection.close()
