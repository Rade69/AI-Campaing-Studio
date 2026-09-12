"""Brand Knowledge domain enums (BK-G1).

Owns the pure classification vocabulary for structured brand knowledge:
``KnowledgeCategory`` (what the knowledge is about), ``KnowledgeStatus``
(its review lifecycle) and ``EvidenceType`` (how it was derived from
approved facts). Pure domain vocabulary — no extraction, no validation, no
I/O. The per-category field-validation policy lives in ``policies.py``, not
here.
"""

from enum import StrEnum


class KnowledgeCategory(StrEnum):
    """The controlled taxonomy a ``KnowledgeEntry`` can be classified into.

    Plan §3.1. There is deliberately no ``OTHER`` bucket — a future
    classifier (BK-G3/G4) must pick exactly one of these eight, and an
    unknown category is a validation error, never a silently accepted value.
    """

    COMPANY = "COMPANY"
    OFFERING = "OFFERING"
    AUDIENCE = "AUDIENCE"
    DIFFERENTIATOR = "DIFFERENTIATOR"
    PRICING = "PRICING"
    CONTACT = "CONTACT"
    BRAND_VOICE = "BRAND_VOICE"
    TRUST = "TRUST"


class KnowledgeStatus(StrEnum):
    """Review lifecycle of one ``KnowledgeEntry`` (plan §3.2).

    ``PROPOSED`` is the entry state awaiting human review; ``APPROVED`` and
    ``REJECTED`` are the review outcomes; ``CONFLICT`` marks entries a
    future dedup/conflict pass (BK-G5) flagged as contradictory. Only
    ``APPROVED`` entries may appear in a ``BrandKnowledgeSnapshot`` —
    enforced by the future BK-G7 use-case, not by this value object.
    """

    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CONFLICT = "CONFLICT"


class EvidenceType(StrEnum):
    """How a ``KnowledgeEntry`` value was derived from approved facts (§3.3).

    ``EXPLICIT`` = the information directly exists in one or more
    ``ApprovedFact`` (e.g. a pricing page stating a price verbatim).
    ``INFERRED`` = the value is derived from a pattern across multiple
    facts (e.g. BRAND_VOICE "direct, accessible" inferred from the style of
    many texts). An inferred value is still grounded in approved facts; it
    is never a free-form claim invented by the classifier.
    """

    EXPLICIT = "EXPLICIT"
    INFERRED = "INFERRED"
