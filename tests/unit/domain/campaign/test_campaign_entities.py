"""Campaign entity tests (A3)."""

from datetime import UTC, datetime

from ai_campaign_studio.domain.campaign.entities import (
    Campaign,
    CampaignBrief,
    CampaignItem,
    CampaignPlan,
)
from ai_campaign_studio.domain.campaign.enums import (
    CampaignItemStatus,
    CampaignPlanStatus,
    CampaignStatus,
)
from ai_campaign_studio.domain.campaign.roles import CampaignRole
from ai_campaign_studio.domain.content.entities import CampaignTarget


def _dt() -> datetime:
    return datetime(2026, 9, 2, tzinfo=UTC)


def test_campaign_brief_coerces_targets_to_tuple() -> None:
    target = CampaignTarget(
        channel="SOCIAL", platform_code="INSTAGRAM", format_code="FEED_POST"
    )
    brief = CampaignBrief(
        id="brief1",
        offer="Offer",
        goal="Goal",
        audience_text="Audience",
        targets=[target],
        content_piece_count=6,
        content_language_context="BHS_LATIN",
        created_at=_dt(),
    )

    assert isinstance(brief.targets, tuple)
    assert brief.targets == (target,)


def test_campaign_plan_coerces_items_to_tuple() -> None:
    item = CampaignItem(
        id="ci1",
        order=1,
        role=CampaignRole.PROBLEM,
        topic="Topic",
        goal="Goal",
        status=CampaignItemStatus.PLANNED,
        facts_needed=["location"],
    )
    plan = CampaignPlan(
        id="p1",
        campaign_id="c1",
        version=1,
        status=CampaignPlanStatus.DRAFT,
        created_at=_dt(),
        items=[item],
    )

    assert isinstance(plan.items, tuple)
    assert plan.items == (item,)


def test_campaign_constructs() -> None:
    campaign = Campaign(
        id="c1",
        brand_id="b1",
        brand_snapshot_id="bs1",
        brief_id="brief1",
        status=CampaignStatus.DRAFT,
        created_at=_dt(),
    )

    assert campaign.status is CampaignStatus.DRAFT
