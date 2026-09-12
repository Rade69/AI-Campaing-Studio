CREATE TABLE brand_knowledge_entries (
    id TEXT PRIMARY KEY,
    brand_snapshot_id TEXT NOT NULL REFERENCES brand_snapshots(id),
    category TEXT NOT NULL,
    field_name TEXT NOT NULL,
    value TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    status TEXT NOT NULL,
    confidence REAL NULL,
    conflict_group_id TEXT NULL,
    created_at TEXT NOT NULL,
    reviewed_at TEXT NULL
);

CREATE TABLE brand_knowledge_entry_facts (
    entry_id TEXT NOT NULL REFERENCES brand_knowledge_entries(id),
    fact_id TEXT NOT NULL REFERENCES approved_facts(id),
    position INTEGER NOT NULL,
    PRIMARY KEY (entry_id, fact_id)
);

CREATE TABLE brand_knowledge_snapshots (
    id TEXT PRIMARY KEY,
    brand_snapshot_id TEXT NOT NULL REFERENCES brand_snapshots(id),
    version INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(brand_snapshot_id, version)
);

CREATE TABLE brand_knowledge_snapshot_entries (
    knowledge_snapshot_id TEXT NOT NULL
        REFERENCES brand_knowledge_snapshots(id),
    entry_id TEXT NOT NULL REFERENCES brand_knowledge_entries(id),
    position INTEGER NOT NULL,
    PRIMARY KEY (knowledge_snapshot_id, entry_id)
);
