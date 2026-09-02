"""Visual domain entities (A3)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ai_campaign_studio.domain.common.ids import CampaignId, VisualSystemId
from ai_campaign_studio.domain.visual.enums import (
    Alignment,
    HeadlineScale,
    LayoutPrimitive,
)


@dataclass(frozen=True)
class CampaignVisualSystem:
    """The visual system for one campaign.

    ``image_treatment``/``logo_rule``/``cta_rule`` are left as plain strings
    for A3 (their full enum taxonomy is not specified); the A4 boundary schema
    will type them. ``primary_layout_family``/``headline_scale``/``alignment``
    use the typed visual enums.
    """

    id: VisualSystemId
    campaign_id: CampaignId
    primary_layout_family: LayoutPrimitive
    headline_scale: HeadlineScale
    image_treatment: str
    logo_rule: str
    cta_rule: str
    alignment: Alignment
    created_at: datetime
    secondary_layout_family: LayoutPrimitive | None = None
    style: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "style", tuple(self.style))
