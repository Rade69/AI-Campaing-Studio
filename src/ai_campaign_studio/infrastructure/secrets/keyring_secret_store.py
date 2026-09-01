"""OS keyring-backed secret store (production desktop adapter)."""

import logging
from typing import Protocol

import keyring  # type: ignore[import-untyped]

from ai_campaign_studio.domain.common.errors import SecretStoreError
from ai_campaign_studio.ports.secrets import SecretStorePort

logger = logging.getLogger("ai_campaign_studio.infrastructure.secrets.keyring")

_SERVICE_NAME = "AI Campaign Studio"


class _KeyringBackend(Protocol):
    def get_password(self, service_name: str, username: str) -> str | None: ...

    def set_password(self, service_name: str, username: str, password: str) -> None: ...

    def delete_password(self, service_name: str, username: str) -> None: ...


class KeyringSecretStore(SecretStorePort):
    """Stores secrets in the OS keyring.

    ``get_secret`` returns ``None`` for a missing entry. Backend errors are
    wrapped in ``SecretStoreError``; the original backend exception is never
    chained (``from None``) so a potentially secret-bearing backend message
    cannot leak through ``__cause__``/traceback. Only the backend exception
    class name is kept as safe ``technical_context``. This adapter never logs
    secret values.
    """

    def __init__(
        self,
        backend: _KeyringBackend | None = None,
        service_name: str = _SERVICE_NAME,
    ) -> None:
        self._backend: _KeyringBackend = backend if backend is not None else keyring
        self._service_name = service_name

    def get_secret(self, name: str) -> str | None:
        try:
            return self._backend.get_password(self._service_name, name)
        except Exception as exc:  # noqa: BLE001
            raise SecretStoreError(
                f"failed to read secret {name!r} from keyring",
                technical_context=f"backend={type(exc).__name__}",
            ) from None

    def set_secret(self, name: str, value: str) -> None:
        try:
            self._backend.set_password(self._service_name, name, value)
        except Exception as exc:  # noqa: BLE001
            raise SecretStoreError(
                f"failed to store secret {name!r} in keyring",
                technical_context=f"backend={type(exc).__name__}",
            ) from None

    def delete_secret(self, name: str) -> None:
        try:
            self._backend.delete_password(self._service_name, name)
        except Exception as exc:  # noqa: BLE001
            raise SecretStoreError(
                f"failed to delete secret {name!r} from keyring",
                technical_context=f"backend={type(exc).__name__}",
            ) from None
