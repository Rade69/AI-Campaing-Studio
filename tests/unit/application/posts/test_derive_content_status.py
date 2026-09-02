"""Unit tests for content status derivation (A12 dio 1)."""

from ai_campaign_studio.application.posts.derive_content_status import (
    derive_content_status,
)
from ai_campaign_studio.domain.content.claims import ContentClaim
from ai_campaign_studio.domain.content.enums import (
    ClaimStatus,
    ClaimType,
    ContentStatus,
)


def _claim(status: ClaimStatus) -> ContentClaim:
    return ContentClaim(id="c1", text="t", type=ClaimType.FACT, status=status)


def test_empty_claims_yield_draft() -> None:
    assert derive_content_status(()) is ContentStatus.DRAFT


def test_prohibited_yields_needs_review() -> None:
    claims = (
        _claim(ClaimStatus.VERIFIED_BY_FACT),
        _claim(ClaimStatus.PROHIBITED),
    )
    assert derive_content_status(claims) is ContentStatus.NEEDS_REVIEW


def test_unsupported_yields_needs_review() -> None:
    claims = (
        _claim(ClaimStatus.VERIFIED_BY_FACT),
        _claim(ClaimStatus.UNSUPPORTED),
    )
    assert derive_content_status(claims) is ContentStatus.NEEDS_REVIEW


def test_no_warnings_yield_draft() -> None:
    claims = (
        _claim(ClaimStatus.VERIFIED_BY_FACT),
        _claim(ClaimStatus.NON_FACTUAL),
    )
    assert derive_content_status(claims) is ContentStatus.DRAFT
