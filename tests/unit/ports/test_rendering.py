"""Unit tests for the rendering port (A14 dio 2, plan section 43).

Pin the dataclass shapes -- this is the "contract surface" for the
renderer and ``RenderPost``. Adding a field to ``RenderRequest`` /
``RenderResult`` without updating the plan / test is a breaking change
that the next reviewer / integrator will catch here.
"""

from __future__ import annotations

import dataclasses

from ai_campaign_studio.ports.rendering import (
    RendererPort,
    RenderRequest,
    RenderResult,
    RenderStatus,
)


def test_render_status_values_match_plan() -> None:
    """``RenderStatus`` is a StrEnum with EXACTLY three values from
    plan section 43 + 44. Adding a fourth requires an updated plan."""
    assert {s.value for s in RenderStatus} == {
        "SUCCESS",
        "LAYOUT_VALIDATION_ERROR",
        "RENDER_ERROR",
    }


def test_render_request_fields_match_plan() -> None:
    """``RenderRequest`` field set is taken verbatim from plan
    section 43. Drift here = a breaking contract change."""
    field_names = {f.name for f in dataclasses.fields(RenderRequest)}
    assert field_names == {
        "content_piece_id",
        "format",
        "layout_spec",
        "content",
        "visual_system",
        "output_path",
        "image_path",
        "logo_path",
    }


def test_render_result_fields_match_plan() -> None:
    """``RenderResult`` field set: status + output_path + warnings +
    measured_slots + render_ms. All are filled in by the renderer
    (or empty defaults for measured_slots on RENDER_ERROR)."""
    field_names = {f.name for f in dataclasses.fields(RenderResult)}
    assert field_names == {
        "status",
        "output_path",
        "warnings",
        "measured_slots",
        "render_ms",
    }


def test_render_request_is_frozen() -> None:
    """``RenderRequest`` is frozen -- the renderer is a hot path and
    accidental mutation of the request inside a renderer implementation
    would change behaviour mid-render."""
    from datetime import UTC, datetime

    import pytest

    from ai_campaign_studio.domain.common.ids import CampaignId, PostId, VisualSystemId
    from ai_campaign_studio.domain.content.entities import SocialPostPayload
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

    spec = LayoutSpec(
        primitive=LayoutPrimitive.HERO,
        image_position=ImagePosition.NONE,
        headline_position=HeadlinePosition.TOP,
        headline_scale=HeadlineScale.MEDIUM,
        overlay=Overlay.NONE,
        logo_position=LogoPosition.TOP_LEFT,
        cta_style=CtaStyle.SOLID,
        alignment=Alignment.LEFT,
        format="1080x1350",
    )
    payload = SocialPostPayload(
        headline="h", caption="c", hook="k", body="b", cta="ct",
    )
    vs = CampaignVisualSystem(
        id=VisualSystemId("vs-1"),
        campaign_id=CampaignId("c-1"),
        primary_layout_family=LayoutPrimitive.HERO,
        headline_scale=HeadlineScale.MEDIUM,
        image_treatment="", logo_rule="", cta_rule="",
        alignment=Alignment.LEFT,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    req = RenderRequest(
        content_piece_id=PostId("p-1"),
        format="1080x1350",
        layout_spec=spec,
        content=payload,
        visual_system=vs,
        output_path="/tmp/x.png",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        req.output_path = "/tmp/y.png"  # type: ignore[misc]


def test_render_result_is_frozen() -> None:
    import dataclasses

    import pytest
    res = RenderResult(
        status=RenderStatus.SUCCESS,
        output_path="/tmp/x.png",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        res.status = RenderStatus.RENDER_ERROR  # type: ignore[misc]


def test_renderer_port_is_runtime_checkable_protocol() -> None:
    """``RendererPort`` is ``@runtime_checkable`` so adapters can be
    ``isinstance``-checked (useful for future A15 export flow that
    might want to verify the renderer's API surface)."""
    from ai_campaign_studio.infrastructure.rendering import PillowRenderer
    assert isinstance(PillowRenderer(), RendererPort)
