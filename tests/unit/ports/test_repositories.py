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
    "IngestionRepositoryPort",
    "TelemetryRepositoryPort",
]


def test_all_repository_ports_are_defined() -> None:
    for name in _ALL_PORTS:
        cls = getattr(repositories, name)
        assert issubclass(cls, Protocol)


def test_ports_are_runtime_checkable() -> None:
    class _FakeBrandRepository:
        def save_brand(self, brand) -> None:
            del brand

        def get_brand(self, brand_id):
            del brand_id
            return None

        def save_snapshot(self, snapshot) -> None:
            del snapshot

        def get_snapshot(self, snapshot_id):
            del snapshot_id
            return None

        def get_latest_snapshot(self, brand_id):
            del brand_id
            return None

        def list_snapshots(self, brand_id):
            del brand_id
            return ()

    # structural isinstance check works because the Protocol is runtime_checkable
    assert isinstance(_FakeBrandRepository(), repositories.BrandRepositoryPort)


def test_ingestion_port_declares_lease_queue_methods() -> None:
    """S2-G2: the crawl-target lease queue surface is part of the port."""
    port = repositories.IngestionRepositoryPort
    for method in (
        "register_crawl_targets",
        "claim_next_crawl_target",
        "update_crawl_target_state",
        "recover_expired_leases",
        "get_crawl_target",
        "list_crawl_targets_by_run",
    ):
        assert hasattr(port, method), f"missing lease-queue method: {method}"
