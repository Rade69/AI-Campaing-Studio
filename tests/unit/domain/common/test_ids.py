"""Unit tests for typed ID aliases (A3 extension)."""

from ai_campaign_studio.domain.common.ids import (
    BrandId,
    BrandSnapshotId,
    CampaignId,
    CampaignItemId,
    CampaignPlanId,
    FactId,
    PostId,
    ProjectId,
    RevisionId,
    VisualSystemId,
    new_id,
)

_ALIASES = [
    ProjectId,
    BrandId,
    BrandSnapshotId,
    FactId,
    CampaignId,
    CampaignPlanId,
    CampaignItemId,
    PostId,
    RevisionId,
    VisualSystemId,
]


def test_aliases_are_runtime_transparent_strings() -> None:
    for alias in _ALIASES:
        value = alias("abc-123")
        assert value == "abc-123"
        assert isinstance(value, str)


def test_all_expected_aliases_exist() -> None:
    names = {alias.__name__ for alias in _ALIASES}
    assert names == {
        "ProjectId",
        "BrandId",
        "BrandSnapshotId",
        "FactId",
        "CampaignId",
        "CampaignPlanId",
        "CampaignItemId",
        "PostId",
        "RevisionId",
        "VisualSystemId",
    }


def test_new_id_still_returns_plain_str() -> None:
    value = new_id()
    assert isinstance(value, str)
    assert len(value) == 36  # canonical UUID4 string form
