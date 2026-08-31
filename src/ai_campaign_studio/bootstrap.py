"""Composition root for the AI Campaign Studio application."""

import logging

from ai_campaign_studio.config.paths import AppPaths
from ai_campaign_studio.config.settings import AppSettings
from ai_campaign_studio.logging.config import configure_logging


class Bootstrap:
    """Application composition root.

    Carries only the foundation objects assembled in this phase: settings,
    paths and the configured logger. It is intentionally NOT a service locator
    or a generic container; later phases extend ``create_bootstrap`` with
    explicit wiring for the objects they actually introduce.
    """

    def __init__(
        self,
        settings: AppSettings,
        paths: AppPaths,
        logger: logging.Logger,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.logger = logger


def create_bootstrap(
    settings: AppSettings | None = None,
    paths: AppPaths | None = None,
) -> Bootstrap:
    """Build the application composition root.

    Wires only Settings → Paths → logging. No network, GUI, browser, provider
    SDK, database or campaign logic is involved in this phase.
    """
    if settings is None:
        settings = AppSettings()
    if paths is None:
        paths = AppPaths(
            app_name=settings.app_name,
            database_filename=settings.database_filename,
            data_dir_override=settings.data_dir_override,
            resource_dir_override=settings.resource_dir_override,
        )
    logger = configure_logging(settings, paths)
    return Bootstrap(settings=settings, paths=paths, logger=logger)
