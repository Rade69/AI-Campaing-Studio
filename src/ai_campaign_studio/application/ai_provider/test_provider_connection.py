"""TestProviderConnection use-case (A8, dio 2).

Owns validating a configured provider's API key by calling an injected
adapter's ``test_connection()`` and persisting the ``validated`` flag. An
unconfigured provider is an expected ``ConnectionTestResult(success=False)``,
not an exception. The adapter is injected via a local ``Protocol`` so the
application layer never imports the concrete ``OpenAIAdapter`` (architecture
boundary); a provider factory will supply it once more than one provider
exists.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol

from ai_campaign_studio.domain.common.errors import InfrastructureError
from ai_campaign_studio.ports.provider_config import ProviderConfigRepositoryPort


@dataclass(frozen=True)
class ConnectionTestResult:
    """Outcome of a provider connection test."""

    success: bool
    error_message: str | None = None


class _ConnectionPort(Protocol):
    """The connection capability the use-case needs from an adapter."""

    def test_connection(self) -> bool: ...


class TestProviderConnection:
    """Validate a configured provider's API key and persist the result."""

    # pytest would try to collect this use-case class as a test case.
    __test__ = False

    def __init__(
        self,
        provider_config_repo: ProviderConfigRepositoryPort,
        adapter: _ConnectionPort,
    ) -> None:
        self._provider_config_repo = provider_config_repo
        self._adapter = adapter

    def execute(self, provider_code: str) -> ConnectionTestResult:
        config = self._provider_config_repo.get_provider_config(provider_code)
        if config is None or not config.configured:
            return ConnectionTestResult(
                success=False, error_message="provider not configured"
            )

        try:
            success = self._adapter.test_connection()
            error_message = None if success else "connection failed"
        except InfrastructureError as exc:
            success = False
            error_message = exc.human_message

        self._provider_config_repo.save_provider_config(
            replace(config, validated=success)
        )
        return ConnectionTestResult(success=success, error_message=error_message)
