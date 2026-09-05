CREATE TABLE performance_import_batches (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    matched_count INTEGER NOT NULL,
    unmatched_count INTEGER NOT NULL,
    mapping_version TEXT NOT NULL,
    source_file_name TEXT NULL,
    platform_code TEXT NULL,
    raw_source_snapshot_ref TEXT NULL
);

CREATE TABLE distribution_instances (
    id TEXT PRIMARY KEY,
    campaign_id TEXT NOT NULL REFERENCES campaigns(id),
    campaign_item_id TEXT NOT NULL REFERENCES campaign_items(id),
    content_piece_id TEXT NOT NULL REFERENCES content_pieces(id),
    content_revision_id TEXT NOT NULL REFERENCES revisions(id),
    channel_code TEXT NOT NULL,
    platform_code TEXT NOT NULL,
    format_code TEXT NOT NULL,
    distribution_source TEXT NOT NULL,
    external_account_id TEXT NULL,
    external_content_id TEXT NULL,
    published_at TEXT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE performance_snapshots (
    id TEXT PRIMARY KEY,
    distribution_instance_id TEXT NOT NULL REFERENCES distribution_instances(id),
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    source TEXT NOT NULL,
    source_batch_id TEXT NULL REFERENCES performance_import_batches(id),
    reach INTEGER NULL,
    impressions INTEGER NULL,
    engagements INTEGER NULL,
    clicks INTEGER NULL,
    conversions INTEGER NULL,
    spend REAL NULL,
    revenue REAL NULL,
    video_views INTEGER NULL,
    watch_time_seconds REAL NULL,
    raw_metrics_json TEXT NOT NULL
);
