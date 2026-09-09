"""Ingestion domain enums (S2-G1).

Owns the page-classification vocabulary (canonical plan §8), the run
lifecycle status, and the ingestion-phase state machine
(DISCOVER→CLASSIFY→FETCH→RENDER→EXTRACT→BUILD_FACTS→DONE, canonical plan §10
S2-G6). Pure domain vocabulary — no classification logic, no I/O, no
orchestration.
"""

from enum import StrEnum


class PageType(StrEnum):
    """Deterministic page-classification bucket (canonical plan §8).

    Classification is signal-based (URL path, anchor text, sitemap name,
    title/H1, breadcrumb, schema.org types) — never an LLM call. The plan
    lists ``ARTICLE/BLOG`` as one group; the domain model keeps ``ARTICLE``
    and ``BLOG`` as separate values so a classifier can distinguish them, and
    a budget/diversity policy (S2-G3/G4) can still treat them as one group if
    it wants.
    """

    HOME = "HOME"
    ABOUT = "ABOUT"
    PRODUCT = "PRODUCT"
    SERVICE = "SERVICE"
    PRICING = "PRICING"
    FAQ = "FAQ"
    SHIPPING = "SHIPPING"
    RETURNS = "RETURNS"
    CONTACT = "CONTACT"
    CATEGORY = "CATEGORY"
    ARTICLE = "ARTICLE"
    BLOG = "BLOG"
    LEGAL = "LEGAL"
    OTHER = "OTHER"


class IngestionRunStatus(StrEnum):
    """Lifecycle of one ``IngestionRun``."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class IngestionPhase(StrEnum):
    """Phases of the ingestion state machine (canonical plan §10 S2-G6).

    ``IngestionCheckpoint`` records the LAST COMPLETED phase; the
    orchestration (S2-G6) advances through this sequence cooperatively.
    """

    DISCOVER = "DISCOVER"
    CLASSIFY = "CLASSIFY"
    FETCH = "FETCH"
    RENDER = "RENDER"
    EXTRACT = "EXTRACT"
    BUILD_FACTS = "BUILD_FACTS"
    DONE = "DONE"
