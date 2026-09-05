CREATE TABLE layout_specs (
    id TEXT PRIMARY KEY,
    content_piece_id TEXT NOT NULL REFERENCES content_pieces(id),
    format TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    validation_status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
