"""Environment-variable backed secret store (dev/test adapter)."""

import os

from ai_campaign_studio.domain.common.errors import SecretStoreError
from ai_campaign_studio.ports.secrets import SecretStorePort

_ENV_PREFIX = "AI_CAMPAIGN_STUDIO_"


def secret_to_env_var(name: str) -> str:
    """Map a secret name to its environment variable.

    ``provider/OPENAI/api_key`` -> ``AI_CAMPAIGN_STUDIO_OPENAI_API_KEY``.
    """
    parts = name.split("/")
    if parts and parts[0].lower() == "provider":
        parts = parts[1:]
    suffix = "_".join(part.upper() for part in parts)
    return f"{_ENV_PREFIX}{suffix}"


class EnvironmentSecretStore(SecretStorePort):
    """Reads secrets from process environment variables.

    ``get_secret`` reads ``AI_CAMPAIGN_STUDIO_<NAME>``. ``set_secret`` and
    ``delete_secret`` are read-only and raise ``SecretStoreError`` so callers
    never silently believe a value was persisted. This adapter never writes a
    ``.env`` file and never logs secret values.
    """

    def get_secret(self, name: str) -> str | None:
        return os.environ.get(secret_to_env_var(name))

    def set_secret(self, name: str, value: str) -> None:
        raise SecretStoreError(
            "EnvironmentSecretStore is read-only; set the environment variable "
            f"{secret_to_env_var(name)} instead"
        )

    def delete_secret(self, name: str) -> None:
        raise SecretStoreError(
            "EnvironmentSecretStore is read-only; unset the environment variable "
            f"{secret_to_env_var(name)} instead"
        )
