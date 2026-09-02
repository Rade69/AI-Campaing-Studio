"""CreateCampaign use-case (A9).

Owns validating a raw brief, mapping it to the domain and persisting the brief
plus a DRAFT campaign atomically. Depends only on ``CampaignRepositoryPort``
and a duck-typed transaction boundary — no SQLite import.
"""

from __future__ import annotations

from typing import Protocol

from ai_campaign_studio.application.mappers.campaign_brief_mapper import (
    map_campaign_brief,
)
from ai_campaign_studio.application.schemas.campaign_brief import CampaignBriefInput
from ai_campaign_studio.domain.campaign.entities import Campaign
from ai_campaign_studio.domain.campaign.enums import CampaignStatus
from ai_campaign_studio.domain.common.ids import (
    BrandId,
    BrandSnapshotId,
    CampaignId,
    new_id,
)
from ai_campaign_studio.domain.common.timestamps import utc_now
from ai_campaign_studio.ports.repositories import CampaignRepositoryPort


class _UnitOfWork(Protocol):
    """Minimal transaction boundary the use-case needs."""

    def __enter__(self) -> _UnitOfWork: ...

    def __exit__(
        self, exc_type: object, exc_value: object, traceback: object
    ) -> bool: ...

    def commit(self) -> None: ...


class CreateCampaign:
    """Validate a brief and create a DRAFT campaign (brief + campaign atomic)."""

    def __init__(
        self,
        campaign_repo: CampaignRepositoryPort,
        unit_of_work: _UnitOfWork,
    ) -> None:
        self._campaign_repo = campaign_repo
        self._unit_of_work = unit_of_work

    def execute(
        self,
        brand_id: BrandId,
        brand_snapshot_id: BrandSnapshotId,
        raw_brief: dict,
    ) -> Campaign:
        """Validate, map and persist the brief + a DRAFT campaign.

        Validation happens before any repository call, so an invalid brief
        leaves the repositories untouched.
        """
        brief_input = CampaignBriefInput.model_validate(raw_brief)
        brief = map_campaign_brief(brief_input)

        campaign = Campaign(
            id=CampaignId(new_id()),
            brand_id=brand_id,
            brand_snapshot_id=brand_snapshot_id,
            brief_id=brief.id,
            status=CampaignStatus.DRAFT,
            created_at=utc_now(),
        )

        with self._unit_of_work:
            self._campaign_repo.save_brief(brief)
            self._campaign_repo.save_campaign(campaign)
            self._unit_of_work.commit()

        return campaign
