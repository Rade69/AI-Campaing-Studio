"""Repository ports (A5).

Owns the framework-neutral ``Protocol`` interfaces for business persistence.
Declarations only — no ``sqlite3``/infrastructure imports and no SQL details
leak through these signatures. The concrete adapters live in
``infrastructure/database/repositories/``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable

from ai_campaign_studio.domain.brand.entities import Brand, BrandSnapshot
from ai_campaign_studio.domain.campaign.entities import (
    Campaign,
    CampaignBrief,
    CampaignPlan,
)
from ai_campaign_studio.domain.common.ids import (
    BrandId,
    BrandSnapshotId,
    CampaignId,
    CampaignPlanId,
    CrawlTargetId,
    DistributionInstanceId,
    FactCandidateId,
    FactId,
    IngestionRunId,
    LayoutSpecId,
    PerformanceImportBatchId,
    PerformanceImportRowId,
    PerformanceSnapshotId,
    PostId,
    RevisionId,
    SourceChunkId,
    SourceSnapshotId,
    VisualSystemId,
)
from ai_campaign_studio.domain.content.entities import ContentPiece
from ai_campaign_studio.domain.content.revisions import Revision
from ai_campaign_studio.domain.facts.entities import ApprovedFact, FactCandidate
from ai_campaign_studio.domain.facts.enums import FactStatus
from ai_campaign_studio.domain.ingestion.entities import (
    CrawlTarget,
    IngestionCheckpoint,
    IngestionRun,
    SourceChunk,
    SourceSnapshot,
)
from ai_campaign_studio.domain.ingestion.enums import CrawlTargetState
from ai_campaign_studio.domain.performance.entities import (
    DistributionInstance,
    PerformanceImportBatch,
    PerformanceImportRow,
    PerformanceSnapshot,
)
from ai_campaign_studio.domain.visual.entities import CampaignVisualSystem
from ai_campaign_studio.domain.visual.layout import LayoutSpec


@runtime_checkable
class BrandRepositoryPort(Protocol):
    """Persistence for ``Brand`` and ``BrandSnapshot``."""

    def save_brand(self, brand: Brand) -> None: ...

    def get_brand(self, brand_id: BrandId) -> Brand | None: ...

    def save_snapshot(self, snapshot: BrandSnapshot) -> None: ...

    def get_snapshot(self, snapshot_id: BrandSnapshotId) -> BrandSnapshot | None: ...

    def get_latest_snapshot(self, brand_id: BrandId) -> BrandSnapshot | None:
        """Return the highest-version BrandSnapshot for a brand, or None
        if no snapshot has been assembled yet. Used by
        ``assemble_brand_snapshot`` to compute the next version.
        """


@runtime_checkable
class FactRepositoryPort(Protocol):
    """Persistence for ``ApprovedFact``."""

    def save_fact(self, fact: ApprovedFact) -> None: ...

    def get_fact(self, fact_id: FactId) -> ApprovedFact | None: ...

    def list_snapshot_facts(
        self, snapshot_id: BrandSnapshotId
    ) -> tuple[ApprovedFact, ...]: ...

    def list_approved_facts_by_brand(
        self, brand_id: BrandId
    ) -> tuple[ApprovedFact, ...]:
        """Return all APPROVED facts for a brand, ordered by created_at DESC.

        Used by ``assemble_brand_snapshot`` to compute ``approved_fact_ids``
        for a new ``BrandSnapshot``. Empty tuple if no approved facts.
        """

    def list_fact_candidates_by_brand(
        self, brand_id: BrandId, statuses: tuple[FactStatus, ...] | None = None
    ) -> tuple[FactCandidate, ...]:
        """Return FactCandidate rows for a brand, optionally filtered by
        statuses. Default returns all (PROPOSED, APPROVED, REJECTED).
        Used by ``get_ingestion_review``.
        """


@runtime_checkable
class CampaignRepositoryPort(Protocol):
    """Persistence for campaign aggregates (adapter in ACS-F1-006)."""

    def save_campaign(self, campaign: Campaign) -> None: ...

    def save_brief(self, brief: CampaignBrief) -> None: ...

    def get_brief(self, brief_id: str) -> CampaignBrief | None: ...

    def save_plan(self, plan: CampaignPlan) -> None: ...

    def get_campaign(self, campaign_id: CampaignId) -> Campaign | None: ...

    def get_plan(self, plan_id: CampaignPlanId) -> CampaignPlan | None: ...

    def list_campaigns(self) -> tuple[Campaign, ...]: ...

    def get_latest_plan_for_campaign(
        self, campaign_id: CampaignId
    ) -> CampaignPlan | None: ...

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
class PerformanceRepositoryPort(Protocol):
    """Persistence for the Performance domain (P1.5-G1 entities).

    Save/get by each entity's own id plus query-by-related-entity methods
    added when their callers landed: distribution instances per campaign
    (P1.5-G4 matching), per content piece and per platform (P1.5-G6 read
    models), and snapshots per distribution instance (P1.5-G6 read models).
    """

    def save_distribution_instance(
        self, instance: DistributionInstance
    ) -> None: ...

    def get_distribution_instance(
        self, distribution_instance_id: DistributionInstanceId
    ) -> DistributionInstance | None: ...

    def list_distribution_instances_by_campaign(
        self, campaign_id: CampaignId
    ) -> tuple[DistributionInstance, ...]: ...

    def list_distribution_instances_by_content_piece(
        self, content_piece_id: PostId
    ) -> tuple[DistributionInstance, ...]: ...

    def list_distribution_instances_by_platform(
        self, platform_code: str
    ) -> tuple[DistributionInstance, ...]: ...

    def save_performance_import_batch(
        self, batch: PerformanceImportBatch
    ) -> None: ...

    def get_performance_import_batch(
        self, batch_id: PerformanceImportBatchId
    ) -> PerformanceImportBatch | None: ...

    def save_performance_snapshot(
        self, snapshot: PerformanceSnapshot
    ) -> None: ...

    def get_performance_snapshot(
        self, snapshot_id: PerformanceSnapshotId
    ) -> PerformanceSnapshot | None: ...

    def list_performance_snapshots_by_distribution_instance(
        self, distribution_instance_id: DistributionInstanceId
    ) -> tuple[PerformanceSnapshot, ...]: ...

    def save_performance_import_row(
        self, row: PerformanceImportRow
    ) -> None: ...

    def get_performance_import_row(
        self, row_id: PerformanceImportRowId
    ) -> PerformanceImportRow | None: ...

    def list_performance_import_rows(
        self, batch_id: PerformanceImportBatchId
    ) -> tuple[PerformanceImportRow, ...]: ...


@runtime_checkable
class IngestionRepositoryPort(Protocol):
    """Persistence for the Website/Brand Ingestion domain (S2-G1).

    Save/get/list for the four ingestion value objects plus the Slice 2
    ``FactCandidate``. The concrete adapter (and its migration) land in
    S2-G2; no implementation exists yet. The list methods cover the
    provenance/review lookups the S2-G6/G7a gates need (chunks per snapshot,
    candidates per snapshot/brand) — no wider query surface is invented here.
    """

    def save_source_snapshot(self, snapshot: SourceSnapshot) -> None: ...

    def get_source_snapshot(
        self, snapshot_id: SourceSnapshotId
    ) -> SourceSnapshot | None: ...

    def list_source_snapshots_by_run(
        self, run_id: IngestionRunId
    ) -> tuple[SourceSnapshot, ...]: ...

    def save_source_chunk(self, chunk: SourceChunk) -> None: ...

    def get_source_chunk(
        self, chunk_id: SourceChunkId
    ) -> SourceChunk | None: ...

    def list_source_chunks_by_snapshot(
        self, snapshot_id: SourceSnapshotId
    ) -> tuple[SourceChunk, ...]: ...

    def save_ingestion_run(self, run: IngestionRun) -> None: ...

    def get_ingestion_run(
        self, run_id: IngestionRunId
    ) -> IngestionRun | None: ...

    def save_ingestion_checkpoint(
        self, checkpoint: IngestionCheckpoint
    ) -> None: ...

    def get_latest_checkpoint(
        self, run_id: IngestionRunId
    ) -> IngestionCheckpoint | None: ...

    def save_fact_candidate(self, candidate: FactCandidate) -> None: ...

    def get_fact_candidate(
        self, candidate_id: FactCandidateId
    ) -> FactCandidate | None: ...

    def list_fact_candidates_by_snapshot(
        self, snapshot_id: SourceSnapshotId
    ) -> tuple[FactCandidate, ...]: ...

    # --- CrawlTarget lease queue (S2-G2, canonical plan §7) ---

    def register_crawl_targets(
        self, targets: Sequence[CrawlTarget]
    ) -> int: ...

    def claim_next_crawl_target(
        self, run_id: IngestionRunId, lease_duration_seconds: int
    ) -> CrawlTarget | None: ...

    def update_crawl_target_state(
        self,
        target_id: CrawlTargetId,
        state: CrawlTargetState,
        *,
        last_error: str | None = None,
        snapshot_id: SourceSnapshotId | None = None,
    ) -> None: ...

    def recover_expired_leases(self, run_id: IngestionRunId) -> int: ...

    def get_crawl_target(
        self, target_id: CrawlTargetId
    ) -> CrawlTarget | None: ...

    def list_crawl_targets_by_run(
        self, run_id: IngestionRunId
    ) -> tuple[CrawlTarget, ...]: ...


@runtime_checkable
class TelemetryRepositoryPort(Protocol):
    """Future analytics telemetry sink (Slice 1.5).

    Interface only: no SQLite adapter and no migration exist in A5. The event
    payload shape is deliberately unspecified until the Performance/Analytics
    module is designed.
    """

    def record_event(self, event: dict[str, Any]) -> None: ...
