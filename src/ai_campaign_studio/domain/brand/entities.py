"""Brand domain entities (A3).

Owns the ``Brand`` aggregate reference and the immutable ``BrandSnapshot``.
``BrandSnapshot`` is frozen and must never be mutated after creation — a new
version means a new snapshot object, never an in-place edit.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ai_campaign_studio.domain.brand.value_objects import (
    Audience,
    BrandVoice,
    Restriction,
    ServiceDefinition,
    VisualIdentity,
)
from ai_campaign_studio.domain.common.ids import BrandId, BrandSnapshotId, FactId


@dataclass(frozen=True)
class Brand:
    """Root brand aggregate reference."""

    id: BrandId
    name: str
    created_at: datetime


@dataclass(frozen=True)
class BrandSnapshot:
    """Immutable point-in-time snapshot of a brand.

    ``language``/``locale``/``script`` are plain strings here to keep the
    domain layer free of the ``localization`` package; callers map them to the
    existing ``ContentLanguageFamily``/``Script`` enum values at the boundary.
    """

    id: BrandSnapshotId
    brand_id: BrandId
    version: int
    language: str
    locale: str
    script: str
    voice: BrandVoice
    audiences: tuple[Audience, ...]
    services: tuple[ServiceDefinition, ...]
    visual_identity: VisualIdentity
    restrictions: tuple[Restriction, ...]
    approved_fact_ids: tuple[FactId, ...]
    created_at: datetime

    def __post_init__(self) -> None:
        for name in ("audiences", "services", "restrictions", "approved_fact_ids"):
            object.__setattr__(self, name, tuple(getattr(self, name)))
