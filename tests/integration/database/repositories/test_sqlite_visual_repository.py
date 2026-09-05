"""Integration tests for SqliteVisualRepository (A5, dio 2)."""

from __future__ import annotations

import sqlite3
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

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
from ai_campaign_studio.domain.common.ids import (
    CampaignId,
    CampaignPlanId,
    LayoutSpecId,
    PostId,
    VisualSystemId,
)
from ai_campaign_studio.domain.visual.entities import CampaignVisualSystem
from ai_campaign_studio.domain.visual.enums import (
    Alignment,
    CtaRule,
    CtaStyle,
    HeadlinePosition,
    HeadlineScale,
    ImagePosition,
    ImageTreatment,
    LayoutPrimitive,
    LogoPosition,
    LogoRule,
    Overlay,
)
from ai_campaign_studio.domain.visual.layout import LayoutSpec
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


def _seed_content_piece(connection: sqlite3.Connection) -> None:
    """Seed plan -> item -> content_piece so a layout spec can reference it."""
    repo = SqliteCampaignRepository(connection)
    repo.save_plan(
        CampaignPlan(
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
                )
            ],
        )
    )
    connection.execute(
        "INSERT INTO content_pieces (id, campaign_item_id, target_channel,"
        " target_platform_code, target_format_code, payload_type, status,"
        " brand_snapshot_id, facts_allowed_json, revision_ids_json,"
        " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "piece-1",
            "item-1",
            "SOCIAL",
            "INSTAGRAM",
            "FEED_POST",
            "SOCIAL_POST",
            "DRAFT",
            "snap-1",
            "[]",
            "[]",
            _CREATED_AT.isoformat(),
            _CREATED_AT.isoformat(),
        ),
    )


def _layout_spec() -> LayoutSpec:
    return LayoutSpec(
        primitive=LayoutPrimitive.HERO,
        image_position=ImagePosition.BACKGROUND,
        headline_position=HeadlinePosition.CENTER,
        headline_scale=HeadlineScale.LARGE,
        overlay=Overlay.DARK,
        logo_position=LogoPosition.TOP_LEFT,
        cta_style=CtaStyle.SOLID,
        alignment=Alignment.CENTER,
        format="FEED_POST",
        id=LayoutSpecId("ls-1"),
        content_piece_id=PostId("piece-1"),
        validation_status="VALID",
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


def test_round_trip_layout_spec(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    _seed_campaign(connection)
    _seed_content_piece(connection)
    repo = SqliteVisualRepository(connection)

    spec = _layout_spec()
    repo.save_layout_spec(spec)

    assert repo.get_layout_spec(LayoutSpecId("ls-1")) == spec
    connection.close()


def test_get_layout_spec_unknown_returns_none(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteVisualRepository(connection)
    assert repo.get_layout_spec(LayoutSpecId("missing")) is None
    connection.close()


def test_save_layout_spec_requires_identity(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteVisualRepository(connection)

    spec = _layout_spec()
    no_id = LayoutSpec(
        primitive=spec.primitive,
        image_position=spec.image_position,
        headline_position=spec.headline_position,
        headline_scale=spec.headline_scale,
        overlay=spec.overlay,
        logo_position=spec.logo_position,
        cta_style=spec.cta_style,
        alignment=spec.alignment,
        format=spec.format,
    )
    with pytest.raises(ValueError):
        repo.save_layout_spec(no_id)
    connection.close()


def test_save_layout_spec_preserves_created_at_on_resave(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    _seed_campaign(connection)
    _seed_content_piece(connection)
    repo = SqliteVisualRepository(connection)

    spec = _layout_spec()  # validation_status="VALID"
    with patch(
        "ai_campaign_studio.infrastructure.database.repositories."
        "sqlite_visual_repository.utc_now",
        return_value=datetime(2026, 1, 1, tzinfo=UTC),
    ):
        repo.save_layout_spec(spec)

    first = connection.execute(
        "SELECT created_at FROM layout_specs WHERE id = ?", ("ls-1",)
    ).fetchone()[0]

    # Re-save the SAME id with a different validation_status (re-validation
    # flow); created_at must NOT change.
    revalidated = replace(spec, validation_status="INVALID")
    with patch(
        "ai_campaign_studio.infrastructure.database.repositories."
        "sqlite_visual_repository.utc_now",
        return_value=datetime(2026, 2, 2, tzinfo=UTC),
    ):
        repo.save_layout_spec(revalidated)

    second = connection.execute(
        "SELECT created_at FROM layout_specs WHERE id = ?", ("ls-1",)
    ).fetchone()[0]

    assert first == second
    loaded = repo.get_layout_spec(LayoutSpecId("ls-1"))
    assert loaded is not None
    assert loaded.validation_status == "INVALID"
    connection.close()
