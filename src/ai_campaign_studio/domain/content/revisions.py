"""Content revision record (A3).

``Revision.id`` is the stable ``content_revision_id`` seam required before
G10 (Performance/Analytics) per the analytics-ready plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from ai_campaign_studio.domain.common.ids import RevisionId


class RevisionOrigin(StrEnum):
    """Who or what produced a revision."""

    MANUAL = "MANUAL"
    AI = "AI"
    SYSTEM = "SYSTEM"


@dataclass(frozen=True)
class Revision:
    """An immutable record of one content change."""

    id: RevisionId
    entity_type: str
    entity_id: str
    version: int
    timestamp: datetime
    origin: RevisionOrigin
    previous_value: str
    new_value: str
    provider: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    instruction: str | None = None
