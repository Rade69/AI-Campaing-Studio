"""Performance domain entities (Faza 0.7 §3, §5, §13)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from ai_campaign_studio.domain.common.ids import (
    CampaignId,
    CampaignItemId,
    DistributionInstanceId,
    PerformanceImportBatchId,
    PerformanceImportRowId,
    PerformanceSnapshotId,
    PostId,
    RevisionId,
)
from ai_campaign_studio.domain.performance.enums import (
    DistributionSource,
    PerformanceSource,
)
from ai_campaign_studio.domain.performance.metrics import (
    CanonicalMetricSet,
    MetricPeriod,
)

# Matching outcome for one imported row (P1.5-G4, Faza 0.7 §14).
# ``None`` means matching was never attempted; a non-None value is the
# recorded, persisted outcome of one matching attempt.
MatchStatus = Literal["UNMATCHED", "AMBIGUOUS", "MATCHED"]


@dataclass(frozen=True)
class DistributionInstance:
    """Concrete content, in a concrete revision, on a concrete
    channel/platform/format (Faza 0.7 §3).
    """

    id: DistributionInstanceId
    campaign_id: CampaignId
    campaign_item_id: CampaignItemId
    content_piece_id: PostId
    content_revision_id: RevisionId
    channel_code: str
    platform_code: str
    format_code: str
    distribution_source: DistributionSource
    created_at: datetime
    external_account_id: str | None = None
    external_content_id: str | None = None
    published_at: datetime | None = None


@dataclass(frozen=True)
class PerformanceSnapshot:
    """Metrics for one period, bound to a ``DistributionInstance``.

    Bound to the DistributionInstance (NOT directly to a ContentPiece) —
    Faza 0.7 §4 critical rule: if a caption changes after publishing, old
    results must not be attributed to the new content revision.
    """

    id: PerformanceSnapshotId
    distribution_instance_id: DistributionInstanceId
    period: MetricPeriod
    observed_at: datetime
    source: PerformanceSource
    metrics: CanonicalMetricSet
    source_batch_id: PerformanceImportBatchId | None = None
    raw_metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PerformanceImportBatch:
    """One data import — must be auditable (Faza 0.7 §13).

    No silent matching without evidence: ``row_count``/``matched_count``/
    ``unmatched_count`` make every import verifiable.
    """

    id: PerformanceImportBatchId
    source: PerformanceSource
    imported_at: datetime
    row_count: int
    matched_count: int
    unmatched_count: int
    mapping_version: str
    source_file_name: str | None = None
    platform_code: str | None = None
    raw_source_snapshot_ref: str | None = None


@dataclass(frozen=True)
class PerformanceImportRow:
    """One imported CSV data row, kept verbatim (Faza 0.7 §13 audit).

    ``raw_values`` preserves the ORIGINAL CSV values keyed by original
    header text — nothing is lost, including unmatched/extra columns.
    ``mapped_values`` maps canonical field -> string value for MATCHED
    columns only. ``errors`` is empty for a valid row; invalid rows are
    STILL persisted (never silently dropped). ``distribution_instance_id``
    stays ``None`` at import time — the matching gate (P1.5-G4) fills it
    later; ``match_status`` records that outcome (``None`` = never attempted).
    """

    id: PerformanceImportRowId
    batch_id: PerformanceImportBatchId
    row_number: int
    raw_values: dict[str, str]
    mapped_values: dict[str, str]
    errors: tuple[str, ...]
    distribution_instance_id: DistributionInstanceId | None = None
    match_status: MatchStatus | None = None
