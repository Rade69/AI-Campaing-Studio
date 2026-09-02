"""Unit tests for CreateCampaign (A9) with fake repositories."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ai_campaign_studio.application.campaigns.create_campaign import CreateCampaign
from ai_campaign_studio.domain.campaign.enums import CampaignStatus
from ai_campaign_studio.domain.common.ids import BrandId, BrandSnapshotId


class _FakeUnitOfWork:
    def __init__(self) -> None:
        self.committed = False

    def __enter__(self) -> _FakeUnitOfWork:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:  # noqa: ANN001
        return False

    def commit(self) -> None:
        self.committed = True


class _FakeCampaignRepository:
    def __init__(self) -> None:
        self.briefs: dict = {}
        self.campaigns: dict = {}

    def save_brief(self, brief) -> None:  # noqa: ANN001
        self.briefs[brief.id] = brief

    def save_campaign(self, campaign) -> None:  # noqa: ANN001
        self.campaigns[campaign.id] = campaign

    def get_campaign(self, campaign_id):  # noqa: ANN001
        return self.campaigns.get(campaign_id)

    def get_brief(self, brief_id):  # noqa: ANN001
        return self.briefs.get(brief_id)

    def save_plan(self, plan) -> None:  # noqa: ANN001
        del plan

    def get_plan(self, plan_id):  # noqa: ANN001
        del plan_id
        return None


def _valid_brief() -> dict:
    return {
        "offer": "Dental implants",
        "goal": "Book consultations",
        "audience_text": "Adults 25-55",
        "targets": [
            {
                "channel": "SOCIAL",
                "platform_code": "INSTAGRAM",
                "format_code": "FEED_POST",
            }
        ],
        "content_piece_count": 3,
        "content_language_context": "BHS_LATIN",
    }


def test_create_campaign_returns_draft_and_persists() -> None:
    repo = _FakeCampaignRepository()
    uow = _FakeUnitOfWork()
    use_case = CreateCampaign(repo, uow)

    campaign = use_case.execute(
        BrandId("brand-1"), BrandSnapshotId("snap-1"), _valid_brief()
    )

    assert campaign.status is CampaignStatus.DRAFT
    assert campaign.brand_id == BrandId("brand-1")
    assert campaign.brand_snapshot_id == BrandSnapshotId("snap-1")
    assert campaign.brief_id in repo.briefs
    assert campaign.id in repo.campaigns
    assert uow.committed is True


def test_invalid_brief_raises_before_persistence() -> None:
    repo = _FakeCampaignRepository()
    uow = _FakeUnitOfWork()
    use_case = CreateCampaign(repo, uow)

    bad_brief = _valid_brief()
    bad_brief["content_piece_count"] = 0  # invalid: must be > 0

    with pytest.raises(ValidationError):
        use_case.execute(BrandId("brand-1"), BrandSnapshotId("snap-1"), bad_brief)

    assert repo.briefs == {}
    assert repo.campaigns == {}
    assert uow.committed is False
