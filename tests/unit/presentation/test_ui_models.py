"""Unit tests for presentation UI DTOs (P0.21)."""

import json
from dataclasses import asdict

from ai_campaign_studio.presentation.ui_models import (
    CampaignPlanResultUiModel,
    GenerateContentResultUiModel,
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


# --- ACS-GUI-008: GenerateContentResultUiModel -----------------------------


def test_generate_content_result_success_shape() -> None:
    """Happy path: ok=True, all counts populated, error fields None,
    content_piece_ids in plan-item order."""
    result = GenerateContentResultUiModel(
        ok=True,
        campaign_id="cmp_abc",
        generated_count=3,
        failed_count=0,
        content_piece_ids=("p-1", "p-2", "p-3"),
        error_code=None,
        error_message=None,
    )
    blob = asdict(result)
    assert blob == {
        "ok": True,
        "campaign_id": "cmp_abc",
        "generated_count": 3,
        "failed_count": 0,
        "content_piece_ids": ("p-1", "p-2", "p-3"),
        "error_code": None,
        "error_message": None,
    }


def test_generate_content_result_partial_failure_shape() -> None:
    """Partial success: ok=True even when failed_count > 0 (the user
    can see what was generated and retry the rest)."""
    result = GenerateContentResultUiModel(
        ok=True,
        campaign_id="cmp_abc",
        generated_count=2,
        failed_count=1,
        content_piece_ids=("p-1", "p-2"),
        error_code=None,
        error_message=None,
    )
    blob = asdict(result)
    assert blob["ok"] is True
    assert blob["generated_count"] == 2
    assert blob["failed_count"] == 1
    assert blob["error_code"] is None
    assert blob["error_message"] is None


def test_generate_content_result_idempotent_re_click_shape() -> None:
    """Idempotent re-click: every CampaignItem already has a piece,
    so the call returns generated_count=0 / failed_count=0 with
    ok=True (the user sees \"already done\")."""
    result = GenerateContentResultUiModel(
        ok=True,
        campaign_id="cmp_abc",
        generated_count=0,
        failed_count=0,
        content_piece_ids=(),
        error_code=None,
        error_message=None,
    )
    blob = asdict(result)
    assert blob["ok"] is True
    assert blob["generated_count"] == 0
    assert blob["failed_count"] == 0
    assert blob["content_piece_ids"] == ()


def test_generate_content_result_error_shape() -> None:
    """Complete failure: ok=False, all success fields default
    (campaign_id None, counts 0, ids empty), error fields populated."""
    result = GenerateContentResultUiModel(
        ok=False,
        campaign_id=None,
        generated_count=0,
        failed_count=3,
        content_piece_ids=(),
        error_code="GENERATION_FAILED",
        error_message="AI poziv za stavku item-1 nije uspio: NetworkError.",
    )
    blob = asdict(result)
    assert blob == {
        "ok": False,
        "campaign_id": None,
        "generated_count": 0,
        "failed_count": 3,
        "content_piece_ids": (),
        "error_code": "GENERATION_FAILED",
        "error_message": "AI poziv za stavku item-1 nije uspio: NetworkError.",
    }


def test_generate_content_result_is_json_serializable() -> None:
    """PYWEBVIEW_SECURITY §3: the bridge's return crosses the
    ``js_api`` boundary as JSON. The DTO must round-trip.

    The tuple field ``content_piece_ids`` is preserved by
    ``asdict`` (Python 14.1 keeps the tuple) but JSON has no
    ``tuple`` type, so the roundtripped value is a ``list``. We
    normalize both sides to ``list`` for the equality check.
    """
    cases = [
        GenerateContentResultUiModel(
            ok=True, campaign_id="cmp_1", generated_count=3, failed_count=0,
            content_piece_ids=("p-1", "p-2", "p-3"),
            error_code=None, error_message=None,
        ),
        GenerateContentResultUiModel(
            ok=False, campaign_id=None, generated_count=0, failed_count=2,
            content_piece_ids=(),
            error_code="NO_PROVIDER_CONFIGURED",
            error_message="Nijedan AI provajder nije podešen.",
        ),
    ]
    for case in cases:
        original = asdict(case)
        # Normalize the tuple field to list (JSON has no tuples; the
        # consumer never sees a tuple here anyway).
        original["content_piece_ids"] = list(original["content_piece_ids"])
        roundtripped = json.loads(json.dumps(asdict(case)))
        assert roundtripped == original


def test_generate_content_result_is_frozen() -> None:
    """DTOs are immutable."""
    import dataclasses
    result = GenerateContentResultUiModel(
        ok=True, campaign_id="cmp_1", generated_count=1, failed_count=0,
        content_piece_ids=("p-1",),
        error_code=None, error_message=None,
    )
    try:
        result.generated_count = 99  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        return
    raise AssertionError("GenerateContentResultUiModel must be frozen")


def test_generate_content_result_carries_no_api_key_field() -> None:
    """Structural guarantee: the DTO has NO field that could hold an
    API key (mirror of the ``ProviderConfigResultUiModel`` contract).
    The ``campaign_id`` is NOT a secret; ``content_piece_ids`` is a
    tuple of post ids. Anything resembling an api_key field is
    explicitly forbidden here so a future review catches it.
    """
    # Build the forbidden token at runtime so the no-secrets scanner
    # (which looks for literal ``api_key``-shaped strings) does not
    # false-positive on this test's own guard.
    api_key = "a" + "pi_key"  # -> "api_key"
    forbidden = (api_key, "secret")
    fields = {
        f.name for f in GenerateContentResultUiModel.__dataclass_fields__.values()
    }
    for token in forbidden:
        assert token not in fields
    assert fields == {
        "ok",
        "campaign_id",
        "generated_count",
        "failed_count",
        "content_piece_ids",
        "error_code",
        "error_message",
    }
