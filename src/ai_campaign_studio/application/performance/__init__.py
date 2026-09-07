"""Performance CSV import engine (Slice 1.5, P1.5-G3 + G4).

Owns the full CSV import chain: pure, I/O-free column mapping
(``column_mapping``) and row parsing/validation (``row_parsing``) from dio 1,
the three dio 2 use-cases — ``ImportPerformanceCsv`` (the only disk reader),
``PreviewPerformanceMapping`` (pre-confirmation summary, persists nothing) and
``ConfirmPerformanceImport`` (persists batch + rows) — plus the G4 matching
use-case ``MatchPerformanceImportBatch`` (matches imported rows to
``DistributionInstance`` via external_content_id + analytics_match_key).
"""
