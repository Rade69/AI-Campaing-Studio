"""Framework-neutral runtime state for the presentation layer (P0.21).

Owns the ``AppRuntimeState`` snapshot the UI reads to render startup/health
status. Does not hold business selection state (selected campaign/post/plan)
and never imports a GUI framework.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from ai_campaign_studio.localization.enums import AppLocale
from ai_campaign_studio.presentation.ui_models import NotificationUiModel


class StartupStatus(StrEnum):
    """Startup lifecycle of the application runtime."""

    NOT_STARTED = "NOT_STARTED"
    STARTING = "STARTING"
    READY = "READY"
    FAILED = "FAILED"


@dataclass
class AppRuntimeState:
    """Mutable snapshot of foundation-level runtime state.

    ``default_text_model`` holds a ``provider_code/model_id`` reference when a
    default model has been resolved. Business selection (campaign/post/plan)
    is deliberately absent in P0.
    """

    app_locale: AppLocale = AppLocale.BHS_LATIN
    startup_status: StartupStatus = StartupStatus.NOT_STARTED
    database_ready: bool = False
    resources_ready: bool = False
    configured_providers: list[str] = field(default_factory=list)
    default_text_model: str | None = None
    current_job: str | None = None
    notifications: list[NotificationUiModel] = field(default_factory=list)
