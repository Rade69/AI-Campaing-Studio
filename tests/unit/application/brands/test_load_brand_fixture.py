"""Unit tests for LoadBrandFixture (A6) with fake repositories."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ai_campaign_studio.application.brands.load_brand_fixture import LoadBrandFixture
from ai_campaign_studio.domain.brand.entities import BrandSnapshot

_FIXTURE_PATH = (
    Path(__file__).resolve().parents[4] / "resources" / "fixtures" / "brightsmile.json"
)


class _FakeUnitOfWork:
    def __init__(self) -> None:
        self.committed = False

    def __enter__(self) -> _FakeUnitOfWork:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:  # noqa: ANN001
        return False

    def commit(self) -> None:
        self.committed = True


class _FakeBrandRepository:
    def __init__(self) -> None:
        self.saved_brands: list = []
        self.saved_snapshots: list = []

    def save_brand(self, brand) -> None:  # noqa: ANN001
        self.saved_brands.append(brand)

    def save_snapshot(self, snapshot) -> None:  # noqa: ANN001
        self.saved_snapshots.append(snapshot)

    def get_snapshot(self, snapshot_id):  # noqa: ANN001
        del snapshot_id
        return None


class _FakeFactRepository:
    def __init__(self) -> None:
        self.saved_facts: list = []

    def save_fact(self, fact) -> None:  # noqa: ANN001
        self.saved_facts.append(fact)

    def get_fact(self, fact_id):  # noqa: ANN001
        del fact_id
        return None

    def list_snapshot_facts(self, snapshot_id):  # noqa: ANN001
        del snapshot_id
        return ()


def test_load_persists_brand_facts_and_snapshot() -> None:
    brand_repo = _FakeBrandRepository()
    fact_repo = _FakeFactRepository()
    uow = _FakeUnitOfWork()
    use_case = LoadBrandFixture(brand_repo, fact_repo, uow)

    snapshot = use_case.execute(_FIXTURE_PATH)

    assert isinstance(snapshot, BrandSnapshot)
    assert len(brand_repo.saved_brands) == 1
    assert len(fact_repo.saved_facts) == 3
    assert len(brand_repo.saved_snapshots) == 1
    assert uow.committed is True


def test_invalid_fixture_raises_before_repository_calls(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    payload = {
        "brand": {"name": "X"},
        "default_content_language_context": {"language_family": "EN", "locale": "EN"},
        "voice": {"formality": "friendly"},
        "audiences": [{"id": "a", "name": "A", "description": "d"}],
        "services": [{"id": "s", "name": "S", "description": "d"}],
        "facts": [],  # empty facts -> invalid
        "restrictions": [],
        "visual_identity": {},
    }
    bad.write_text(json.dumps(payload), encoding="utf-8")

    brand_repo = _FakeBrandRepository()
    fact_repo = _FakeFactRepository()
    uow = _FakeUnitOfWork()
    use_case = LoadBrandFixture(brand_repo, fact_repo, uow)

    with pytest.raises(ValidationError):
        use_case.execute(bad)

    assert brand_repo.saved_brands == []
    assert brand_repo.saved_snapshots == []
    assert fact_repo.saved_facts == []
    assert uow.committed is False


def test_use_case_runs_against_port_fakes_only() -> None:
    """The use-case works with plain in-memory port implementations (no SQLite)."""
    use_case = LoadBrandFixture(
        _FakeBrandRepository(), _FakeFactRepository(), _FakeUnitOfWork()
    )
    snapshot = use_case.execute(_FIXTURE_PATH)
    assert snapshot.version == 1
    assert len(snapshot.approved_fact_ids) == 3
