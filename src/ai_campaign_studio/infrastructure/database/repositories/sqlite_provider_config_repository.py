"""SQLite adapters for provider config / model selection persistence (A8, dio 1).

Owns reading/writing the P0 ``provider_configs`` and ``model_selections``
tables (no new migration — the tables exist since ``0000_foundation.sql``).
``configured``/``validated`` are stored as INTEGER 0/1 and reconstructed as
real ``bool``. ``credential_ref`` is a plain string reference — this adapter
never stores or touches an actual secret value.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

from ai_campaign_studio.ports.provider_config import (
    ModelSelection,
    ProviderConfig,
)


class SqliteProviderConfigRepository:
    """SQLite implementation of ``ProviderConfigRepositoryPort``."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def save_provider_config(self, config: ProviderConfig) -> None:
        self._connection.execute(
            "INSERT INTO provider_configs (provider_code, configured, validated,"
            " credential_ref, base_url, updated_at) VALUES (?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(provider_code) DO UPDATE SET"
            " configured=excluded.configured, validated=excluded.validated,"
            " credential_ref=excluded.credential_ref, base_url=excluded.base_url,"
            " updated_at=excluded.updated_at",
            (
                config.provider_code,
                int(config.configured),
                int(config.validated),
                config.credential_ref,
                config.base_url,
                config.updated_at.isoformat(),
            ),
        )

    def get_provider_config(self, provider_code: str) -> ProviderConfig | None:
        row = self._connection.execute(
            "SELECT * FROM provider_configs WHERE provider_code = ?",
            (provider_code,),
        ).fetchone()
        if row is None:
            return None
        return _provider_config_from_row(row)

    def list_provider_configs(self) -> tuple[ProviderConfig, ...]:
        rows = self._connection.execute(
            "SELECT * FROM provider_configs ORDER BY provider_code"
        ).fetchall()
        return tuple(_provider_config_from_row(row) for row in rows)


class SqliteModelSelectionRepository:
    """SQLite implementation of ``ModelSelectionRepositoryPort``."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def save_model_selection(self, selection: ModelSelection) -> None:
        self._connection.execute(
            "INSERT INTO model_selections (purpose, provider_code, model_id,"
            " updated_at) VALUES (?, ?, ?, ?)"
            " ON CONFLICT(purpose) DO UPDATE SET"
            " provider_code=excluded.provider_code, model_id=excluded.model_id,"
            " updated_at=excluded.updated_at",
            (
                selection.purpose,
                selection.provider_code,
                selection.model_id,
                selection.updated_at.isoformat(),
            ),
        )

    def get_model_selection(self, purpose: str) -> ModelSelection | None:
        row = self._connection.execute(
            "SELECT * FROM model_selections WHERE purpose = ?", (purpose,)
        ).fetchone()
        if row is None:
            return None
        return _model_selection_from_row(row)


def _provider_config_from_row(row: sqlite3.Row) -> ProviderConfig:
    return ProviderConfig(
        provider_code=row["provider_code"],
        configured=bool(row["configured"]),
        validated=bool(row["validated"]),
        credential_ref=row["credential_ref"],
        base_url=row["base_url"],
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def _model_selection_from_row(row: sqlite3.Row) -> ModelSelection:
    return ModelSelection(
        purpose=row["purpose"],
        provider_code=row["provider_code"],
        model_id=row["model_id"],
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )
