"""Unit tests for the secret store adapters (security-focused)."""

import logging
import traceback

import pytest

from ai_campaign_studio.domain.common.errors import SecretStoreError
from ai_campaign_studio.infrastructure.secrets.environment_secret_store import (
    EnvironmentSecretStore,
    secret_to_env_var,
)
from ai_campaign_studio.infrastructure.secrets.keyring_secret_store import (
    KeyringSecretStore,
)

SECRET = "test-secret-value-123"


class _FakeKeyringBackend:
    def __init__(self) -> None:
        self._store: dict[tuple[str, str], str] = {}

    def get_password(self, service_name: str, username: str) -> str | None:
        return self._store.get((service_name, username))

    def set_password(self, service_name: str, username: str, password: str) -> None:
        self._store[(service_name, username)] = password

    def delete_password(self, service_name: str, username: str) -> None:
        self._store.pop((service_name, username), None)


class _FailingBackend:
    def get_password(self, service_name: str, username: str) -> str | None:
        raise RuntimeError("backend down")

    def set_password(self, service_name: str, username: str, password: str) -> None:
        raise RuntimeError("backend down")

    def delete_password(self, service_name: str, username: str) -> None:
        raise RuntimeError("backend down")


def test_secret_to_env_var_mapping() -> None:
    assert (
        secret_to_env_var("provider/OPENAI/api_key")
        == "AI_CAMPAIGN_STUDIO_OPENAI_API_KEY"
    )


def test_environment_store_get_and_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_CAMPAIGN_STUDIO_OPENAI_API_KEY", SECRET)
    store = EnvironmentSecretStore()

    assert store.get_secret("provider/OPENAI/api_key") == SECRET
    assert store.get_secret("provider/ANTHROPIC/api_key") is None


def test_environment_store_set_is_read_only() -> None:
    store = EnvironmentSecretStore()
    with pytest.raises(SecretStoreError):
        store.set_secret("provider/OPENAI/api_key", SECRET)


def test_environment_store_delete_is_read_only() -> None:
    store = EnvironmentSecretStore()
    with pytest.raises(SecretStoreError):
        store.delete_secret("provider/OPENAI/api_key")


def test_keyring_store_set_get_delete() -> None:
    store = KeyringSecretStore(backend=_FakeKeyringBackend())

    store.set_secret("provider/OPENAI/api_key", SECRET)
    assert store.get_secret("provider/OPENAI/api_key") == SECRET
    store.delete_secret("provider/OPENAI/api_key")
    assert store.get_secret("provider/OPENAI/api_key") is None


def test_keyring_store_missing_returns_none() -> None:
    store = KeyringSecretStore(backend=_FakeKeyringBackend())
    assert store.get_secret("provider/OPENAI/api_key") is None


def test_keyring_store_error_does_not_leak_secret_in_exception() -> None:
    store = KeyringSecretStore(backend=_FailingBackend())

    with pytest.raises(SecretStoreError) as excinfo:
        store.set_secret("provider/OPENAI/api_key", SECRET)

    assert SECRET not in str(excinfo.value)
    assert SECRET not in repr(excinfo.value)


def test_environment_store_error_does_not_leak_secret() -> None:
    store = EnvironmentSecretStore()

    with pytest.raises(SecretStoreError) as excinfo:
        store.set_secret("provider/OPENAI/api_key", SECRET)

    assert SECRET not in str(excinfo.value)
    assert SECRET not in repr(excinfo.value)


def test_keyring_store_never_logs_secret(
    caplog: pytest.LogCaptureFixture,
) -> None:
    store = KeyringSecretStore(backend=_FakeKeyringBackend())

    with caplog.at_level(logging.DEBUG):
        store.set_secret("provider/OPENAI/api_key", SECRET)
        store.get_secret("provider/OPENAI/api_key")
        store.delete_secret("provider/OPENAI/api_key")

    assert SECRET not in caplog.text


def test_keyring_store_error_does_not_leak_secret_in_cause() -> None:
    class _EchoingBackend:
        def get_password(self, service_name: str, username: str) -> str | None:
            raise RuntimeError(f"get failed for {SECRET}")

        def set_password(
            self, service_name: str, username: str, password: str
        ) -> None:
            raise RuntimeError(f"set failed for {password}")

        def delete_password(self, service_name: str, username: str) -> None:
            raise RuntimeError(f"delete failed for {SECRET}")

    store = KeyringSecretStore(backend=_EchoingBackend())

    with pytest.raises(SecretStoreError) as excinfo:
        store.set_secret("provider/OPENAI/api_key", SECRET)

    exc = excinfo.value
    assert exc.__cause__ is None
    assert SECRET not in str(exc)
    assert SECRET not in repr(exc)
    assert SECRET not in "".join(traceback.format_exception(exc))


@pytest.mark.parametrize(
    "name",
    [
        "OPENAI/api_key",
        "",
        "provider//api_key",
        "provider/OPENAI/api-key",
        "provider/OPENAI_API/key",
        "provider/OPENAI/api_key/extra",
    ],
)
def test_secret_to_env_var_rejects_non_canonical_names(name: str) -> None:
    with pytest.raises(ValueError):
        secret_to_env_var(name)


def test_environment_store_get_rejects_non_canonical_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_CAMPAIGN_STUDIO_OPENAI_API_KEY", SECRET)
    store = EnvironmentSecretStore()
    with pytest.raises(ValueError):
        store.get_secret("OPENAI/api_key")
