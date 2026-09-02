"""Unit tests for GenerateCampaignPlan (A9) with fake ports."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ai_campaign_studio.application.campaigns.generate_campaign_plan import (
    GenerateCampaignPlan,
)
from ai_campaign_studio.domain.brand.entities import BrandSnapshot
from ai_campaign_studio.domain.brand.value_objects import (
    Audience,
    BrandVoice,
    Restriction,
    ServiceDefinition,
    VisualIdentity,
)
from ai_campaign_studio.domain.campaign.entities import Campaign, CampaignBrief
from ai_campaign_studio.domain.campaign.enums import CampaignStatus
from ai_campaign_studio.domain.common.errors import EntityNotFound, InvariantViolation
from ai_campaign_studio.domain.common.ids import BrandId, BrandSnapshotId, CampaignId
from ai_campaign_studio.domain.content.entities import CampaignTarget
from ai_campaign_studio.ports.ai import AIRequest, AIResponse
from ai_campaign_studio.ports.prompts import PromptDefinition

_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


class _FakeUnitOfWork:
    def __init__(self) -> None:
        self.committed = False

    def __enter__(self) -> _FakeUnitOfWork:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:  # noqa: ANN001
        return False

    def commit(self) -> None:
        self.committed = True


class _FakeCampaignRepository:
    def __init__(self, campaign: Campaign, brief: CampaignBrief) -> None:
        self.campaign = campaign
        self.brief = brief
        self.plans: dict = {}

    def get_campaign(self, campaign_id):  # noqa: ANN001
        return self.campaign if self.campaign.id == campaign_id else None

    def get_brief(self, brief_id):  # noqa: ANN001
        return self.brief if self.brief.id == brief_id else None

    def save_plan(self, plan) -> None:  # noqa: ANN001
        self.plans[plan.id] = plan

    def save_campaign(self, campaign) -> None:  # noqa: ANN001
        self.campaign = campaign

    def save_brief(self, brief) -> None:  # noqa: ANN001
        del brief

    def get_plan(self, plan_id):  # noqa: ANN001
        return self.plans.get(plan_id)


class _FakeBrandRepository:
    def __init__(self, snapshot: BrandSnapshot) -> None:
        self._snapshot = snapshot

    def save_brand(self, brand) -> None:  # noqa: ANN001
        del brand

    def save_snapshot(self, snapshot) -> None:  # noqa: ANN001
        del snapshot

    def get_snapshot(self, snapshot_id):  # noqa: ANN001
        return self._snapshot if self._snapshot.id == snapshot_id else None


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


class _FakeAiPort:
    def __init__(self, payload: dict | None) -> None:
        self._payload = payload
        self.requests: list[AIRequest] = []

    def generate(self, request: AIRequest) -> AIResponse:
        self.requests.append(request)
        return AIResponse(
            provider="fake",
            model="fake",
            latency_ms=1,
            structured_payload=self._payload,
        )


def _snapshot() -> BrandSnapshot:
    return BrandSnapshot(
        id=BrandSnapshotId("snap-1"),
        brand_id=BrandId("brand-1"),
        version=1,
        language="BHS",
        locale="BHS_LATIN",
        script="LATIN",
        voice=BrandVoice(formality="friendly"),
        audiences=[Audience(id="a1", name="Adults", description="d")],
        services=[ServiceDefinition(id="s1", name="Implants", description="d")],
        visual_identity=VisualIdentity(),
        restrictions=[Restriction(description="No guarantees.")],
        approved_fact_ids=(),
        created_at=_CREATED_AT,
    )


def _brief(content_piece_count: int = 3) -> CampaignBrief:
    return CampaignBrief(
        id="brief-1",
        offer="Implants",
        goal="Book consultations",
        audience_text="Adults",
        targets=[
            CampaignTarget(
                channel="SOCIAL", platform_code="INSTAGRAM", format_code="FEED_POST"
            )
        ],
        content_piece_count=content_piece_count,
        content_language_context="BHS_LATIN",
        created_at=_CREATED_AT,
    )


def _campaign() -> Campaign:
    return Campaign(
        id=CampaignId("campaign-1"),
        brand_id=BrandId("brand-1"),
        brand_snapshot_id=BrandSnapshotId("snap-1"),
        brief_id="brief-1",
        status=CampaignStatus.DRAFT,
        created_at=_CREATED_AT,
    )


def _payload(items: list[dict]) -> dict:
    return {"campaign_theme": "Healthy smile", "items": items}


def _valid_items() -> list[dict]:
    return [
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
    ]


def _make_use_case(campaign, brief, ai_port):
    return GenerateCampaignPlan(
        _FakeCampaignRepository(campaign, brief),
        _FakeBrandRepository(_snapshot()),
        _FakePromptRepository(),
        ai_port,
        _FakeUnitOfWork(),
    )


def test_happy_path_generates_and_advances_status() -> None:
    ai_port = _FakeAiPort(_payload(_valid_items()))
    use_case = _make_use_case(_campaign(), _brief(3), ai_port)

    plan = use_case.execute(CampaignId("campaign-1"))

    assert plan.items is not None
    assert len(plan.items) == 3
    assert ai_port.requests  # AI was actually called
    # campaign status advanced to PLAN_GENERATED in the repo
    assert use_case._campaign_repo.campaign.status is CampaignStatus.PLAN_GENERATED


def test_unknown_campaign_raises() -> None:
    use_case = _make_use_case(
        _campaign(), _brief(3), _FakeAiPort(_payload(_valid_items()))
    )
    with pytest.raises(EntityNotFound):
        use_case.execute(CampaignId("missing"))


def test_invalid_schema_leaves_campaign_unchanged() -> None:
    bad_payload = _payload(_valid_items()[:2])  # 2 items, but count is 3
    ai_port = _FakeAiPort(bad_payload)
    use_case = _make_use_case(_campaign(), _brief(3), ai_port)

    with pytest.raises(ValueError):
        use_case.execute(CampaignId("campaign-1"))

    assert use_case._campaign_repo.campaign.status is CampaignStatus.DRAFT
    assert use_case._campaign_repo.plans == {}


def test_duplicate_topics_rejected() -> None:
    items = _valid_items()
    items[1]["topic"] = items[0]["topic"]  # duplicate topic
    ai_port = _FakeAiPort(_payload(items))
    use_case = _make_use_case(_campaign(), _brief(3), ai_port)

    with pytest.raises(InvariantViolation):
        use_case.execute(CampaignId("campaign-1"))

    assert use_case._campaign_repo.campaign.status is CampaignStatus.DRAFT
    assert use_case._campaign_repo.plans == {}


def test_role_diversity_rejected() -> None:
    items = [
        {
            "order": 1,
            "role": "PROBLEM",
            "topic": "Topic A",
            "goal": "g",
            "facts_needed": [],
        },
        {
            "order": 2,
            "role": "PROBLEM",
            "topic": "Topic B",
            "goal": "g",
            "facts_needed": [],
        },
    ]
    ai_port = _FakeAiPort(_payload(items))
    use_case = _make_use_case(_campaign(), _brief(2), ai_port)

    with pytest.raises(InvariantViolation):
        use_case.execute(CampaignId("campaign-1"))

    assert use_case._campaign_repo.campaign.status is CampaignStatus.DRAFT
    assert use_case._campaign_repo.plans == {}
