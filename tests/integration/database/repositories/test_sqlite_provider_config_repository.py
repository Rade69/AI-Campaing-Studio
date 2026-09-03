"""Integration tests for SQLite provider config / model selection repos (A8, dio 1)."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories.sqlite_provider_config_repository import (  # noqa: E501
    SqliteModelSelectionRepository,
    SqliteProviderConfigRepository,
)
from ai_campaign_studio.ports.provider_config import (
    ModelSelection,
    ModelSelectionRepositoryPort,
    ProviderConfig,
    ProviderConfigRepositoryPort,
)

_MIGRATIONS_DIR = Path(__file__).resolve().parents[4] / "resources" / "migrations"
_UPDATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def _setup_db(tmp_path: Path) -> sqlite3.Connection:
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)
    return connection


def _provider_config(
    *,
    configured: bool = True,
    validated: bool = True,
    credential_ref: str | None = "provider/OPENAI/api_key",
    base_url: str | None = "https://api.openai.com/v1",
) -> ProviderConfig:
    return ProviderConfig(
        provider_code="OPENAI",
        configured=configured,
        validated=validated,
        credential_ref=credential_ref,
        base_url=base_url,
        updated_at=_UPDATED_AT,
    )


def _model_selection() -> ModelSelection:
    return ModelSelection(
        purpose="default_text_model",
        provider_code="OPENAI",
        model_id="gpt-4o-mini",
        updated_at=_UPDATED_AT,
    )


def test_repository_is_provider_config_port(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteProviderConfigRepository(connection)
    assert isinstance(repo, ProviderConfigRepositoryPort)
    connection.close()


def test_repository_is_model_selection_port(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteModelSelectionRepository(connection)
    assert isinstance(repo, ModelSelectionRepositoryPort)
    connection.close()


def test_round_trip_provider_config(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteProviderConfigRepository(connection)

    config = _provider_config()
    repo.save_provider_config(config)

    assert repo.get_provider_config("OPENAI") == config
    connection.close()


def test_round_trip_provider_config_null_optionals(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteProviderConfigRepository(connection)

    config = _provider_config(credential_ref=None, base_url=None)
    repo.save_provider_config(config)

    result = repo.get_provider_config("OPENAI")
    assert result is not None
    assert result.credential_ref is None
    assert result.base_url is None
    assert result == config
    connection.close()


def test_bool_fields_round_trip_as_bool(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteProviderConfigRepository(connection)

    repo.save_provider_config(_provider_config(configured=False, validated=True))

    result = repo.get_provider_config("OPENAI")
    assert result is not None
    assert isinstance(result.configured, bool)
    assert isinstance(result.validated, bool)
    assert result.configured is False
    assert result.validated is True
    connection.close()


def test_save_provider_config_is_idempotent(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteProviderConfigRepository(connection)

    repo.save_provider_config(_provider_config(validated=False))
    repo.save_provider_config(_provider_config(validated=True))

    count = connection.execute(
        "SELECT COUNT(*) FROM provider_configs WHERE provider_code = ?",
        ("OPENAI",),
    ).fetchone()[0]
    assert count == 1

    result = repo.get_provider_config("OPENAI")
    assert result is not None
    assert result.validated is True
    connection.close()


def test_get_unknown_provider_config_returns_none(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteProviderConfigRepository(connection)
    assert repo.get_provider_config("MISSING") is None
    connection.close()


def test_list_provider_configs_sorted(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteProviderConfigRepository(connection)

    for code in ("OPENAI", "ANTHROPIC", "GOOGLE"):
        repo.save_provider_config(
            ProviderConfig(
                provider_code=code,
                configured=True,
                validated=False,
                credential_ref=f"provider/{code}/api_key",
                base_url=None,
                updated_at=_UPDATED_AT,
            )
        )

    configs = repo.list_provider_configs()
    assert [c.provider_code for c in configs] == ["ANTHROPIC", "GOOGLE", "OPENAI"]
    connection.close()


def test_round_trip_model_selection(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteModelSelectionRepository(connection)

    selection = _model_selection()
    repo.save_model_selection(selection)

    assert repo.get_model_selection("default_text_model") == selection
    connection.close()


def test_save_model_selection_is_idempotent(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteModelSelectionRepository(connection)

    repo.save_model_selection(_model_selection())
    repo.save_model_selection(_model_selection())

    count = connection.execute(
        "SELECT COUNT(*) FROM model_selections WHERE purpose = ?",
        ("default_text_model",),
    ).fetchone()[0]
    assert count == 1
    connection.close()


def test_get_unknown_model_selection_returns_none(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteModelSelectionRepository(connection)
    assert repo.get_model_selection("missing_purpose") is None
    connection.close()


def test_model_selections_table_is_empty_by_default(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    count = connection.execute("SELECT COUNT(*) FROM model_selections").fetchone()[0]
    assert count == 0
    connection.close()
