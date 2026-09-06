"""Performance CSV import engine (Slice 1.5, P1.5-G3).

Owns the full CSV import chain: pure, I/O-free column mapping
(``column_mapping``) and row parsing/validation (``row_parsing``) from dio 1,
plus the three dio 2 use-cases — ``ImportPerformanceCsv`` (the only disk
reader), ``PreviewPerformanceMapping`` (pre-confirmation summary, persists
nothing) and ``ConfirmPerformanceImport`` (persists batch + rows). Does NOT
match rows to ``DistributionInstance`` (that is P1.5-G4).
"""
