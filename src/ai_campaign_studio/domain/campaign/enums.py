"""Campaign domain enums (A3)."""

from enum import StrEnum


class CampaignStatus(StrEnum):
    """Lifecycle of a campaign."""

    DRAFT = "DRAFT"
    PLAN_GENERATED = "PLAN_GENERATED"
    PLAN_APPROVED = "PLAN_APPROVED"
    GENERATING_POSTS = "GENERATING_POSTS"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    EXPORTED = "EXPORTED"


class CampaignPlanStatus(StrEnum):
    """Lifecycle of a campaign plan."""

    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    SUPERSEDED = "SUPERSEDED"


class CampaignItemStatus(StrEnum):
    """Lifecycle of a single planned campaign item."""

    PLANNED = "PLANNED"
    APPROVED = "APPROVED"
    GENERATED = "GENERATED"
    REJECTED = "REJECTED"
