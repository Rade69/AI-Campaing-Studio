"""Unit tests for AppRuntimeState (P0.21)."""

from ai_campaign_studio.localization.enums import AppLocale
from ai_campaign_studio.presentation.state import AppRuntimeState, StartupStatus


def test_defaults_are_foundation_only() -> None:
    state = AppRuntimeState()
    assert state.app_locale is AppLocale.BHS_LATIN
    assert state.startup_status is StartupStatus.NOT_STARTED
    assert state.database_ready is False
    assert state.resources_ready is False
    assert state.configured_providers == []
    assert state.default_text_model is None
    assert state.current_job is None
    assert state.notifications == []


def test_mutation_reflects_runtime_changes() -> None:
    state = AppRuntimeState()
    state.database_ready = True
    state.startup_status = StartupStatus.READY
    state.configured_providers.append("OPENAI")
    state.current_job = "job-123"
    assert state.database_ready is True
    assert state.startup_status is StartupStatus.READY
    assert state.configured_providers == ["OPENAI"]
    assert state.current_job == "job-123"
