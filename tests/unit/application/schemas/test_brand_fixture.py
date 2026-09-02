"""Unit tests for the brand fixture boundary schema (A4)."""

import pytest
from pydantic import ValidationError

from ai_campaign_studio.application.schemas.brand_fixture import BrandFixtureSchema


def _valid_payload() -> dict:
    return {
        "brand": {"name": "Test Brand"},
        "default_content_language_context": {
            "language_family": "EN",
            "locale": "EN",
        },
        "voice": {"formality": "friendly"},
        "audiences": [{"id": "a1", "name": "Adults", "description": "25-45"}],
        "services": [{"id": "s1", "name": "Service", "description": "desc"}],
        "facts": [
            {
                "logical_fact_id": "f1",
                "version": 1,
                "content": "Fact one.",
                "source_ref": {"source_type": "fixture", "uri": "fixture://x"},
            },
            {
                "logical_fact_id": "f2",
                "version": 1,
                "content": "Fact two.",
                "source_ref": {"source_type": "fixture", "uri": "fixture://x"},
            },
        ],
        "restrictions": [{"description": "No guarantees."}],
        "visual_identity": {},
    }


def test_valid_fixture_parses() -> None:
    schema = BrandFixtureSchema.model_validate(_valid_payload())
    assert schema.brand.name == "Test Brand"
    assert len(schema.facts) == 2
    assert schema.default_content_language_context.language_family.value == "EN"


def test_empty_facts_rejected() -> None:
    payload = _valid_payload()
    payload["facts"] = []
    with pytest.raises(ValidationError):
        BrandFixtureSchema.model_validate(payload)


def test_duplicate_logical_fact_id_rejected() -> None:
    payload = _valid_payload()
    payload["facts"][1]["logical_fact_id"] = payload["facts"][0]["logical_fact_id"]
    with pytest.raises(ValidationError):
        BrandFixtureSchema.model_validate(payload)


def test_missing_source_ref_rejected() -> None:
    payload = _valid_payload()
    del payload["facts"][0]["source_ref"]
    with pytest.raises(ValidationError):
        BrandFixtureSchema.model_validate(payload)


def test_empty_source_type_rejected() -> None:
    payload = _valid_payload()
    payload["facts"][0]["source_ref"]["source_type"] = ""
    with pytest.raises(ValidationError):
        BrandFixtureSchema.model_validate(payload)
