"""Unit tests for presentation UI DTOs (P0.21)."""

import json
from dataclasses import asdict

from ai_campaign_studio.presentation.ui_models import (
    CampaignPlanResultUiModel,
    NotificationLevel,
    NotificationUiModel,
    ProviderConfigResultUiModel,
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


# --- ACS-GUI-005: CampaignPlanResultUiModel ---------------------------


def test_campaign_plan_result_success_shape() -> None:
    """Success case: ok=True with campaign_id + plan_item_count set,
    error fields explicitly None."""
    result = CampaignPlanResultUiModel(
        ok=True,
        campaign_id="cmp_abc123",
        plan_item_count=3,
        error_code=None,
        error_message=None,
    )
    blob = asdict(result)
    assert blob == {
        "ok": True,
        "campaign_id": "cmp_abc123",
        "plan_item_count": 3,
        "error_code": None,
        "error_message": None,
    }


def test_campaign_plan_result_error_shape() -> None:
    """Error case: ok=False, success fields None, error fields populated."""
    result = CampaignPlanResultUiModel(
        ok=False,
        campaign_id=None,
        plan_item_count=None,
        error_code="NO_PROVIDER_CONFIGURED",
        error_message="Nijedan AI provajder nije podešen.",
    )
    blob = asdict(result)
    assert blob == {
        "ok": False,
        "campaign_id": None,
        "plan_item_count": None,
        "error_code": "NO_PROVIDER_CONFIGURED",
        "error_message": "Nijedan AI provajder nije podešen.",
    }


def test_campaign_plan_result_is_json_serializable() -> None:
    """PYWEBVIEW_SECURITY §3: the bridge's return crosses the
    ``js_api`` boundary as JSON. The DTO must round-trip through
    ``json.dumps`` and ``json.loads`` without surprises."""
    cases = [
        CampaignPlanResultUiModel(
            ok=True, campaign_id="cmp_1", plan_item_count=2,
            error_code=None, error_message=None,
        ),
        CampaignPlanResultUiModel(
            ok=False, campaign_id=None, plan_item_count=None,
            error_code="VALIDATION_ERROR", error_message="offer: required",
        ),
    ]
    for case in cases:
        roundtripped = json.loads(json.dumps(asdict(case)))
        assert roundtripped == asdict(case)


def test_campaign_plan_result_is_frozen() -> None:
    """DTOs are immutable (frozen=True). Forbidding mutation prevents
    accidental in-place changes after the bridge has shipped the dict
    to JS — by then the user is looking at a stale value."""
    import dataclasses
    result = CampaignPlanResultUiModel(
        ok=True, campaign_id="cmp_1", plan_item_count=1,
        error_code=None, error_message=None,
    )
    try:
        result.ok = False  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        return
    raise AssertionError("CampaignPlanResultUiModel must be frozen")


# --- ACS-GUI-007: ProviderConfigResultUiModel ---------------------------


def test_provider_config_result_success_shape() -> None:
    """Success case: ok=True, provider_code normalized UPPERCASE,
    error fields None."""
    result = ProviderConfigResultUiModel(
        ok=True,
        provider_code="OPENAI",
        error_code=None,
        error_message=None,
    )
    blob = asdict(result)
    assert blob == {
        "ok": True,
        "provider_code": "OPENAI",
        "error_code": None,
        "error_message": None,
    }


def test_provider_config_result_error_shape() -> None:
    """Error case: ok=False, success fields None, error fields populated."""
    result = ProviderConfigResultUiModel(
        ok=False,
        provider_code=None,
        error_code="VALIDATION_ERROR",
        error_message="provider_code je obavezan (string).",
    )
    blob = asdict(result)
    assert blob == {
        "ok": False,
        "provider_code": None,
        "error_code": "VALIDATION_ERROR",
        "error_message": "provider_code je obavezan (string).",
    }


def test_provider_config_result_carries_no_api_key_field() -> None:
    """Structural guarantee: the DTO has NO field that could hold an
    API key — by design, not by convention. A future maintainer cannot
    accidentally add an ``api_key_preview`` field and pass review,
    because this test would have to be updated AND it documents the
    intent."""
    fields = {f.name for f in ProviderConfigResultUiModel.__dataclass_fields__.values()}
    assert "api_key" not in fields
    assert "api_key_preview" not in fields
    assert "api_key_masked" not in fields
    # The only fields the DTO exposes are: ok, provider_code, error_code,
    # error_message. Assert that explicitly so the test catches
    # accidental additions.
    assert fields == {"ok", "provider_code", "error_code", "error_message"}


def test_provider_config_result_is_json_serializable() -> None:
    cases = [
        ProviderConfigResultUiModel(
            ok=True, provider_code="OPENAI",
            error_code=None, error_message=None,
        ),
        ProviderConfigResultUiModel(
            ok=False, provider_code=None,
            error_code="INTERNAL_ERROR", error_message="...",
        ),
    ]
    for case in cases:
        roundtripped = json.loads(json.dumps(asdict(case)))
        assert roundtripped == asdict(case)


def test_provider_config_result_is_frozen() -> None:
    """The DTO is immutable; accidental mutation after the bridge has
    shipped the dict to JS would silently corrupt the user-visible
    state."""
    import dataclasses
    result = ProviderConfigResultUiModel(
        ok=True, provider_code="OPENAI",
        error_code=None, error_message=None,
    )
    try:
        result.provider_code = "DEEPSEEK"  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        return
    raise AssertionError("ProviderConfigResultUiModel must be frozen")
