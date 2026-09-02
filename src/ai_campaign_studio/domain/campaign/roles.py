"""Campaign message roles (A3)."""

from enum import StrEnum


class CampaignRole(StrEnum):
    """The message role a campaign item plays in a sequence.

    Not every role must be used in the first fixture. ``CampaignTemplate``
    selects an ordered ``role_sequence`` from this set.
    """

    PROBLEM = "PROBLEM"
    EDUCATION = "EDUCATION"
    INSIGHT = "INSIGHT"
    BENEFIT = "BENEFIT"
    PROOF = "PROOF"
    TRUST = "TRUST"
    OBJECTION = "OBJECTION"
    MYTH_BUSTING = "MYTH_BUSTING"
    COMPARISON = "COMPARISON"
    BEHIND_THE_SCENES = "BEHIND_THE_SCENES"
    PRODUCT = "PRODUCT"
    OFFER = "OFFER"
    URGENCY = "URGENCY"
    ACTION = "ACTION"
    COMMUNITY = "COMMUNITY"
    STORY = "STORY"
    FAQ = "FAQ"
