CREATE TABLE performance_import_rows (
    id TEXT PRIMARY KEY,
    batch_id TEXT NOT NULL REFERENCES performance_import_batches(id),
    row_number INTEGER NOT NULL,
    raw_values_json TEXT NOT NULL,
    mapped_values_json TEXT NOT NULL,
    errors_json TEXT NOT NULL,
    distribution_instance_id TEXT NULL REFERENCES distribution_instances(id)
);
