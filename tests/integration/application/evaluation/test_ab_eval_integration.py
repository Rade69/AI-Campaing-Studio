"""Integration test for the A/B evaluation harness (A16).

Runs both Control A and System B against the same brightsmile fixture and the
same brief, using a scripted fake AI port, and confirms ``compute_metrics``
works on both outputs without error.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from ai_campaign_studio.application.brands.load_brand_fixture import LoadBrandFixture
from ai_campaign_studio.application.evaluation.deterministic_metrics import (
    compute_metrics,
)
from ai_campaign_studio.application.evaluation.run_control_a import run_control_a
from ai_campaign_studio.application.evaluation.run_system_b import run_system_b
from ai_campaign_studio.application.posts.claim_linter import ClaimRules
from ai_campaign_studio.domain.brand.entities import BrandSnapshot
from ai_campaign_studio.domain.campaign.entities import CampaignBrief
from ai_campaign_studio.domain.content.entities import CampaignTarget
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories import (
    SqliteBrandRepository,
    SqliteCampaignRepository,
    SqliteContentRepository,
    SqliteFactRepository,
    SqliteRevisionRepository,
)
from ai_campaign_studio.infrastructure.database.unit_of_work import SqliteUnitOfWork
from ai_campaign_studio.ports.ai import AIRequest, AIResponse
from ai_campaign_studio.ports.prompts import PromptDefinition

_MIGRATIONS_DIR = Path(__file__).resolve().parents[4] / "resources" / "migrations"
_FIXTURE_PATH = (
    Path(__file__).resolve().parents[4] / "resources" / "fixtures" / "brightsmile.json"
)
_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


class _ScriptedAiPort:
    """Returns a different deterministic payload per prompt name."""

    def generate(self, request: AIRequest) -> AIResponse:
        if request.prompt_name == "campaign_plan":
            payload: dict = {
                "campaign_theme": "Healthy smile",
                "items": [
                    {
                        "order": 1,
                        "role": "PROBLEM",
                        "topic": "Cost of implants",
                        "goal": "awareness",
                        "facts_needed": ["implant"],
                    }
                ],
            }
        elif request.prompt_name == "post_generation":
            payload = {
                "headline": "System B headline",
                "caption": "System B caption",
                "hook": "Hook",
                "body": "Body",
                "cta": "CTA",
                "hashtags": [],
                "claims": [],
            }
        elif request.prompt_name == "ab_control":
            payload = {
                "posts": [
                    {
                        "headline": "Control A headline",
                        "caption": "Control A caption",
                        "hook": "",
                        "body": "",
                        "cta": "CTA",
                        "hashtags": [],
                        "claims": [],
                    }
                ]
            }
        else:
            payload = {}
        return AIResponse(
            provider="fake",
            model="fake",
            latency_ms=1,
            structured_payload=payload,
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
            instructions="Generate.",
        )


def _brief(snapshot: BrandSnapshot) -> CampaignBrief:
    return CampaignBrief(
        id="brief-1",
        offer="Dental implants",
        goal="Book consultations",
        audience_text="Adults",
        targets=[
            CampaignTarget(
                channel="SOCIAL", platform_code="INSTAGRAM", format_code="FEED_POST"
            )
        ],
        content_piece_count=1,
        content_language_context="BHS_LATIN",
        created_at=_CREATED_AT,
    )


def _raw_brief() -> dict:
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


def test_ab_eval_metrics_work_on_both(tmp_path: Path) -> None:
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)

    brand_repo = SqliteBrandRepository(connection)
    fact_repo = SqliteFactRepository(connection)
    campaign_repo = SqliteCampaignRepository(connection)
    content_repo = SqliteContentRepository(connection)
    revision_repo = SqliteRevisionRepository(connection)
    uow = SqliteUnitOfWork(connection)

    snapshot = LoadBrandFixture(brand_repo, fact_repo, uow).execute(_FIXTURE_PATH)
    snapshot_facts = fact_repo.list_snapshot_facts(snapshot.id)
    ai = _ScriptedAiPort()
    prompt_repo = _FakePromptRepository()
    rules = ClaimRules(prohibited_terms=(), currency_symbols=())

    # Control A
    control_posts = run_control_a(
        snapshot, snapshot_facts, _brief(snapshot), prompt_repo, ai, rules
    )
    control_metrics = compute_metrics(control_posts)
    assert len(control_posts) == 1
    assert control_metrics.unique_role_count is None  # Control A has no role

    # System B
    system_posts = run_system_b(
        snapshot.brand_id,
        snapshot.id,
        _raw_brief(),
        campaign_repo,
        brand_repo,
        fact_repo,
        content_repo,
        revision_repo,
        prompt_repo,
        ai,
        uow,
    )
    system_metrics = compute_metrics(system_posts)
    assert len(system_posts) == 1
    assert system_metrics.unique_role_count == 1  # System B has a role

    connection.close()
