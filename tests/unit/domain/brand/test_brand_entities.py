"""Unit tests for brand entities (A3)."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from ai_campaign_studio.domain.brand.entities import Brand, BrandSnapshot
from ai_campaign_studio.domain.brand.value_objects import (
    Audience,
    BrandVoice,
    Restriction,
    ServiceDefinition,
    VisualIdentity,
)
from ai_campaign_studio.domain.common.ids import BrandId, BrandSnapshotId, FactId

_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def _snapshot() -> BrandSnapshot:
    return BrandSnapshot(
        id=BrandSnapshotId("snap-1"),
        brand_id=BrandId("brand-1"),
        version=1,
        language="EN",
        locale="en-US",
        script="LATIN",
        voice=BrandVoice(formality="friendly"),
        audiences=[Audience(id="a1", name="Adults", description="25-45")],
        services=[ServiceDefinition(id="s1", name="Implants", description="...")],
        visual_identity=VisualIdentity(),
        restrictions=[Restriction(description="No medical guarantees.")],
        approved_fact_ids=[FactId("fact-1"), FactId("fact-2")],
        created_at=_CREATED_AT,
    )


def test_brand_is_frozen() -> None:
    brand = Brand(id=BrandId("b1"), name="Acme", created_at=_CREATED_AT)
    assert brand.name == "Acme"
    with pytest.raises(FrozenInstanceError):
        brand.name = "changed"


def test_brand_snapshot_is_frozen() -> None:
    snapshot = _snapshot()
    with pytest.raises(FrozenInstanceError):
        snapshot.version = 2
    with pytest.raises(FrozenInstanceError):
        snapshot.voice = BrandVoice(formality="formal")


def test_brand_snapshot_collections_are_tuples() -> None:
    snapshot = _snapshot()
    # list inputs were coerced to tuples at construction time.
    assert isinstance(snapshot.audiences, tuple)
    assert isinstance(snapshot.services, tuple)
    assert isinstance(snapshot.restrictions, tuple)
    assert isinstance(snapshot.approved_fact_ids, tuple)


def test_brand_snapshot_fields_round_trip() -> None:
    snapshot = _snapshot()
    assert snapshot.id == BrandSnapshotId("snap-1")
    assert snapshot.brand_id == BrandId("brand-1")
    assert snapshot.version == 1
    assert snapshot.language == "EN"
    assert snapshot.locale == "en-US"
    assert snapshot.script == "LATIN"
    assert snapshot.voice.formality == "friendly"
    assert snapshot.approved_fact_ids == (FactId("fact-1"), FactId("fact-2"))
