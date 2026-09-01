CREATE TABLE app_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE provider_configs (
    provider_code TEXT PRIMARY KEY,
    configured INTEGER NOT NULL DEFAULT 0,
    validated INTEGER NOT NULL DEFAULT 0,
    credential_ref TEXT NULL,
    base_url TEXT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE model_selections (
    purpose TEXT PRIMARY KEY,
    provider_code TEXT NOT NULL,
    model_id TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
