"""Campaign domain tests (A3 — enums, roles, templates)."""

from ai_campaign_studio.domain.campaign.enums import (
    CampaignItemStatus,
    CampaignPlanStatus,
    CampaignStatus,
)
from ai_campaign_studio.domain.campaign.roles import CampaignRole
from ai_campaign_studio.domain.campaign.templates import LEAD_GENERATION_V1


def test_campaign_status_members() -> None:
    assert {m.value for m in CampaignStatus} == {
        "DRAFT",
        "PLAN_GENERATED",
        "PLAN_APPROVED",
        "GENERATING_POSTS",
        "IN_REVIEW",
        "APPROVED",
        "EXPORTED",
    }


def test_campaign_plan_status_members() -> None:
    assert {m.value for m in CampaignPlanStatus} == {"DRAFT", "APPROVED", "SUPERSEDED"}


def test_campaign_item_status_members() -> None:
    assert {m.value for m in CampaignItemStatus} == {
        "PLANNED",
        "APPROVED",
        "GENERATED",
        "REJECTED",
    }


def test_campaign_role_members() -> None:
    assert {m.value for m in CampaignRole} == {
        "PROBLEM",
        "EDUCATION",
        "INSIGHT",
        "BENEFIT",
        "PROOF",
        "TRUST",
        "OBJECTION",
        "MYTH_BUSTING",
        "COMPARISON",
        "BEHIND_THE_SCENES",
        "PRODUCT",
        "OFFER",
        "URGENCY",
        "ACTION",
        "COMMUNITY",
        "STORY",
        "FAQ",
    }


def test_lead_generation_v1_sequence() -> None:
    roles = LEAD_GENERATION_V1.role_sequence

    assert roles == (
        CampaignRole.PROBLEM,
        CampaignRole.EDUCATION,
        CampaignRole.PROOF,
        CampaignRole.OBJECTION,
        CampaignRole.BENEFIT,
        CampaignRole.OFFER,
        CampaignRole.ACTION,
    )
    assert len(roles) == 7
    assert len(set(roles)) == 7  # no duplicates
