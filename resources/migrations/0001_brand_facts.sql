CREATE TABLE brands (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE brand_snapshots (
    id TEXT PRIMARY KEY,
    brand_id TEXT NOT NULL REFERENCES brands(id),
    version INTEGER NOT NULL,
    language TEXT NOT NULL,
    locale TEXT NOT NULL,
    script TEXT NOT NULL,
    voice_json TEXT NOT NULL,
    audiences_json TEXT NOT NULL,
    services_json TEXT NOT NULL,
    visual_identity_json TEXT NOT NULL,
    restrictions_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE approved_facts (
    id TEXT PRIMARY KEY,
    logical_fact_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    content TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_uri TEXT NOT NULL,
    source_snapshot_id TEXT NULL,
    source_chunk_id TEXT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    superseded_by TEXT NULL,
    deleted_at TEXT NULL
);

CREATE TABLE brand_snapshot_facts (
    snapshot_id TEXT NOT NULL REFERENCES brand_snapshots(id),
    fact_id TEXT NOT NULL REFERENCES approved_facts(id),
    position INTEGER NOT NULL,
    PRIMARY KEY (snapshot_id, fact_id)
);
