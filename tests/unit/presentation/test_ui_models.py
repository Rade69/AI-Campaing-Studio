"""Unit tests for presentation UI DTOs (P0.21)."""

from ai_campaign_studio.presentation.ui_models import (
    NotificationLevel,
    NotificationUiModel,
    ProviderStatusUiModel,
)


def test_notification_ui_model_defaults() -> None:
    notification = NotificationUiModel(
        level=NotificationLevel.INFO,
        message_key="app.ready",
    )
    assert notification.level is NotificationLevel.INFO
    assert notification.message_key == "app.ready"
    assert notification.params == {}
    assert notification.technical_details is None


def test_notification_ui_model_with_params() -> None:
    notification = NotificationUiModel(
        level=NotificationLevel.ERROR,
        message_key="error.database",
        params={"detail": "locked"},
        technical_details="SQLITE_BUSY",
    )
    assert notification.params == {"detail": "locked"}
    assert notification.technical_details == "SQLITE_BUSY"


def test_provider_status_ui_model() -> None:
    status = ProviderStatusUiModel(
        provider_code="OPENAI",
        display_name="OpenAI",
        configured=False,
        validated=False,
        model_count=0,
    )
    assert status.provider_code == "OPENAI"
    assert status.display_name == "OpenAI"
    assert status.configured is False
    assert status.validated is False
    assert status.model_count == 0
