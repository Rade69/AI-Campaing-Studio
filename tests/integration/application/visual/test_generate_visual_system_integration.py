"""Integration test for GenerateVisualSystem (A13) on a real SQLite DB."""

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
from ai_campaign_studio.application.visual.generate_visual_system import (
    GenerateVisualSystem,
)
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories import (
    SqliteBrandRepository,
    SqliteCampaignRepository,
    SqliteFactRepository,
    SqliteVisualRepository,
)
from ai_campaign_studio.infrastructure.database.unit_of_work import SqliteUnitOfWork
from ai_campaign_studio.ports.ai import AIRequest, AIResponse
from ai_campaign_studio.ports.prompts import PromptDefinition

_MIGRATIONS_DIR = Path(__file__).resolve().parents[4] / "resources" / "migrations"
_FIXTURE_PATH = (
    Path(__file__).resolve().parents[4] / "resources" / "fixtures" / "brightsmile.json"
)


def _valid_brief() -> dict:
    return {
        "offer": "Dental implants",
        "goal": "Book consultations",
        "audience_text": "Adults 25-55",
        "targets": [
            {
                "channel": "SOCIAL",
                "platform_code": "INSTAGRAM",
                "format_code": "FEED_POST",
            }
        ],
        "content_piece_count": 3,
        "content_language_context": "BHS_LATIN",
    }


def _valid_plan_payload() -> dict:
    return {
        "campaign_theme": "Healthy smile",
        "items": [
            {
                "order": 1,
                "role": "PROBLEM",
                "topic": "Cost of implants",
                "goal": "awareness",
                "facts_needed": [],
            },
            {
                "order": 2,
                "role": "EDUCATION",
                "topic": "Implant process",
                "goal": "educate",
                "facts_needed": [],
            },
            {
                "order": 3,
                "role": "ACTION",
                "topic": "Book consultation",
                "goal": "convert",
                "facts_needed": [],
            },
        ],
    }


def _valid_visual_payload() -> dict:
    return {
        "campaign_visual_system": {
            "primary_layout_family": "HERO",
            "secondary_layout_family": None,
            "headline_scale": "LARGE",
            "image_treatment": "ROUNDED",
            "logo_rule": "SHOW",
            "cta_rule": "SHOW",
            "alignment": "CENTER",
            "style": ["clean", "calm"],
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


def test_end_to_end_visual_system_round_trip(tmp_path: Path) -> None:
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)

    brand_repo = SqliteBrandRepository(connection)
    fact_repo = SqliteFactRepository(connection)
    campaign_repo = SqliteCampaignRepository(connection)
    visual_repo = SqliteVisualRepository(connection)
    uow = SqliteUnitOfWork(connection)

    # fixture -> brief -> plan -> approve
    snapshot = LoadBrandFixture(brand_repo, fact_repo, uow).execute(_FIXTURE_PATH)
    campaign = CreateCampaign(campaign_repo, uow).execute(
        snapshot.brand_id, snapshot.id, _valid_brief()
    )
    plan = GenerateCampaignPlan(
        campaign_repo,
        brand_repo,
        _FakePromptRepository(),
        _FakeAiPort(_valid_plan_payload()),
        uow,
    ).execute(campaign.id)
    approved_plan = ApproveCampaignPlan(campaign_repo, uow).execute(plan.id)

    # generate visual system (fake AI port)
    use_case = GenerateVisualSystem(
        campaign_repo,
        brand_repo,
        visual_repo,
        _FakePromptRepository(),
        _FakeAiPort(_valid_visual_payload()),
        uow,
    )
    visual_system, layout_spec = use_case.execute(approved_plan.id)

    # round-trip through the real SqliteVisualRepository
    persisted = visual_repo.get_visual_system(visual_system.id)
    assert persisted is not None
    assert persisted == visual_system
    assert persisted.style == ("clean", "calm")
    assert persisted.image_treatment == "ROUNDED"
    assert persisted.primary_layout_family.value == "HERO"
    assert layout_spec.primitive.value == "HERO"

    connection.close()
