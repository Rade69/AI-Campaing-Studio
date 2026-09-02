"""LoadBrandFixture use-case (A6).

Owns the orchestration of loading a brand fixture: validate the JSON, map it
to domain objects, then persist everything in one transaction. Depends only on
the repository ports and a duck-typed transaction boundary — no SQLite import
(``SqliteUnitOfWork`` satisfies the protocol at runtime).
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ai_campaign_studio.application.mappers.brand_fixture_mapper import (
    map_brand_fixture,
)
from ai_campaign_studio.application.schemas.brand_fixture import BrandFixtureSchema
from ai_campaign_studio.domain.brand.entities import BrandSnapshot
from ai_campaign_studio.ports.repositories import (
    BrandRepositoryPort,
    FactRepositoryPort,
)


class _UnitOfWork(Protocol):
    """Minimal transaction boundary the use-case needs.

    Implemented by ``SqliteUnitOfWork`` (begin / commit-or-rollback). Declared
    here so this use-case keeps no infrastructure import.
    """

    def __enter__(self) -> _UnitOfWork: ...

    def __exit__(
        self, exc_type: object, exc_value: object, traceback: object
    ) -> bool: ...

    def commit(self) -> None: ...


class LoadBrandFixture:
    """Load a brand fixture file into the domain and persist it atomically.

    ``brand_repo``, ``fact_repo`` and ``unit_of_work`` must all be bound to the
    same database connection — the caller guarantees this (the repositories are
    typically constructed over ``unit_of_work.connection``).
    """

    def __init__(
        self,
        brand_repo: BrandRepositoryPort,
        fact_repo: FactRepositoryPort,
        unit_of_work: _UnitOfWork,
    ) -> None:
        self._brand_repo = brand_repo
        self._fact_repo = fact_repo
        self._unit_of_work = unit_of_work

    def execute(self, fixture_path: Path) -> BrandSnapshot:
        """Validate, map and persist a fixture; return the new snapshot.

        Validation happens before any repository call, so an invalid fixture
        leaves the repositories untouched. Persistence is one transaction: if
        any save fails, the unit-of-work rolls back and nothing is stored.
        """
        text = fixture_path.read_text(encoding="utf-8")
        fixture = BrandFixtureSchema.model_validate_json(text)
        brand, snapshot, facts = map_brand_fixture(fixture)

        with self._unit_of_work:
            self._brand_repo.save_brand(brand)
            for fact in facts:
                self._fact_repo.save_fact(fact)
            self._brand_repo.save_snapshot(snapshot)
            self._unit_of_work.commit()

        return snapshot
