"""Content domain entities (A3)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ai_campaign_studio.domain.common.ids import (
    BrandSnapshotId,
    CampaignItemId,
    FactId,
    PostId,
    RevisionId,
)
from ai_campaign_studio.domain.content.claims import ContentClaim
from ai_campaign_studio.domain.content.enums import ContentPayloadType, ContentStatus


@dataclass(frozen=True)
class CampaignTarget:
    """A channel/platform/format destination for one content piece.

    ``channel``/``platform_code``/``format_code`` are plain strings here to
    keep the domain free of the ``channels`` registry package; callers map
    them to ``Channel`` and registry codes at the boundary.
    """

    channel: str
    platform_code: str
    format_code: str


@dataclass(frozen=True)
class ContentPiece:
    """A single generated content piece for one campaign item.

    Contract for the application layer (not enforced inside this dataclass):
    an ``APPROVED`` ``ContentPiece`` must never be changed silently. Revising
    approved content must create a new ``Revision`` record and return the
    status to ``NEEDS_REVIEW``.
    """

    id: PostId
    campaign_item_id: CampaignItemId
    target: CampaignTarget
    payload_type: ContentPayloadType
    status: ContentStatus
    brand_snapshot_id: BrandSnapshotId
    created_at: datetime
    updated_at: datetime
    facts_allowed: tuple[FactId, ...] = ()
    claims: tuple[ContentClaim, ...] = ()
    revision_ids: tuple[RevisionId, ...] = ()
    payload: SocialPostPayload | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "facts_allowed", tuple(self.facts_allowed))
        object.__setattr__(self, "claims", tuple(self.claims))
        object.__setattr__(self, "revision_ids", tuple(self.revision_ids))


@dataclass(frozen=True)
class SocialPostPayload:
    """The concrete payload of a ``SOCIAL_POST`` content piece."""

    headline: str
    caption: str
    hook: str
    body: str
    cta: str
    hashtags: tuple[str, ...] = ()
    visual_direction: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "hashtags", tuple(self.hashtags))
