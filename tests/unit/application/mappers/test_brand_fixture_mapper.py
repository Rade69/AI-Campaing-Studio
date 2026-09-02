"""Unit + end-to-end tests for the brand fixture mapper (A4)."""

from pathlib import Path

from ai_campaign_studio.application.mappers.brand_fixture_mapper import (
    map_brand_fixture,
)
from ai_campaign_studio.application.schemas.brand_fixture import BrandFixtureSchema
from ai_campaign_studio.domain.brand.entities import Brand, BrandSnapshot
from ai_campaign_studio.domain.facts.entities import ApprovedFact
from ai_campaign_studio.domain.facts.enums import FactStatus

_FIXTURE_PATH = (
    Path(__file__).resolve().parents[4] / "resources" / "fixtures" / "brightsmile.json"
)


def _load_fixture() -> BrandFixtureSchema:
    return BrandFixtureSchema.model_validate_json(
        _FIXTURE_PATH.read_text(encoding="utf-8")
    )


def test_mapper_returns_domain_types() -> None:
    brand, snapshot, facts = map_brand_fixture(_load_fixture())
    assert isinstance(brand, Brand)
    assert isinstance(snapshot, BrandSnapshot)
    assert isinstance(facts, tuple)
    assert all(isinstance(fact, ApprovedFact) for fact in facts)


def test_all_facts_are_approved() -> None:
    _, _, facts = map_brand_fixture(_load_fixture())
    assert facts
    assert all(fact.status is FactStatus.APPROVED for fact in facts)


def test_snapshot_fact_ids_match_facts_exactly() -> None:
    _, snapshot, facts = map_brand_fixture(_load_fixture())
    assert snapshot.approved_fact_ids == tuple(fact.id for fact in facts)
    assert len(snapshot.approved_fact_ids) == len(facts)
    assert len(set(snapshot.approved_fact_ids)) == len(facts)  # no duplicates


def test_language_locale_script_mapped_from_context() -> None:
    _, snapshot, _ = map_brand_fixture(_load_fixture())
    assert snapshot.language == "BHS"
    assert snapshot.locale == "BHS_LATIN"
    assert snapshot.script == "LATIN"


def test_snapshot_is_version_one_and_linked_to_brand() -> None:
    brand, snapshot, _ = map_brand_fixture(_load_fixture())
    assert snapshot.version == 1
    assert snapshot.brand_id == brand.id


def test_fact_fields_map_from_fixture() -> None:
    _, _, facts = map_brand_fixture(_load_fixture())
    logical_ids = {fact.logical_fact_id for fact in facts}
    assert "fact-location" in logical_ids
    assert all(fact.version == 1 for fact in facts)
    assert all(fact.content for fact in facts)
    assert all(fact.source_ref.source_type == "fixture" for fact in facts)
    assert all(fact.superseded_by is None for fact in facts)
    assert all(fact.deleted_at is None for fact in facts)


def test_end_to_end_json_to_domain() -> None:
    """JSON file -> Pydantic validation -> immutable domain objects."""
    schema = _load_fixture()
    brand, snapshot, facts = map_brand_fixture(schema)

    assert brand.name == "BrightSmile Dental"
    assert len(facts) >= 3
    assert snapshot.brand_id == brand.id
    assert snapshot.approved_fact_ids == tuple(fact.id for fact in facts)
