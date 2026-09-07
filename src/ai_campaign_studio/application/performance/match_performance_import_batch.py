"""MatchPerformanceImportBatch use-case (P1.5-G4, Faza 0.7 §14).

Owns matching imported ``PerformanceImportRow`` rows to concrete
``DistributionInstance`` rows for ONE campaign, using ONLY priority 1
(``external_content_id``) and priority 2 (computed ``analytics_match_key``).
Rows that were already attempted (``match_status`` is not ``None``) are never
touched again, so the use-case is idempotent. Priority 3 (stable-ID fallback)
and priority 4 (manual confirmation UI) are deliberately OUT of scope.

Documented distinction (see ``MatchResult``): ``skipped`` counts rows that
carry NO matching-relevant value at all (neither ``external_content_id`` nor
``analytics_match_key`` mapped); they still get ``match_status="UNMATCHED"``
but are reported separately from rows that HAD a value and found nothing
(``unmatched``).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from ai_campaign_studio.domain.analytics.match_key import compute_analytics_match_key
from ai_campaign_studio.domain.common.ids import (
    CampaignId,
    DistributionInstanceId,
    PerformanceImportBatchId,
)
from ai_campaign_studio.domain.performance.entities import (
    DistributionInstance,
    MatchStatus,
)
from ai_campaign_studio.ports.repositories import PerformanceRepositoryPort


@dataclass(frozen=True)
class MatchResult:
    """Outcome counters for one matching run over a batch."""

    matched_count: int
    ambiguous_count: int
    unmatched_count: int
    skipped_count: int


class MatchPerformanceImportBatch:
    """Match one import batch's rows to campaign DistributionInstances."""

    def __init__(self, performance_repo: PerformanceRepositoryPort) -> None:
        self._repo = performance_repo

    def execute(
        self,
        batch_id: PerformanceImportBatchId,
        campaign_id: CampaignId,
    ) -> MatchResult:
        """Match not-yet-attempted rows and return the outcome counters.

        Every candidate row is persisted back with its new ``match_status``
        (and ``distribution_instance_id`` when matched). Rows whose
        ``match_status`` is already set are skipped untouched (idempotent).
        """
        rows = self._repo.list_performance_import_rows(batch_id)
        instances = self._repo.list_distribution_instances_by_campaign(
            campaign_id
        )

        matched = 0
        ambiguous = 0
        unmatched = 0
        skipped = 0

        for row in rows:
            if row.match_status is not None:
                # Already attempted (matched/unmatched/ambiguous) — do not
                # touch it again.
                continue

            external_content_id = row.mapped_values.get("external_content_id")
            match_key = row.mapped_values.get("analytics_match_key")

            if not external_content_id and not match_key:
                skipped += 1
                status: MatchStatus = "UNMATCHED"
                distribution_id: DistributionInstanceId | None = None
            else:
                status, distribution_id = _match_row(
                    external_content_id, match_key, instances
                )
                if status == "MATCHED":
                    matched += 1
                elif status == "AMBIGUOUS":
                    ambiguous += 1
                else:
                    unmatched += 1

            self._repo.save_performance_import_row(
                replace(
                    row,
                    match_status=status,
                    distribution_instance_id=distribution_id,
                )
            )

        return MatchResult(
            matched_count=matched,
            ambiguous_count=ambiguous,
            unmatched_count=unmatched,
            skipped_count=skipped,
        )


def _match_row(
    external_content_id: str | None,
    match_key: str | None,
    instances: tuple[DistributionInstance, ...],
) -> tuple[MatchStatus, DistributionInstanceId | None]:
    """Apply priority 1 then priority 2 to ONE row against the instance list.

    Priority 1 ``AMBIGUOUS`` (2+ matches) is FINAL — it returns immediately
    and does NOT fall through to priority 2, per Faza 0.7 §14.
    """
    if external_content_id:
        hits = [
            di for di in instances if di.external_content_id == external_content_id
        ]
        if len(hits) == 1:
            return "MATCHED", hits[0].id
        if len(hits) >= 2:
            return "AMBIGUOUS", None

    if match_key:
        hits = [di for di in instances if _compute_match_key(di) == match_key]
        if len(hits) == 1:
            return "MATCHED", hits[0].id
        if len(hits) >= 2:
            return "AMBIGUOUS", None

    return "UNMATCHED", None


def _compute_match_key(instance: DistributionInstance) -> str:
    """Compute the priority-2 key for one instance (same 4-tuple order as
    ``export_campaign.py``: content_piece_id, content_revision_id,
    platform_code, format_code)."""
    return compute_analytics_match_key(
        instance.content_piece_id,
        instance.content_revision_id,
        instance.platform_code,
        instance.format_code,
    )
