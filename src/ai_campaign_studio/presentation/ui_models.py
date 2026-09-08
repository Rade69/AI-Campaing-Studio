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


@dataclass(frozen=True)
class ExportCampaignResultUiModel:
    """Result of an "Izvezi ZIP paket" click (ACS-GUI-009 bridge).

    Returned by ``CampaignBridgeApi.export_campaign_package`` and converted
    to a plain ``dict`` before crossing the pywebview ``js_api`` boundary.
    ``zip_path`` is an ABSOLUTE local filesystem path (the export contract
    deliberately returns it to the user instead of opening a file-picker in
    this task) — it is a path, not a secret/token/API key, and never contains
    ``SecretStore`` content or traceback text.
    """

    ok: bool
    campaign_id: str | None
    zip_path: str | None
    exported_count: int | None
    skipped_count: int | None
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True)
class CampaignSummaryUiModel:
    """One row of the Kampanje list (ACS-F1-046 read path).

    ``name`` is the campaign brief's ``offer`` (the ``Campaign`` entity has
    no ``name`` field); ``brand`` is the brand's ``name`` (or ``""`` if the
    brand lookup fails, which should not happen in practice because
    ``campaign.brand_id`` is FK-referenced); ``plan_item_count`` is ``0``
    when the campaign has no plan yet. ``created_at`` is an ISO 8601 string
    (the ``Campaign`` entity has no ``updated_at`` — deliberately excluded
    from this task). Every field is JSON-safe.
    """

    id: str
    name: str
    status: str
    plan_item_count: int
    brand: str
    created_at: str


@dataclass(frozen=True)
class ListCampaignsResultUiModel:
    """Result of a ``list_campaigns`` call (ACS-F1-046).

    ``campaigns`` is ordered newest-first (``created_at DESC``). An empty
    list is a valid success (``ok=True``), NOT an error. Never carries
    secret/path/exception text.
    """

    ok: bool
    campaigns: tuple[CampaignSummaryUiModel, ...]
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True)
class BrandFactUiModel:
    """One approved fact shown on the Brend screen (ACS-F1-049).

    ``code`` is the fact's ``logical_fact_id``; ``text`` is the fact
    ``content``. Only ``is_fact_usable`` facts are emitted (see the bridge).
    """

    code: str
    text: str


@dataclass(frozen=True)
class BrandOverviewResultUiModel:
    """Result of a ``get_brand_overview`` call (ACS-F1-049).

    Single-brand MVP: the bridge resolves the demo brand via
    ``_ensure_brand()`` and returns its name, primary audience (first
    ``Audience``), voice (``BrandVoice.formality`` + ``tone``) and the list
    of usable approved facts. ``description`` is deliberately NOT included
    (``BrandSnapshot`` has no brand-description field — that stays
    fixture-only in the SSR). Never carries secret/path/exception text.
    """

    ok: bool
    brand_name: str | None
    primary_audience: str | None
    voice: tuple[str, ...]
    facts: tuple[BrandFactUiModel, ...]
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True)
class DashboardRecentCampaignUiModel:
    """One "Nedavne kampanje" row on the Početna dashboard (ACS-F1-051).

    ``name`` is the campaign brief's ``offer`` (same offer-as-name pattern as
    ``CampaignSummaryUiModel``); ``status`` is the raw ``CampaignStatus.value``
    string (consistent with the Kampanje list, which shows the raw status).
    """

    name: str
    status: str


@dataclass(frozen=True)
class DashboardOverviewResultUiModel:
    """Result of a ``get_dashboard_overview`` call (ACS-F1-051).

    Aggregates the 4 KPI counters across ALL campaigns and returns the most
    recent campaigns (newest first, capped at 5 — no pagination in this MVP).
    ``activity`` is deliberately NOT included (no domain activity-log concept
    — that panel stays fixture-only). Never carries secret/path/exception
    text.
    """

    ok: bool
    active_campaigns: int
    posts_planned: int
    drafts: int
    approved: int
    recent_campaigns: tuple[DashboardRecentCampaignUiModel, ...]
    error_code: str | None
    error_message: str | None
