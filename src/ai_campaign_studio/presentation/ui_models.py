"""Framework-neutral UI data-transfer objects (P0.21).

Owns the immutable ``NotificationUiModel`` and ``ProviderStatusUiModel`` DTOs
shared by the future PySide6/pywebview frontends. No Qt model classes, no
signals, no bridge objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class NotificationLevel(StrEnum):
    """Severity of a UI notification."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass(frozen=True)
class NotificationUiModel:
    """A single user-facing notification."""

    level: NotificationLevel
    message_key: str
    params: dict[str, str] = field(default_factory=dict)
    technical_details: str | None = None


@dataclass(frozen=True)
class ProviderStatusUiModel:
    """Provider status shown in settings UI."""

    provider_code: str
    display_name: str
    configured: bool
    validated: bool
    model_count: int


@dataclass(frozen=True)
class CampaignPlanResultUiModel:
    """Result of a "Sačuvaj i napravi plan" click (ACS-GUI-005 bridge,
    extended in ACS-GUI-008 with ``plan_id``).

    Returned by ``CampaignBridgeApi.create_campaign_and_generate_plan``.
    Converted to a plain ``dict`` before crossing the pywebview ``js_api``
    boundary (``js_api`` is required to return JSON-serializable values,
    so the bridge calls ``dataclasses.asdict`` on this model). Every
    field is JSON-safe by construction — no ``SecretStore`` content,
    no traceback strings, no file paths.

    ACS-GUI-008 added ``plan_id`` so the JS caller can forward it to
    ``generate_campaign_content`` on the next step (Studio sadržaja
    screen), removing the need for the bridge to do raw SQL to look
    up "the current plan for this campaign". The new field is added
    AFTER the existing ones (aditive — old fields and old test
    expectations stay untouched).
    """

    ok: bool
    campaign_id: str | None
    plan_id: str | None
    plan_item_count: int | None
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True)
class ProviderConfigResultUiModel:
    """Result of a "Sačuvaj" click on the Podešavanja → AI provajderi
    panel (ACS-GUI-007 bridge).

    Returned by ``CampaignBridgeApi.configure_provider``. Converted to
    a plain ``dict`` before crossing the pywebview ``js_api`` boundary.
    **NEVER carries the API key** — neither the input key, nor an
    echoed/masked/preview copy. The ``provider_code`` is the
    normalized UPPERCASE registry code (e.g. ``"OPENAI"``); it is not
    a secret.
    """

    ok: bool
    provider_code: str | None
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True)
class GenerateContentResultUiModel:
    """Result of a "Generiši sadržaj" click on the Studio sadržaja
    screen (ACS-GUI-008 bridge).

    Returned by ``CampaignBridgeApi.generate_campaign_content``.
    Converted to a plain ``dict`` before crossing the pywebview
    ``js_api`` boundary.

    ACS-F1-047: this DTO shrank from the original 7-field shape
    (``generated_count`` / ``failed_count`` / ``content_piece_ids``)
    to a 5-field STARTED shape (``ok`` / ``campaign_id`` / ``job_id``
    / ``error_code`` / ``error_message``). The full per-piece outcome
    now lives on the background job's ``JobState`` and is reachable
    via ``CampaignBridgeApi.get_job_status(job_id)``. JS polls that
    endpoint and shows a live progress counter on the same button
    while the job is ``RUNNING``; per-piece counts are read from the
    terminal ``JobState`` once the job lands in ``SUCCEEDED`` /
    ``FAILED`` / ``CANCELLED``.

    The pre-F1-047 semantic invariants still hold, just at a
    different layer:

    - ``ok=True`` means the job was ACCEPTED and started; it does
      NOT guarantee any piece was generated (partial / total failure
      is reported on the terminal ``JobState``).
    - ``ok=False`` is only set on a sync error path (boundary
      validation, plan lookup, provider resolution, JobManager
      submission failure, or infrastructure lifecycle failure --
      BF-5). Any error that happens AFTER the job is accepted is
      surfaced via the terminal ``JobState``'s ``error_code`` /
      ``error_message``.
    - ``job_id`` is the lookup key for the background job; it is
      the ONLY way the JS side learns the per-piece outcome.
    """

    ok: bool
    campaign_id: str | None
    job_id: str | None
    error_code: str | None
    error_message: str | None
