"""Repository ports (A5).

Owns the framework-neutral ``Protocol`` interfaces for business persistence.
Declarations only — no ``sqlite3``/infrastructure imports and no SQL details
leak through these signatures. The concrete adapters live in
``infrastructure/database/repositories/``.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from ai_campaign_studio.domain.brand.entities import Brand, BrandSnapshot
from ai_campaign_studio.domain.campaign.entities import (
    Campaign,
    CampaignBrief,
    CampaignPlan,
)
from ai_campaign_studio.domain.common.ids import (
    BrandSnapshotId,
    CampaignId,
    CampaignPlanId,
    FactId,
    LayoutSpecId,
    PostId,
    RevisionId,
    VisualSystemId,
)
from ai_campaign_studio.domain.content.entities import ContentPiece
from ai_campaign_studio.domain.content.revisions import Revision
from ai_campaign_studio.domain.facts.entities import ApprovedFact
from ai_campaign_studio.domain.visual.entities import CampaignVisualSystem
from ai_campaign_studio.domain.visual.layout import LayoutSpec


@runtime_checkable
class BrandRepositoryPort(Protocol):
    """Persistence for ``Brand`` and ``BrandSnapshot``."""

    def save_brand(self, brand: Brand) -> None: ...

    def save_snapshot(self, snapshot: BrandSnapshot) -> None: ...

    def get_snapshot(self, snapshot_id: BrandSnapshotId) -> BrandSnapshot | None: ...


@runtime_checkable
class FactRepositoryPort(Protocol):
    """Persistence for ``ApprovedFact``."""

    def save_fact(self, fact: ApprovedFact) -> None: ...

    def get_fact(self, fact_id: FactId) -> ApprovedFact | None: ...

    def list_snapshot_facts(
        self, snapshot_id: BrandSnapshotId
    ) -> tuple[ApprovedFact, ...]: ...


@runtime_checkable
class CampaignRepositoryPort(Protocol):
    """Persistence for campaign aggregates (adapter in ACS-F1-006)."""

    def save_campaign(self, campaign: Campaign) -> None: ...

    def save_brief(self, brief: CampaignBrief) -> None: ...

    def get_brief(self, brief_id: str) -> CampaignBrief | None: ...

    def save_plan(self, plan: CampaignPlan) -> None: ...

    def get_campaign(self, campaign_id: CampaignId) -> Campaign | None: ...

    def get_plan(self, plan_id: CampaignPlanId) -> CampaignPlan | None: ...

    def delete_campaign(
        self, campaign_id: CampaignId, *, brief_id: str | None = None
    ) -> None:
        """Compensating-action delete (ACS-GUI-006). USE SPARINGLY.

        This is the ONLY delete operation in the entire repository layer
        (the project is otherwise append-only / audit-trail oriented by
        design). It is intended exclusively for compensating actions in
        multi-step orchestrations where a later step failed AFTER an
        earlier step's row was already committed. The current (and only)
        caller is ``CampaignBridgeApi`` rolling back an orphan DRAFT
        campaign when ``GenerateCampaignPlan`` fails after
        ``CreateCampaign`` already committed.

        Do NOT use this for:
        - general "user wants to delete a campaign" UI flow (does not
          exist in the product yet, and the audit model is wrong for it);
        - ad-hoc test cleanup outside the bridge orchestrator;
        - any other write that might silently lose work.

        ``brief_id`` is required if the caller wants the brief row
        removed too (the bridge always passes it; the schema has
        ``campaigns.brief_id REFERENCES campaign_briefs(id)`` so the
        brief cannot be deleted BEFORE the campaign row is gone, and
        the campaign row is gone by the time the brief is deleted —
        a simple direct ``DELETE FROM campaign_briefs WHERE id=?``
        is the right tool here, not a subquery). ``brief_id=None``
        leaves the brief alone (use this when the brief is shared
        with another campaign; not the case in any current call site
        but kept as an explicit opt-out for future safety).

        Implementation notes (see ``SqliteCampaignRepository.delete_campaign``
        for the canonical child-before-parent ordering):

        - the delete is idempotent: deleting a non-existent campaign
          is a no-op, not an error (caller's compensating action may
          run after the row was already removed by another path);
        - dependent rows (brief if requested, plan, items, visual_system)
          MUST be removed in the same method, because the SQLite schema
          does not declare ``ON DELETE CASCADE`` (resources/migrations/0002)
          and we intentionally do not change the migration set from
          application code.
        """


@runtime_checkable
class ContentRepositoryPort(Protocol):
    """Persistence for content pieces (adapter in ACS-F1-006)."""

    def save_content_piece(self, content_piece: ContentPiece) -> None: ...

    def get_content_piece(self, content_piece_id: PostId) -> ContentPiece | None: ...

    def list_campaign_content(
        self, campaign_id: CampaignId
    ) -> tuple[ContentPiece, ...]: ...


@runtime_checkable
class VisualRepositoryPort(Protocol):
    """Persistence for the campaign visual system (adapter in ACS-F1-006)."""

    def save_visual_system(self, system: CampaignVisualSystem) -> None: ...

    def get_visual_system(
        self, visual_system_id: VisualSystemId
    ) -> CampaignVisualSystem | None: ...

    def save_layout_spec(self, layout_spec: LayoutSpec) -> None:
        """Persist one per-post raster layout (A13 dio 2b foundation).

        Requires ``layout_spec.id``, ``layout_spec.content_piece_id`` and
        ``layout_spec.validation_status`` to all be set (not ``None``) before
        the call — an in-memory ``LayoutSpec`` (ACS-F1-029 style) is NOT
        persistable. Adapters raise ``ValueError`` on a missing required
        field rather than storing an unidentifiable row.
        """

    def get_layout_spec(self, layout_spec_id: LayoutSpecId) -> LayoutSpec | None: ...

    def get_layout_spec_by_content_piece(
        self, content_piece_id: PostId
    ) -> LayoutSpec | None:
        """Most recently created layout spec for one content piece.

        ``layout_specs.content_piece_id`` has no unique constraint
        (ACS-F1-030) — if multiple rows exist (e.g. the post was re-planned),
        return the NEWEST one (ORDER BY created_at DESC). This is a
        documented simplification, not a full de-duplication /
        superseding scheme; the application layer (RenderPost) is the
        single caller, and the latest-wins rule is what it needs.
        """



@runtime_checkable
class RevisionRepositoryPort(Protocol):
    """Persistence for content revisions (adapter in ACS-F1-006)."""

    def save_revision(self, revision: Revision) -> None: ...

    def get_revision(self, revision_id: RevisionId) -> Revision | None: ...

    def list_entity_revisions(
        self, entity_type: str, entity_id: str
    ) -> tuple[Revision, ...]: ...


@runtime_checkable
class TelemetryRepositoryPort(Protocol):
    """Future analytics telemetry sink (Slice 1.5).

    Interface only: no SQLite adapter and no migration exist in A5. The event
    payload shape is deliberately unspecified until the Performance/Analytics
    module is designed.
    """

    def record_event(self, event: dict[str, Any]) -> None: ...
