"""Content domain enum tests (A3)."""

from ai_campaign_studio.domain.content.enums import (
    ClaimStatus,
    ClaimType,
    ContentPayloadType,
    ContentStatus,
)


def test_content_status_members() -> None:
    assert {m.value for m in ContentStatus} == {
        "PLANNED",
        "GENERATING",
        "DRAFT",
        "NEEDS_REVIEW",
        "APPROVED",
        "REJECTED",
        "EXPORTED",
    }


def test_content_payload_type_members() -> None:
    assert {m.value for m in ContentPayloadType} == {"SOCIAL_POST"}


def test_claim_type_members() -> None:
    assert {m.value for m in ClaimType} == {"FACT", "CTA", "OPINION", "CREATIVE"}


def test_claim_status_members() -> None:
    assert {m.value for m in ClaimStatus} == {
        "VERIFIED_BY_FACT",
        "UNSUPPORTED",
        "USER_APPROVED",
        "PROHIBITED",
        "NON_FACTUAL",
    }
