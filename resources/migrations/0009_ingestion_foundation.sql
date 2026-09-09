CREATE TABLE source_snapshots (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    raw_content_ref TEXT NULL,
    content_type TEXT NULL,
    status_code INTEGER NULL
);

CREATE TABLE source_chunks (
    id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL REFERENCES source_snapshots(id),
    locator_type TEXT NOT NULL,
    locator TEXT NOT NULL,
    text TEXT NOT NULL
);

CREATE TABLE ingestion_runs (
    id TEXT PRIMARY KEY,
    brand_id TEXT NOT NULL REFERENCES brands(id),
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT NULL,
    source_scope_json TEXT NOT NULL,
    discovered_urls INTEGER NOT NULL,
    fetched_pages INTEGER NOT NULL,
    extracted_chunks INTEGER NOT NULL,
    built_candidates INTEGER NOT NULL,
    failed_pages INTEGER NOT NULL
);

CREATE TABLE ingestion_checkpoints (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES ingestion_runs(id),
    phase TEXT NOT NULL,
    finished_at TEXT NOT NULL
);

CREATE TABLE fact_candidates (
    id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL REFERENCES source_snapshots(id),
    chunk_id TEXT NULL REFERENCES source_chunks(id),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE crawl_targets (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES ingestion_runs(id),
    normalized_url TEXT NOT NULL,
    depth INTEGER NOT NULL,
    page_type_hint TEXT NULL,
    priority INTEGER NOT NULL,
    state TEXT NOT NULL,
    attempts INTEGER NOT NULL,
    lease_until TEXT NULL,
    next_attempt_at TEXT NULL,
    last_error TEXT NULL,
    snapshot_id TEXT NULL REFERENCES source_snapshots(id),
    UNIQUE(run_id, normalized_url)
);

CREATE INDEX idx_crawl_targets_run_state_priority
    ON crawl_targets(run_id, state, priority);
CREATE INDEX idx_source_chunks_snapshot ON source_chunks(snapshot_id);
CREATE INDEX idx_fact_candidates_snapshot ON fact_candidates(snapshot_id);
