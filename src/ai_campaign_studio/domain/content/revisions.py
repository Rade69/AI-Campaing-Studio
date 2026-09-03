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


class RevisionType(StrEnum):
    """The kind of revision a user/agent requests (plan section 38)."""

    SHORTER = "SHORTER"
    LONGER = "LONGER"
    STRONGER_HOOK = "STRONGER_HOOK"
    MORE_PROFESSIONAL = "MORE_PROFESSIONAL"
    MORE_FRIENDLY = "MORE_FRIENDLY"
    LESS_PROMOTIONAL = "LESS_PROMOTIONAL"
    NEW_CTA = "NEW_CTA"
    NEW_HEADLINE = "NEW_HEADLINE"
    NEW_VISUAL_DIRECTION = "NEW_VISUAL_DIRECTION"
    CUSTOM = "CUSTOM"


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
