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
