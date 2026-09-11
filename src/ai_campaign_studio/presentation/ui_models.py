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
class StartIngestionResultUiModel:
    """Result of a "Pokreni ingestion" click on the Brend screen
    (ACS-GUI-011 bridge).

    Returned by ``CampaignBridgeApi.start_brand_ingestion`` and converted
    to a plain ``dict`` before crossing the pywebview ``js_api`` boundary.
    Same STARTED-shape convention as ``GenerateContentResultUiModel``
    (ACS-F1-047): ``ok=True`` only means the job was accepted, not that any
    page was actually fetched — the per-run outcome (``fetched_pages``,
    ``extracted_chunks``, ``built_candidates``, ``failed_pages``) lives on
    the background job's terminal ``JobState``, reachable via
    ``CampaignBridgeApi.get_job_status(job_id)``.
    """

    ok: bool
    brand_id: str | None
    job_id: str | None
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True)
class ClearIngestionResultUiModel:
    """Result of an "Obriši sve" click on the Brend screen's "Pregled
    činjenica" panel (ACS-GUI-013 bridge).

    Returned by ``CampaignBridgeApi.clear_brand_ingestion``. Deletes every
    ingestion run for the brand (and its snapshots/chunks/candidates/crawl
    targets/checkpoints) so the review list starts empty again for a new
    test URL — does NOT touch ``approved_facts`` (see
    ``IngestionRepositoryPort.delete_ingestion_data_for_brand``).
    """

    ok: bool
    brand_id: str | None
    deleted_run_count: int | None
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


@dataclass(frozen=True)
class DerivedMetricSetUiModel:
    """The 6 derived performance metrics (P1.5-G6/G7a).

    Presentation copy of the domain ``DerivedMetricSet`` values — the
    presentation layer does not import domain types, so the bridge maps
    ``DerivedMetricSet`` onto these primitives. CTR and Conversion Rate are
    RATIOS (0.034 == 3.4%), matching the G5 contract.
    """

    ctr: float | None = None
    cpc: float | None = None
    cpm: float | None = None
    cpa: float | None = None
    roas: float | None = None
    conversion_rate: float | None = None


@dataclass(frozen=True)
class RawMetricSetUiModel:
    """Relevant raw metric subset shown alongside derived metrics (G7a).

    ``impressions``/``clicks``/``spend`` are the three inputs the G7a UI
    surfaces as context for the derived CTR/CPC/CPM numbers; the remaining
    ``CanonicalMetricSet`` fields are deliberately omitted from this MVP.
    """

    impressions: int | None = None
    clicks: int | None = None
    spend: float | None = None


@dataclass(frozen=True)
class CampaignPerformanceResultUiModel:
    """Result of a ``get_campaign_performance`` call (ACS-F1-053).

    Aggregated performance for one campaign, computed by the G6
    ``build_campaign_performance_summary``. ``derived`` carries the G5
    ``DerivedMetricSet`` result; ``raw`` a relevant subset of the summed
    ``CanonicalMetricSet``; ``distribution_instance_count`` is the number of
    distribution instances for the campaign. A campaign with no performance
    data returns ``ok=True`` with all metrics ``None`` and count 0 (not an
    error). Never carries secret/path/exception text.
    """

    ok: bool
    derived: DerivedMetricSetUiModel
    raw: RawMetricSetUiModel
    distribution_instance_count: int
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True)
class ContentPerformanceRowUiModel:
    """One content-piece-level performance row (ACS-F1-054).

    ``label`` is the human-readable piece identifier (platform/format code,
    plus the payload headline when one exists); ``ctr``/``cpc`` are the
    derived metrics mapped straight from the G6
    ``build_content_performance_summary`` result (CTR + CPC is the chosen MVP
    subset — the full six-metric set already lives on the campaign-level
    G7a card). A piece with no performance data yields ``None`` metrics.
    """

    content_piece_id: str
    label: str
    ctr: float | None
    cpc: float | None


@dataclass(frozen=True)
class ContentPerformanceResultUiModel:
    """Result of a ``get_campaign_content_performance`` call (ACS-F1-054).

    One row per ``ContentPiece`` of the campaign, ordered by piece id (the
    repository's ``list_campaign_content`` ordering). A campaign with zero
    content pieces returns ``ok=True`` with an empty ``rows`` tuple (not an
    error). ``derived`` values per row come ONLY from the G6
    ``build_content_performance_summary`` builder — no hand-written formula
    in the bridge. Never carries secret/path/exception text.
    """

    ok: bool
    rows: tuple[ContentPerformanceRowUiModel, ...]
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True)
class PerformanceCsvColumnUiModel:
    """Mapping status of ONE canonical field in the CSV preview (ACS-F1-055).

    ``header`` is the single CSV header that matched (or ``None`` for
    ambiguous/unmatched); ``candidates`` is every CSV header aliasing the
    field; ``status`` is the raw G3 mapping status
    ("matched"/"ambiguous"/"unmatched"). ``header``/``candidates`` are
    verbatim CSV text — the frontend MUST escape them (XSS).
    """

    canonical_field: str
    header: str | None
    status: str
    candidates: tuple[str, ...]


@dataclass(frozen=True)
class PerformanceCsvInvalidSampleUiModel:
    """One invalid CSV row sample with its readable errors (ACS-F1-055).

    ``errors`` strings embed the offending CSV cell values — verbatim
    user-file text, MUST be escaped by the frontend.
    """

    row_number: int
    errors: tuple[str, ...]


