"""Renderer port (A14 dio 2, plan section 43).

Owns the framework-neutral ``RendererPort`` interface that takes a fully-
hydrated ``RenderRequest`` and produces a rendered PNG at a known path.
The renderer does NOT know about repositories, content pieces, or
campaigns — everything it needs arrives in the request (plan doslovno:
"Renderer ne zna Campaign repository. Dobije sve kroz request.").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol, runtime_checkable

from ai_campaign_studio.domain.common.ids import PostId
from ai_campaign_studio.domain.content.entities import SocialPostPayload
from ai_campaign_studio.domain.visual.entities import CampaignVisualSystem
from ai_campaign_studio.domain.visual.layout import LayoutSpec


class RenderStatus(StrEnum):
    """Outcome of a single ``RendererPort.render`` call.

    The renderer always writes the PNG to ``request.output_path`` (even on
    LAYOUT_VALIDATION_ERROR or RENDER_ERROR) so the caller can decide what
    to do with the artifact — typically, trigger a downstream
    ``SHORTEN_HEADLINE`` action instead of a full re-plan. This mirrors
    the plan-section 44 decision that we do NOT regenerate the whole
    pipeline on a layout warning.
    """

    SUCCESS = "SUCCESS"
    LAYOUT_VALIDATION_ERROR = "LAYOUT_VALIDATION_ERROR"
    RENDER_ERROR = "RENDER_ERROR"


@dataclass(frozen=True)
class RenderRequest:
    """Everything the renderer needs to produce one PNG.

    Field set is taken verbatim from plan section 43 — no additions, no
    removals. ``image_path`` and ``logo_path`` are optional because Slice-1
    has no image-upload pipeline (image is always ``None``) and the brand
    snapshot is not threaded into ``RenderPost`` (so the caller passes
    ``None`` for logo unless it has the brand snapshot in hand).
    ``output_path`` is the only required path — the renderer creates the
    parent directory if needed.
    """

    content_piece_id: PostId
    format: str
    layout_spec: LayoutSpec
    content: SocialPostPayload
    visual_system: CampaignVisualSystem
    output_path: str
    image_path: str | None = None
    logo_path: str | None = None


@dataclass(frozen=True)
class RenderResult:
    """Outcome of one render call.

    ``measured_slots`` carries per-slot pixel measurements (width, height)
    that the caller can use to drive follow-up actions like
    SHORTEN_HEADLINE (which lives in the application layer, not here).
    Empty dict on RENDER_ERROR; always populated on SUCCESS /
    LAYOUT_VALIDATION_ERROR for the headline slot at minimum.
    """

    status: RenderStatus
    output_path: str | None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    measured_slots: dict[str, dict[str, float]] = field(default_factory=dict)
    render_ms: float = 0.0


@runtime_checkable
class RendererPort(Protocol):
    """Render one ``RenderRequest`` to a PNG.

    Implementations MUST be deterministic: same input -> same output
    bytes (modulo the measured wall-clock ``render_ms``). Implementations
    MUST NOT raise; every error path returns a ``RenderResult`` with a
    non-SUCCESS status and a human-readable message in ``warnings``.
    """

    def render(self, request: RenderRequest) -> RenderResult: ...


__all__ = [
    "RenderRequest",
    "RenderResult",
    "RenderStatus",
    "RendererPort",
]
