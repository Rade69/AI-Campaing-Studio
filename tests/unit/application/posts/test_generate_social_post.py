"""Unit tests for GenerateSocialPost (A11) with fake ports."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ai_campaign_studio.application.posts.generate_social_post import (
    GenerateSocialPost,
)
from ai_campaign_studio.domain.brand.entities import BrandSnapshot
from ai_campaign_studio.domain.brand.value_objects import (
    Audience,
    BrandVoice,
    Restriction,
    ServiceDefinition,
    VisualIdentity,
)
from ai_campaign_studio.domain.campaign.entities import (
    Campaign,
    CampaignItem,
    CampaignPlan,
)
from ai_campaign_studio.domain.campaign.enums import (
    CampaignItemStatus,
    CampaignPlanStatus,
    CampaignStatus,
)
from ai_campaign_studio.domain.campaign.roles import CampaignRole
from ai_campaign_studio.domain.common.errors import EntityNotFound
from ai_campaign_studio.domain.common.ids import (
    BrandId,
    BrandSnapshotId,
    CampaignId,
    CampaignItemId,
    CampaignPlanId,
    FactId,
)
from ai_campaign_studio.domain.content.entities import CampaignTarget
from ai_campaign_studio.domain.content.enums import ContentStatus
from ai_campaign_studio.domain.facts.entities import ApprovedFact, SourceReference
from ai_campaign_studio.domain.facts.enums import FactStatus
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
    def __init__(self, campaign: Campaign, plan: CampaignPlan) -> None:
        self._campaign = campaign
        self._plan = plan

    def get_campaign(self, campaign_id):  # noqa: ANN001
        return self._campaign if self._campaign.id == campaign_id else None

    def get_plan(self, plan_id):  # noqa: ANN001
        return self._plan if self._plan.id == plan_id else None

    def save_brief(self, brief) -> None:  # noqa: ANN001
        del brief

    def get_brief(self, brief_id):  # noqa: ANN001
        del brief_id
        return None

    def save_campaign(self, campaign) -> None:  # noqa: ANN001
        del campaign

    def save_plan(self, plan) -> None:  # noqa: ANN001
        del plan


class _FakeBrandRepository:
    def __init__(self, snapshot: BrandSnapshot) -> None:
        self._snapshot = snapshot

    def save_brand(self, brand) -> None:  # noqa: ANN001
        del brand

    def save_snapshot(self, snapshot) -> None:  # noqa: ANN001
        del snapshot

    def get_snapshot(self, snapshot_id):  # noqa: ANN001
        return self._snapshot if self._snapshot.id == snapshot_id else None


class _FakeFactRepository:
    def __init__(self, facts: tuple[ApprovedFact, ...]) -> None:
        self._facts = {fact.id: fact for fact in facts}

    def get_fact(self, fact_id):  # noqa: ANN001
        return self._facts.get(fact_id)

    def save_fact(self, fact) -> None:  # noqa: ANN001
        del fact

    def list_snapshot_facts(self, snapshot_id):  # noqa: ANN001
        del snapshot_id
        return tuple(self._facts.values())


class _FakeContentRepository:
    def __init__(self) -> None:
        self.saved: list = []

    def save_content_piece(self, content_piece) -> None:  # noqa: ANN001
        self.saved.append(content_piece)

    def get_content_piece(self, content_piece_id):  # noqa: ANN001
        del content_piece_id
        return None

    def list_campaign_content(self, campaign_id):  # noqa: ANN001
        del campaign_id
        return ()


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
    def __init__(self, payload: dict | None) -> None:
        self._payload = payload

    def generate(self, request: AIRequest) -> AIResponse:
        del request
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
        approved_fact_ids=(FactId("fact-1"),),
        created_at=_CREATED_AT,
    )


def _campaign() -> Campaign:
    return Campaign(
        id=CampaignId("campaign-1"),
        brand_id=BrandId("brand-1"),
        brand_snapshot_id=BrandSnapshotId("snap-1"),
        brief_id="brief-1",
        status=CampaignStatus.PLAN_GENERATED,
        created_at=_CREATED_AT,
    )


def _item() -> CampaignItem:
    return CampaignItem(
        id=CampaignItemId("item-1"),
        order=1,
        role=CampaignRole.PROBLEM,
        topic="Cost",
        goal="Awareness",
        status=CampaignItemStatus.PLANNED,
        facts_needed=("implant",),
    )


def _plan() -> CampaignPlan:
    return CampaignPlan(
        id=CampaignPlanId("plan-1"),
        campaign_id=CampaignId("campaign-1"),
        version=1,
        status=CampaignPlanStatus.DRAFT,
        created_at=_CREATED_AT,
        items=[_item()],
    )


def _fact() -> ApprovedFact:
    return ApprovedFact(
        id=FactId("fact-1"),
        logical_fact_id="logical-1",
        version=1,
        content="We offer dental implants",
        source_ref=SourceReference(source_type="fixture", uri="fixture://x"),
        status=FactStatus.APPROVED,
        created_at=_CREATED_AT,
    )


def _target() -> CampaignTarget:
    return CampaignTarget(
        channel="SOCIAL", platform_code="INSTAGRAM", format_code="FEED_POST"
    )


def _valid_output() -> dict:
    return {
        "headline": "H",
        "caption": "C",
        "hook": "Hook",
        "body": "Body",
        "cta": "CTA",
        "hashtags": [],
        "claims": [
            {"text": "We offer implants", "type": "FACT", "fact_ids": ["fact-1"]},
            {"text": "Book now", "type": "CTA", "fact_ids": []},
        ],
    }


def _make_use_case(ai_payload: dict | None, content_repo=None):
    return GenerateSocialPost(
        _FakeCampaignRepository(_campaign(), _plan()),
        _FakeBrandRepository(_snapshot()),
        _FakeFactRepository((_fact(),)),
        content_repo if content_repo is not None else _FakeContentRepository(),
        _FakePromptRepository(),
        _FakeAiPort(ai_payload),
        _FakeUnitOfWork(),
    )


def test_happy_path_generates_and_persists() -> None:
    content_repo = _FakeContentRepository()
    use_case = _make_use_case(_valid_output(), content_repo)

    piece = use_case.execute(
        CampaignId("campaign-1"),
        CampaignPlanId("plan-1"),
        CampaignItemId("item-1"),
        _target(),
    )

    assert piece.status is ContentStatus.DRAFT
    assert piece.payload is not None
    assert piece.payload.headline == "H"
    assert len(piece.claims) == 2
    assert content_repo.saved == [piece]


def test_prohibited_claim_yields_needs_review() -> None:
    output = _valid_output()
    # Fact-backed claim that still contains a prohibited term -> PROHIBITED.
    output["claims"][0]["text"] = "Mi smo najbolji izbor"
    output["claims"][0]["fact_ids"] = ["fact-1"]
    use_case = _make_use_case(output)

    piece = use_case.execute(
        CampaignId("campaign-1"),
        CampaignPlanId("plan-1"),
        CampaignItemId("item-1"),
        _target(),
    )

    assert piece.status is ContentStatus.NEEDS_REVIEW


def test_unsupported_claim_yields_needs_review() -> None:
    output = _valid_output()
    output["claims"][0]["fact_ids"] = ["fact-not-allowed"]  # not in allowed set
    use_case = _make_use_case(output)

    piece = use_case.execute(
        CampaignId("campaign-1"),
        CampaignPlanId("plan-1"),
        CampaignItemId("item-1"),
        _target(),
    )

    assert piece.status is ContentStatus.NEEDS_REVIEW


def test_invalid_output_raises_before_persistence() -> None:
    content_repo = _FakeContentRepository()
    bad_output = _valid_output()
    del bad_output["headline"]  # missing required field
    use_case = _make_use_case(bad_output, content_repo)

    with pytest.raises(ValidationError):
        use_case.execute(
            CampaignId("campaign-1"),
            CampaignPlanId("plan-1"),
            CampaignItemId("item-1"),
            _target(),
        )

    assert content_repo.saved == []


@pytest.mark.parametrize(
    ("campaign_id", "plan_id", "item_id"),
    [
        (CampaignId("missing"), CampaignPlanId("plan-1"), CampaignItemId("item-1")),
        (CampaignId("campaign-1"), CampaignPlanId("missing"), CampaignItemId("item-1")),
        (CampaignId("campaign-1"), CampaignPlanId("plan-1"), CampaignItemId("missing")),
    ],
)
def test_unknown_entities_raise(campaign_id, plan_id, item_id) -> None:  # noqa: ANN001
    use_case = _make_use_case(_valid_output())
    with pytest.raises(EntityNotFound):
        use_case.execute(campaign_id, plan_id, item_id, _target())
