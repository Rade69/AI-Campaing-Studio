"""Secret store port (framework-neutral)."""

from typing import Protocol


class SecretStorePort(Protocol):
    """Contract for storing and retrieving secrets (e.g. provider API keys).

    Implementations must never log or expose secret values; ``get_secret``
    returns ``None`` for a missing entry instead of raising.
    """

    def get_secret(self, name: str) -> str | None: ...

    def set_secret(self, name: str, value: str) -> None: ...

    def delete_secret(self, name: str) -> None: ...
