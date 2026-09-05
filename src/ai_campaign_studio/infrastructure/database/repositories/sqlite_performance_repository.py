"""SQLite adapter for ``PerformanceRepositoryPort`` (P1.5-G2).

Owns saving and reading back ``DistributionInstance``, ``PerformanceSnapshot``
and ``PerformanceImportBatch`` rows. Enum-typed attributes are stored as
``.value`` and reconstructed as real domain enums; ``MetricPeriod`` and
``CanonicalMetricSet`` are rebuilt from flat columns; ``raw_metrics`` is a
JSON text column. Does NOT own CSV import parsing, matching, or the per-row
audit table (``performance_import_rows`` — that is P1.5-G3).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from ai_campaign_studio.domain.common.ids import (
    CampaignId,
    CampaignItemId,
    DistributionInstanceId,
    PerformanceImportBatchId,
    PerformanceSnapshotId,
    PostId,
    RevisionId,
)
from ai_campaign_studio.domain.performance.entities import (
    DistributionInstance,
    PerformanceImportBatch,
    PerformanceSnapshot,
)
from ai_campaign_studio.domain.performance.enums import (
    DistributionSource,
    PerformanceSource,
)
from ai_campaign_studio.domain.performance.metrics import (
    CanonicalMetricSet,
    MetricPeriod,
)


class SqlitePerformanceRepository:
    """SQLite implementation of ``PerformanceRepositoryPort``."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def save_distribution_instance(
        self, instance: DistributionInstance
    ) -> None:
        published_at = (
            instance.published_at.isoformat()
            if instance.published_at is not None
            else None
        )
        self._connection.execute(
            "INSERT INTO distribution_instances (id, campaign_id,"
            " campaign_item_id, content_piece_id, content_revision_id,"
            " channel_code, platform_code, format_code, distribution_source,"
            " external_account_id, external_content_id, published_at,"
            " created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET"
            " campaign_id=excluded.campaign_id,"
            " campaign_item_id=excluded.campaign_item_id,"
            " content_piece_id=excluded.content_piece_id,"
            " content_revision_id=excluded.content_revision_id,"
            " channel_code=excluded.channel_code,"
            " platform_code=excluded.platform_code,"
            " format_code=excluded.format_code,"
            " distribution_source=excluded.distribution_source,"
            " external_account_id=excluded.external_account_id,"
            " external_content_id=excluded.external_content_id,"
            " published_at=excluded.published_at,"
            " created_at=excluded.created_at",
            (
                instance.id,
                instance.campaign_id,
                instance.campaign_item_id,
                instance.content_piece_id,
                instance.content_revision_id,
                instance.channel_code,
                instance.platform_code,
                instance.format_code,
                instance.distribution_source.value,
                instance.external_account_id,
                instance.external_content_id,
                published_at,
                instance.created_at.isoformat(),
            ),
        )

    def get_distribution_instance(
        self, distribution_instance_id: DistributionInstanceId
    ) -> DistributionInstance | None:
        row = self._connection.execute(
            "SELECT * FROM distribution_instances WHERE id = ?",
            (distribution_instance_id,),
        ).fetchone()
        if row is None:
            return None
        return DistributionInstance(
            id=DistributionInstanceId(row["id"]),
            campaign_id=CampaignId(row["campaign_id"]),
            campaign_item_id=CampaignItemId(row["campaign_item_id"]),
            content_piece_id=PostId(row["content_piece_id"]),
            content_revision_id=RevisionId(row["content_revision_id"]),
            channel_code=row["channel_code"],
            platform_code=row["platform_code"],
            format_code=row["format_code"],
            distribution_source=DistributionSource(row["distribution_source"]),
            external_account_id=row["external_account_id"],
            external_content_id=row["external_content_id"],
            published_at=(
                datetime.fromisoformat(row["published_at"])
                if row["published_at"] is not None
                else None
            ),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def save_performance_import_batch(
        self, batch: PerformanceImportBatch
    ) -> None:
        self._connection.execute(
            "INSERT INTO performance_import_batches (id, source, imported_at,"
            " row_count, matched_count, unmatched_count, mapping_version,"
            " source_file_name, platform_code, raw_source_snapshot_ref)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET"
            " source=excluded.source,"
            " imported_at=excluded.imported_at,"
            " row_count=excluded.row_count,"
            " matched_count=excluded.matched_count,"
            " unmatched_count=excluded.unmatched_count,"
            " mapping_version=excluded.mapping_version,"
            " source_file_name=excluded.source_file_name,"
            " platform_code=excluded.platform_code,"
            " raw_source_snapshot_ref=excluded.raw_source_snapshot_ref",
            (
                batch.id,
                batch.source.value,
                batch.imported_at.isoformat(),
                batch.row_count,
                batch.matched_count,
                batch.unmatched_count,
                batch.mapping_version,
                batch.source_file_name,
                batch.platform_code,
                batch.raw_source_snapshot_ref,
            ),
        )

    def get_performance_import_batch(
        self, batch_id: PerformanceImportBatchId
    ) -> PerformanceImportBatch | None:
        row = self._connection.execute(
            "SELECT * FROM performance_import_batches WHERE id = ?",
            (batch_id,),
        ).fetchone()
        if row is None:
            return None
        return PerformanceImportBatch(
            id=PerformanceImportBatchId(row["id"]),
            source=PerformanceSource(row["source"]),
            imported_at=datetime.fromisoformat(row["imported_at"]),
            row_count=row["row_count"],
            matched_count=row["matched_count"],
            unmatched_count=row["unmatched_count"],
            mapping_version=row["mapping_version"],
            source_file_name=row["source_file_name"],
            platform_code=row["platform_code"],
            raw_source_snapshot_ref=row["raw_source_snapshot_ref"],
        )

    def save_performance_snapshot(
        self, snapshot: PerformanceSnapshot
    ) -> None:
        self._connection.execute(
            "INSERT INTO performance_snapshots (id, distribution_instance_id,"
            " period_start, period_end, observed_at, source, source_batch_id,"
            " reach, impressions, engagements, clicks, conversions, spend,"
            " revenue, video_views, watch_time_seconds, raw_metrics_json)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET"
            " distribution_instance_id=excluded.distribution_instance_id,"
            " period_start=excluded.period_start,"
            " period_end=excluded.period_end,"
            " observed_at=excluded.observed_at,"
            " source=excluded.source,"
            " source_batch_id=excluded.source_batch_id,"
            " reach=excluded.reach,"
            " impressions=excluded.impressions,"
            " engagements=excluded.engagements,"
            " clicks=excluded.clicks,"
            " conversions=excluded.conversions,"
            " spend=excluded.spend,"
            " revenue=excluded.revenue,"
            " video_views=excluded.video_views,"
            " watch_time_seconds=excluded.watch_time_seconds,"
            " raw_metrics_json=excluded.raw_metrics_json",
            (
                snapshot.id,
                snapshot.distribution_instance_id,
                snapshot.period.start.isoformat(),
                snapshot.period.end.isoformat(),
                snapshot.observed_at.isoformat(),
                snapshot.source.value,
                snapshot.source_batch_id,
                snapshot.metrics.reach,
                snapshot.metrics.impressions,
                snapshot.metrics.engagements,
                snapshot.metrics.clicks,
                snapshot.metrics.conversions,
                snapshot.metrics.spend,
                snapshot.metrics.revenue,
                snapshot.metrics.video_views,
                snapshot.metrics.watch_time_seconds,
                json.dumps(snapshot.raw_metrics),
            ),
        )

    def get_performance_snapshot(
        self, snapshot_id: PerformanceSnapshotId
    ) -> PerformanceSnapshot | None:
        row = self._connection.execute(
            "SELECT * FROM performance_snapshots WHERE id = ?",
            (snapshot_id,),
        ).fetchone()
        if row is None:
            return None
        return PerformanceSnapshot(
            id=PerformanceSnapshotId(row["id"]),
            distribution_instance_id=DistributionInstanceId(
                row["distribution_instance_id"]
            ),
            period=MetricPeriod(
                start=datetime.fromisoformat(row["period_start"]),
                end=datetime.fromisoformat(row["period_end"]),
            ),
            observed_at=datetime.fromisoformat(row["observed_at"]),
            source=PerformanceSource(row["source"]),
            metrics=CanonicalMetricSet(
                reach=row["reach"],
                impressions=row["impressions"],
                engagements=row["engagements"],
                clicks=row["clicks"],
                conversions=row["conversions"],
                spend=row["spend"],
                revenue=row["revenue"],
                video_views=row["video_views"],
                watch_time_seconds=row["watch_time_seconds"],
            ),
            source_batch_id=(
                PerformanceImportBatchId(row["source_batch_id"])
                if row["source_batch_id"] is not None
                else None
            ),
            raw_metrics=json.loads(row["raw_metrics_json"]),
        )
