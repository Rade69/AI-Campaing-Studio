"""Integration test for the AI-R5 provider setup flow on a real SQLite DB.

Covers configure -> test connection -> discover models -> select default model
end-to-end. The OpenAI SDK transport is replaced by an injected fake adapter
so no real network call is made; only the SQLite persistence path is exercised
for real.
"""

from __future__ import annotations

from pathlib import Path

from ai_campaign_studio.ai_registry.model_profiles import ModelProfile, ModelSource
from ai_campaign_studio.ai_registry.registry import AIProviderRegistry
from ai_campaign_studio.application.ai_provider.configure_provider import (
    ConfigureProvider,
)
from ai_campaign_studio.application.ai_provider.discover_models import DiscoverModels
from ai_campaign_studio.application.ai_provider.select_default_model import (
    SelectDefaultModel,
)
from ai_campaign_studio.application.ai_provider.test_provider_connection import (
    TestProviderConnection,
)
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories import (
    SqliteModelSelectionRepository,
    SqliteProviderConfigRepository,
)

_MIGRATIONS_DIR = Path(__file__).resolve().parents[4] / "resources" / "migrations"


class _FakeSecretStore:
    def __init__(self) -> None:
        self.secrets: dict[str, str] = {}

    def get_secret(self, name: str) -> str | None:
        return self.secrets.get(name)

    def set_secret(self, name: str, value: str) -> None:
        self.secrets[name] = value

    def delete_secret(self, name: str) -> None:
        self.secrets.pop(name, None)


class _FakeAdapter:
    def test_connection(self) -> bool:
        return True

    def discover_models(self) -> list[ModelProfile]:
        return [
            ModelProfile(
                provider_code="OPENAI",
                model_id="gpt-4o",
                display_name="gpt-4o",
                source=ModelSource.DISCOVERED,
            )
        ]


def test_provider_setup_flow(tmp_path: Path) -> None:
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)

    config_repo = SqliteProviderConfigRepository(connection)
    selection_repo = SqliteModelSelectionRepository(connection)
    secret_store = _FakeSecretStore()
    registry = AIProviderRegistry.from_bundled_resources()
    adapter = _FakeAdapter()

    # 1. Configure
    config = ConfigureProvider(registry, config_repo, secret_store).execute(
        "OPENAI", "sk-EXAMPLE-key"
    )
    assert config.credential_ref == "provider/OPENAI/api_key"
    assert secret_store.secrets["provider/OPENAI/api_key"] == "sk-EXAMPLE-key"
    persisted = config_repo.get_provider_config("OPENAI")
    assert persisted is not None
    assert persisted.configured is True
    assert persisted.validated is False

    # 2. Test connection
    result = TestProviderConnection(config_repo, adapter).execute("OPENAI")
    assert result.success is True
    assert config_repo.get_provider_config("OPENAI").validated is True

    # 3. Discover models
    models = DiscoverModels(registry, registry, adapter).execute("OPENAI")
    assert [m.model_id for m in models] == ["gpt-4o"]

    # 4. Select default model
    selection = SelectDefaultModel(registry, selection_repo).execute(
        "OPENAI", "gpt-4o"
    )
    assert selection.purpose == "default_text_model"
    assert selection_repo.get_model_selection("default_text_model") == selection

    connection.close()
