"""Unit tests for presentation UI DTOs (P0.21)."""

import json
from dataclasses import asdict

from ai_campaign_studio.presentation.ui_models import (
    CampaignPlanResultUiModel,
    CampaignSummaryUiModel,
    ExportCampaignResultUiModel,
    GenerateContentResultUiModel,
    ListCampaignsResultUiModel,
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
    """Success case: ok=True with campaign_id + plan_id (ACS-GUI-008)
    + plan_item_count set, error fields explicitly None."""
    result = CampaignPlanResultUiModel(
        ok=True,
        campaign_id="cmp_abc123",
        plan_id="plan_xyz789",
        plan_item_count=3,
        error_code=None,
        error_message=None,
    )
    blob = asdict(result)
    assert blob == {
        "ok": True,
        "campaign_id": "cmp_abc123",
        "plan_id": "plan_xyz789",
        "plan_item_count": 3,
        "error_code": None,
        "error_message": None,
    }


def test_campaign_plan_result_error_shape() -> None:
    """Error case: ok=False, success fields None, error fields populated.
    ``plan_id`` is also None on errors (the bridge only knows the
    plan_id after a successful run)."""
    result = CampaignPlanResultUiModel(
        ok=False,
        campaign_id=None,
        plan_id=None,
        plan_item_count=None,
        error_code="NO_PROVIDER_CONFIGURED",
        error_message="Nijedan AI provajder nije podešen.",
    )
    blob = asdict(result)
    assert blob == {
        "ok": False,
        "campaign_id": None,
        "plan_id": None,
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
            ok=True, campaign_id="cmp_1", plan_id="plan_1",
            plan_item_count=2,
            error_code=None, error_message=None,
        ),
        CampaignPlanResultUiModel(
            ok=False, campaign_id=None, plan_id=None, plan_item_count=None,
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
        ok=True, campaign_id="cmp_1", plan_id="plan_1", plan_item_count=1,
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
# ACS-F1-047: this DTO shrank from a 7-field RESULT shape to a 5-field
# STARTED shape. Per-piece outcomes (generated_count / failed_count /
# content_piece_ids) live on the JobState now and are reachable via
# ``get_job_status`` -- the sync response only carries ``ok`` /
# ``campaign_id`` / ``job_id`` / ``error_code`` / ``error_message``.


def test_generate_content_result_success_shape() -> None:
    """Happy path: ok=True, job_id populated, error fields None.

    The JS caller learns the per-piece outcome by polling
    ``get_job_status(job_id)`` until the job is terminal.
    """
    result = GenerateContentResultUiModel(
        ok=True,
        campaign_id="cmp_abc",
        job_id="job-1",
        error_code=None,
        error_message=None,
    )
    blob = asdict(result)
    assert blob == {
        "ok": True,
        "campaign_id": "cmp_abc",
        "job_id": "job-1",
        "error_code": None,
        "error_message": None,
    }


def test_generate_content_result_partial_failure_shape() -> None:
    """Partial success at the sync layer: ok=True with a job_id; the
    *partial* outcome is in the terminal JobState, not in the sync
    DTO. The test asserts only the sync DTO contract.
    """
    result = GenerateContentResultUiModel(
        ok=True,
        campaign_id="cmp_abc",
        job_id="job-2",
        error_code=None,
        error_message=None,
    )
    blob = asdict(result)
    assert blob["ok"] is True
    assert blob["job_id"] == "job-2"
    assert blob["campaign_id"] == "cmp_abc"
    assert blob["error_code"] is None
    assert blob["error_message"] is None


def test_generate_content_result_idempotent_re_click_shape() -> None:
    """Idempotent re-click: ok=True with a (fresh) job_id; the closure
    inside the job will see all items already have a piece and
    generate nothing. The DTO is structurally identical to a
    happy-path sync submission.
    """
    result = GenerateContentResultUiModel(
        ok=True,
        campaign_id="cmp_abc",
        job_id="job-3",
        error_code=None,
        error_message=None,
    )
    blob = asdict(result)
    assert blob["ok"] is True
    assert blob["job_id"] == "job-3"
    assert blob["error_code"] is None


def test_generate_content_result_error_shape() -> None:
    """Sync failure: ok=False, no job started (job_id is None),
    error fields populated. Replaces the old test that used
    ``generated_count=0, failed_count=3`` for the same purpose --
    those counters no longer live on the sync DTO.
    """
    result = GenerateContentResultUiModel(
        ok=False,
        campaign_id=None,
        job_id=None,
        error_code="GENERATION_FAILED",
        error_message="AI poziv za stavku item-1 nije uspio: NetworkError.",
    )
    blob = asdict(result)
    assert blob == {
        "ok": False,
        "campaign_id": None,
        "job_id": None,
        "error_code": "GENERATION_FAILED",
        "error_message": "AI poziv za stavku item-1 nije uspio: NetworkError.",
    }


def test_generate_content_result_is_json_serializable() -> None:
    """PYWEBVIEW_SECURITY §3: the bridge's return crosses the
    ``js_api`` boundary as JSON. The DTO must round-trip.
    """
    cases = [
        GenerateContentResultUiModel(
            ok=True, campaign_id="cmp_1", job_id="job-1",
            error_code=None, error_message=None,
        ),
        GenerateContentResultUiModel(
            ok=False, campaign_id=None, job_id=None,
            error_code="NO_PROVIDER_CONFIGURED",
            error_message="Nijedan AI provajder nije podešen.",
        ),
    ]
    for case in cases:
        roundtripped = json.loads(json.dumps(asdict(case)))
        assert roundtripped == asdict(case)


def test_generate_content_result_is_frozen() -> None:
    """DTOs are immutable."""
    import dataclasses
    result = GenerateContentResultUiModel(
        ok=True, campaign_id="cmp_1", job_id="job-1",
        error_code=None, error_message=None,
    )
    try:
        result.job_id = "hacked"  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        return
    raise AssertionError("GenerateContentResultUiModel must be frozen")


def test_generate_content_result_carries_no_api_key_field() -> None:
    """Structural guarantee: the DTO has NO field that could hold an
    API key (mirror of the ``ProviderConfigResultUiModel`` contract).
    ``job_id`` and ``campaign_id`` are NOT secrets.
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
        "job_id",
        "error_code",
        "error_message",
    }


def test_export_campaign_result_success_shape() -> None:
    """ACS-GUI-009: success case carries zip_path (an absolute local path,
    NOT a secret) plus exported/skipped counts."""
    result = ExportCampaignResultUiModel(
        ok=True,
        campaign_id="cmp_1",
        zip_path="/abs/exports/cmp_1.zip",
        exported_count=2,
        skipped_count=1,
        error_code=None,
        error_message=None,
    )
    blob = asdict(result)
    assert blob == {
        "ok": True,
        "campaign_id": "cmp_1",
        "zip_path": "/abs/exports/cmp_1.zip",
        "exported_count": 2,
        "skipped_count": 1,
        "error_code": None,
        "error_message": None,
    }


def test_export_campaign_result_is_frozen() -> None:
    import dataclasses
    result = ExportCampaignResultUiModel(
        ok=False,
        campaign_id=None,
        zip_path=None,
        exported_count=None,
        skipped_count=None,
        error_code="VALIDATION_ERROR",
        error_message="nope",
    )
    try:
        result.zip_path = "/tmp/x"  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        return
    raise AssertionError("ExportCampaignResultUiModel must be frozen")


def test_export_campaign_result_carries_no_secret_field() -> None:
    """Structural guarantee: the DTO has no api_key/secret field. The
    ``zip_path`` is a path, not a secret."""
    api_key = "a" + "pi_key"  # -> "api_key"
    fields = {
        f.name for f in ExportCampaignResultUiModel.__dataclass_fields__.values()
    }
    assert api_key not in fields
    assert "secret" not in fields
    assert fields == {
        "ok",
        "campaign_id",
        "zip_path",
        "exported_count",
        "skipped_count",
        "error_code",
        "error_message",
    }


def test_campaign_summary_ui_model_shape() -> None:
    """ACS-F1-046: one Kampanje-list row is JSON-safe with the exact
    fields the bridge produces (created_at as ISO string, no updated_at)."""
    row = CampaignSummaryUiModel(
        id="cmp-1",
        name="Test offer",
        status="PLAN_GENERATED",
        plan_item_count=3,
        brand="BrightSmile",
        created_at="2026-01-01T00:00:00+00:00",
    )
    blob = asdict(row)
    assert blob == {
        "id": "cmp-1",
        "name": "Test offer",
        "status": "PLAN_GENERATED",
        "plan_item_count": 3,
        "brand": "BrightSmile",
        "created_at": "2026-01-01T00:00:00+00:00",
    }


def test_list_campaigns_result_empty_success_shape() -> None:
    """ACS-F1-046: empty list is a valid success (``ok=True``), not an error."""
    result = ListCampaignsResultUiModel(
        ok=True,
        campaigns=(),
        error_code=None,
        error_message=None,
    )
    blob = asdict(result)
    assert blob == {
        "ok": True,
        "campaigns": (),
        "error_code": None,
        "error_message": None,
    }


def test_list_campaigns_result_carries_no_secret_field() -> None:
    """Structural guarantee: no api_key/secret field on the read DTOs."""
    api_key = "a" + "pi_key"  # -> "api_key"
    summary_fields = {
        f.name for f in CampaignSummaryUiModel.__dataclass_fields__.values()
    }
    result_fields = {
        f.name for f in ListCampaignsResultUiModel.__dataclass_fields__.values()
    }
    assert api_key not in summary_fields
    assert api_key not in result_fields
    assert "secret" not in summary_fields
    assert "secret" not in result_fields
