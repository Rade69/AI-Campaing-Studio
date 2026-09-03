"""Provider config / model selection persistence ports (A8, dio 1).

Owns the framework-neutral ``Protocol`` interfaces plus the ``ProviderConfig``
and ``ModelSelection`` dataclasses that represent a user's provider
configuration state. ``credential_ref`` is a plain string reference (e.g.
``"provider/OPENAI/api_key"``), never the secret value itself — this module
never imports or touches the SecretStore. The concrete adapter lives in
``infrastructure/database/repositories/sqlite_provider_config_repository.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ProviderConfig:
    """A user's configuration state for one provider (not the secret itself)."""

    provider_code: str
    configured: bool
    validated: bool
    credential_ref: str | None
    base_url: str | None
    updated_at: datetime


@dataclass(frozen=True)
class ModelSelection:
    """The chosen model for a purpose (e.g. ``default_text_model``)."""

    purpose: str
    provider_code: str
    model_id: str
    updated_at: datetime


@runtime_checkable
class ProviderConfigRepositoryPort(Protocol):
    """Persistence for ``ProviderConfig``."""

    def save_provider_config(self, config: ProviderConfig) -> None: ...

    def get_provider_config(self, provider_code: str) -> ProviderConfig | None: ...

    def list_provider_configs(self) -> tuple[ProviderConfig, ...]: ...


@runtime_checkable
class ModelSelectionRepositoryPort(Protocol):
    """Persistence for ``ModelSelection``."""

    def save_model_selection(self, selection: ModelSelection) -> None: ...

    def get_model_selection(self, purpose: str) -> ModelSelection | None: ...
