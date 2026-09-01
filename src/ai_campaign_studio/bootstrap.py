"""Composition root for the AI Campaign Studio application.

Owns wiring every P0 foundation adapter (Settings, paths, logger, translator,
both registries, secret store, database connection + migrations, job manager)
into a single ``Bootstrap`` for ``main.py``. Never calls a provider SDK,
network, browser, GUI, or campaign logic — fully offline by design.
"""

from __future__ import annotations

import logging
import platform
import sqlite3
from collections.abc import Callable
from pathlib import Path

from ai_campaign_studio.ai_registry.registry import AIProviderRegistry
from ai_campaign_studio.channels.registry import PlatformRegistry
from ai_campaign_studio.config.paths import AppPaths
from ai_campaign_studio.config.settings import AppSettings
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.secrets.environment_secret_store import (
    EnvironmentSecretStore,
)
from ai_campaign_studio.infrastructure.secrets.keyring_secret_store import (
    KeyringSecretStore,
)
from ai_campaign_studio.jobs.manager import JobManager
from ai_campaign_studio.localization.translator import Translator
from ai_campaign_studio.logging.config import configure_logging
from ai_campaign_studio.ports.secrets import SecretStorePort

_HEALTHY_KEY = "app.title"


class Bootstrap:
    """Application composition root.

    Carries the explicit set of wired foundation objects; it is NOT a service
    locator. ``create_bootstrap`` is the single place where concrete adapters
    are chosen and connected.
    """

    def __init__(
        self,
        *,
        settings: AppSettings,
        paths: AppPaths,
        logger: logging.Logger,
        translator: Translator,
        platform_registry: PlatformRegistry,
        provider_registry: AIProviderRegistry,
        secret_store: SecretStorePort,
        database_connection: sqlite3.Connection,
        migration_runner: Callable[..., list[int]],
        migrations_dir: Path,
        job_manager: JobManager,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.logger = logger
        self.translator = translator
        self.platform_registry = platform_registry
        self.provider_registry = provider_registry
        # Same object: AIProviderRegistry already implements ModelRegistryPort.
        self.model_registry = provider_registry
        self.secret_store = secret_store
        self.database_connection = database_connection
        self.migration_runner = migration_runner
        self.migrations_dir = migrations_dir
        self.job_manager = job_manager


def create_bootstrap(
    settings: AppSettings | None = None,
    paths: AppPaths | None = None,
) -> Bootstrap:
    """Build the application composition root (P0.22 build sequence).

    Order matters: Settings → Paths → logging → Translator → PlatformRegistry
    → AIProviderRegistry → SecretStore → DB connection → migrations →
    JobManager. Fully offline: no provider SDK, network, browser, GUI or
    campaign logic is touched.
    """
    # 1. Settings
    if settings is None:
        settings = AppSettings()

    # 2. AppPaths
    if paths is None:
        paths = AppPaths(
            app_name=settings.app_name,
            database_filename=settings.database_filename,
            data_dir_override=settings.data_dir_override,
            resource_dir_override=settings.resource_dir_override,
        )

    # 3. Logging
    logger = configure_logging(settings, paths)

    # 4. Translator resources
    translator = Translator(paths.resources_dir / "i18n")

    # 5. Platform registry (loaded/validated now, fail fast)
    platform_registry = PlatformRegistry(paths.resources_dir / "platforms")
    platform_registry.list_platforms()

    # 6. AI provider registry (loaded/validated now, fail fast)
    provider_registry = AIProviderRegistry(paths.resources_dir / "ai_providers")
    provider_registry.list_providers()

    # 7. Secret store adapter selection (no secret is read during boot)
    secret_store = _build_secret_store(settings)

    # 8. DB connection
    paths.ensure_directories()
    database_connection = create_connection(paths.database_path)

    # 9. Migrations
    migrations_dir = paths.resources_dir / "migrations"
    run_migrations(database_connection, migrations_dir)

    # 10. Job manager
    job_manager = JobManager()

    return Bootstrap(
        settings=settings,
        paths=paths,
        logger=logger,
        translator=translator,
        platform_registry=platform_registry,
        provider_registry=provider_registry,
        secret_store=secret_store,
        database_connection=database_connection,
        migration_runner=run_migrations,
        migrations_dir=migrations_dir,
        job_manager=job_manager,
    )


def _build_secret_store(settings: AppSettings) -> SecretStorePort:
    """Pick the secret-store adapter by environment (no secret is read)."""
    if settings.environment == "production":
        return KeyringSecretStore()
    return EnvironmentSecretStore()


def run_health_check(bootstrap: Bootstrap) -> dict[str, str]:
    """Return the machine-readable health status for a built bootstrap."""

    def _ok(predicate: Callable[[], object]) -> str:
        try:
            predicate()
        except Exception:  # noqa: BLE001
            return "error"
        return "ok"

    database = _ok(lambda: bootstrap.database_connection.execute("SELECT 1"))
    migrations = _ok(
        lambda: bootstrap.migration_runner(
            bootstrap.database_connection, bootstrap.migrations_dir
        )
    )
    translations = _ok(lambda: _check_translation(bootstrap))
    platform_registry = _ok(lambda: bootstrap.platform_registry.list_platforms())
    provider_registry = _ok(lambda: bootstrap.provider_registry.list_providers())

    secret_store = (
        "available" if bootstrap.secret_store is not None else "unavailable"
    )

    checks_ok = (
        database == "ok"
        and migrations == "ok"
        and translations == "ok"
        and platform_registry == "ok"
        and provider_registry == "ok"
        and secret_store == "available"
    )
    status = "ok" if checks_ok else "error"

    return {
        "status": status,
        "python": platform.python_version(),
        "database": database,
        "migrations": migrations,
        "translations": translations,
        "platform_registry": platform_registry,
        "provider_registry": provider_registry,
        "secret_store": secret_store,
        "ui_framework": "not_selected",
    }


def _check_translation(bootstrap: Bootstrap) -> None:
    value = bootstrap.translator.t(_HEALTHY_KEY)
    if value.startswith("[missing:"):
        raise RuntimeError(f"missing translation key: {_HEALTHY_KEY}")


def build_failed_health_result() -> dict[str, str]:
    """Health result reported when ``create_bootstrap`` itself raised."""
    return {
        "status": "error",
        "python": platform.python_version(),
        "database": "error",
        "migrations": "error",
        "translations": "error",
        "platform_registry": "error",
        "provider_registry": "error",
        "secret_store": "unavailable",
        "ui_framework": "not_selected",
    }
