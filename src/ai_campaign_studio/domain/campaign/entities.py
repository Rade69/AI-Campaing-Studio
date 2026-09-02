"""Campaign domain entities (A3)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ai_campaign_studio.domain.campaign.enums import (
    CampaignItemStatus,
    CampaignPlanStatus,
    CampaignStatus,
)
from ai_campaign_studio.domain.campaign.roles import CampaignRole
from ai_campaign_studio.domain.common.ids import (
    BrandId,
    BrandSnapshotId,
    CampaignId,
    CampaignItemId,
    CampaignPlanId,
)
from ai_campaign_studio.domain.content.entities import CampaignTarget


@dataclass(frozen=True)
class CampaignBrief:
    """Input brief that seeds a campaign.

    ``content_language_context`` is a plain string (e.g. ``"BHS_LATIN"`` or
    ``"EN"``) to keep the domain free of the ``localization`` package; callers
    map it to the existing locale enum at the boundary.
    """

    id: str
    offer: str
    goal: str
    audience_text: str
    targets: tuple[CampaignTarget, ...]
    content_piece_count: int
    content_language_context: str
    created_at: datetime
    special_instructions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "targets", tuple(self.targets))
        object.__setattr__(
            self, "special_instructions", tuple(self.special_instructions)
        )


@dataclass(frozen=True)
class Campaign:
    """A campaign aggregate reference."""

    id: CampaignId
    brand_id: BrandId
    brand_snapshot_id: BrandSnapshotId
    brief_id: str
    status: CampaignStatus
    created_at: datetime


@dataclass(frozen=True)
class CampaignPlan:
    """An approved plan of ordered campaign items."""

    id: CampaignPlanId
    campaign_id: CampaignId
    version: int
    status: CampaignPlanStatus
    created_at: datetime
    items: tuple[CampaignItem, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "items", tuple(self.items))


@dataclass(frozen=True)
class CampaignItem:
    """A single planned content item within a campaign plan.

    ``facts_needed`` is a semantic need (free-text descriptions), not actual
    ``FactId`` values — actual fact selection happens in the later post-
    generation use case.
    """

    id: CampaignItemId
    order: int
    role: CampaignRole
    topic: str
    goal: str
    status: CampaignItemStatus
    target_audience_id: str | None = None
    facts_needed: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "facts_needed", tuple(self.facts_needed))
