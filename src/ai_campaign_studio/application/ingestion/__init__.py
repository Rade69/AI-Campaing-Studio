"""Ingestion use-cases (Slice 2).

Website/Brand ingestion application layer: the S2-G6 pipeline orchestration
(``IngestBrandSources``) and the S2-G7a human-review step
(``ApproveFactCandidate``/``RejectFactCandidate``). Concrete adapters are
injected by the caller — no infrastructure imports here.

Parallel-work note: ``application/ingestion/`` is created by both S2-G6 and
S2-G7a at once. When both land, this ``__init__`` must export BOTH
``IngestBrandSources`` (S2-G6) and the review use-cases below (S2-G7a); each
branch only imports what exists on its own base.
"""

from ai_campaign_studio.application.ingestion.approve_fact_candidates import (
    ApproveFactCandidate,
    RejectFactCandidate,
)

__all__ = ["ApproveFactCandidate", "RejectFactCandidate"]
