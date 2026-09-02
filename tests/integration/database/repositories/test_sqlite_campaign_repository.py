"""Integration tests for SqliteCampaignRepository (A5, dio 2)."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

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
from ai_campaign_studio.domain.common.ids import CampaignId, CampaignPlanId
from ai_campaign_studio.domain.content.entities import CampaignTarget
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories.sqlite_campaign_repository import (  # noqa: E501
    SqliteCampaignRepository,
)
from ai_campaign_studio.ports.repositories import CampaignRepositoryPort

_MIGRATIONS_DIR = Path(__file__).resolve().parents[4] / "resources" / "migrations"
_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def _setup_db(tmp_path: Path) -> sqlite3.Connection:
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)
    return connection


def _brief() -> CampaignBrief:
    return CampaignBrief(
        id="brief-1",
        offer="Offer",
        goal="Goal",
        audience_text="Audience",
        targets=[
            CampaignTarget(
                channel="SOCIAL", platform_code="INSTAGRAM", format_code="FEED_POST"
            )
        ],
        content_piece_count=6,
        content_language_context="BHS_LATIN",
        created_at=_CREATED_AT,
        special_instructions=["Keep it friendly"],
    )


def _campaign() -> Campaign:
    return Campaign(
        id=CampaignId("campaign-1"),
        brand_id="brand-1",
        brand_snapshot_id="snap-1",
        brief_id="brief-1",
        status=CampaignStatus.DRAFT,
        created_at=_CREATED_AT,
    )


def _plan() -> CampaignPlan:
    return CampaignPlan(
        id=CampaignPlanId("plan-1"),
        campaign_id=CampaignId("campaign-1"),
        version=1,
        status=CampaignPlanStatus.DRAFT,
        created_at=_CREATED_AT,
        items=[
            CampaignItem(
                id="item-1",
                order=1,
                role=CampaignRole.PROBLEM,
                topic="Topic",
                goal="Goal",
                status=CampaignItemStatus.PLANNED,
                facts_needed=["location"],
            )
        ],
    )


def test_repository_is_a_campaign_repository_port(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteCampaignRepository(connection)
    assert isinstance(repo, CampaignRepositoryPort)
    connection.close()


def test_round_trip_campaign_and_plan(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteCampaignRepository(connection)

    repo.save_brief(_brief())
    repo.save_campaign(_campaign())
    repo.save_plan(_plan())

    assert repo.get_campaign(CampaignId("campaign-1")) == _campaign()
    assert repo.get_plan(CampaignPlanId("plan-1")) == _plan()
    connection.close()


def test_round_trip_brief(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteCampaignRepository(connection)

    repo.save_brief(_brief())

    assert repo.get_brief("brief-1") == _brief()
    connection.close()


def test_get_unknown_brief_returns_none(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteCampaignRepository(connection)
    assert repo.get_brief("missing") is None
    connection.close()


def test_save_plan_is_idempotent(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteCampaignRepository(connection)
    repo.save_brief(_brief())
    repo.save_campaign(_campaign())
    plan = _plan()
    repo.save_plan(plan)
    repo.save_plan(plan)

    count = connection.execute(
        "SELECT COUNT(*) FROM campaign_items WHERE plan_id = ?", (plan.id,)
    ).fetchone()[0]
    assert count == len(plan.items)
    connection.close()


def test_get_unknown_returns_none(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteCampaignRepository(connection)
    assert repo.get_campaign(CampaignId("missing")) is None
    assert repo.get_plan(CampaignPlanId("missing")) is None
    connection.close()


def test_foreign_keys_enforced(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO campaign_items (id, plan_id, \"order\", role, topic, goal,"
            " target_audience_id, facts_needed_json, status)"
            " VALUES ('item-x', 'missing-plan', 1, 'PROBLEM', 't', 'g', NULL, '[]',"
            " 'PLANNED')"
        )
    connection.close()
