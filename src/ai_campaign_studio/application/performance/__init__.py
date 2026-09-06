"""Performance CSV import engine (Slice 1.5, P1.5-G3 dio 1).

Pure, I/O-free column mapping and row parsing/validation for CSV performance
imports. Operates only on already-read ``dict[str, str]`` rows; no file,
database or network access. Does NOT match rows to ``DistributionInstance``
(that is P1.5-G4 / dio 2) and does NOT persist anything (dio 2).
"""
