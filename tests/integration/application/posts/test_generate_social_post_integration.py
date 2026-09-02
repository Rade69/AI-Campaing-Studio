"""Integration tests for GenerateSocialPost (A11) on a real SQLite DB."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from ai_campaign_studio.application.brands.load_brand_fixture import LoadBrandFixture
from ai_campaign_studio.application.campaigns.create_campaign import CreateCampaign
from ai_campaign_studio.application.posts.generate_social_post import (
    GenerateSocialPost,
)
from ai_campaign_studio.application.posts.select_allowed_facts import (
    select_allowed_facts,
)
from ai_campaign_studio.domain.campaign.entities import CampaignItem, CampaignPlan
from ai_campaign_studio.domain.campaign.enums import (
    CampaignItemStatus,
    CampaignPlanStatus,
)
from ai_campaign_studio.domain.campaign.roles import CampaignRole
from ai_campaign_studio.domain.common.ids import CampaignItemId, CampaignPlanId
from ai_campaign_studio.domain.content.entities import CampaignTarget
from ai_campaign_studio.domain.content.enums import ContentStatus
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories import (
    SqliteBrandRepository,
    SqliteCampaignRepository,
    SqliteContentRepository,
    SqliteFactRepository,
)
from ai_campaign_studio.infrastructure.database.unit_of_work import SqliteUnitOfWork
from ai_campaign_studio.ports.ai import AIRequest, AIResponse
from ai_campaign_studio.ports.prompts import PromptDefinition

_MIGRATIONS_DIR = Path(__file__).resolve().parents[4] / "resources" / "migrations"
_FIXTURE_PATH = (
    Path(__file__).resolve().parents[4] / "resources" / "fixtures" / "brightsmile.json"
)


def _setup_db(tmp_path: Path):
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)
    return connection


def _valid_brief() -> dict:
    return {
        "offer": "Dental implants",
        "goal": "Book consultations",
        "audience_text": "Adults",
        "targets": [
            {
                "channel": "SOCIAL",
                "platform_code": "INSTAGRAM",
                "format_code": "FEED_POST",
            }
        ],
        "content_piece_count": 1,
        "content_language_context": "BHS_LATIN",
    }


def _item() -> CampaignItem:
    return CampaignItem(
        id=CampaignItemId("item-1"),
        order=1,
        role=CampaignRole.PROBLEM,
        topic="Implantati",
        goal="Edukacija",
        status=CampaignItemStatus.PLANNED,
        facts_needed=("implantat",),
    )


class _FakePromptRepository:
    def get(self, name: str, version: str) -> PromptDefinition:
        return PromptDefinition(
            name=name,
            version=version,
            purpose="post",
            input_contract="...",
            output_contract="...",
            language_support="EN/BHS",
            instructions="Generate a post.",
        )


class _FakeAiPort:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def generate(self, request: AIRequest) -> AIResponse:
        del request
        return AIResponse(
            provider="fake",
            model="fake",
            latency_ms=1,
            structured_payload=self._payload,
        )


class _FailingContentRepository:
    def __init__(self, inner: SqliteContentRepository) -> None:
        self._inner = inner

    def save_content_piece(self, content_piece) -> None:  # noqa: ANN001
        raise RuntimeError("simulated mid-persist failure")

    def get_content_piece(self, content_piece_id):  # noqa: ANN001
        return self._inner.get_content_piece(content_piece_id)

    def list_campaign_content(self, campaign_id):  # noqa: ANN001
        return self._inner.list_campaign_content(campaign_id)


def _post_payload(fact_id: str) -> dict:
    return {
        "headline": "H",
        "caption": "C",
        "hook": "Hook",
        "body": "Body",
        "cta": "CTA",
        "hashtags": [],
        "claims": [
            {"text": "Nudimo implantate", "type": "FACT", "fact_ids": [fact_id]},
            {"text": "Zakažite", "type": "CTA", "fact_ids": []},
        ],
    }


def test_end_to_end_fixture_to_post(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    brand_repo = SqliteBrandRepository(connection)
    fact_repo = SqliteFactRepository(connection)
    campaign_repo = SqliteCampaignRepository(connection)
    content_repo = SqliteContentRepository(connection)
    uow = SqliteUnitOfWork(connection)

    snapshot = LoadBrandFixture(brand_repo, fact_repo, uow).execute(_FIXTURE_PATH)
    campaign = CreateCampaign(campaign_repo, uow).execute(
        snapshot.brand_id, snapshot.id, _valid_brief()
    )

    item = _item()
    plan = CampaignPlan(
        id=CampaignPlanId("plan-1"),
        campaign_id=campaign.id,
        version=1,
        status=CampaignPlanStatus.DRAFT,
        created_at=datetime.now(UTC),
        items=[item],
    )
    campaign_repo.save_plan(plan)

    # Determine the allowed fact id from the real snapshot facts.
    allowed = select_allowed_facts(item, fact_repo.list_snapshot_facts(snapshot.id))
    assert allowed.fact_ids  # "implantat" must match the implants fact
    fact_id = allowed.fact_ids[0]

    generate = GenerateSocialPost(
        campaign_repo,
        brand_repo,
        fact_repo,
        content_repo,
        _FakePromptRepository(),
        _FakeAiPort(_post_payload(fact_id)),
        uow,
    )
    piece = generate.execute(
        campaign.id,
        plan.id,
        item.id,
        CampaignTarget(
            channel="SOCIAL", platform_code="INSTAGRAM", format_code="FEED_POST"
        ),
    )

    assert piece.status is ContentStatus.GENERATING
    assert piece.payload is not None
    assert piece.facts_allowed == (fact_id,)
    assert content_repo.get_content_piece(piece.id) == piece
    connection.close()


def test_generate_post_is_atomic_on_failure(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    brand_repo = SqliteBrandRepository(connection)
    fact_repo = SqliteFactRepository(connection)
    campaign_repo = SqliteCampaignRepository(connection)
    content_repo = SqliteContentRepository(connection)
    uow = SqliteUnitOfWork(connection)

    snapshot = LoadBrandFixture(brand_repo, fact_repo, uow).execute(_FIXTURE_PATH)
    campaign = CreateCampaign(campaign_repo, uow).execute(
        snapshot.brand_id, snapshot.id, _valid_brief()
    )
    item = _item()
    plan = CampaignPlan(
        id=CampaignPlanId("plan-1"),
        campaign_id=campaign.id,
        version=1,
        status=CampaignPlanStatus.DRAFT,
        created_at=datetime.now(UTC),
        items=[item],
    )
    campaign_repo.save_plan(plan)

    allowed = select_allowed_facts(item, fact_repo.list_snapshot_facts(snapshot.id))
    fact_id = allowed.fact_ids[0]

    generate = GenerateSocialPost(
        campaign_repo,
        brand_repo,
        fact_repo,
        _FailingContentRepository(content_repo),
        _FakePromptRepository(),
        _FakeAiPort(_post_payload(fact_id)),
        uow,
    )

    with pytest.raises(RuntimeError):
        generate.execute(
            campaign.id,
            plan.id,
            item.id,
            CampaignTarget(
                channel="SOCIAL", platform_code="INSTAGRAM", format_code="FEED_POST"
            ),
        )

    assert connection.execute("SELECT COUNT(*) FROM content_pieces").fetchone()[0] == 0
    connection.close()
