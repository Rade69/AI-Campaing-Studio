"""Content domain enums (A3)."""

from enum import StrEnum


class ContentStatus(StrEnum):
    """Lifecycle of a content piece."""

    PLANNED = "PLANNED"
    GENERATING = "GENERATING"
    DRAFT = "DRAFT"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPORTED = "EXPORTED"


class ContentPayloadType(StrEnum):
    """The kind of content payload.

    Faza 1 implements only ``SOCIAL_POST``; additional types may be added
    later without changing the campaign plan model.
    """

    SOCIAL_POST = "SOCIAL_POST"


class ClaimType(StrEnum):
    """The kind of claim within generated content."""

    FACT = "FACT"
    CTA = "CTA"
    OPINION = "OPINION"
    CREATIVE = "CREATIVE"


class ClaimStatus(StrEnum):
    """Verification/approval state of a claim."""

    VERIFIED_BY_FACT = "VERIFIED_BY_FACT"
    UNSUPPORTED = "UNSUPPORTED"
    USER_APPROVED = "USER_APPROVED"
    PROHIBITED = "PROHIBITED"
    NON_FACTUAL = "NON_FACTUAL"
