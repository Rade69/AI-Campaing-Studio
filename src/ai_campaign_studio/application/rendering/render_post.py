"""RenderPost use-case (A14 dio 2, plan sections 43-44).

Orchestrates a single content piece into a rendered PNG by looking
up the content + the most recent layout spec + the visual system and
handing them to the ``RendererPort``.

Per the contract, ``visual_system_id`` is an EXPLICIT parameter (same
shape as ``PlanPostLayout.execute(plan_id=...)`` -- the caller already
has the ``VisualSystemId`` from the upstream step, so there is no
ambition to discover it through the campaign_item_id chain).
"""

from __future__ import annotations

from ai_campaign_studio.domain.common.errors import EntityNotFound, InvariantViolation
from ai_campaign_studio.domain.common.ids import PostId, VisualSystemId
from ai_campaign_studio.ports.rendering import (
    RendererPort,
    RenderRequest,
    RenderResult,
)
from ai_campaign_studio.ports.repositories import (
    CampaignRepositoryPort,
    ContentRepositoryPort,
    VisualRepositoryPort,
)


class RenderPost:
    """Render one content piece to a PNG via the ``RendererPort``.

    Per the contract, this use-case does NOT persist anything: there is
    no ``render_artifacts`` table, and the artifact path is whatever
    the caller passes. The use-case is a pure orchestrator -- the
    application layer that knows how to find the inputs, hands them
    to the renderer, and returns the result.
    """

    def __init__(
        self,
        content_repo: ContentRepositoryPort,
        campaign_repo: CampaignRepositoryPort,
        visual_repo: VisualRepositoryPort,
        renderer: RendererPort,
    ) -> None:
        self._content_repo = content_repo
        self._campaign_repo = campaign_repo
        self._visual_repo = visual_repo
        self._renderer = renderer

    def execute(
        self,
        content_piece_id: PostId,
        visual_system_id: VisualSystemId,
        output_path: str,
    ) -> RenderResult:
        # 1. Content piece (must exist; must have a payload to render).
        piece = self._content_repo.get_content_piece(content_piece_id)
        if piece is None:
            raise EntityNotFound(
                f"content piece {content_piece_id} not found"
            )
        if piece.payload is None:
            raise InvariantViolation(
                f"content piece {content_piece_id} has no payload to render"
            )
        payload = piece.payload  # typed as SocialPostPayload by the domain

        # 2. Layout spec: most recent for this content piece. Without
        #    it, the post was never put through ``PlanPostLayout``.
        layout_spec = self._visual_repo.get_layout_spec_by_content_piece(
            content_piece_id
        )
        if layout_spec is None:
            raise EntityNotFound(
                f"no layout spec for content piece {content_piece_id}"
            )

        # 3. Visual system (explicit parameter, see class docstring).
        visual_system = self._visual_repo.get_visual_system(visual_system_id)
        if visual_system is None:
            raise EntityNotFound(
                f"visual system {visual_system_id} not found"
            )

        # 4. Optional brand snapshot -- used to source the logo path.
        #    Per the A14 dio 2 contract, the brand snapshot is NOT
        #    threaded through RenderRequest as a typed dependency
        #    (logo is an optional path string only). If we can find
        #    the brand snapshot cheaply via the campaign chain, use
        #    it; otherwise logo_path stays None and the renderer
        #    silently skips the logo.
        logo_path = self._resolve_logo_path(visual_system.campaign_id)

        # 5. Compose RenderRequest and dispatch to the renderer.
        request = RenderRequest(
            content_piece_id=content_piece_id,
            format=layout_spec.format,
            layout_spec=layout_spec,
            content=payload,
            visual_system=visual_system,
            output_path=output_path,
            image_path=None,    # Slice 1 has no image-upload pipeline.
            logo_path=logo_path,
        )
        return self._renderer.render(request)

    def _resolve_logo_path(self, campaign_id: object) -> str | None:
        """Brand logo path is not resolvable yet.

        ``BrandRepositoryPort`` is not part of this use-case's port set
        (the A14 dio 2 contract specifies exactly 4 ports: content/
        campaign/visual/renderer), so there is no way to walk
        ``campaign_id`` -> brand snapshot -> ``visual_identity.logo_path``.
        Always ``None`` until brand threading is formalized (a future
        task, e.g. the A15 export flow, once a real port/data path
        exists) -- an earlier version of this method made a ``get_campaign``
        call here that could never change this return value; removed as
        dead code during review (ACS-F1-033).
        """
        del campaign_id  # unused until brand threading exists
        return None


__all__ = ["RenderPost"]
