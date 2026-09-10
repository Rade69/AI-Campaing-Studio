"""Ingestion use-cases (Slice 2).

Website/Brand ingestion application layer: the S2-G6 pipeline orchestration
(``IngestBrandSources``, DISCOVER→CLASSIFY→FETCH→RENDER→EXTRACT→BUILD_FACTS→
DONE over the existing S2-G1/G2 ports and injected G3/G4/G5/G9 adapters) and
the S2-G7a human-review step (``ApproveFactCandidate``/``RejectFactCandidate``).
No infrastructure imports here (application boundary) — concrete adapters are
wired by the caller.
"""

from ai_campaign_studio.application.ingestion.approve_fact_candidates import (
    ApproveFactCandidate,
    RejectFactCandidate,
)
from ai_campaign_studio.application.ingestion.ingest_brand_sources import (
    IngestBrandSources,
)

__all__ = ["ApproveFactCandidate", "IngestBrandSources", "RejectFactCandidate"]
