"""Unit tests for RevisionType enum (A12 dio 2)."""

from ai_campaign_studio.domain.content.revisions import RevisionType

_EXPECTED = {
    "SHORTER",
    "LONGER",
    "STRONGER_HOOK",
    "MORE_PROFESSIONAL",
    "MORE_FRIENDLY",
    "LESS_PROMOTIONAL",
    "NEW_CTA",
    "NEW_HEADLINE",
    "NEW_VISUAL_DIRECTION",
    "CUSTOM",
}


def test_revision_type_has_all_ten_values() -> None:
    assert {member.value for member in RevisionType} == _EXPECTED
    assert len(RevisionType) == 10
