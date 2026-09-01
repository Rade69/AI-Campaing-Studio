"""Integration tests: bootstrap composition root (P0.22)."""

from __future__ import annotations

import socket
from pathlib import Path

from ai_campaign_studio.bootstrap import create_bootstrap, run_health_check
from ai_campaign_studio.config.paths import AppPaths
from ai_campaign_studio.infrastructure.secrets.environment_secret_store import (
    EnvironmentSecretStore,
)


def _block_network(monkeypatch) -> None:
    def _forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("network access attempted during bootstrap")

    monkeypatch.setattr(socket, "socket", _forbidden)
    monkeypatch.setattr(socket, "create_connection", _forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", _forbidden)


def test_bootstrap_builds_offline(tmp_path: Path, monkeypatch) -> None:
    _block_network(monkeypatch)

    paths = AppPaths(data_dir_override=tmp_path / "data")
    bootstrap = create_bootstrap(paths=paths)
    try:
        # Database exists on disk.
        assert bootstrap.paths.database_path.exists()

        # Migration applied: schema_migrations table exists.
        row = bootstrap.database_connection.execute(
            "SELECT name FROM sqlite_master WHERE name='schema_migrations'"
        ).fetchone()
        assert row is not None

        # Platform registry loaded (not empty).
        assert len(bootstrap.platform_registry.list_platforms()) > 0

        # Provider registry loaded (not empty).
        assert len(bootstrap.provider_registry.list_providers()) > 0

        # Translator loaded.
        assert bootstrap.translator.t("app.title") == "AI Campaign Studio"

        # Health check reports ok.
        assert run_health_check(bootstrap)["status"] == "ok"
    finally:
        bootstrap.job_manager.shutdown(wait=False)
        bootstrap.database_connection.close()


def test_bootstrap_uses_environment_secret_store_in_development(
    tmp_path: Path, monkeypatch
) -> None:
    _block_network(monkeypatch)
    paths = AppPaths(data_dir_override=tmp_path / "data")
    bootstrap = create_bootstrap(paths=paths)
    try:
        assert isinstance(bootstrap.secret_store, EnvironmentSecretStore)
    finally:
        bootstrap.job_manager.shutdown(wait=False)
        bootstrap.database_connection.close()
