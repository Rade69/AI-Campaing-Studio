"""Framework-neutral UI data-transfer objects (P0.21).

Owns the immutable ``NotificationUiModel`` and ``ProviderStatusUiModel`` DTOs
shared by the future PySide6/pywebview frontends. No Qt model classes, no
signals, no bridge objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class NotificationLevel(StrEnum):
    """Severity of a UI notification."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass(frozen=True)
class NotificationUiModel:
    """A single user-facing notification."""

    level: NotificationLevel
    message_key: str
    params: dict[str, str] = field(default_factory=dict)
    technical_details: str | None = None


@dataclass(frozen=True)
class ProviderStatusUiModel:
    """Provider status shown in settings UI."""

    provider_code: str
    display_name: str
    configured: bool
    validated: bool
    model_count: int


@dataclass(frozen=True)
class CampaignPlanResultUiModel:
    """Result of a "Sačuvaj i napravi plan" click (ACS-GUI-005 bridge).

    Returned by ``CampaignBridgeApi.create_campaign_and_generate_plan``.
    Converted to a plain ``dict`` before crossing the pywebview ``js_api``
    boundary (``js_api`` is required to return JSON-serializable values,
    so the bridge calls ``dataclasses.asdict`` on this model). Every
    field is JSON-safe by construction — no ``SecretStore`` content,
    no traceback strings, no file paths.
    """

    ok: bool
    campaign_id: str | None
    plan_item_count: int | None
    error_code: str | None
    error_message: str | None
