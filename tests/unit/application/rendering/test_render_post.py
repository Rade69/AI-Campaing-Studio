"""Unit tests for ``RenderPost`` use-case (A14 dio 2).

Fake ports keep this test in the unit tier. The integration tier
(``tests/integration/application/rendering/test_render_post_integration.py``)
runs the full pipeline against a real SQLite + the production
``PillowRenderer``.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ai_campaign_studio.application.rendering import RenderPost
from ai_campaign_studio.domain.campaign.entities import Campaign
from ai_campaign_studio.domain.campaign.enums import CampaignStatus
from ai_campaign_studio.domain.common.errors import EntityNotFound, InvariantViolation
from ai_campaign_studio.domain.common.ids import (
    BrandId,
    BrandSnapshotId,
    CampaignId,
    PostId,
    VisualSystemId,
)
from ai_campaign_studio.domain.content.entities import (
    CampaignTarget,
    ContentPiece,
    SocialPostPayload,
)
from ai_campaign_studio.domain.content.enums import (
    ContentPayloadType,
    ContentStatus,
)
from ai_campaign_studio.domain.visual.entities import CampaignVisualSystem
from ai_campaign_studio.domain.visual.enums import (
    Alignment,
    CtaStyle,
    HeadlinePosition,
    HeadlineScale,
    ImagePosition,
    LayoutPrimitive,
    LogoPosition,
    Overlay,
)
from ai_campaign_studio.domain.visual.layout import LayoutSpec
from ai_campaign_studio.ports.rendering import (
    RenderRequest,
    RenderResult,
    RenderStatus,
)


def _dt() -> datetime:
    return datetime(2026, 1, 1, tzinfo=UTC)


def _layout() -> LayoutSpec:
    return LayoutSpec(
        primitive=LayoutPrimitive.HERO,
        image_position=ImagePosition.NONE,
        headline_position=HeadlinePosition.TOP,
        headline_scale=HeadlineScale.MEDIUM,
        overlay=Overlay.NONE,
        logo_position=LogoPosition.TOP_LEFT,
        cta_style=CtaStyle.SOLID,
        alignment=Alignment.LEFT,
        format="200x200",
    )


def _payload() -> SocialPostPayload:
    return SocialPostPayload(
        headline="h", caption="c", hook="k", body="b", cta="ct",
    )


def _content_piece() -> ContentPiece:
    return ContentPiece(
        id=PostId("p-1"),
        campaign_item_id="ci-1",
        target=CampaignTarget(
            channel="SOCIAL", platform_code="INSTAGRAM", format_code="FEED_POST",
        ),
        payload_type=ContentPayloadType.SOCIAL_POST,
        status=ContentStatus.APPROVED,
        brand_snapshot_id=BrandSnapshotId("bs-1"),
        created_at=_dt(),
        updated_at=_dt(),
        payload=_payload(),
    )


def _visual_system() -> CampaignVisualSystem:
    return CampaignVisualSystem(
        id=VisualSystemId("vs-1"),
        campaign_id=CampaignId("c-1"),
        primary_layout_family=LayoutPrimitive.HERO,
        headline_scale=HeadlineScale.MEDIUM,
        image_treatment="",
        logo_rule="",
        cta_rule="",
        alignment=Alignment.LEFT,
        created_at=_dt(),
    )


def _campaign() -> Campaign:
    return Campaign(
        id=CampaignId("c-1"),
        brand_id=BrandId("b-1"),
        brand_snapshot_id=BrandSnapshotId("bs-1"),
        brief_id="br-1",
        status=CampaignStatus.DRAFT,
        created_at=_dt(),
    )


class _FakeContentRepo:
    def __init__(self, piece: ContentPiece | None = None) -> None:
        self._piece = piece or _content_piece()
        self.calls = 0

    def get_content_piece(self, content_piece_id: PostId) -> Any:
        self.calls += 1
        if content_piece_id == self._piece.id:
            return self._piece
        return None


class _FakeCampaignRepo:
    def get_campaign(self, campaign_id: CampaignId) -> Any:
        if campaign_id == CampaignId("c-1"):
            return _campaign()
        return None


# Sentinel objects to distinguish "default fixture" from "explicit
# None" in ``_FakeVisualRepo``. Tests that want the lookup to return
# None pass one of these explicitly.
_NO_LAYOUT = object()
_NO_VS = object()


class _FakeVisualRepo:
    def __init__(
        self,
        layout: LayoutSpec | None | object = _NO_LAYOUT,
        vs: CampaignVisualSystem | None | object = _NO_VS,
    ) -> None:
        # Default state: both lookups return None. Tests that want a
        # valid value pass the fixture explicitly via ``_layout()`` /
        # ``_visual_system()``. Tests that want the lookup to return
        # None pass ``_NO_LAYOUT`` / ``_NO_VS`` explicitly (which is
        # equivalent to the default but documents intent).
        self._layout: LayoutSpec | None = (
            layout if layout is not _NO_LAYOUT else None  # type: ignore[assignment]
        )
        self._vs: CampaignVisualSystem | None = (
            vs if vs is not _NO_VS else None  # type: ignore[assignment]
        )
        self.layout_calls: list[PostId] = []
        self.vs_calls: list[VisualSystemId] = []

    def get_layout_spec_by_content_piece(self, content_piece_id: PostId) -> Any:
        self.layout_calls.append(content_piece_id)
        if content_piece_id == PostId("p-1") and self._layout is not None:
            return self._layout
        return None

    def get_visual_system(self, visual_system_id: VisualSystemId) -> Any:
        self.vs_calls.append(visual_system_id)
        if visual_system_id == VisualSystemId("vs-1") and self._vs is not None:
            return self._vs
        return None


class _RecordingRenderer:
    """Fake ``RendererPort`` that records the request it was called with
    and returns a configurable result (defaults to SUCCESS)."""

    def __init__(
        self, status: RenderStatus = RenderStatus.SUCCESS,
        result_output_path: str | None = "/tmp/recorded.png",
    ) -> None:
        self.requests: list[RenderRequest] = []
        self._status = status
        self._output = result_output_path

    def render(self, request: RenderRequest) -> RenderResult:
        self.requests.append(request)
        warnings: tuple[str, ...] = (
            ("recorded",)
            if self._status is RenderStatus.LAYOUT_VALIDATION_ERROR
            else ()
        )
        return RenderResult(
            status=self._status,
            output_path=self._output,
            warnings=warnings,
            render_ms=12.34,
        )


@pytest.fixture
def renderer() -> _RecordingRenderer:
    return _RecordingRenderer()


@pytest.fixture
def use_case(renderer: _RecordingRenderer):
    return RenderPost(
        content_repo=_FakeContentRepo(),
        campaign_repo=_FakeCampaignRepo(),
        visual_repo=_FakeVisualRepo(layout=_layout(), vs=_visual_system()),
        renderer=renderer,
    )


def test_happy_path_returns_renderer_result_and_does_not_persist(
    use_case: RenderPost, renderer: _RecordingRenderer, tmp_path: Path
) -> None:
    out = str(tmp_path / "out.png")
    result = use_case.execute(
        PostId("p-1"),
        VisualSystemId("vs-1"),
        out,
    )
    # Returns the renderer's result unchanged.
    assert result.status is RenderStatus.SUCCESS
    assert result.output_path == "/tmp/recorded.png"
    # Renderer was called exactly once with the right inputs.
    assert len(renderer.requests) == 1
    req = renderer.requests[0]
    assert req.content_piece_id == PostId("p-1")
    assert req.visual_system.id == VisualSystemId("vs-1")
    assert req.format == "200x200"   # taken from the layout spec
    assert req.layout_spec.primitive is LayoutPrimitive.HERO
    assert req.content.headline == "h"
    # Slice 1 has no image pipeline -> image_path is always None.
    assert req.image_path is None
    # BrandRepositoryPort is NOT in the constructor signature (per the
    # A14 dio 2 contract) -> logo_path is None even though a brand
    # snapshot could be located. The renderer silently skips the logo.
    assert req.logo_path is None
    # The output path passed by the caller is the renderer's
    # output_path, NOT the renderer's recorded path. Verify we did
    # not leak / rewrite the caller's argument.
    assert req.output_path == out


def test_missing_content_piece_raises_entity_not_found(
    renderer: _RecordingRenderer,
) -> None:
    repo = _FakeContentRepo()  # default piece
    repo._piece = dataclasses.replace(repo._piece, id=PostId("other"))
    use_case = RenderPost(
        content_repo=repo,
        campaign_repo=_FakeCampaignRepo(),
        visual_repo=_FakeVisualRepo(),
        renderer=renderer,
    )
    with pytest.raises(EntityNotFound):
        use_case.execute(
            PostId("p-1"),
            VisualSystemId("vs-1"),
            "/tmp/x.png",
        )
    # Renderer was NOT called.
    assert renderer.requests == []


def test_missing_layout_spec_raises_entity_not_found(
    renderer: _RecordingRenderer,
) -> None:
    repo = _FakeVisualRepo(layout=_NO_LAYOUT, vs=_visual_system())
    use_case = RenderPost(
        content_repo=_FakeContentRepo(),
        campaign_repo=_FakeCampaignRepo(),
        visual_repo=repo,
        renderer=renderer,
    )
    with pytest.raises(EntityNotFound):
        use_case.execute(
            PostId("p-1"),
            VisualSystemId("vs-1"),
            "/tmp/x.png",
        )
    assert renderer.requests == []


def test_missing_visual_system_raises_entity_not_found(
    renderer: _RecordingRenderer,
) -> None:
    repo = _FakeVisualRepo(layout=_layout(), vs=_NO_VS)
    use_case = RenderPost(
        content_repo=_FakeContentRepo(),
        campaign_repo=_FakeCampaignRepo(),
        visual_repo=repo,
        renderer=renderer,
    )
    with pytest.raises(EntityNotFound):
        use_case.execute(
            PostId("p-1"),
            VisualSystemId("vs-1"),
            "/tmp/x.png",
        )
    assert renderer.requests == []


def test_content_piece_with_no_payload_raises_invariant_violation(
    renderer: _RecordingRenderer,
) -> None:
    """A post whose payload is None cannot be rendered (the renderer
    would receive ``None`` for a typed ``SocialPostPayload`` field).
    The use-case raises ``InvariantViolation`` BEFORE calling the
    renderer."""
    piece = _content_piece()
    piece = dataclasses.replace(piece, payload=None, status=ContentStatus.PLANNED)
    repo = _FakeContentRepo(piece=piece)
    use_case = RenderPost(
        content_repo=repo,
        campaign_repo=_FakeCampaignRepo(),
        visual_repo=_FakeVisualRepo(),
        renderer=renderer,
    )
    with pytest.raises(InvariantViolation):
        use_case.execute(
            PostId("p-1"),
            VisualSystemId("vs-1"),
            "/tmp/x.png",
        )
    assert renderer.requests == []


def test_does_not_persist_anything(
    renderer: _RecordingRenderer, tmp_path: Path
) -> None:
    """``RenderPost`` is a pure orchestrator. It does NOT write to any
    repository. We assert that the fake repos received no save /
    persist calls."""
    content_repo = _FakeContentRepo()
    visual_repo = _FakeVisualRepo(layout=_layout(), vs=_visual_system())
    use_case = RenderPost(
        content_repo=content_repo,
        campaign_repo=_FakeCampaignRepo(),
        visual_repo=visual_repo,
        renderer=renderer,
    )
    use_case.execute(PostId("p-1"), VisualSystemId("vs-1"), str(tmp_path / "x.png"))
    # Fakes have no save_* methods by construction. We just verify the
    # recorded read calls match the expected lookup sequence.
    assert content_repo.calls == 1
    assert visual_repo.layout_calls == [PostId("p-1")]
    assert visual_repo.vs_calls == [VisualSystemId("vs-1")]


def test_renderer_validation_warning_propagates_to_caller(
    tmp_path: Path,
) -> None:
    """When the renderer returns LAYOUT_VALIDATION_ERROR, the use-case
    passes the result through unchanged -- the application layer is
    the right place for the future SHORTEN_HEADLINE action, NOT here."""
    renderer = _RecordingRenderer(status=RenderStatus.LAYOUT_VALIDATION_ERROR)
    use_case = RenderPost(
        content_repo=_FakeContentRepo(),
        campaign_repo=_FakeCampaignRepo(),
        visual_repo=_FakeVisualRepo(layout=_layout(), vs=_visual_system()),
        renderer=renderer,
    )
    result = use_case.execute(
        PostId("p-1"),
        VisualSystemId("vs-1"),
        str(tmp_path / "x.png"),
    )
    assert result.status is RenderStatus.LAYOUT_VALIDATION_ERROR
    assert "recorded" in result.warnings
