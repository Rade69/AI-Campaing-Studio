"""Unit tests for DiscoverModels (A8, dio 2)."""

from __future__ import annotations

import pytest

from ai_campaign_studio.ai_registry.model_profiles import ModelProfile, ModelSource
from ai_campaign_studio.ai_registry.provider_models import AIProviderDefinition
from ai_campaign_studio.application.ai_provider.discover_models import DiscoverModels
from ai_campaign_studio.domain.common.errors import InvariantViolation


def _provider(supports_discovery: bool = True) -> AIProviderDefinition:
    return AIProviderDefinition(
        provider_code="OPENAI",
        display_name="OpenAI",
        adapter_type="openai",
        requires_api_key=True,
        supports_model_discovery=supports_discovery,
        base_url_mode="FIXED",
        enabled=True,
    )


class _FakeProviderRegistry:
    def __init__(self, provider: AIProviderDefinition) -> None:
        self._provider = provider

    def get_provider(self, provider_code: str) -> AIProviderDefinition:
        del provider_code
        return self._provider

    def list_providers(self) -> list[AIProviderDefinition]:
        return []


class _FakeModelRegistry:
    def __init__(self) -> None:
        self.registered: list[ModelProfile] | None = None
        self.registered_provider: str | None = None

    def register_discovered_models(
        self, provider_code: str, models: list[ModelProfile]
    ) -> None:
        self.registered_provider = provider_code
        self.registered = models

    def get_model(self, provider_code: str, model_id: str) -> ModelProfile:
        del provider_code, model_id
        raise AssertionError("not used")

    def list_models(self, provider_code: str | None = None) -> list[ModelProfile]:
        del provider_code
        return []


class _FakeAdapter:
    def discover_models(self) -> list[ModelProfile]:
        return [
            ModelProfile(
                provider_code="OPENAI",
                model_id="gpt-4o",
                display_name="gpt-4o",
                source=ModelSource.DISCOVERED,
            )
        ]


def test_unsupported_discovery_raises_invariant() -> None:
    registry = _FakeProviderRegistry(_provider(supports_discovery=False))
    model_registry = _FakeModelRegistry()

    use_case = DiscoverModels(registry, model_registry, _FakeAdapter())

    with pytest.raises(InvariantViolation):
        use_case.execute("OPENAI")


def test_discover_registers_and_returns_models() -> None:
    registry = _FakeProviderRegistry(_provider())
    model_registry = _FakeModelRegistry()

    use_case = DiscoverModels(registry, model_registry, _FakeAdapter())
    models = use_case.execute("OPENAI")

    assert [m.model_id for m in models] == ["gpt-4o"]
    assert model_registry.registered_provider == "OPENAI"
    assert model_registry.registered == models
