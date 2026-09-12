"""Unit tests for Brand Knowledge policies (BK-G1)."""

import pytest

from ai_campaign_studio.domain.brand_knowledge.enums import KnowledgeCategory
from ai_campaign_studio.domain.brand_knowledge.policies import (
    ALLOWED_FIELDS_BY_CATEGORY,
    assert_field_allowed,
    is_field_allowed,
)
from ai_campaign_studio.domain.common.errors import InvariantViolation


def test_registry_covers_all_categories() -> None:
    assert set(ALLOWED_FIELDS_BY_CATEGORY) == set(KnowledgeCategory)


def test_registry_matches_plan_exactly() -> None:
    assert ALLOWED_FIELDS_BY_CATEGORY == {
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


def test_is_field_allowed_true_for_known_field() -> None:
    assert is_field_allowed(KnowledgeCategory.COMPANY, "name") is True


def test_is_field_allowed_false_for_unknown_field() -> None:
    assert is_field_allowed(KnowledgeCategory.COMPANY, "nope") is False


def test_assert_field_allowed_passes_for_known_field() -> None:
    assert_field_allowed(KnowledgeCategory.COMPANY, "mission")  # no raise


def test_assert_field_allowed_raises_for_unknown_field() -> None:
    with pytest.raises(InvariantViolation):
        assert_field_allowed(KnowledgeCategory.OFFERING, "email")
