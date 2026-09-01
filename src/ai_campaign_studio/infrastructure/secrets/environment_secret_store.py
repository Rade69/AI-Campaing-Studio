"""Environment-variable backed secret store (dev/test adapter)."""

import os
import re

from ai_campaign_studio.domain.common.errors import SecretStoreError
from ai_campaign_studio.ports.secrets import SecretStorePort

_ENV_PREFIX = "AI_CAMPAIGN_STUDIO_"
_SECRET_NAME_RE = re.compile(r"^provider/([A-Za-z0-9_]+)/api_key$")


def secret_to_env_var(name: str) -> str:
    """Map a canonical secret name to its environment variable.

    ``provider/OPENAI/api_key`` -> ``AI_CAMPAIGN_STUDIO_OPENAI_API_KEY``.

    Only the canonical ``provider/<PROVIDER_CODE>/api_key`` form is accepted;
    any other shape raises ``ValueError`` so two different names can never
    silently map to the same environment variable.
    """
    match = _SECRET_NAME_RE.fullmatch(name)
    if match is None:
        raise ValueError(
            f"invalid secret name {name!r}; "
            "expected 'provider/<PROVIDER_CODE>/api_key'"
        )
    provider_code = match.group(1).upper()
    return f"{_ENV_PREFIX}{provider_code}_API_KEY"


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
