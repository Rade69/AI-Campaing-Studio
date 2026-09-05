"""Unit tests for GenerateVisualSystem (A13, plan section 39) with fake ports."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ai_campaign_studio.application.visual.generate_visual_system import (
    GenerateVisualSystem,
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
from ai_campaign_studio.domain.common.errors import EntityNotFound, InvariantViolation
from ai_campaign_studio.domain.common.ids import (
    BrandId,
    BrandSnapshotId,
    CampaignId,
    CampaignItemId,
    CampaignPlanId,
    VisualSystemId,
)
from ai_campaign_studio.domain.content.entities import CampaignTarget
from ai_campaign_studio.domain.visual.entities import CampaignVisualSystem
from ai_campaign_studio.domain.visual.enums import LayoutPrimitive
from ai_campaign_studio.domain.visual.layout import LayoutSpec
from ai_campaign_studio.ports.ai import AIRequest, AIResponse
from ai_campaign_studio.ports.prompts import PromptDefinition

_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)

_SENTINEL = object()


class _FakeUnitOfWork:
    def __init__(self) -> None:
        self.committed = False

    def __enter__(self) -> _FakeUnitOfWork:
        return self

    def __exit__(
        self, exc_type: object, exc_value: object, traceback: object
    ) -> bool:
        return False

    def commit(self) -> None:
        self.committed = True


class _FakeCampaignRepository:
    def __init__(
        self,
        campaign: Campaign,
        brief: CampaignBrief,
        plan: CampaignPlan | None,
    ) -> None:
        self.campaign = campaign
        self.brief = brief
        self.plan = plan

    def get_campaign(self, campaign_id: CampaignId) -> Campaign | None:
        return self.campaign if self.campaign.id == campaign_id else None

    def get_brief(self, brief_id: str) -> CampaignBrief | None:
        return self.brief if self.brief.id == brief_id else None

    def get_plan(self, plan_id: CampaignPlanId) -> CampaignPlan | None:
        if self.plan is not None and self.plan.id == plan_id:
            return self.plan
        return None


class _FakeBrandRepository:
    def __init__(self, snapshot: BrandSnapshot | None) -> None:
        self._snapshot = snapshot

    def get_snapshot(self, snapshot_id: BrandSnapshotId) -> BrandSnapshot | None:
        if self._snapshot is not None and self._snapshot.id == snapshot_id:
            return self._snapshot
        return None


class _FakeVisualRepository:
    def __init__(self) -> None:
        self.saved: list[CampaignVisualSystem] = []
        self.save_count = 0

    def save_visual_system(self, system: CampaignVisualSystem) -> None:
        self.saved.append(system)
        self.save_count += 1

    def get_visual_system(
        self, visual_system_id: VisualSystemId
    ) -> CampaignVisualSystem | None:
        return next((s for s in self.saved if s.id == visual_system_id), None)


class _FakePromptRepository:
    def get(self, name: str, version: str) -> PromptDefinition:
        return PromptDefinition(
            name=name,
            version=version,
            purpose="visual_direction",
            input_contract="...",
            output_contract="...",
            language_support="EN",
            instructions="Produce a visual direction.",
        )


class _FakeAiPort:
    def __init__(self, payload: dict | None) -> None:
        self._payload = payload
        self.call_count = 0

    def generate(self, request: AIRequest) -> AIResponse:
        self.call_count += 1
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


def _brief() -> CampaignBrief:
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
        content_piece_count=3,
        content_language_context="BHS_LATIN",
        created_at=_CREATED_AT,
    )


def _campaign() -> Campaign:
    return Campaign(
        id=CampaignId("campaign-1"),
        brand_id=BrandId("brand-1"),
        brand_snapshot_id=BrandSnapshotId("snap-1"),
        brief_id="brief-1",
        status=CampaignStatus.PLAN_APPROVED,
        created_at=_CREATED_AT,
    )


def _plan(status: CampaignPlanStatus = CampaignPlanStatus.APPROVED) -> CampaignPlan:
    return CampaignPlan(
        id=CampaignPlanId("plan-1"),
        campaign_id=CampaignId("campaign-1"),
        version=1,
        status=status,
        created_at=_CREATED_AT,
        items=(
            CampaignItem(
                id=CampaignItemId("item-1"),
                order=1,
                role=CampaignRole.PROBLEM,
                topic="Cost of implants",
                goal="awareness",
                status=CampaignItemStatus.PLANNED,
            ),
        ),
    )


def _valid_payload(primitive: str = "HERO") -> dict:
    return {
        "campaign_visual_system": {
            "primary_layout_family": primitive,
            "secondary_layout_family": None,
            "headline_scale": "LARGE",
            "image_treatment": "ROUNDED",
            "logo_rule": "SHOW",
            "cta_rule": "SHOW",
            "alignment": "CENTER",
            "style": ["clean", "calm"],
        },
        "layout_spec": {
            "primitive": primitive,
            "image_position": "LEFT" if primitive == "SPLIT" else "BACKGROUND",
            "headline_position": "CENTER",
            "headline_scale": "LARGE",
            "overlay": "DARK",
            "logo_position": "TOP_LEFT",
            "cta_style": "SOLID",
            "alignment": "CENTER",
            "format": "FEED_POST",
        },
    }


def _make_use_case(
    plan: CampaignPlan | None,
    ai_port: _FakeAiPort,
    snapshot: BrandSnapshot | None | object = _SENTINEL,
) -> tuple[GenerateVisualSystem, _FakeVisualRepository]:
    if snapshot is _SENTINEL:
        snapshot = _snapshot()
    visual_repo = _FakeVisualRepository()
    use_case = GenerateVisualSystem(
        _FakeCampaignRepository(_campaign(), _brief(), plan),
        _FakeBrandRepository(snapshot),  # type: ignore[arg-type]
        visual_repo,
        _FakePromptRepository(),
        ai_port,
        _FakeUnitOfWork(),
    )
    return use_case, visual_repo


def test_happy_path_hero_persists_and_returns_layout() -> None:
    ai_port = _FakeAiPort(_valid_payload("HERO"))
    use_case, visual_repo = _make_use_case(_plan(), ai_port)

    visual_system, layout_spec = use_case.execute(CampaignPlanId("plan-1"))

    assert isinstance(visual_system, CampaignVisualSystem)
    assert isinstance(layout_spec, LayoutSpec)
    assert visual_repo.save_count == 1
    assert visual_repo.saved[0].id == visual_system.id
    # enum -> str conversion must be explicit (image_treatment/logo_rule/cta_rule)
    assert visual_system.image_treatment == "ROUNDED"
    assert visual_system.logo_rule == "SHOW"
    assert visual_system.cta_rule == "SHOW"
    assert visual_system.primary_layout_family is LayoutPrimitive.HERO
    assert visual_system.style == ("clean", "calm")
    assert layout_spec.primitive is LayoutPrimitive.HERO


def test_happy_path_split_persists_and_returns_layout() -> None:
    ai_port = _FakeAiPort(_valid_payload("SPLIT"))
    use_case, visual_repo = _make_use_case(_plan(), ai_port)

    visual_system, layout_spec = use_case.execute(CampaignPlanId("plan-1"))

    assert visual_system.primary_layout_family is LayoutPrimitive.SPLIT
    assert layout_spec.primitive is LayoutPrimitive.SPLIT
    assert layout_spec.image_position.value == "LEFT"
    assert visual_repo.save_count == 1


def test_non_approved_plan_rejected_without_ai_call() -> None:
    ai_port = _FakeAiPort(_valid_payload("HERO"))
    use_case, visual_repo = _make_use_case(
        _plan(status=CampaignPlanStatus.DRAFT), ai_port
    )

    with pytest.raises(InvariantViolation):
        use_case.execute(CampaignPlanId("plan-1"))

    assert ai_port.call_count == 0
    assert visual_repo.save_count == 0


@pytest.mark.parametrize("missing", ["plan", "campaign", "brief", "snapshot"])
def test_missing_entities_raise_entity_not_found(missing: str) -> None:
    ai_port = _FakeAiPort(_valid_payload("HERO"))
    if missing == "plan":
        use_case, _ = _make_use_case(None, ai_port)
        plan_id = CampaignPlanId("missing-plan")
        expected = "campaign plan missing-plan"
    elif missing == "campaign":
        plan = CampaignPlan(
            id=CampaignPlanId("plan-1"),
            campaign_id=CampaignId("missing-campaign"),
            version=1,
            status=CampaignPlanStatus.APPROVED,
            created_at=_CREATED_AT,
            items=(),
        )
        use_case, _ = _make_use_case(plan, ai_port)
        plan_id = CampaignPlanId("plan-1")
        expected = "campaign missing-campaign"
    elif missing == "brief":
        # campaign is FOUND, but its brief_id points at a brief the repo
        # does not hold — this exercises the get_brief() is None path.
        campaign_without_brief = Campaign(
            id=CampaignId("campaign-1"),
            brand_id=BrandId("brand-1"),
            brand_snapshot_id=BrandSnapshotId("snap-1"),
            brief_id="missing-brief",
            status=CampaignStatus.PLAN_APPROVED,
            created_at=_CREATED_AT,
        )
        visual_repo = _FakeVisualRepository()
        use_case = GenerateVisualSystem(
            _FakeCampaignRepository(campaign_without_brief, _brief(), _plan()),
            _FakeBrandRepository(_snapshot()),
            visual_repo,
            _FakePromptRepository(),
            ai_port,
            _FakeUnitOfWork(),
        )
        plan_id = CampaignPlanId("plan-1")
        expected = "brief missing-brief"
    else:  # snapshot
        use_case, _ = _make_use_case(_plan(), ai_port, snapshot=None)
        plan_id = CampaignPlanId("plan-1")
        expected = "snapshot snap-1"

    with pytest.raises(EntityNotFound) as exc_info:
        use_case.execute(plan_id)
    assert expected in str(exc_info.value).lower()
    assert ai_port.call_count == 0


def test_missing_structured_payload_raises_invariant() -> None:
    ai_port = _FakeAiPort(None)
    use_case, _ = _make_use_case(_plan(), ai_port)

    with pytest.raises(InvariantViolation):
        use_case.execute(CampaignPlanId("plan-1"))


def test_invalid_enum_value_raises_validation_error() -> None:
    payload = _valid_payload("HERO")
    payload["campaign_visual_system"]["primary_layout_family"] = "DIAGONAL"
    ai_port = _FakeAiPort(payload)
    use_case, visual_repo = _make_use_case(_plan(), ai_port)

    with pytest.raises(ValidationError):
        use_case.execute(CampaignPlanId("plan-1"))

    assert visual_repo.save_count == 0


def test_disallowed_style_value_raises_invariant() -> None:
    payload = _valid_payload("HERO")
    payload["campaign_visual_system"]["style"] = ["clean", "aggressive"]
    ai_port = _FakeAiPort(payload)
    use_case, visual_repo = _make_use_case(_plan(), ai_port)

    with pytest.raises(InvariantViolation) as exc_info:
        use_case.execute(CampaignPlanId("plan-1"))

    assert "aggressive" in str(exc_info.value)
    assert visual_repo.save_count == 0
