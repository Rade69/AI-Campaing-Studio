"""Brand Knowledge domain policies (BK-G1).

Owns the controlled per-category field registry (plan §5) and the two
field-validation helpers that every later gate (BK-G3 deterministic
extractor, BK-G4 LLM validator) MUST reuse instead of re-implementing.
Unknown fields are never silently accepted — this is the single source of
truth for what a ``KnowledgeEntry.field`` may contain for a given
``KnowledgeCategory``.
"""

from __future__ import annotations

from collections.abc import Mapping

from ai_campaign_studio.domain.brand_knowledge.enums import KnowledgeCategory
from ai_campaign_studio.domain.common.errors import InvariantViolation

ALLOWED_FIELDS_BY_CATEGORY: Mapping[KnowledgeCategory, frozenset[str]] = {
    KnowledgeCategory.COMPANY: frozenset({
        "name", "description", "industry", "company_type", "location",
        "founded", "mission",
    }),
    KnowledgeCategory.OFFERING: frozenset({
        "service", "product", "package", "feature", "benefit",
    }),
    KnowledgeCategory.AUDIENCE: frozenset({
        "target_segment", "industry", "geography", "need", "pain_point",
        "objection", "motivation",
    }),
    KnowledgeCategory.DIFFERENTIATOR: frozenset({
        "advantage", "unique_selling_point", "expertise", "guarantee",
        "capability",
    }),
    KnowledgeCategory.PRICING: frozenset({
        "price", "starting_price", "price_range", "discount",
        "payment_terms", "pricing_model",
    }),
    KnowledgeCategory.CONTACT: frozenset({
        "email", "phone", "address", "website", "social_profile",
    }),
    KnowledgeCategory.BRAND_VOICE: frozenset({
        "tone", "formality", "vocabulary", "preferred_phrase",
        "forbidden_phrase", "sentence_style", "cta_style",
        "technical_language",
    }),
    KnowledgeCategory.TRUST: frozenset({
        "testimonial", "customer", "certification", "award",
        "statistic", "case_study", "years_experience", "project_count",
    }),
}


def is_field_allowed(category: KnowledgeCategory, field: str) -> bool:
    """Return True iff ``field`` is in the controlled registry for ``category``."""
    return field in ALLOWED_FIELDS_BY_CATEGORY[category]


def assert_field_allowed(category: KnowledgeCategory, field: str) -> None:
    """Raise ``InvariantViolation`` if ``field`` is not allowed for ``category``.

    Unknown fields are NEVER silently accepted (plan §5) — this is the
    single source of truth every later gate (BK-G3 deterministic extractor,
    BK-G4 LLM validator) must reuse, not re-implement.
    """
    if not is_field_allowed(category, field):
        raise InvariantViolation(
            f"field {field!r} is not allowed for category {category.value}"
        )
