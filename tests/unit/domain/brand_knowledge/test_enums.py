"""Unit tests for Brand Knowledge enums (BK-G1)."""

from ai_campaign_studio.domain.brand_knowledge.enums import (
    EvidenceType,
    KnowledgeCategory,
    KnowledgeStatus,
)


def test_knowledge_category_covers_plan_vocabulary() -> None:
    assert {c.value for c in KnowledgeCategory} == {
        "COMPANY",
        "OFFERING",
        "AUDIENCE",
        "DIFFERENTIATOR",
        "PRICING",
        "CONTACT",
        "BRAND_VOICE",
        "TRUST",
    }


def test_knowledge_status_covers_plan_vocabulary() -> None:
    assert {s.value for s in KnowledgeStatus} == {
        "PROPOSED",
        "APPROVED",
        "REJECTED",
        "CONFLICT",
    }


def test_evidence_type_covers_plan_vocabulary() -> None:
    assert {e.value for e in EvidenceType} == {"EXPLICIT", "INFERRED"}
