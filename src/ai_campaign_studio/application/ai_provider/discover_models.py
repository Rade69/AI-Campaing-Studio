"""DiscoverModels use-case (A8, dio 2).

Owns discovering a provider's available models and registering them in the
model registry. Only providers with ``supports_model_discovery`` are allowed;
the manual/registry fallback branch (AI-R7) is deliberately out of scope until
a provider actually needs it. The adapter is injected via a local ``Protocol``
so the application layer never imports the concrete ``OpenAIAdapter``.
"""

from __future__ import annotations

from typing import Protocol

from ai_campaign_studio.ai_registry.model_profiles import ModelProfile
from ai_campaign_studio.domain.common.errors import InvariantViolation
from ai_campaign_studio.ports.ai_registry import (
    AIProviderRegistryPort,
    ModelRegistryPort,
)


class _ModelDiscoveryPort(Protocol):
    """The discovery capability the use-case needs from an adapter."""

    def discover_models(self) -> list[ModelProfile]: ...


class DiscoverModels:
    """Discover and register a provider's models."""

    def __init__(
        self,
        provider_registry: AIProviderRegistryPort,
        model_registry: ModelRegistryPort,
        adapter: _ModelDiscoveryPort,
    ) -> None:
        self._provider_registry = provider_registry
        self._model_registry = model_registry
        self._adapter = adapter

    def execute(self, provider_code: str) -> list[ModelProfile]:
        provider = self._provider_registry.get_provider(provider_code)
        if not provider.supports_model_discovery:
            raise InvariantViolation(
                f"provider {provider.provider_code} does not support model discovery"
            )

        models = self._adapter.discover_models()
        self._model_registry.register_discovered_models(
            provider.provider_code, models
        )
        return models
