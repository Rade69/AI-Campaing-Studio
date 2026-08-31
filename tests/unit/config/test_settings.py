"""Unit tests for application settings."""

import pytest
from pydantic import ValidationError

from ai_campaign_studio.config.settings import AppSettings


def test_default_settings() -> None:
    settings = AppSettings()
    assert settings.app_name == "AI Campaign Studio"
    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert settings.app_locale == "BHS_LATIN"
    assert settings.database_filename == "ai_campaign_studio.db"
    assert settings.data_dir_override is None
    assert settings.resource_dir_override is None


def test_accepts_known_environment_and_locale() -> None:
    settings = AppSettings(environment="production", app_locale="EN")
    assert settings.environment == "production"
    assert settings.app_locale == "EN"


def test_environment_must_be_known() -> None:
    with pytest.raises(ValidationError):
        AppSettings(environment="staging")


def test_settings_have_no_secret_fields() -> None:
    fields = set(AppSettings.model_fields)
    assert "api_key" not in fields
    assert "openai_key" not in fields
    assert "anthropic_key" not in fields
    assert "token" not in fields
