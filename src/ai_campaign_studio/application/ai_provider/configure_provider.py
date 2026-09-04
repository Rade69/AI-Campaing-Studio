"""ConfigureProvider use-case (A8, dio 2).

Owns persisting a provider's API key into the SecretStore and marking the
provider as configured. The key is stored only in the SecretStore under a
canonical ``provider/<CODE>/api_key`` reference; ``ProviderConfig`` carries the
reference string, never the key value. ``validated`` is always ``False`` here —
validation is ``TestProviderConnection``'s job (AI-R5 flow separation).
"""

from __future__ import annotations

from ai_campaign_studio.domain.common.errors import InvariantViolation
from ai_campaign_studio.domain.common.timestamps import utc_now
from ai_campaign_studio.ports.ai_registry import AIProviderRegistryPort
from ai_campaign_studio.ports.provider_config import (
    ProviderConfig,
    ProviderConfigRepositoryPort,
)
from ai_campaign_studio.ports.secrets import SecretStorePort


class ConfigureProvider:
    """Store a provider API key and mark the provider configured."""

    def __init__(
        self,
        provider_registry: AIProviderRegistryPort,
        provider_config_repo: ProviderConfigRepositoryPort,
        secret_store: SecretStorePort,
    ) -> None:
        self._provider_registry = provider_registry
        self._provider_config_repo = provider_config_repo
        self._secret_store = secret_store

    def execute(
        self,
        provider_code: str,
        api_key: str,
        base_url: str | None = None,
    ) -> ProviderConfig:
        provider = self._provider_registry.get_provider(provider_code)
        if not provider.requires_api_key:
            raise InvariantViolation(
                f"provider {provider.provider_code} does not require an API key"
            )

        credential_ref = f"provider/{provider.provider_code}/api_key"
        self._secret_store.set_secret(credential_ref, api_key)

        config = ProviderConfig(
            provider_code=provider.provider_code,
            configured=True,
            validated=False,
            credential_ref=credential_ref,
            base_url=base_url,
            updated_at=utc_now(),
        )
        self._provider_config_repo.save_provider_config(config)
        return config