@dataclass(frozen=True)
class PerformanceCsvPreviewResultUiModel:
    """Result of ``pick_and_preview_performance_csv`` (ACS-F1-055).

    ``cancelled=True`` is a normal "user dismissed the native dialog"
    outcome (``ok=True``, NOT an error) with every other field empty.
    On a real preview, ``file_path`` is the chosen CSV path (a path, not a
    secret — deliberately returned so the confirm step can reference it
    without reopening the dialog) and the mapping summary follows.
    Never carries secret/path/exception text beyond the chosen
    ``file_path``.
    """

    ok: bool
    cancelled: bool
    file_path: str | None
    columns: tuple[PerformanceCsvColumnUiModel, ...]
    total_rows: int
    valid_rows: int
    invalid_rows: int
    invalid_samples: tuple[PerformanceCsvInvalidSampleUiModel, ...]
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True)
class ConfirmPerformanceImportResultUiModel:
    """Result of ``confirm_performance_import`` (ACS-F1-055, ACS-F1-057).

    ``row_count``/``valid_count``/``invalid_count`` come from the persisted
    ``PerformanceImportBatch`` (valid = ``matched_count``, invalid =
    ``unmatched_count`` per the G3 temporary semantics); the four match
    counters come from the G4 ``MatchPerformanceImportBatch`` result;
    ``materialized_count``/``skipped_invalid_count`` come from the
    ACS-F1-057 ``MaterializePerformanceSnapshots`` step (how many matched +
    valid rows became ``PerformanceSnapshot`` rows, and how many matched but
    invalid rows were skipped). Never carries secret/path/exception text.
    """

    ok: bool
    batch_id: str | None
    row_count: int
    valid_count: int
    invalid_count: int
    matched_count: int
    ambiguous_count: int
    unmatched_count: int
    skipped_count: int
    materialized_count: int
    skipped_invalid_count: int
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True)
class IngestionReviewCandidateUiModel:
    """One FactCandidate row for the fact-review list (S2-G7b).

    ``snapshot_url`` is the ``SourceSnapshot.url`` the candidate's
    provenance points at (G-WI-EVIDENCE); ``content`` is the plain-text
    candidate content; ``chunk_id`` is optional locator-precise evidence.
    """

    candidate_id: str
    snapshot_id: str
    snapshot_url: str
    content: str
    chunk_id: str | None
    status: str
    created_at: str


@dataclass(frozen=True)
class IngestionReviewResultUiModel:
    """Result of ``get_ingestion_review`` (S2-G7b).

    Returns every ``FactCandidate`` for the brand plus separate
    ``approved_count``/``rejected_count`` counters. Never carries
    secret/path/exception text.
    """

    ok: bool
    brand_id: str | None
    candidates: tuple[IngestionReviewCandidateUiModel, ...]
    approved_count: int
    rejected_count: int
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True)
class ApproveFactResultUiModel:
    """Result of ``approve_fact_candidate`` (S2-G7b).

    ``approved_fact_id`` is the new ``ApprovedFact.id`` created by the G7a
    ``ApproveFactCandidate`` use-case; ``version`` is always 1 (first
    version of a brand-new logical fact).
    """

    ok: bool
    approved_fact_id: str | None
    candidate_id: str | None
    snapshot_url: str | None
    version: int | None
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True)
class RejectFactResultUiModel:
    """Result of ``reject_fact_candidate`` (S2-G7b)."""

    ok: bool
    candidate_id: str | None
    status: str | None
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True)
class BulkReviewResultUiModel:
    """Result of ``bulk_review_fact_candidates`` (ACS-GUI-017).

    A single page can produce 100+ tiny PROPOSED candidates (deterministic
    1:1 paragraph->candidate, no LLM synthesis — see BUILD_FACTS), so
    one-by-one approve/reject does not scale. This loops the existing
    ``ApproveFactCandidate``/``RejectFactCandidate`` use-cases per id and
    reports counts — partial success (some ids already decided by a
    concurrent action, or missing) is a normal outcome for a large batch,
    not an all-or-nothing failure.
    """

    ok: bool
    action: str | None
    succeeded_count: int | None
    failed_count: int | None
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True)
class AssembleSnapshotResultUiModel:
    """Result of ``assemble_brand_snapshot`` (S2-G7b)."""

    ok: bool
    snapshot_id: str | None
    brand_id: str | None
    version: int | None
    approved_fact_count: int
    created_at: str | None
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True)
class ActivateBrandSnapshotResultUiModel:
    """Result of ``activate_brand_snapshot`` (ACS-S2-018).

    ``was_already_active=True`` means the requested snapshot_id matched
    what was already in the ``brand-seed.json`` cache — the GUI uses this
    to skip the post-activation reload + show a calmer toast ("already
    active" vs "activated").
    """

    ok: bool
    snapshot_id: str | None
    brand_id: str | None
    version: int | None
    approved_fact_count: int
    created_at: str | None
    was_already_active: bool
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True)
class BrandSnapshotSummaryUiModel:
    """One row in the snapshot history list (ACS-S2-018).

    The bridge flattens a ``BrandSnapshot`` VO into this dict so the GUI
    can render it without depending on the domain dataclass. ``is_active``
    reflects the ``brand-seed.json`` cache at the moment of listing (NOT
    a per-row lookup of the latest seed).
    """

    snapshot_id: str
    version: int
    language: str
    locale: str
    script: str
    approved_fact_count: int
    created_at: str
    is_active: bool


@dataclass(frozen=True)
class ListBrandSnapshotsResultUiModel:
    """Result of ``list_brand_snapshots`` (ACS-S2-018)."""

    ok: bool
    brand_id: str | None
    snapshots: tuple[dict, ...]
    error_code: str | None
    error_message: str | None
