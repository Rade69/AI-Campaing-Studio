"""Integration tests for SqliteVisualRepository (A5, dio 2)."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from ai_campaign_studio.domain.campaign.entities import Campaign, CampaignBrief
from ai_campaign_studio.domain.campaign.enums import CampaignStatus
from ai_campaign_studio.domain.common.ids import CampaignId, VisualSystemId
from ai_campaign_studio.domain.visual.entities import CampaignVisualSystem
from ai_campaign_studio.domain.visual.enums import (
    Alignment,
    CtaRule,
    HeadlineScale,
    ImageTreatment,
    LayoutPrimitive,
    LogoRule,
)
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories.sqlite_campaign_repository import (  # noqa: E501
    SqliteCampaignRepository,
)
from ai_campaign_studio.infrastructure.database.repositories.sqlite_visual_repository import (  # noqa: E501
    SqliteVisualRepository,
)
from ai_campaign_studio.ports.repositories import VisualRepositoryPort

_MIGRATIONS_DIR = Path(__file__).resolve().parents[4] / "resources" / "migrations"
_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def _setup_db(tmp_path: Path) -> sqlite3.Connection:
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)
    return connection


def _seed_campaign(connection: sqlite3.Connection) -> None:
    repo = SqliteCampaignRepository(connection)
    repo.save_brief(
        CampaignBrief(
            id="brief-1",
            offer="Offer",
            goal="Goal",
            audience_text="Audience",
            targets=[],
            content_piece_count=1,
            content_language_context="BHS_LATIN",
            created_at=_CREATED_AT,
        )
    )
    repo.save_campaign(
        Campaign(
            id=CampaignId("campaign-1"),
            brand_id="brand-1",
            brand_snapshot_id="snap-1",
            brief_id="brief-1",
            status=CampaignStatus.DRAFT,
            created_at=_CREATED_AT,
        )
    )


def _system() -> CampaignVisualSystem:
    return CampaignVisualSystem(
        id=VisualSystemId("vs-1"),
        campaign_id=CampaignId("campaign-1"),
        primary_layout_family=LayoutPrimitive.HERO,
        headline_scale=HeadlineScale.LARGE,
        image_treatment=ImageTreatment.BORDER,
        logo_rule=LogoRule.SHOW,
        cta_rule=CtaRule.SHOW,
        alignment=Alignment.CENTER,
        created_at=_CREATED_AT,
        style=["clean", "minimal"],
    )


def test_repository_is_a_visual_repository_port(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteVisualRepository(connection)
    assert isinstance(repo, VisualRepositoryPort)
    connection.close()


def test_round_trip_visual_system(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    _seed_campaign(connection)
    repo = SqliteVisualRepository(connection)

    system = _system()
    repo.save_visual_system(system)

    assert repo.get_visual_system(VisualSystemId("vs-1")) == system
    connection.close()


def test_get_unknown_returns_none(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteVisualRepository(connection)
    assert repo.get_visual_system(VisualSystemId("missing")) is None
    connection.close()
