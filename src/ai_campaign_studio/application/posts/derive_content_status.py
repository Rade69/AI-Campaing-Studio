"""Content status derivation (A12 dio 1, plan section 37).

Owns the pure function that maps a tuple of (linted) claims to the final
``ContentStatus``. Never auto-approves: the best outcome is ``DRAFT``.
"""

from __future__ import annotations

from ai_campaign_studio.domain.content.claims import ContentClaim
from ai_campaign_studio.domain.content.enums import ClaimStatus, ContentStatus


def derive_content_status(claims: tuple[ContentClaim, ...]) -> ContentStatus:
    """Derive the content status from already-linted claims.

    Any ``PROHIBITED`` or ``UNSUPPORTED`` claim forces ``NEEDS_REVIEW``;
    otherwise ``DRAFT``. ``APPROVED`` is never returned here — approval is an
    explicit future action.
    """
    if any(claim.status is ClaimStatus.PROHIBITED for claim in claims):
        return ContentStatus.NEEDS_REVIEW
    if any(claim.status is ClaimStatus.UNSUPPORTED for claim in claims):
        return ContentStatus.NEEDS_REVIEW
    return ContentStatus.DRAFT
