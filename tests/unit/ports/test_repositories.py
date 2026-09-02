"""Unit tests for repository ports (A5)."""

from typing import Protocol

from ai_campaign_studio.ports import repositories

_ALL_PORTS = [
    "BrandRepositoryPort",
    "FactRepositoryPort",
    "CampaignRepositoryPort",
    "ContentRepositoryPort",
    "VisualRepositoryPort",
    "RevisionRepositoryPort",
    "TelemetryRepositoryPort",
]


def test_all_seven_ports_are_defined() -> None:
    for name in _ALL_PORTS:
        cls = getattr(repositories, name)
        assert issubclass(cls, Protocol)


def test_ports_are_runtime_checkable() -> None:
    class _FakeBrandRepository:
        def save_brand(self, brand) -> None:
            del brand

        def save_snapshot(self, snapshot) -> None:
            del snapshot

        def get_snapshot(self, snapshot_id):
            del snapshot_id
            return None

    # structural isinstance check works because the Protocol is runtime_checkable
    assert isinstance(_FakeBrandRepository(), repositories.BrandRepositoryPort)
