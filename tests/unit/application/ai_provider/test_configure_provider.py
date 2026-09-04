"""Unit tests for ConfigureProvider (A8, dio 2)."""

from __future__ import annotations

import pytest

from ai_campaign_studio.ai_registry.provider_models import AIProviderDefinition
from ai_campaign_studio.application.ai_provider.configure_provider import (
    ConfigureProvider,
)
from ai_campaign_studio.domain.common.errors import InvariantViolation, RegistryError


class _FakeProviderRegistry:
    def __init__(self, provider: AIProviderDefinition | None) -> None:
        self._provider = provider

    def get_provider(self, provider_code: str) -> AIProviderDefinition:
        if self._provider is None:
            raise RegistryError(f"unknown provider: {provider_code}")
        return self._provider

    def list_providers(self) -> list[AIProviderDefinition]:
        return []


class _FakeProviderConfigRepo:
    def __init__(self) -> None:
        self.saved = None

    def get_provider_config(self, provider_code: str):
        del provider_code
        return None

    def save_provider_config(self, config) -> None:  # noqa: ANN001
        self.saved = config

    def list_provider_configs(self):
        return ()


class _FakeSecretStore:
    def __init__(self) -> None:
        self.secrets: dict[str, str] = {}

    def get_secret(self, name: str) -> str | None:
        return self.secrets.get(name)

    def set_secret(self, name: str, value: str) -> None:
        self.secrets[name] = value

    def delete_secret(self, name: str) -> None:
        self.secrets.pop(name, None)


def _openai_provider() -> AIProviderDefinition:
    return AIProviderDefinition(
        provider_code="OPENAI",
        display_name="OpenAI",
        adapter_type="openai",
        requires_api_key=True,
        supports_model_discovery=True,
        base_url_mode="FIXED",
        enabled=True,
    )


def test_configure_stores_secret_and_config() -> None:
    registry = _FakeProviderRegistry(_openai_provider())
    config_repo = _FakeProviderConfigRepo()
    secret_store = _FakeSecretStore()
    use_case = ConfigureProvider(registry, config_repo, secret_store)

    result = use_case.execute("OPENAI", "sk-EXAMPLE-key")

    assert secret_store.secrets["provider/OPENAI/api_key"] == "sk-EXAMPLE-key"
    assert result.configured is True
    assert result.validated is False
    assert result.credential_ref == "provider/OPENAI/api_key"
    assert config_repo.saved.credential_ref == "provider/OPENAI/api_key"


def test_configure_stores_reference_not_key() -> None:
    registry = _FakeProviderRegistry(_openai_provider())
    config_repo = _FakeProviderConfigRepo()
    secret_store = _FakeSecretStore()
    use_case = ConfigureProvider(registry, config_repo, secret_store)

    result = use_case.execute("OPENAI", "sk-EXAMPLE-key")

    assert result.credential_ref != "sk-EXAMPLE-key"
    assert "sk-EXAMPLE-key" not in result.credential_ref


def test_unknown_provider_raises_and_secret_store_untouched() -> None:
    registry = _FakeProviderRegistry(None)
    config_repo = _FakeProviderConfigRepo()
    secret_store = _FakeSecretStore()
    use_case = ConfigureProvider(registry, config_repo, secret_store)

    with pytest.raises(RegistryError):
        use_case.execute("UNKNOWN", "sk-EXAMPLE-key")

    assert secret_store.secrets == {}
    assert config_repo.saved is None


def test_provider_without_api_key_rejected() -> None:
    provider = AIProviderDefinition(
        provider_code="OPENAI",
        display_name="OpenAI",
        adapter_type="openai",
        requires_api_key=False,
        supports_model_discovery=True,
        base_url_mode="FIXED",
        enabled=True,
    )
    registry = _FakeProviderRegistry(provider)
    config_repo = _FakeProviderConfigRepo()
    secret_store = _FakeSecretStore()
    use_case = ConfigureProvider(registry, config_repo, secret_store)

    with pytest.raises(InvariantViolation):
        use_case.execute("OPENAI", "sk-EXAMPLE-key")

    assert secret_store.secrets == {}
    assert config_repo.saved is None
