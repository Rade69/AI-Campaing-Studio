"""AI provider/model registry ports.

Owns three contracts: ``AIProviderRegistryPort``/``ModelRegistryPort`` (P0-ready,
implemented by ``ai_registry/registry.py``) and ``AIProviderConnectionPort``
(future-only — no P0 component implements or calls it). Does not implement
registry logic or provider connectivity itself.
"""

from typing import Any, Protocol

from ai_campaign_studio.ai_registry.model_profiles import ModelCapability, ModelProfile
from ai_campaign_studio.ai_registry.provider_models import AIProviderDefinition


class AIProviderRegistryPort(Protocol):
    """P0-ready provider registry contract."""

    def list_providers(self) -> list[AIProviderDefinition]:
        """Return enabled providers."""
        ...

    def get_provider(self, provider_code: str) -> AIProviderDefinition:
        """Return a provider by code, or raise ``RegistryError``."""
        ...


class AIProviderConnectionPort(Protocol):
    """Future capability contract (not implemented in P0).

    Defines the live connection/discovery surface that provider adapters will
    implement after the P0 gate; no P0 component implements or calls it.
    """

    def test_connection(self, provider_code: str, **config: Any) -> bool:
        """Verify provider connectivity (future)."""
        ...

    def discover_models(self, provider_code: str, **config: Any) -> list[ModelProfile]:
        """Discover available models from the provider (future)."""
        ...


class ModelRegistryPort(Protocol):
    """In-memory model registry contract."""

    def list_models(self, provider_code: str | None = None) -> list[ModelProfile]:
        """Return enabled models, optionally filtered by provider."""
        ...

    def get_model(self, provider_code: str, model_id: str) -> ModelProfile:
        """Return a model by provider + model id, or raise ``RegistryError``."""
        ...

    def register_discovered_models(
        self, provider_code: str, models: list[ModelProfile]
    ) -> None:
        """Register server-discovered models for a provider."""
        ...

    def register_manual_model(self, model: ModelProfile) -> None:
        """Register a manually-entered model."""
        ...

    def resolve_default_text_model(
        self, provider_code: str | None = None
    ) -> ModelProfile:
        """Resolve the default text-generation model."""
        ...

    def supports(
        self, capability: ModelCapability, provider_code: str | None = None
    ) -> bool:
        """Return whether any enabled model supports ``capability``."""
        ...
