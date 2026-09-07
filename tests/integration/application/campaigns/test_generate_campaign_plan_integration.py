"""Integration tests for GenerateCampaignPlan (A9) on a real SQLite DB."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_campaign_studio.application.brands.load_brand_fixture import LoadBrandFixture
from ai_campaign_studio.application.campaigns.create_campaign import CreateCampaign
from ai_campaign_studio.application.campaigns.generate_campaign_plan import (
    GenerateCampaignPlan,
)
from ai_campaign_studio.application.posts.select_allowed_facts import (
    select_allowed_facts,
)
from ai_campaign_studio.domain.campaign.enums import CampaignStatus
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories import (  # noqa: E501
    SqliteBrandRepository,
    SqliteCampaignRepository,
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


def _valid_payload() -> dict:
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
            purpose="plan",
            input_contract="...",
            output_contract="...",
            language_support="EN/BHS",
            instructions="Plan the campaign.",
        )


class _FailingCampaignRepository:
    """save_plan succeeds, save_campaign raises (mid-persist failure)."""

    def __init__(self, inner: SqliteCampaignRepository) -> None:
        self._inner = inner

    def save_plan(self, plan) -> None:  # noqa: ANN001
        self._inner.save_plan(plan)

    def save_campaign(self, campaign) -> None:  # noqa: ANN001
        raise RuntimeError("simulated mid-persist failure")

    def get_campaign(self, campaign_id):  # noqa: ANN001
        return self._inner.get_campaign(campaign_id)

    def get_brief(self, brief_id):  # noqa: ANN001
        return self._inner.get_brief(brief_id)

    def save_brief(self, brief) -> None:  # noqa: ANN001
        self._inner.save_brief(brief)

    def get_plan(self, plan_id):  # noqa: ANN001
        return self._inner.get_plan(plan_id)


def test_end_to_end_fixture_to_plan(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    brand_repo = SqliteBrandRepository(connection)
    fact_repo = SqliteFactRepository(connection)
    campaign_repo = SqliteCampaignRepository(connection)
    uow = SqliteUnitOfWork(connection)

    # 1. Load the brand fixture -> persisted Brand + BrandSnapshot + facts.
    snapshot = LoadBrandFixture(brand_repo, fact_repo, uow).execute(_FIXTURE_PATH)

    # 2. Create the campaign brief + DRAFT campaign.
    campaign = CreateCampaign(campaign_repo, uow).execute(
        snapshot.brand_id, snapshot.id, _valid_brief()
    )

    # 3. Generate the plan (fake AI port).
    generate = GenerateCampaignPlan(
        campaign_repo,
        brand_repo,
        fact_repo,
        _FakePromptRepository(),
        _FakeAiPort(_valid_payload()),
        uow,
    )
    plan = generate.execute(campaign.id)

    assert plan.items is not None
    assert len(plan.items) == 3
    persisted_campaign = campaign_repo.get_campaign(campaign.id)
    assert persisted_campaign is not None
    assert persisted_campaign.status is CampaignStatus.PLAN_GENERATED
    assert campaign_repo.get_plan(plan.id) == plan
    connection.close()


def test_generate_plan_is_atomic_on_mid_failure(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    brand_repo = SqliteBrandRepository(connection)
    fact_repo = SqliteFactRepository(connection)
    inner_campaign_repo = SqliteCampaignRepository(connection)
    uow = SqliteUnitOfWork(connection)

    snapshot = LoadBrandFixture(brand_repo, fact_repo, uow).execute(_FIXTURE_PATH)
    campaign = CreateCampaign(inner_campaign_repo, uow).execute(
        snapshot.brand_id, snapshot.id, _valid_brief()
    )

    failing_repo = _FailingCampaignRepository(inner_campaign_repo)
    generate = GenerateCampaignPlan(
        failing_repo,
        brand_repo,
        fact_repo,
        _FakePromptRepository(),
        _FakeAiPort(_valid_payload()),
        uow,
    )

    with pytest.raises(RuntimeError):
        generate.execute(campaign.id)

    # Campaign status unchanged, no plans/items persisted.
    persisted = inner_campaign_repo.get_campaign(campaign.id)
    assert persisted is not None
    assert persisted.status is CampaignStatus.DRAFT
    assert connection.execute("SELECT COUNT(*) FROM campaign_plans").fetchone()[0] == 0
    assert connection.execute("SELECT COUNT(*) FROM campaign_items").fetchone()[0] == 0
    connection.close()


def test_fact_id_from_catalog_is_found_by_select_allowed_facts(
    tmp_path: Path,
) -> None:
    """Nalaz 1 fix, end-to-end: the fake AI returns the EXACT
    ``logical_fact_id`` the new prompt teaches (``fact-implants``), and the
    UNCHANGED ``select_allowed_facts`` matching actually finds the fact."""
    connection = _setup_db(tmp_path)
    brand_repo = SqliteBrandRepository(connection)
    fact_repo = SqliteFactRepository(connection)
    campaign_repo = SqliteCampaignRepository(connection)
    uow = SqliteUnitOfWork(connection)

    snapshot = LoadBrandFixture(brand_repo, fact_repo, uow).execute(_FIXTURE_PATH)
    campaign = CreateCampaign(campaign_repo, uow).execute(
        snapshot.brand_id, snapshot.id, _valid_brief()
    )

    payload = {
        "campaign_theme": "Healthy smile",
        "items": [
            {
                "order": 1,
                "role": "PROBLEM",
                "topic": "Cost of implants",
                "goal": "awareness",
                "facts_needed": ["fact-implants"],
            },
            {
                "order": 2,
                "role": "EDUCATION",
                "topic": "Implant process",
                "goal": "educate",
                "facts_needed": ["fact-team"],
            },
            {
                "order": 3,
                "role": "ACTION",
                "topic": "Book consultation",
                "goal": "convert",
                "facts_needed": ["fact-location"],
            },
        ],
    }
    generate = GenerateCampaignPlan(
        campaign_repo,
        brand_repo,
        fact_repo,
        _FakePromptRepository(),
        _FakeAiPort(payload),
        uow,
    )
    plan = generate.execute(campaign.id)

    snapshot_facts = fact_repo.list_snapshot_facts(snapshot.id)

    first = plan.items[0]
    allowed = select_allowed_facts(first, snapshot_facts)
    assert len(allowed.fact_ids) == 1
    matched_fact = next(
        f for f in snapshot_facts if f.logical_fact_id == "fact-implants"
    )
    assert allowed.fact_ids[0] == matched_fact.id
    connection.close()
