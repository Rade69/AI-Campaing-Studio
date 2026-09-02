CREATE TABLE campaign_briefs (
    id TEXT PRIMARY KEY,
    offer TEXT NOT NULL,
    goal TEXT NOT NULL,
    audience_text TEXT NOT NULL,
    targets_json TEXT NOT NULL,
    content_piece_count INTEGER NOT NULL,
    content_language_context TEXT NOT NULL,
    special_instructions_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE campaigns (
    id TEXT PRIMARY KEY,
    brand_id TEXT NOT NULL,
    brand_snapshot_id TEXT NOT NULL,
    brief_id TEXT NOT NULL REFERENCES campaign_briefs(id),
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE campaign_plans (
    id TEXT PRIMARY KEY,
    campaign_id TEXT NOT NULL REFERENCES campaigns(id),
    version INTEGER NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE campaign_items (
    id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL REFERENCES campaign_plans(id),
    "order" INTEGER NOT NULL,
    role TEXT NOT NULL,
    topic TEXT NOT NULL,
    goal TEXT NOT NULL,
    target_audience_id TEXT NULL,
    facts_needed_json TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE content_pieces (
    id TEXT PRIMARY KEY,
    campaign_item_id TEXT NOT NULL REFERENCES campaign_items(id),
    target_channel TEXT NOT NULL,
    target_platform_code TEXT NOT NULL,
    target_format_code TEXT NOT NULL,
    payload_type TEXT NOT NULL,
    status TEXT NOT NULL,
    brand_snapshot_id TEXT NOT NULL,
    facts_allowed_json TEXT NOT NULL,
    revision_ids_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE content_claims (
    id TEXT PRIMARY KEY,
    piece_id TEXT NOT NULL REFERENCES content_pieces(id),
    position INTEGER NOT NULL,
    text TEXT NOT NULL,
    type TEXT NOT NULL,
    fact_ids_json TEXT NOT NULL,
    status TEXT NOT NULL,
    reason_codes_json TEXT NOT NULL
);

CREATE TABLE revisions (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    origin TEXT NOT NULL,
    previous_value TEXT NOT NULL,
    new_value TEXT NOT NULL,
    provider TEXT NULL,
    model TEXT NULL,
    prompt_version TEXT NULL,
    instruction TEXT NULL
);

CREATE TABLE campaign_visual_systems (
    id TEXT PRIMARY KEY,
    campaign_id TEXT NOT NULL REFERENCES campaigns(id),
    primary_layout_family TEXT NOT NULL,
    secondary_layout_family TEXT NULL,
    headline_scale TEXT NOT NULL,
    image_treatment TEXT NOT NULL,
    logo_rule TEXT NOT NULL,
    cta_rule TEXT NOT NULL,
    alignment TEXT NOT NULL,
    style_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
