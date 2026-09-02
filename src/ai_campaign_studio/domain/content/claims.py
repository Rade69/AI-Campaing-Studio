"""Content claim value object (A3)."""

from __future__ import annotations

from dataclasses import dataclass

from ai_campaign_studio.domain.common.ids import FactId
from ai_campaign_studio.domain.content.enums import ClaimStatus, ClaimType


@dataclass(frozen=True)
class ContentClaim:
    """A single verifiable claim within generated content."""

    id: str
    text: str
    type: ClaimType
    status: ClaimStatus
    fact_ids: tuple[FactId, ...] = ()
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "fact_ids", tuple(self.fact_ids))
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))
