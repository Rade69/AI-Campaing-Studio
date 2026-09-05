"""Unit tests for PlanPostLayout (A13 dio 2b) with fake ports."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ai_campaign_studio.application.visual.plan_post_layout import PlanPostLayout
from ai_campaign_studio.domain.campaign.entities import CampaignItem, CampaignPlan
from ai_campaign_studio.domain.campaign.enums import (
    CampaignItemStatus,
    CampaignPlanStatus,
)
from ai_campaign_studio.domain.campaign.roles import CampaignRole
from ai_campaign_studio.domain.common.errors import EntityNotFound, InvariantViolation
from ai_campaign_studio.domain.common.ids import (
    BrandSnapshotId,
    CampaignId,
    CampaignItemId,
    CampaignPlanId,
    PostId,
    VisualSystemId,
)
from ai_campaign_studio.domain.content.entities import (
    CampaignTarget,
    ContentPiece,
    SocialPostPayload,
)
from ai_campaign_studio.domain.content.enums import ContentPayloadType, ContentStatus
from ai_campaign_studio.domain.visual.entities import CampaignVisualSystem
from ai_campaign_studio.domain.visual.enums import (
    Alignment,
    HeadlineScale,
    LayoutPrimitive,
)
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


class _FakeContentRepository:
    def __init__(self, piece: ContentPiece | None) -> None:
        self._piece = piece

    def get_content_piece(self, content_piece_id):  # noqa: ANN001
        if self._piece is None:
            return None
        return self._piece if self._piece.id == content_piece_id else None

    def save_content_piece(self, piece) -> None:  # noqa: ANN001
        del piece

    def list_campaign_content(self, campaign_id):  # noqa: ANN001
        del campaign_id
        return ()


class _FakeVisualRepository:
    def __init__(self, visual_system: CampaignVisualSystem | None) -> None:
        self._visual_system = visual_system
        self.saved: list = []

    def get_visual_system(self, visual_system_id):  # noqa: ANN001
        return self._visual_system

    def save_visual_system(self, system) -> None:  # noqa: ANN001
        del system

    def save_layout_spec(self, layout_spec) -> None:  # noqa: ANN001
        self.saved.append(layout_spec)

    def get_layout_spec(self, layout_spec_id):  # noqa: ANN001
        del layout_spec_id
        return None


class _FakeCampaignRepository:
    def __init__(self, plan: CampaignPlan | None) -> None:
        self._plan = plan

    def get_plan(self, plan_id):  # noqa: ANN001
        return self._plan

    def get_campaign(self, campaign_id):  # noqa: ANN001
        del campaign_id
        return None


class _FakePromptRepository:
    def get(self, name: str, version: str) -> PromptDefinition:
        return PromptDefinition(
            name=name,
            version=version,
            purpose="post_layout",
            input_contract="...",
            output_contract="...",
            language_support="EN",
            instructions="Choose a layout.",
        )


class _FakeAiPort:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.calls: list[AIRequest] = []

    def generate(self, request: AIRequest) -> AIResponse:
        self.calls.append(request)
        return AIResponse(
            provider="fake",
            model="fake",
            latency_ms=1,
            structured_payload=self._payload,
        )


def _payload(headline: str = "Short headline", cta: str = "CTA") -> SocialPostPayload:
    return SocialPostPayload(
        headline=headline, caption="", hook="", body="", cta=cta
    )


def _piece(payload: SocialPostPayload | None) -> ContentPiece:
    return ContentPiece(
        id=PostId("post-1"),
        campaign_item_id=CampaignItemId("item-1"),
        target=CampaignTarget(
            channel="SOCIAL", platform_code="INSTAGRAM", format_code="FEED_POST"
        ),
        payload_type=ContentPayloadType.SOCIAL_POST,
        status=ContentStatus.DRAFT,
        brand_snapshot_id=BrandSnapshotId("snap-1"),
        created_at=_CREATED_AT,
        updated_at=_CREATED_AT,
        payload=payload,
    )


def _visual_system(
    primary: LayoutPrimitive = LayoutPrimitive.HERO,
    secondary: LayoutPrimitive | None = None,
) -> CampaignVisualSystem:
    return CampaignVisualSystem(
        id=VisualSystemId("vs-1"),
        campaign_id=CampaignId("campaign-1"),
        primary_layout_family=primary,
        secondary_layout_family=secondary,
        headline_scale=HeadlineScale.LARGE,
        image_treatment="none",
        logo_rule="show",
        cta_rule="show",
        alignment=Alignment.CENTER,
        created_at=_CREATED_AT,
    )


def _plan(item_id: str = "item-1") -> CampaignPlan:
    item = CampaignItem(
        id=CampaignItemId(item_id),
        order=1,
        role=CampaignRole.PROBLEM,
        topic="Cost",
        goal="Awareness",
        status=CampaignItemStatus.PLANNED,
    )
    return CampaignPlan(
        id=CampaignPlanId("plan-1"),
        campaign_id=CampaignId("campaign-1"),
        version=1,
        status=CampaignPlanStatus.APPROVED,
        created_at=_CREATED_AT,
        items=[item],
    )


def _layout_payload(primitive: str = "HERO", format_: str = "999x999") -> dict:
    return {
        "primitive": primitive,
        "image_position": "BACKGROUND",
        "headline_position": "CENTER",
        "headline_scale": "LARGE",
        "overlay": "DARK",
        "logo_position": "TOP_LEFT",
        "cta_style": "SOLID",
        "alignment": "CENTER",
        "format": format_,
    }


def _make_use_case(
    piece: ContentPiece | None,
    visual_system: CampaignVisualSystem | None,
    plan: CampaignPlan | None,
    ai_payload: dict,
) -> tuple[PlanPostLayout, _FakeVisualRepository, _FakeAiPort]:
    content_repo = _FakeContentRepository(piece)
    visual_repo = _FakeVisualRepository(visual_system)
    campaign_repo = _FakeCampaignRepository(plan)
    ai_port = _FakeAiPort(ai_payload)
    use_case = PlanPostLayout(
        campaign_repo,
        content_repo,
        visual_repo,
        _FakePromptRepository(),
        ai_port,
        _FakeUnitOfWork(),
    )
    return use_case, visual_repo, ai_port


def test_happy_path_persists_valid_layout_with_forced_format() -> None:
    use_case, visual_repo, _ = _make_use_case(
        _piece(_payload()), _visual_system(), _plan(),
        _layout_payload(primitive="HERO", format_="999x999"),
    )

    layout = use_case.execute(
        PostId("post-1"), VisualSystemId("vs-1"), CampaignPlanId("plan-1")
    )

    assert len(visual_repo.saved) == 1
    assert layout.validation_status == "VALID"
    assert layout.format == "1080x1350"  # AI returned "999x999" but overridden


def test_secondary_primitive_allowed() -> None:
    use_case, visual_repo, _ = _make_use_case(
        _piece(_payload()),
        _visual_system(primary=LayoutPrimitive.HERO, secondary=LayoutPrimitive.SPLIT),
        _plan(),
        _layout_payload(primitive="SPLIT"),
    )

    layout = use_case.execute(
        PostId("post-1"), VisualSystemId("vs-1"), CampaignPlanId("plan-1")
    )

    assert len(visual_repo.saved) == 1
    assert layout.primitive is LayoutPrimitive.SPLIT


def test_primitive_outside_campaign_set_rejected() -> None:
    use_case, visual_repo, _ = _make_use_case(
        _piece(_payload()), _visual_system(), _plan(),
        _layout_payload(primitive="SPLIT"),
    )

    with pytest.raises(InvariantViolation):
        use_case.execute(
            PostId("post-1"), VisualSystemId("vs-1"), CampaignPlanId("plan-1")
        )

    assert visual_repo.saved == []


def test_long_headline_persists_invalid_not_fatal() -> None:
    use_case, visual_repo, _ = _make_use_case(
        _piece(_payload(headline="x" * 56)),
        _visual_system(),
        _plan(),
        _layout_payload(primitive="HERO"),
    )

    layout = use_case.execute(
        PostId("post-1"), VisualSystemId("vs-1"), CampaignPlanId("plan-1")
    )

    assert len(visual_repo.saved) == 1
    assert layout.validation_status == "INVALID"


def test_missing_payload_raises_without_ai_call() -> None:
    use_case, _, ai_port = _make_use_case(
        _piece(None), _visual_system(), _plan(), _layout_payload()
    )

    with pytest.raises(InvariantViolation):
        use_case.execute(
            PostId("post-1"), VisualSystemId("vs-1"), CampaignPlanId("plan-1")
        )

    assert ai_port.calls == []


def test_missing_content_piece_raises() -> None:
    use_case, _, _ = _make_use_case(
        None, _visual_system(), _plan(), _layout_payload()
    )

    with pytest.raises(EntityNotFound):
        use_case.execute(
            PostId("post-1"), VisualSystemId("vs-1"), CampaignPlanId("plan-1")
        )


def test_missing_visual_system_raises() -> None:
    use_case, _, _ = _make_use_case(
        _piece(_payload()), None, _plan(), _layout_payload()
    )

    with pytest.raises(EntityNotFound):
        use_case.execute(
            PostId("post-1"), VisualSystemId("vs-1"), CampaignPlanId("plan-1")
        )


def test_missing_plan_raises() -> None:
    use_case, _, _ = _make_use_case(
        _piece(_payload()), _visual_system(), None, _layout_payload()
    )

    with pytest.raises(EntityNotFound):
        use_case.execute(
            PostId("post-1"), VisualSystemId("vs-1"), CampaignPlanId("plan-1")
        )


def test_item_not_in_plan_raises() -> None:
    use_case, _, _ = _make_use_case(
        _piece(_payload()), _visual_system(), _plan(item_id="item-other"),
        _layout_payload(),
    )

    with pytest.raises(EntityNotFound):
        use_case.execute(
            PostId("post-1"), VisualSystemId("vs-1"), CampaignPlanId("plan-1")
        )


def test_invalid_enum_value_raises_validation_error() -> None:
    payload = _layout_payload()
    payload["primitive"] = "NOT_A_REAL_PRIMITIVE"
    use_case, _, _ = _make_use_case(
        _piece(_payload()), _visual_system(), _plan(), payload
    )

    with pytest.raises(ValidationError):
        use_case.execute(
            PostId("post-1"), VisualSystemId("vs-1"), CampaignPlanId("plan-1")
        )
