"""Integration tests for SqliteContentRepository (A5, dio 2)."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

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
from ai_campaign_studio.domain.content.claims import ContentClaim
from ai_campaign_studio.domain.content.entities import CampaignTarget, ContentPiece
from ai_campaign_studio.domain.content.enums import (
    ClaimStatus,
    ClaimType,
    ContentPayloadType,
    ContentStatus,
)
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories.sqlite_campaign_repository import (  # noqa: E501
    SqliteCampaignRepository,
)
from ai_campaign_studio.infrastructure.database.repositories.sqlite_content_repository import (  # noqa: E501
    SqliteContentRepository,
)
from ai_campaign_studio.ports.repositories import ContentRepositoryPort

_MIGRATIONS_DIR = Path(__file__).resolve().parents[4] / "resources" / "migrations"
_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def _setup_db(tmp_path: Path) -> sqlite3.Connection:
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)
    return connection


def _seed_campaign(
    connection: sqlite3.Connection, campaign_id: str, item_id: str
) -> None:
    """Seed a campaign -> plan -> item chain so a content piece can reference it."""
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
            id=CampaignId(campaign_id),
            brand_id="brand-1",
            brand_snapshot_id="snap-1",
            brief_id="brief-1",
            status=CampaignStatus.DRAFT,
            created_at=_CREATED_AT,
        )
    )
    repo.save_plan(
        CampaignPlan(
            id=CampaignPlanId(f"plan-{campaign_id}"),
            campaign_id=CampaignId(campaign_id),
            version=1,
            status=CampaignPlanStatus.DRAFT,
            created_at=_CREATED_AT,
            items=[
                CampaignItem(
                    id=item_id,
                    order=1,
                    role=CampaignRole.PROBLEM,
                    topic="Topic",
                    goal="Goal",
                    status=CampaignItemStatus.PLANNED,
                )
            ],
        )
    )


def _piece(campaign_id: str, item_id: str) -> ContentPiece:
    return ContentPiece(
        id=f"piece-{campaign_id}",
        campaign_item_id=item_id,
        target=CampaignTarget(
            channel="SOCIAL", platform_code="INSTAGRAM", format_code="FEED_POST"
        ),
        payload_type=ContentPayloadType.SOCIAL_POST,
        status=ContentStatus.DRAFT,
        brand_snapshot_id="snap-1",
        created_at=_CREATED_AT,
        updated_at=_CREATED_AT,
        facts_allowed=["fact-1"],
        revision_ids=["rev-1"],
        claims=[
            ContentClaim(
                id=f"claim-{campaign_id}",
                text="We are open seven days a week",
                type=ClaimType.FACT,
                status=ClaimStatus.VERIFIED_BY_FACT,
                fact_ids=["fact-1"],
                reason_codes=["ok"],
            )
        ],
    )


def test_repository_is_a_content_repository_port(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteContentRepository(connection)
    assert isinstance(repo, ContentRepositoryPort)
    connection.close()


def test_round_trip_content_piece(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    _seed_campaign(connection, "campaign-1", "item-1")
    repo = SqliteContentRepository(connection)

    piece = _piece("campaign-1", "item-1")
    repo.save_content_piece(piece)

    loaded = repo.get_content_piece(piece.id)
    assert loaded == piece  # dataclass equality covers claims + all nested lists
    connection.close()


def test_save_content_piece_is_idempotent(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    _seed_campaign(connection, "campaign-1", "item-1")
    repo = SqliteContentRepository(connection)

    piece = _piece("campaign-1", "item-1")
    repo.save_content_piece(piece)
    repo.save_content_piece(piece)

    count = connection.execute(
        "SELECT COUNT(*) FROM content_claims WHERE piece_id = ?", (piece.id,)
    ).fetchone()[0]
    assert count == len(piece.claims)
    connection.close()


def test_list_campaign_content_is_isolated(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    _seed_campaign(connection, "campaign-1", "item-1")
    _seed_campaign(connection, "campaign-2", "item-2")
    repo = SqliteContentRepository(connection)

    repo.save_content_piece(_piece("campaign-1", "item-1"))
    repo.save_content_piece(_piece("campaign-2", "item-2"))

    result = repo.list_campaign_content(CampaignId("campaign-1"))
    assert [piece.id for piece in result] == ["piece-campaign-1"]
    connection.close()


def test_get_unknown_returns_none(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteContentRepository(connection)
    assert repo.get_content_piece("missing") is None  # type: ignore[arg-type]
    connection.close()
