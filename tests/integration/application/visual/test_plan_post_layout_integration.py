"""Integration test for PlanPostLayout (A13 dio 2b) on a real SQLite DB."""

from __future__ import annotations

from pathlib import Path

from ai_campaign_studio.application.brands.load_brand_fixture import LoadBrandFixture
from ai_campaign_studio.application.campaigns.approve_campaign_plan import (
    ApproveCampaignPlan,
)
from ai_campaign_studio.application.campaigns.create_campaign import CreateCampaign
from ai_campaign_studio.application.campaigns.generate_campaign_plan import (
    GenerateCampaignPlan,
)
from ai_campaign_studio.application.posts.generate_social_post import (
    GenerateSocialPost,
)
from ai_campaign_studio.application.visual.generate_visual_system import (
    GenerateVisualSystem,
)
from ai_campaign_studio.application.visual.plan_post_layout import PlanPostLayout
from ai_campaign_studio.domain.content.entities import CampaignTarget
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories import (
    SqliteBrandRepository,
    SqliteCampaignRepository,
    SqliteContentRepository,
    SqliteFactRepository,
    SqliteRevisionRepository,
    SqliteVisualRepository,
)
from ai_campaign_studio.infrastructure.database.unit_of_work import SqliteUnitOfWork
from ai_campaign_studio.ports.ai import AIRequest, AIResponse
from ai_campaign_studio.ports.prompts import PromptDefinition

_MIGRATIONS_DIR = Path(__file__).resolve().parents[4] / "resources" / "migrations"
_FIXTURE_PATH = (
    Path(__file__).resolve().parents[4] / "resources" / "fixtures" / "brightsmile.json"
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


class _FakePromptRepository:
    def get(self, name: str, version: str) -> PromptDefinition:
        return PromptDefinition(
            name=name,
            version=version,
            purpose=name,
            input_contract="...",
            output_contract="...",
            language_support="EN/BHS",
            instructions="Produce the output.",
        )


def _brief() -> dict:
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


def _plan_payload() -> dict:
    return {
        "campaign_theme": "Healthy smile",
        "items": [
            {
                "order": 1,
                "role": "PROBLEM",
                "topic": "Cost of implants",
                "goal": "awareness",
                "facts_needed": [],
            }
        ],
    }


def _post_payload() -> dict:
    return {
        "headline": "Short headline",
        "caption": "Caption",
        "hook": "Hook",
        "body": "Body",
        "cta": "CTA",
        "hashtags": [],
        "claims": [],
    }


def _visual_payload() -> dict:
    return {
        "campaign_visual_system": {
            "primary_layout_family": "HERO",
            "secondary_layout_family": None,
            "headline_scale": "LARGE",
            "image_treatment": "ROUNDED",
            "logo_rule": "SHOW",
            "cta_rule": "SHOW",
            "alignment": "CENTER",
            "style": ["clean"],
        },
        "layout_spec": {
            "primitive": "HERO",
            "image_position": "BACKGROUND",
            "headline_position": "CENTER",
            "headline_scale": "LARGE",
            "overlay": "DARK",
            "logo_position": "TOP_LEFT",
            "cta_style": "SOLID",
            "alignment": "CENTER",
            "format": "FEED_POST",
        },
    }


def _layout_payload() -> dict:
    return {
        "primitive": "HERO",
        "image_position": "BACKGROUND",
        "headline_position": "CENTER",
        "headline_scale": "LARGE",
        "overlay": "DARK",
        "logo_position": "TOP_LEFT",
        "cta_style": "SOLID",
        "alignment": "CENTER",
        "format": "999x999",
    }


def test_end_to_end_plan_post_layout_round_trip(tmp_path: Path) -> None:
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)

    brand_repo = SqliteBrandRepository(connection)
    fact_repo = SqliteFactRepository(connection)
    campaign_repo = SqliteCampaignRepository(connection)
    content_repo = SqliteContentRepository(connection)
    revision_repo = SqliteRevisionRepository(connection)
    visual_repo = SqliteVisualRepository(connection)
    uow = SqliteUnitOfWork(connection)

    snapshot = LoadBrandFixture(brand_repo, fact_repo, uow).execute(_FIXTURE_PATH)
    campaign = CreateCampaign(campaign_repo, uow).execute(
        snapshot.brand_id, snapshot.id, _brief()
    )
    plan = GenerateCampaignPlan(
        campaign_repo,
        brand_repo,
        _FakePromptRepository(),
        _FakeAiPort(_plan_payload()),
        uow,
    ).execute(campaign.id)
    approved = ApproveCampaignPlan(campaign_repo, uow).execute(plan.id)

    item = approved.items[0]
    piece = GenerateSocialPost(
        campaign_repo,
        brand_repo,
        fact_repo,
        content_repo,
        revision_repo,
        _FakePromptRepository(),
        _FakeAiPort(_post_payload()),
        uow,
    ).execute(
        campaign.id,
        approved.id,
        item.id,
        CampaignTarget(
            channel="SOCIAL", platform_code="INSTAGRAM", format_code="FEED_POST"
        ),
    )

    visual_system, _ = GenerateVisualSystem(
        campaign_repo,
        brand_repo,
        visual_repo,
        _FakePromptRepository(),
        _FakeAiPort(_visual_payload()),
        uow,
    ).execute(approved.id)

    layout = PlanPostLayout(
        campaign_repo,
        content_repo,
        visual_repo,
        _FakePromptRepository(),
        _FakeAiPort(_layout_payload()),
        uow,
    ).execute(piece.id, visual_system.id, approved.id)

    persisted = visual_repo.get_layout_spec(layout.id)
    assert persisted is not None
    assert persisted == layout
    assert persisted.format == "1080x1350"  # AI returned "999x999", overridden
    assert persisted.validation_status == "VALID"

    connection.close()
