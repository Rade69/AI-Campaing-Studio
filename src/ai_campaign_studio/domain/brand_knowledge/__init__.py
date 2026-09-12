"""Brand Knowledge domain (BK-G1).

Owns the immutable value objects and pure vocabulary for structured brand
knowledge (``KnowledgeEntry``/``BrandKnowledgeSnapshot``), the
``KnowledgeCategory``/``KnowledgeStatus``/``EvidenceType`` enums, and the
controlled per-category field registry (plan §5). No persistence, no
extraction, no LLM, no orchestration — BK-G2 gives these their first SQLite
table, BK-G3/G4 the classifiers.
"""

from ai_campaign_studio.domain.brand_knowledge.entities import (
    BrandKnowledgeSnapshot,
    KnowledgeEntry,
)
from ai_campaign_studio.domain.brand_knowledge.enums import (
    EvidenceType,
    KnowledgeCategory,
    KnowledgeStatus,
)
from ai_campaign_studio.domain.brand_knowledge.policies import (
    ALLOWED_FIELDS_BY_CATEGORY,
    assert_field_allowed,
    is_field_allowed,
)

__all__ = [
    "ALLOWED_FIELDS_BY_CATEGORY",
    "BrandKnowledgeSnapshot",
    "EvidenceType",
    "KnowledgeCategory",
    "KnowledgeEntry",
    "KnowledgeStatus",
    "assert_field_allowed",
    "is_field_allowed",
]
