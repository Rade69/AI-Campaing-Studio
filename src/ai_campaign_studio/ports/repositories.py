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
    PostId,
    RevisionId,
    VisualSystemId,
)
from ai_campaign_studio.domain.content.entities import ContentPiece
from ai_campaign_studio.domain.content.revisions import Revision
from ai_campaign_studio.domain.facts.entities import ApprovedFact
from ai_campaign_studio.domain.visual.entities import CampaignVisualSystem


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

    def save_plan(self, plan: CampaignPlan) -> None: ...

    def get_campaign(self, campaign_id: CampaignId) -> Campaign | None: ...

    def get_plan(self, plan_id: CampaignPlanId) -> CampaignPlan | None: ...


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
