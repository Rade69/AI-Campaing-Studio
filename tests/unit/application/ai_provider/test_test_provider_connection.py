"""Unit tests for TestProviderConnection (A8, dio 2)."""

from __future__ import annotations

from datetime import UTC, datetime

from ai_campaign_studio.application.ai_provider.test_provider_connection import (
    ConnectionTestResult,
    TestProviderConnection,
)
from ai_campaign_studio.domain.common.errors import ErrorCode, InfrastructureError
from ai_campaign_studio.ports.provider_config import ProviderConfig

_CREATED = datetime(2026, 1, 1, tzinfo=UTC)


def _config(configured: bool = True) -> ProviderConfig:
    return ProviderConfig(
        provider_code="OPENAI",
        configured=configured,
        validated=False,
        credential_ref="provider/OPENAI/api_key",
        base_url=None,
        updated_at=_CREATED,
    )


class _FakeConfigRepo:
    def __init__(self, config: ProviderConfig | None) -> None:
        self.config = config
        self.saved: ProviderConfig | None = None

    def get_provider_config(self, provider_code: str) -> ProviderConfig | None:
        del provider_code
        return self.config

    def save_provider_config(self, config: ProviderConfig) -> None:
        self.saved = config

    def list_provider_configs(self):
        return ()


class _FakeAdapter:
    def __init__(self, result: bool = True) -> None:
        self._result = result

    def test_connection(self) -> bool:
        return self._result


class _RaisingAdapter:
    def test_connection(self) -> bool:
        raise InfrastructureError(
            "OpenAI rate limit exceeded", error_code=ErrorCode.RATE_LIMIT
        )


def test_unconfigured_provider_returns_false_not_exception() -> None:
    repo = _FakeConfigRepo(None)
    use_case = TestProviderConnection(repo, _FakeAdapter(True))

    result = use_case.execute("OPENAI")

    assert result.success is False
    assert result.error_message


def test_valid_connection_persists_validated() -> None:
    repo = _FakeConfigRepo(_config())
    use_case = TestProviderConnection(repo, _FakeAdapter(True))

    result = use_case.execute("OPENAI")

    assert result.success is True
    assert result.error_message is None
    assert repo.saved is not None
    assert repo.saved.validated is True


def test_invalid_key_persists_validated_false() -> None:
    repo = _FakeConfigRepo(_config())
    use_case = TestProviderConnection(repo, _FakeAdapter(False))

    result = use_case.execute("OPENAI")

    assert result.success is False
    assert repo.saved is not None
    assert repo.saved.validated is False


def test_unexpected_error_returns_false_result() -> None:
    repo = _FakeConfigRepo(_config())
    use_case = TestProviderConnection(repo, _RaisingAdapter())

    result = use_case.execute("OPENAI")

    assert isinstance(result, ConnectionTestResult)
    assert result.success is False
    assert result.error_message
    assert repo.saved is not None
    assert repo.saved.validated is False
