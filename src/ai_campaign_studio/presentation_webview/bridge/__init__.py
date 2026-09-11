"""pywebview ``js_api`` bridge (ACS-GUI-005 / ACS-GUI-007).

The first real GUI→backend wiring in the project. Exposes a narrow class
(``CampaignBridgeApi``) to the WebView2 JavaScript context via pywebview's
``js_api=`` argument. Per ``docs/PYWEBVIEW_SECURITY.md`` §3:

- Two narrow public methods: ``create_campaign_and_generate_plan``
  (ACS-GUI-005) and ``configure_provider`` (ACS-GUI-007 — the FIRST
  method that accepts a secret string FROM JS; the campaign flow only
  USES secrets, never accepts them from the user). Each method is
  narrow on its own: one positional ``dict`` argument, one
  ``CampaignPlanResultUiModel`` / ``ProviderConfigResultUiModel``
  return shape.
- Every payload from JS is validated at the boundary (Pydantic schema
  for the campaign flow, explicit string-type checks for the
  configure flow; we do NOT trust JS types/values either way).
- The return ``dict`` is JSON-serializable, never contains API keys,
  tokens, SecretStore contents, file paths, or raw Python exception
  text. In particular, ``configure_provider`` NEVER carries the
  ``api_key`` field (input or echoed) in the result DTO.

The bridge is the ONLY component that knows how to translate the
form-shaped GUI input into the application-layer shape. It is
composition: it wires use-cases, repositories, the AI provider
factory, and a brand-seeding cache.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass
from functools import wraps
from pathlib import Path
from typing import Any

from ai_campaign_studio.application.ai_provider.configure_provider import (
    ConfigureProvider,
)
from ai_campaign_studio.application.brands.load_brand_fixture import LoadBrandFixture
from ai_campaign_studio.application.campaigns.approve_campaign_plan import (
    ApproveCampaignPlan,
)
from ai_campaign_studio.application.campaigns.create_campaign import CreateCampaign
from ai_campaign_studio.application.campaigns.generate_campaign_plan import (
    GenerateCampaignPlan,
)
from ai_campaign_studio.application.export import ExportCampaign
from ai_campaign_studio.application.ingestion.approve_fact_candidates import (
    ApproveFactCandidate,
    RejectFactCandidate,
)
from ai_campaign_studio.application.ingestion.ingest_brand_sources import (
    IngestBrandSources,
)
from ai_campaign_studio.application.performance import materialize_performance_snapshots
from ai_campaign_studio.application.performance.build_performance_summaries import (
    build_campaign_performance_summary,
    build_content_performance_summary,
)
from ai_campaign_studio.application.performance.confirm_performance_import import (
    ConfirmPerformanceImport,
)
from ai_campaign_studio.application.performance.match_performance_import_batch import (
    MatchPerformanceImportBatch,
)
from ai_campaign_studio.application.performance.preview_performance_mapping import (
    PreviewPerformanceMapping,
)
from ai_campaign_studio.application.posts.generate_social_post import (
    GenerateSocialPost,
)
from ai_campaign_studio.application.schemas.campaign_brief import CampaignBriefInput
from ai_campaign_studio.application.visual.generate_visual_system import (
    GenerateVisualSystem,
)
from ai_campaign_studio.application.visual.plan_post_layout import PlanPostLayout
from ai_campaign_studio.bootstrap import create_bootstrap
from ai_campaign_studio.config.paths import AppPaths
from ai_campaign_studio.config.settings import AppSettings
from ai_campaign_studio.domain.brand.entities import BrandSnapshot
from ai_campaign_studio.domain.brand.value_objects import BrandVoice, VisualIdentity
from ai_campaign_studio.domain.campaign.entities import CampaignBrief
from ai_campaign_studio.domain.campaign.enums import (
    CampaignPlanStatus,
    CampaignStatus,
)
from ai_campaign_studio.domain.common.errors import (
    EntityNotFound,
    InvariantViolation,
    JobError,
    RegistryError,
)
from ai_campaign_studio.domain.common.ids import (
    BrandId,
    BrandSnapshotId,
    CampaignId,
    CampaignPlanId,
    FactCandidateId,
    VisualSystemId,
    new_id,
)
from ai_campaign_studio.domain.common.timestamps import utc_now
from ai_campaign_studio.domain.content.entities import CampaignTarget, ContentPiece
from ai_campaign_studio.domain.content.enums import ContentStatus
from ai_campaign_studio.domain.facts.enums import FactStatus
from ai_campaign_studio.domain.facts.policies import is_fact_usable
from ai_campaign_studio.infrastructure.ai.provider_adapter_factory import (
    _PROVIDER_PRIORITY,
    build_text_generation_adapter,
)
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.repositories import (
    SqliteBrandRepository,
    SqliteCampaignRepository,
    SqliteContentRepository,
    SqliteFactRepository,
    SqliteIngestionRepository,
    SqlitePerformanceRepository,
    SqliteProviderConfigRepository,
    SqliteRevisionRepository,
    SqliteVisualRepository,
)
from ai_campaign_studio.infrastructure.database.unit_of_work import SqliteUnitOfWork
from ai_campaign_studio.infrastructure.export import ZipExportWriter
from ai_campaign_studio.infrastructure.extraction import (
    BoilerplateFilter,
    Deduplicator,
    MainContentExtractor,
)
from ai_campaign_studio.infrastructure.prompts.yaml_prompt_repository import (
    YamlPromptRepository,
)
from ai_campaign_studio.infrastructure.rendering import PillowRenderer
from ai_campaign_studio.infrastructure.visual_extraction.adapter import (
    VisualIdentityAdapter,
)
from ai_campaign_studio.infrastructure.web_ingestion.crawl_budget import CrawlBudget
from ai_campaign_studio.infrastructure.web_ingestion.domain_discovery import (
    DomainDiscovery,
)
from ai_campaign_studio.infrastructure.web_ingestion.http_fetcher import HttpFetcher
from ai_campaign_studio.infrastructure.web_ingestion.robots_reader import RobotsReader
from ai_campaign_studio.infrastructure.web_ingestion.sitemap_reader import (
    SitemapReader,
)
from ai_campaign_studio.infrastructure.web_ingestion.url_classifier import (
    UrlClassifier,
)
from ai_campaign_studio.infrastructure.web_ingestion.url_normalizer import (
    normalize_url,
)
from ai_campaign_studio.infrastructure.web_ingestion.url_safety_policy import (
    UrlSafetyPolicy,
)
from ai_campaign_studio.jobs.cancellation import CancellationError
from ai_campaign_studio.presentation.ui_models import (
    ActivateBrandSnapshotResultUiModel,
    ApproveFactResultUiModel,
    AssembleSnapshotResultUiModel,
    BrandFactUiModel,
    BrandOverviewResultUiModel,
    BrandSnapshotSummaryUiModel,
    BulkReviewResultUiModel,
    CampaignPerformanceResultUiModel,
    CampaignPlanResultUiModel,
    CampaignSummaryUiModel,
    ClearIngestionResultUiModel,
    ConfirmPerformanceImportResultUiModel,
    ContentPerformanceResultUiModel,
    ContentPerformanceRowUiModel,
    DashboardOverviewResultUiModel,
    DashboardRecentCampaignUiModel,
    DerivedMetricSetUiModel,
    ExportCampaignResultUiModel,
    GenerateContentResultUiModel,
    IngestionReviewCandidateUiModel,
    IngestionReviewResultUiModel,
    ListBrandSnapshotsResultUiModel,
    ListCampaignsResultUiModel,
    PerformanceCsvColumnUiModel,
    PerformanceCsvInvalidSampleUiModel,
    PerformanceCsvPreviewResultUiModel,
    ProviderConfigResultUiModel,
    RawMetricSetUiModel,
    RejectFactResultUiModel,
    StartIngestionResultUiModel,
)

_BRAND_SEED_FILE = "brand-seed.json"

# Stable error codes that flow back to JS. These are PART OF THE
# BRIDGE'S PUBLIC API — changing them is a breaking change for the
# frontend (app.js). Always map internal exceptions to one of these.
_ERROR_NO_PROVIDER = "NO_PROVIDER_CONFIGURED"
_ERROR_KEY_MISSING = "PROVIDER_KEY_MISSING"
_ERROR_VALIDATION = "VALIDATION_ERROR"
_ERROR_GENERATION = "GENERATION_FAILED"
_ERROR_INTERNAL = "INTERNAL_ERROR"


@dataclass(frozen=True)
class _CallResources:
    """SQLite adapters owned by exactly one js_api invocation."""

    brand_repo: SqliteBrandRepository
    fact_repo: SqliteFactRepository
    ingestion_repo: SqliteIngestionRepository
    campaign_repo: SqliteCampaignRepository
    provider_config_repo: SqliteProviderConfigRepository
    # ACS-GUI-008: ``generate_campaign_content`` reads pieces and writes
    # revisions; both repos live in the per-call graph (same lifetime
    # as the rest).
    content_repo: SqliteContentRepository
    revision_repo: SqliteRevisionRepository
    # ACS-GUI-009: ``export_campaign_package`` reads/writes visual
    # systems + layout specs and persists ``DistributionInstance`` rows.
    visual_repo: SqliteVisualRepository
    performance_repo: SqlitePerformanceRepository
    uow: SqliteUnitOfWork


# ACS-GUI-008 (fix-brief-3 / Codex BF-5): lifecycle error mapper
# dispatch. ``_with_call_resources`` catches exceptions raised by
# ``_resource_scope()`` itself (e.g. SQLite open/close failure)
# BEFORE the wrapped method's own try/except sees them. Without an
# operation-aware mapper, every non-``configure_provider`` method
# used to fall through to ``self._err()`` — which builds a
# ``CampaignPlanResultUiModel`` dict, NOT the right DTO for the
# method. JS callers typed to the wrong DTO got missing or
# extra fields on the one failure path that is hardest to recover
# from silently. Fix: each public method declares which DTO it
# returns, and the decorator dispatches accordingly. New methods
# MUST add an entry here.
_LIFECYCLE_ERROR_MAPPERS: dict[str, str] = {
    "configure_provider": "_provider_err",
    "create_campaign_and_generate_plan": "_err",
    "generate_campaign_content": "_generate_err",
    "get_job_status": "_job_status_err",
    "cancel_job": "_job_status_err",
    "export_campaign_package": "_export_err",
    "list_campaigns": "_list_err",
    "get_brand_overview": "_brand_err",
    "get_dashboard_overview": "_dashboard_err",
    "get_campaign_performance": "_performance_err",
    "get_campaign_content_performance": "_content_performance_err",
    "pick_and_preview_performance_csv": "_preview_err",
    "confirm_performance_import": "_confirm_err",
    "get_ingestion_review": "_ingestion_review_err",
    "approve_fact_candidate": "_approve_err",
    "reject_fact_candidate": "_reject_err",
    "assemble_brand_snapshot": "_assemble_err",
    "start_brand_ingestion": "_start_ingestion_err",
    "clear_brand_ingestion": "_clear_ingestion_err",
    "bulk_review_fact_candidates": "_bulk_review_err",
    "activate_brand_snapshot": "_activate_err",
    "list_brand_snapshots": "_list_snapshots_err",
}
# Per-method fallback message used ONLY when the resource-lifecycle
# fails (we never want to surface the underlying exception text;
# provider secrets could in theory end up in a downstream
# adapter's exception message).
_LIFECYCLE_ERROR_MESSAGES: dict[str, str] = {
    "configure_provider": "Konfiguracija provajdera nije uspjela (interna greška).",
    "create_campaign_and_generate_plan": "Interna greška — pogledajte log aplikacije.",
    "generate_campaign_content": "Generisanje sadržaja nije uspjelo (interna greška).",
    "get_job_status": "Ne mogu pročitati status posla (interna greška).",
    "cancel_job": "Otkazivanje posla nije uspjelo (interna greška).",
    "export_campaign_package": "Izvoz nije uspio (interna greška).",
    "list_campaigns": "Učitavanje kampanja nije uspjelo (interna greška).",
    "get_brand_overview": "Učitavanje brenda nije uspjelo (interna greška).",
    "get_dashboard_overview": "Učitavanje pregleda nije uspjelo (interna greška).",
    "get_campaign_performance": "Učitavanje učinka nije uspjelo (interna greška).",
    "get_campaign_content_performance": (
        "Učitavanje učinka po objavi nije uspjelo "
        "(interna greška)."
    ),
    "pick_and_preview_performance_csv": (
        "Učitavanje CSV pregleda nije uspjelo "
        "(interna greška)."
    ),
    "confirm_performance_import": "Uvoz performansi nije uspio (interna greška).",
    "get_ingestion_review": (
        "Učitavanje pregleda činjenica nije uspjelo (interna greška)."
    ),
    "approve_fact_candidate": (
        "Odobravanje činjenice nije uspjelo (interna greška)."
    ),
    "reject_fact_candidate": (
        "Odbijanje činjenice nije uspjelo (interna greška)."
    ),
    "assemble_brand_snapshot": (
        "Kreiranje snimka brenda nije uspjelo (interna greška)."
    ),
    "start_brand_ingestion": (
        "Pokretanje preuzimanja sadržaja nije uspjelo (interna greška)."
    ),
    "clear_brand_ingestion": (
        "Brisanje preuzetih podataka nije uspjelo (interna greška)."
    ),
    "bulk_review_fact_candidates": (
        "Masovna akcija nad činjenicama nije uspjela (interna greška)."
    ),
    "activate_brand_snapshot": (
        "Aktivacija snimka brenda nije uspjela (interna greška)."
    ),
    "list_brand_snapshots": (
        "Učitavanje liste snimaka brenda nije uspjelo (interna greška)."
    ),
}


def _with_call_resources(method: Callable[..., dict]) -> Callable[..., dict]:
    """Run one public bridge method with a fresh, thread-local DB graph."""

    @wraps(method)
    def _wrapped(self: CampaignBridgeApi, *args: Any, **kwargs: Any) -> dict:
        try:
            with self._resource_scope():
                return method(self, *args, **kwargs)
        except Exception as exc:
            # Connection open/close failures happen outside the method's
            # own error mapping. Keep the js_api no-raise contract and do
            # not log exception text: configure_provider's args may carry
            # an API key even though the DB exception normally would not.
            # BF-5 (Codex runda 2): dispatch to the DTO-specific error
            # mapper so the result has the EXACT key set the public
            # contract promises for THIS method (not a different
            # method's DTO leaking through ``_err()``). Unknown methods
            # fall back to ``_err`` (the plan-flow DTO) which is the
            # historical default; the table is the source of truth.
            self._bootstrap.logger.error(
                "bridge resource lifecycle failed for %s (err=%s)",
                method.__name__,
                type(exc).__name__,
            )
            mapper_name = _LIFECYCLE_ERROR_MAPPERS.get(
                method.__name__, "_err"
            )
            mapper = getattr(self, mapper_name)
            return mapper(
                _ERROR_INTERNAL,
                _LIFECYCLE_ERROR_MESSAGES.get(
                    method.__name__,
                    "Interna greška — pogledajte log aplikacije.",
                ),
            )

    return _wrapped


def _ordered_configured_codes(configured_codes: list[str]) -> list[str]:
    """Return configured provider codes in priority order.

    Same ordering as ``pick_configured_provider`` (``_PROVIDER_PRIORITY``
    first, then any remaining codes in their original order), but returns
    ALL candidates so the bridge can fall back through every configured
    provider instead of stopping at the first. ``_PROVIDER_PRIORITY`` is
    imported from the factory so the ordering has a single source of truth
    and can never drift.
    """
    upper_to_original = {code.upper(): code for code in configured_codes}
    ordered: list[str] = []
    seen: set[str] = set()
    for priority_code in _PROVIDER_PRIORITY:
        original = upper_to_original.get(priority_code)
        if original is not None and original.upper() not in seen:
            ordered.append(original)
            seen.add(original.upper())
    for code in configured_codes:
        if code.upper() not in seen:
            ordered.append(code)
            seen.add(code.upper())
    return ordered


def _targets_from_brief(brief: CampaignBrief) -> list[CampaignTarget]:
    """Convert a persisted ``CampaignBrief.targets`` to a ``list[CampaignTarget]``.

    Deliberate copy of the helper in ``application/evaluation/run_system_b.py``
    rather than an import: this module is in the presentation layer and
    ``application/`` is in ``forbidden_paths`` for ACS-GUI-008, so the
    helper has to live in both places. The two implementations are
    pinned to the same shape (round-robin over the same list) by the
    test ``test_round_robin_assignment_matches_run_system_b``.
    """
    return [
        CampaignTarget(
            channel=t.channel,
            platform_code=t.platform_code,
            format_code=t.format_code,
        )
        for t in brief.targets
    ]


def _target_for_item(
    index: int, targets: list[CampaignTarget]
) -> CampaignTarget | None:
    """Round-robin target for the ``index``-th ``CampaignItem``.

    Same shape as ``run_system_b.py:86``
    (``targets[index % len(targets)] if targets else None``). Returns
    ``None`` when the brief has no targets at all (degenerate brief
    created without any platform) so the caller can record a
    user-level "no targets" failure rather than a misleading AI error.
    """
    if not targets:
        return None
    return targets[index % len(targets)]


def _content_piece_label(piece: ContentPiece) -> str:
    """Human-readable label for one content-piece performance row.

    ``platform_code/format_code`` is always present; the payload headline
    is appended only when a payload exists. A piece with no payload (not
    yet generated) falls back to the bare platform/format label — never an
    empty string. The returned label is free-form user/AI text, so the
    frontend MUST escape it before inserting it into the DOM (the bridge
    never escapes here — it returns raw data, same contract as every other
    read DTO).
    """
    base = f"{piece.target.platform_code}/{piece.target.format_code}"
    if piece.payload is not None:
        return f"{base} — {piece.payload.headline}"
    return base


class CampaignBridgeApi:
    """Narrow pywebview ``js_api`` surface for the campaign workflow.

    Single public method for JS (``create_campaign_and_generate_plan``).
    Everything else is internal helper prefixed with ``_``.

    Lifetime: the bridge is constructed once in ``presentation_webview/
    __main__.py`` and passed to ``webview.create_window(..., js_api=self)``.
    Pywebview dispatches each call on a fresh thread, so the bridge keeps
    thread-safe shared services only. Every public call creates and closes
    its own SQLite connection, repositories, and unit of work.
    """

    def __init__(
        self,
        *,
        paths: AppPaths | None = None,
        settings: AppSettings | None = None,
    ) -> None:
        # Bootstrap is the single source of truth for settings, paths,
        # secret store, DB migrations, and registries. Its connection is
        # startup-only: create_bootstrap runs migrations exactly once, then
        # we close it before pywebview starts dispatching worker threads.
        #
        # ``paths`` and ``settings`` are explicit test seams. Production
        # code passes neither, and the defaults below pick the right
        # values:
        # - ``paths=None`` -> ``create_bootstrap`` builds the canonical
        #   ``AppPaths`` (resolved via ``AppSettings`` -> env -> defaults).
        # - ``settings=None`` -> the real GUI app uses
        #   ``AppSettings(environment="production")`` so the SecretStore
        #   is the real OS keyring (``KeyringSecretStore``), not the
        #   read-only dev/test ``EnvironmentSecretStore``. Tests that
        #   build the bridge directly MUST pass an explicit ``settings``
        #   (typically ``AppSettings(environment="development")``) so
        #   they do not touch the real OS keyring during test runs.
        if settings is None:
            settings = AppSettings(environment="production")
        self._bootstrap = create_bootstrap(settings=settings, paths=paths)
        self._bootstrap.database_connection.close()
        # ACS-GUI-008 (post-HOTFIX-002): every public call opens its
        # own SQLite connection graph via ``_resource_scope()`` (a
        # ContextVar + context manager). This is the per-thread pattern
        # that survives pywebview's worker-thread dispatch -- the
        # connection is created on the worker thread and closed there.
        # ``content_repo`` and ``revision_repo`` (needed by
        # ``generate_campaign_content``) are added in ``_CallResources``
        # below + exposed as ``@property`` getters.
        self._active_resources: ContextVar[_CallResources | None] = ContextVar(
            f"campaign_bridge_resources_{id(self)}", default=None
        )
        # YamlPromptRepository.from_bundled_resources() reads from the
        # repo's ``resources/prompts/`` dir; this is the same source the
        # integration test uses, so prompts are identical between
        # tests and the live app.
        self._prompt_repo = YamlPromptRepository.from_bundled_resources()
        self._brand_fixture_path = (
            self._bootstrap.paths.resources_dir / "fixtures" / "brightsmile.json"
        )
        # ACS-GUI-008 (fix-brief-2 BF-3): in-process lock per
        # ``(campaign_id, plan_id)`` pair. Without this, two pywebview
        # worker threads can both read the "empty existing-pieces"
        # snapshot before either writes, and BOTH call
        # ``GenerateSocialPost`` for the same ``CampaignItem`` (duplicate
        # content in the pipeline). The lock is created lazily on first
        # access, then reused; different ``(campaign_id, plan_id)`` pairs
        # do not block each other. The single live ``CampaignBridgeApi``
        # instance per process makes the instance-level dict the right
        # scope (no need for a process-global).
        self._generation_locks: dict[tuple[str, str], threading.Lock] = {}
        self._generation_locks_guard = threading.Lock()
        # ACS-S2-016 R1-BF-1: assembling a snapshot is a read-version-write
        # sequence. Pywebview can dispatch two calls on separate workers, so
        # serialize that sequence per brand while allowing unrelated brands
        # to assemble independently.
        self._snapshot_assembly_locks: dict[str, threading.Lock] = {}
        self._snapshot_assembly_locks_guard = threading.Lock()
        # ACS-GUI-009: in-process ``plan_id -> visual_system_id`` cache for
        # export idempotency (``VisualRepositoryPort`` has no "get by plan_id"
        # lookup). Same instance-level scope as ``_generation_locks``; a
        # double-click that makes a SECOND visual system for the same plan is
        # an accepted low-risk edge case (orphaned unused row, NOT duplicated
        # exported content).
        self._visual_system_by_plan: dict[str, str] = {}
        self._visual_system_by_plan_guard = threading.Lock()
        # ACS-S2-018: the brand-seed.json cache is a single file shared by
        # ``_ensure_brand`` (reads from ``create_campaign_and_generate_plan``
        # and ``get_brand_overview``) and the new ``activate_brand_snapshot``
        # (writes). One process-wide lock is enough — the file is global,
        # not per-brand — and it covers the activate-vs-read race that
        # would otherwise let a campaign be created against an older
        # snapshot than the user just activated.
        self._active_seed_lock = threading.Lock()

    # --- js_api surface ---

    @_with_call_resources
    def create_campaign_and_generate_plan(self, raw_brief: dict) -> dict:
        """End-to-end: validate, persist brand+campaign, generate plan.

        ``raw_brief`` is the arbitrary ``dict`` shipped by ``app.js``. We do
        NOT trust its shape — ``CampaignBriefInput.model_validate`` is the
        source of truth. Returns a plain ``dict`` (JSON-serializable)
        suitable for crossing the pywebview boundary. Never raises into JS
        (per PYWEBVIEW_SECURITY §3): every exception path is mapped to a
        result ``dict`` with ``ok=False``.
        """
        try:
            # 1. Boundary validation (Pydantic). If JS sent garbage,
            #    ValidationError -> VALIDATION_ERROR.
            if not isinstance(raw_brief, dict):
                return self._err(
                    _ERROR_VALIDATION,
                    "Pošiljka iz GUI-ja nije objekat.",
                )
            try:
                brief_input = CampaignBriefInput.model_validate(raw_brief)
            except Exception as exc:  # ValidationError or any pydantic quirk
                return self._err(_ERROR_VALIDATION, str(exc))

            # 2. Brand seeding (idempotent via brand-seed.json cache).
            try:
                brand_id, snapshot_id = self._ensure_brand()
            except Exception as exc:
                self._bootstrap.logger.exception("brand seeding failed")
                return self._err(
                    _ERROR_INTERNAL,
                    f"Ne mogu pripremiti demo brend: {type(exc).__name__}.",
                )

            # 3. Provider resolution (configured-only, hardcoded priority).
            try:
                provider_code, api_key = self._resolve_provider()
            except Exception as exc:
                self._bootstrap.logger.exception("provider resolution failed")
                return self._err(
                    _ERROR_INTERNAL,
                    "Greška pri čitanju konfiguracije provajdera: "
                    f"{type(exc).__name__}.",
                )
            if provider_code is None:
                return self._err(
                    _ERROR_NO_PROVIDER,
                    "Nijedan AI provajder nije podešen. Podesi API ključ ručno "
                    "(skripta) dok Podešavanja ekran ne bude spojen na pravi backend.",
                )
            if not api_key:
                return self._err(
                    _ERROR_KEY_MISSING,
                    f"Provajder {provider_code} je konfigurisan ali API ključ "
                    "nije dostupan u SecretStore-u.",
                )

            # 4. Build AI adapter. Factory only sees the api_key string
            #    (no SecretStore access) — per contract.
            try:
                adapter = build_text_generation_adapter(provider_code, api_key)
            except Exception as exc:
                # Same secret-in-log hardening as _resolve_ai_adapter
                # (ACS-GUI-009 BF-1): an SDK may inline the credential
                # into its exception message, so logger.exception's
                # full traceback/str(exc) would leak it. Log only the
                # safe provider_code and the exception class name.
                self._bootstrap.logger.error(
                    "adapter factory failed for %s (%s)",
                    provider_code,
                    type(exc).__name__,
                )
                return self._err(
                    _ERROR_KEY_MISSING,
                    f"Ne mogu instancirati adapter za {provider_code}.",
                )

            # 5. CreateCampaign: validate brief + persist campaign.
            try:
                campaign = CreateCampaign(
                    campaign_repo=self._campaign_repo,
                    unit_of_work=self._uow,
                ).execute(
                    brand_id,
                    snapshot_id,
                    brief_input.model_dump(mode="json"),
                )
            except (InvariantViolation, ValueError, TypeError) as exc:
                return self._err(_ERROR_VALIDATION, str(exc))
            except Exception as exc:
                self._bootstrap.logger.exception(
                    "CreateCampaign failed (provider=%s)", provider_code
                )
                return self._err(
                    _ERROR_INTERNAL,
                    f"Kreiranje kampanje nije uspjelo: {type(exc).__name__}.",
                )

            # 6. GenerateCampaignPlan: AI call + persist plan.
            try:
                plan = GenerateCampaignPlan(
                    campaign_repo=self._campaign_repo,
                    brand_repo=self._brand_repo,
                    fact_repo=self._fact_repo,
                    prompt_repo=self._prompt_repo,
                    ai_port=adapter,
                    unit_of_work=self._uow,
                ).execute(campaign.id)
            except (EntityNotFound, InvariantViolation) as exc:
                # Compensating action (ACS-GUI-006): ``CreateCampaign``
                # already committed the campaign row in its own
                # transaction. The plan generation failed, so the
                # campaign is now an orphan DRAFT (no plan, invisible
                # to the user via the GUI) — a duplicate target on the
                # next click. Best-effort delete; never mask the
                # original GENERATION_FAILED.
                self._compensate_orphan_campaign(campaign)
                return self._err(_ERROR_GENERATION, str(exc))
            except Exception as exc:
                # AI/network/SDK errors land here. Per PYWEBVIEW_SECURITY
                # §3, do NOT leak the SDK exception verbatim — map to a
                # generic message and log the detail server-side.
                self._bootstrap.logger.exception(
                    "GenerateCampaignPlan failed (provider=%s, err=%s)",
                    provider_code, type(exc).__name__,
                )
                # Same compensating action as the domain-error path
                # above — see ACS-GUI-006.
                self._compensate_orphan_campaign(campaign)
                return self._err(
                    _ERROR_GENERATION,
                    f"AI generisanje plana nije uspjelo ({type(exc).__name__}). "
                    "Provjerite API ključ, kvotu i mrežu.",
                )

            return asdict(
                CampaignPlanResultUiModel(
                    ok=True,
                    campaign_id=str(campaign.id),
                    # ACS-GUI-008: forward the plan_id so the next
                    # call (``generate_campaign_content``) does not
                    # have to look it up.
                    plan_id=str(plan.id),
                    plan_item_count=len(plan.items),
                    error_code=None,
                    error_message=None,
                )
            )
        except Exception:
            # Catch-all: the bridge must NEVER raise into JS. Log full
            # traceback server-side, return a safe internal error.
            self._bootstrap.logger.exception("unexpected bridge error")
            return self._err(
                _ERROR_INTERNAL,
                "Interna greška — pogledajte log aplikacije.",
            )

    @_with_call_resources
    def generate_campaign_content(self, raw_payload: dict) -> dict:
        """Submit a "Generiši sadržaj" job; return ``job_id`` IMMEDIATELY.

        ACS-F1-047: this method used to do the entire per-piece AI
        loop synchronously inside the single ``js_api`` call, freezing
        the UI button for ``~num_items * ~10s``. The work now runs on
        a background thread via ``JobManager.submit``; this method
        only does the SYNCHRONOUS boundary validation + plan/campaign
        lookup + plan-approval dance, then hands off.

        The sync phase still returns a ``_generate_err`` DTO on any
        validation / lookup / approval failure -- those are user
        errors and the user should see them immediately, not have to
        wait for a job to start and then fail. Anything that happens
        AFTER the job is accepted is reported via the terminal
        ``JobState`` (reachable through ``get_job_status(job_id)``).

        The closure runs on a ``ThreadPoolExecutor`` worker thread
        (NOT the pywebview worker thread that invoked this method).
        That means the closure MUST open its OWN ``_resource_scope``
        -- the ``@_with_call_resources`` decorator only covers the
        synchronous method body, and the bridge's per-call connection
        is closed before the closure even starts. Same problem as
        HOTFIX-002, now applied to a different thread boundary.

        Partial success and cooperative cancellation are preserved
        verbatim. The BF-3 per-pair lock is STILL required -- the
        ``JobManager`` executor runs ``max_workers=4`` parallel
        threads and gives no guarantee that two concurrent
        ``generate_campaign_content`` jobs for the SAME
        ``(campaign_id, plan_id)`` would land on the same worker;
        without the lock both closures would see an empty
        ``existing_pieces`` snapshot and BOTH would call
        ``GenerateSocialPost`` for the same items, producing
        duplicates.
        """
        # -- 1. Boundary validation (Pydantic-style; we do not trust JS).
        if not isinstance(raw_payload, dict):
            return self._generate_err(
                _ERROR_VALIDATION, "Pošiljka iz GUI-ja nije objekat."
            )
        campaign_id_raw = raw_payload.get("campaign_id")
        if not isinstance(campaign_id_raw, str) or not campaign_id_raw.strip():
            return self._generate_err(
                _ERROR_VALIDATION, "campaign_id je obavezan (string)."
            )
        # ACS-GUI-008 (review feedback): the JS caller is REQUIRED to
        # pass ``plan_id`` too — the bridge got the plan_id from the
        # earlier ``create_campaign_and_generate_plan`` response and
        # MUST forward it here, instead of having the bridge do raw
        # SQL to look it up. This is the boundary that prevents the
        # bridge from having to know about the campaign_plans SQL
        # schema. ``plan_id`` is NOT a secret.
        plan_id_raw = raw_payload.get("plan_id")
        if not isinstance(plan_id_raw, str) or not plan_id_raw.strip():
            return self._generate_err(
                _ERROR_VALIDATION,
                "plan_id je obavezan (string). "
                "Ponovo pokreni 'Sačuvaj i napravi plan'.",
            )
        campaign_id = CampaignId(campaign_id_raw.strip())
        plan_id = CampaignPlanId(plan_id_raw.strip())

        # -- 2. Sync phase: campaign / brief / plan / targets lookup +
        #    approve-if-DRAFT + BF-4 SUPERSEDED rejection. All of these
        #    are fast DB reads/writes and the user wants a synchronous
        #    error if the plan is wrong -- the JS layer would have to
        #    poll a job just to discover a SUPERSEDED plan, which is
        #    a strictly worse UX. Only the AI loop is worth backgrounding.
        try:
            campaign = self._campaign_repo.get_campaign(campaign_id)
            if campaign is None:
                return self._generate_err(
                    _ERROR_VALIDATION,
                    f"Kampanja {campaign_id} ne postoji.",
                )
            brief = self._campaign_repo.get_brief(campaign.brief_id)
            if brief is None:
                return self._generate_err(
                    _ERROR_VALIDATION,
                    f"Brief {campaign.brief_id} ne postoji.",
                )
            plan = self._campaign_repo.get_plan(plan_id)
            if plan is None:
                return self._generate_err(
                    _ERROR_VALIDATION,
                    f"Plan {plan_id} ne postoji. "
                    "Ponovo pokreni 'Sačuvaj i napravi plan'.",
                )
            if plan.campaign_id != campaign_id:
                return self._generate_err(
                    _ERROR_VALIDATION,
                    f"Plan {plan_id} ne pripada kampanji {campaign_id}.",
                )
            targets = _targets_from_brief(brief)
        except (EntityNotFound, InvariantViolation, ValueError, TypeError) as exc:
            return self._generate_err(_ERROR_VALIDATION, str(exc))
        except Exception as exc:
            self._bootstrap.logger.exception(
                "generate_campaign_content: plan lookup failed"
                " (campaign=%s, err=%s)",
                campaign_id, type(exc).__name__,
            )
            return self._generate_err(
                _ERROR_INTERNAL,
                f"Ne mogu učitati plan: {type(exc).__name__}.",
            )

        if plan.status is CampaignPlanStatus.DRAFT:
            # BF-3 (F1-047): the per-pair lock is also acquired here
            # in the SYNC phase so two concurrent submitters cannot
            # both read plan.status=DRAFT and both call
            # ``ApproveCampaignPlan.execute()`` -- the second one
            # would either no-op the approve (domain-level) or fail
            # with an ``IntegrityError`` (FK cascade on items). The
            # closure re-acquires the same lock for the per-piece
            # loop, but the sync phase needs its own acquisition
            # window so the approve + status read are atomic with
            # respect to other submitters.
            with self._lock_for(str(campaign_id), str(plan_id)):
                # Re-load the plan under the lock -- the previous
                # read may have been stale.
                plan = self._campaign_repo.get_plan(plan_id)
                if plan is None:
                    return self._generate_err(
                        _ERROR_VALIDATION,
                        f"Plan {plan_id} ne postoji. "
                        "Ponovo pokreni 'Sačuvaj i napravi plan'.",
                    )
                if plan.status is CampaignPlanStatus.DRAFT:
                    try:
                        approved = ApproveCampaignPlan(
                            campaign_repo=self._campaign_repo,
                            unit_of_work=self._uow,
                        ).execute(plan_id)
                    except (EntityNotFound, InvariantViolation) as exc:
                        return self._generate_err(_ERROR_VALIDATION, str(exc))
                    except Exception as exc:
                        self._bootstrap.logger.exception(
                            "generate_campaign_content: ApproveCampaignPlan failed"
                            " (campaign=%s, err=%s)",
                            campaign_id, type(exc).__name__,
                        )
                        return self._generate_err(
                            _ERROR_GENERATION,
                            f"Odobravanje plana nije uspjelo: {type(exc).__name__}.",
                        )
                else:
                    # Plan was approved between the outer read and
                    # this re-read; that's fine, reuse it.
                    approved = plan
        else:
            approved = plan

        # BF-4: explicit rejection of non-APPROVED plans.
        if approved.status is not CampaignPlanStatus.APPROVED:
            return self._generate_err(
                _ERROR_VALIDATION,
                f"Plan {plan_id} je u stanju {approved.status.value}, "
                "očekivano APPROVED. Napravi novi plan.",
            )

        # -- 3. Submit the job. The closure is given a snapshot of the
        #    validated entities (campaign.id, approved.items, targets,
        #    plus a frozen copy of brief/campaign if needed later) and
        #    runs on the JobManager's executor. We return immediately
        #    with the new ``job_id`` -- this is the only thing the JS
        #    caller learns from the click; the per-piece outcome is
        #    polled via ``get_job_status``.
        plan_items_snapshot = tuple(approved.items)
        targets_snapshot: tuple = tuple(targets)
        try:
            job_id = self._bootstrap.job_manager.submit(
                "generate_campaign_content",
                self._build_generate_content_closure(
                    campaign_id=campaign_id,
                    plan_id=plan_id,
                    plan_items=plan_items_snapshot,
                    targets=targets_snapshot,
                ),
            )
        except RuntimeError as exc:
            # JobManager shut down (or about to be) -- map to a sync
            # VALIDATION_ERROR so the JS shows a useful toast instead
            # of a stuck "Generiram…" label.
            self._bootstrap.logger.error(
                "generate_campaign_content: JobManager.submit failed: %s",
                exc,
            )
            return self._generate_err(
                _ERROR_INTERNAL,
                "Sistem je zauzet. Pokušaj ponovo za par sekundi.",
            )

        return asdict(
            GenerateContentResultUiModel(
                ok=True,
                campaign_id=str(campaign_id),
                job_id=job_id,
                error_code=None,
                error_message=None,
            )
        )

    def _build_generate_content_closure(
        self,
        campaign_id: CampaignId,
        plan_id: CampaignPlanId,
        plan_items: tuple,
        targets: tuple,
    ):
        """Return a closure that runs the per-piece AI loop on the
        ``JobManager`` executor thread.

        Closure contract: it acquires the per-``(campaign_id, plan_id)``
        lock (BF-3 carried over from the sync API -- without it, two
        concurrent job submissions for the same pair would both see
        an empty ``existing_pieces`` snapshot and BOTH generate for
        the same items), opens its own ``_resource_scope``
        (HOTFIX-002 pattern, because the bridge's per-call connection
        is closed before the worker thread runs), checks the
        ``CancellationToken`` before every piece, and publishes
        progress via ``job_manager.update_progress`` after every
        piece. On a natural exit the final ``generated_count`` /
        ``failed_count`` / ``content_piece_ids`` are recorded on the
        terminal ``JobState``; on ``CancellationError`` JobManager
        transitions to ``CANCELLED`` and we patch the partial outcome
        via the same private hook (``_patch_terminal_state``).
        """
        job_manager = self._bootstrap.job_manager
        total = len(plan_items)
        # Capture by-value so the closure cannot be tricked by a
        # late-bound ``self`` rebind (defensive; ``self`` is already
        # closed over in the enclosing method).
        lock_for = self._lock_for

        def _run(token) -> None:  # type: ignore[no-untyped-def]
            # BF-3 lock is held across the full per-piece loop so two
            # concurrent workers for the same (campaign, plan) cannot
            # race. Different pairs do not block each other.
            with lock_for(str(campaign_id), str(plan_id)):
                with self._resource_scope():
                    return self._run_generate_content_locked(
                        token=token,
                        campaign_id=campaign_id,
                        plan_id=plan_id,
                        plan_items=plan_items,
                        targets=targets,
                        total=total,
                        job_manager=job_manager,
                    )

        return _run

    def _run_generate_content_locked(
        self,
        token,
        campaign_id: CampaignId,
        plan_id: CampaignPlanId,
        plan_items: tuple,
        targets: tuple,
        total: int,
        job_manager,
    ) -> None:
        """Per-piece loop running on the ``JobManager`` worker thread.

        The function name mirrors ``_generate_campaign_content_locked``
        from ACS-F1-046 -- it is the "real work" half of the
        previously-synchronous method. It always opens its own
        ``_resource_scope`` via the enclosing closure; it never
        touches the bridge's per-call connection (which is closed by
        the time we get here).

        Raises ``CancellationError`` from ``token.raise_if_cancelled()``
        on cooperative cancel; that bubbles up to ``JobManager._run``
        which transitions the job to ``CANCELLED``. The per-piece
        counters at the point of cancellation are NOT lost -- we
        patch them onto the ``JobState`` via a private hook
        (``_patch_terminal_state``) that the JobManager calls from
        inside its own lock for us. That is a one-off collaboration
        we negotiated here for the F1-047 scope; the public API stays
        ``update_progress``-only.
        """
        # Provider resolution.
        try:
            provider_code, api_key = self._resolve_provider()
        except Exception as exc:
            self._bootstrap.logger.exception(
                "generate_campaign_content job: provider resolution failed"
            )
            raise RuntimeError(
                f"Provider read failed: {type(exc).__name__}."
            ) from exc
        if provider_code is None:
            raise RuntimeError("No AI provider configured.")
        if not api_key:
            raise RuntimeError(
                f"Provider {provider_code} is configured but the API key "
                "is not available in the SecretStore."
            )

        try:
            adapter = build_text_generation_adapter(provider_code, api_key)
        except Exception as exc:
            # Same secret-in-log hardening as _resolve_ai_adapter
            # (ACS-GUI-009 BF-1): an SDK may inline the credential
            # into its exception message, so logger.exception's full
            # traceback/str(exc) would leak it. Log only the safe
            # provider_code and the exception class name.
            self._bootstrap.logger.error(
                "generate_campaign_content job: adapter factory failed"
                " for %s (%s)",
                provider_code,
                type(exc).__name__,
            )
            raise RuntimeError(
                f"Could not instantiate adapter for {provider_code}: "
                f"{type(exc).__name__}."
            ) from exc

        generator = GenerateSocialPost(
            campaign_repo=self._campaign_repo,
            brand_repo=self._brand_repo,
            fact_repo=self._fact_repo,
            content_repo=self._content_repo,
            revision_repo=self._revision_repo,
            prompt_repo=self._prompt_repo,
            ai_port=adapter,
            unit_of_work=self._uow,
        )

        existing_pieces = self._content_repo.list_campaign_content(
            campaign_id
        )
        existing_item_ids = {
            str(p.campaign_item_id) for p in existing_pieces
        }

        # Mutable per-piece accumulators we want to attach to the
        # final JobState (whether SUCCEEDED, FAILED, or CANCELLED).
        # We update progress (current+total) after every item so the
        # live polling UX is correct.
        generated_ids: list[str] = []
        failed_count = 0
        first_error: str | None = None
        # ``token.job_id`` is the deterministic channel for the
        # worker to identify its own job. ``JobManager.submit``
        # populates it before the future is registered, so by the
        # time the worker thread runs this closure the value is
        # already set -- no race, no ``_jobs`` lookup, no ambiguity
        # even when sibling jobs (of any type) are concurrently
        # RUNNING on the shared executor.
        jid = token.job_id
        # ``try/finally`` around the per-piece loop so that
        # ``_patch_terminal_state`` runs EXACTLY ONCE on BOTH
        # outcomes:
        #   - natural end of the loop (everything attempted) ->
        #     JobManager -> SUCCEEDED
        #   - ``CancellationError`` raised by ``raise_if_cancelled``
        #     on any iteration -> JobManager -> CANCELLED
        # Without the ``finally`` branch the CANCELLED path was
        # leaving the terminal ``JobState`` on default
        # ``generated_count=0, content_piece_ids=()`` even though
        # some pieces had already been written (the per-piece
        # accumulators were dropped on the floor). ACS-F1-047
        # (Codex BF-CODEX-2).
        try:
            for index, item in enumerate(plan_items):
                token.raise_if_cancelled()
                if jid:
                    # Live progress (1-based "current"). "Phase" is the
                    # human-readable message; we keep it short so the
                    # JS button label is not too wide.
                    job_manager.update_progress(
                        jid,
                        current=index,  # not yet "tried this one"
                        total=total,
                        phase="GENERATE",
                        message="",
                    )
                if str(item.id) in existing_item_ids:
                    continue
                target = _target_for_item(index, list(targets))
                if target is None:
                    failed_count += 1
                    if first_error is None:
                        first_error = (
                            "Nema definisanih targeta u briefu — "
                            "objave ne mogu biti generisane."
                        )
                    continue
                try:
                    piece = generator.execute(
                        campaign_id, plan_id, item.id, target
                    )
                    generated_ids.append(str(piece.id))
                except CancellationError:
                    # Re-raise so JobManager transitions to CANCELLED
                    # (not FAILED). The per-piece try/except below must
                    # NOT swallow this -- a cancellation is a control
                    # signal, not a generation failure.
                    raise
                except Exception as exc:
                    failed_count += 1
                    if first_error is None:
                        first_error = (
                            f"AI poziv za stavku {item.id} nije uspio: "
                            f"{type(exc).__name__}."
                        )
                    self._bootstrap.logger.error(
                        "GenerateSocialPost failed for item %s (err=%s)",
                        item.id, type(exc).__name__,
                    )
                finally:
                    # Re-check the token AFTER the per-piece work. A
                    # ``cancel_job`` call that landed during
                    # ``generator.execute`` would otherwise be invisible
                    # to us until the START of the next iteration -- by
                    # which time the work may already be done. Raising
                    # here propagates out of the for-loop, into
                    # ``except CancellationError: raise`` above, and
                    # then up to ``JobManager._run`` which transitions
                    # the job to ``CANCELLED``.
                    token.raise_if_cancelled()
                    if jid:
                        job_manager.update_progress(
                            jid,
                            current=index + 1,  # "tried this one"
                            total=total,
                            phase="GENERATE",
                            message="",
                        )
        finally:
            # On both natural exit AND cancellation, persist the
            # accumulators (``generated_count`` / ``failed_count`` /
            # ``content_piece_ids``) onto the JobState. This is the
            # ONLY way the JS side learns the per-piece outcome on
            # a CANCELLED job -- without it, the terminal DTO was
            # always zero even when some pieces had been written.
            if jid:
                _patch_terminal_state(
                    job_manager, jid,
                    generated_count=len(generated_ids),
                    failed_count=failed_count,
                    content_piece_ids=tuple(generated_ids),
                    message=first_error or "",
                )

    @_with_call_resources
    def get_job_status(self, raw_payload: dict) -> dict:
        """Return the current ``JobState`` of a background job as a JSON-safe dict.

        JS polls this while ``generate_campaign_content`` is in flight
        to render a progress counter on the same button. On unknown
        ``job_id`` we return ``VALIDATION_ERROR`` (the JS does not
        need to handle ``JobError`` -- that would cross an exception
        type into the JS-facing API contract).
        """
        if not isinstance(raw_payload, dict):
            return self._job_status_err(
                _ERROR_VALIDATION, "Pošiljka iz GUI-ja nije objekat."
            )
        job_id_raw = raw_payload.get("job_id")
        if not isinstance(job_id_raw, str) or not job_id_raw.strip():
            return self._job_status_err(
                _ERROR_VALIDATION, "job_id je obavezan (string)."
            )
        job_id = job_id_raw.strip()
        try:
            state = self._bootstrap.job_manager.get_state(job_id)
        except JobError:
            return self._job_status_err(
                _ERROR_VALIDATION, f"Job {job_id} ne postoji."
            )
        # ``asdict`` is fine: ``JobState`` is JSON-safe by construction
        # (only ``str | int | tuple[str, ...] | datetime | None`` fields).
        # ``datetime`` instances are NOT JSON-serialisable, so we
        # serialise them as ISO strings.
        snapshot = asdict(state)
        for key in ("started_at", "finished_at"):
            value = snapshot.get(key)
            if value is not None and hasattr(value, "isoformat"):
                snapshot[key] = value.isoformat()
        snapshot["status"] = state.status.value
        return snapshot

    @_with_call_resources
    def cancel_job(self, raw_payload: dict) -> dict:
        """Request cooperative cancellation of a background job.

        Unknown ``job_id`` -> ``VALIDATION_ERROR`` (same no-leak rule
        as ``get_job_status``). Already-terminal jobs are a no-op on
        the manager side; we still return ``ok=True`` because the
        observable state is already what the user wanted.
        """
        if not isinstance(raw_payload, dict):
            return self._job_status_err(
                _ERROR_VALIDATION, "Pošiljka iz GUI-ja nije objekat."
            )
        job_id_raw = raw_payload.get("job_id")
        if not isinstance(job_id_raw, str) or not job_id_raw.strip():
            return self._job_status_err(
                _ERROR_VALIDATION, "job_id je obavezan (string)."
            )
        job_id = job_id_raw.strip()
        try:
            self._bootstrap.job_manager.cancel(job_id)
        except JobError:
            return self._job_status_err(
                _ERROR_VALIDATION, f"Job {job_id} ne postoji."
            )
        return {
            "ok": True,
            "job_id": job_id,
            "error_code": None,
            "error_message": None,
        }

    @staticmethod
    def _job_status_err(code: str, message: str) -> dict:
        """Error shape for ``get_job_status`` / ``cancel_job``.

        Same minimal shape as ``_generate_err`` (5 fields, no
        ``generated_count``/``failed_count``/``content_piece_ids``
        because these are job-introspection methods, not
        job-submission methods).
        """
        return {
            "ok": False,
            "job_id": None,
            "error_code": code,
            "error_message": message,
        }

    @_with_call_resources
    def export_campaign_package(self, raw_payload: dict) -> dict:
        """Build and ZIP-export an already-generated campaign (ACS-GUI-009).

        First GUI→backend path that runs the real ``GenerateVisualSystem`` /
        ``PlanPostLayout`` / ``ExportCampaign`` pipeline. ``ExportCampaign``
        is a pure orchestrator (no AI) but the two upstream steps DO call the
        AI port, so provider resolution is reused via ``_resolve_ai_adapter``
        (single source of truth for priority/fallback).

        Per PYWEBVIEW_SECURITY §3, this method NEVER raises into JS — every
        error path returns a result dict with ``ok=False`` and a stable
        ``error_code``. The result dict carries a filesystem ``zip_path``
        (deliberately returned to the user; it is a path, not a secret), but
        never an API key, token, SecretStore content, or traceback text.

        Steps:
        1. boundary-validate ``campaign_id`` + ``plan_id`` (the JS caller
           forwards the plan_id from the earlier
           ``create_campaign_and_generate_plan`` response, same as
           ``generate_campaign_content`` — no raw-SQL "current plan" lookup);
        2. load campaign + plan, require the plan to be APPROVED and to
           belong to THIS campaign (BF-4 equivalent: a SUPERSEDED or any
           other non-APPROVED plan is rejected up-front, 0 AI calls);
        3. idempotently ensure a ``CampaignVisualSystem`` exists via the
           in-process ``_visual_system_by_plan`` map (a second click does
           NOT create a second visual system);
        4. generate a per-post ``LayoutSpec`` for any piece that does not yet
           have one (partial failure allowed — one AI error must not abort
           the loop; ``ExportCampaign`` skips pieces without a layout);
        5. run ``ExportCampaign`` with its CURRENT 7-parameter constructor
           and write the ZIP to ``data_dir/exports/<campaign_id>.zip``.
        """
        # -- 1. Boundary validation (we do not trust JS types/values).
        if not isinstance(raw_payload, dict):
            return self._export_err(_ERROR_VALIDATION, "Pošiljka nije objekat.")
        campaign_id_raw = raw_payload.get("campaign_id")
        if not isinstance(campaign_id_raw, str) or not campaign_id_raw.strip():
            return self._export_err(
                _ERROR_VALIDATION, "campaign_id je obavezan (string)."
            )
        plan_id_raw = raw_payload.get("plan_id")
        if not isinstance(plan_id_raw, str) or not plan_id_raw.strip():
            return self._export_err(
                _ERROR_VALIDATION,
                "plan_id je obavezan (string). "
                "Ponovo pokreni 'Sačuvaj i napravi plan'.",
            )
        campaign_id = CampaignId(campaign_id_raw.strip())
        plan_id = CampaignPlanId(plan_id_raw.strip())

        try:
            # -- 2. Load campaign + plan; require APPROVED + ownership.
            campaign = self._campaign_repo.get_campaign(campaign_id)
            if campaign is None:
                return self._export_err(
                    _ERROR_VALIDATION,
                    f"Kampanja {campaign_id} ne postoji.",
                )
            plan = self._campaign_repo.get_plan(plan_id)
            if plan is None:
                return self._export_err(
                    _ERROR_VALIDATION,
                    f"Plan {plan_id} ne postoji. "
                    "Ponovo pokreni 'Sačuvaj i napravi plan'.",
                )
            if plan.campaign_id != campaign_id:
                return self._export_err(
                    _ERROR_VALIDATION,
                    f"Plan {plan_id} ne pripada kampanji {campaign_id}.",
                )
            if plan.status is not CampaignPlanStatus.APPROVED:
                return self._export_err(
                    _ERROR_VALIDATION,
                    f"Plan {plan_id} je u stanju {plan.status.value}, "
                    "očekivano APPROVED. Sadržaj još nije generisan.",
                )

            # -- 3-5. The whole export sequence (get/create visual system ->
            #    layout loop -> ExportCampaign.execute) runs under the SAME
            #    per-(campaign_id, plan_id) lock as generate_campaign_content.
            #    BF-2 (Codex): without this, two worker threads writing the
            #    same ZIP path concurrently interleave ZipExportWriter's
            #    mode="w" write and corrupt the archive. The lock also makes
            #    the visual-system idempotency atomic (the read-check-create
            #    sequence in ``_get_cached_visual_system`` is no longer a
            #    TOCTOU race, so a concurrent double-click cannot create two
            #    visual systems for the same plan).
            with self._lock_for(str(campaign_id), str(plan_id)):
                adapter = None
                visual_system = self._get_cached_visual_system(
                    campaign_id, plan_id
                )
                if visual_system is None:
                    adapter, adapter_err = self._resolve_ai_adapter()
                    if adapter_err is not None:
                        return adapter_err
                    try:
                        visual_system, _ = GenerateVisualSystem(
                            campaign_repo=self._campaign_repo,
                            brand_repo=self._brand_repo,
                            visual_repo=self._visual_repo,
                            prompt_repo=self._prompt_repo,
                            ai_port=adapter,
                            unit_of_work=self._uow,
                        ).execute(plan_id)
                    except Exception:
                        self._bootstrap.logger.exception(
                            "GenerateVisualSystem failed (campaign=%s)",
                            campaign_id,
                        )
                        return self._export_err(
                            _ERROR_GENERATION,
                            "AI generisanje vizuelnog sistema nije uspjelo.",
                        )
                    self._record_campaign_visual_system(
                        plan_id, visual_system.id
                    )

                # -- 4. Per-post layout specs (only for pieces that still
                #    need one). Partial failure allowed: one AI/layout error
                #    must not abort the whole export — ``ExportCampaign``
                #    already skips pieces that have no LayoutSpec.
                for piece in self._content_repo.list_campaign_content(
                    campaign_id
                ):
                    if (
                        self._visual_repo.get_layout_spec_by_content_piece(
                            piece.id
                        )
                        is not None
                    ):
                        continue
                    if piece.payload is None:
                        # No payload -> no layout can be generated;
                        # ExportCampaign will skip it as well.
                        continue
                    if adapter is None:
                        adapter, adapter_err = self._resolve_ai_adapter()
                        if adapter_err is not None:
                            return adapter_err
                    try:
                        PlanPostLayout(
                            campaign_repo=self._campaign_repo,
                            content_repo=self._content_repo,
                            visual_repo=self._visual_repo,
                            prompt_repo=self._prompt_repo,
                            ai_port=adapter,
                            unit_of_work=self._uow,
                        ).execute(piece.id, visual_system.id, plan_id)
                    except Exception:
                        self._bootstrap.logger.exception(
                            "PlanPostLayout failed (piece=%s)", piece.id
                        )

                # -- 5. ExportCampaign (current 7-parameter constructor).
                exports_dir = self._user_data_dir() / "exports"
                exports_dir.mkdir(parents=True, exist_ok=True)
                output_zip_path = exports_dir / f"{campaign_id}.zip"
                result = ExportCampaign(
                    campaign_repo=self._campaign_repo,
                    content_repo=self._content_repo,
                    visual_repo=self._visual_repo,
                    revision_repo=self._revision_repo,
                    renderer=PillowRenderer(),
                    export_writer=ZipExportWriter(),
                    performance_repo=self._performance_repo,
                ).execute(
                    campaign_id,
                    plan_id,
                    visual_system.id,
                    str(output_zip_path),
                )

                return asdict(
                    ExportCampaignResultUiModel(
                        ok=True,
                        campaign_id=str(campaign_id),
                        zip_path=str(output_zip_path),
                        exported_count=len(result.exported_content_piece_ids),
                        skipped_count=len(result.skipped_content_piece_ids),
                        error_code=None,
                        error_message=None,
                    )
                )
        except Exception:
            self._bootstrap.logger.exception("unexpected export bridge error")
            return self._export_err(
                _ERROR_INTERNAL,
                "Izvoz nije uspio — pogledajte log aplikacije.",
            )

    @_with_call_resources
    def configure_provider(self, raw_payload: dict) -> dict:
        """Persist a provider API key into the real SecretStore (ACS-GUI-007).

        This is the FIRST js_api method that takes a secret string FROM
        JS (the campaign flow only USES secrets, never accepts them from
        the user). Per ``docs/PYWEBVIEW_SECURITY.md`` §3:

        - boundary validation BEFORE the use-case runs (Pydantic
          pattern: we do NOT trust JS types/values — provider_code and
          api_key are explicit str checks);
        - the return ``dict`` is JSON-serializable and NEVER contains
          the api_key (input or echoed/masked);
        - the api_key is NEVER logged — only ``provider_code`` and
          exception class names appear in log lines.

        Like ``create_campaign_and_generate_plan``, this method NEVER
        raises into JS — every error path returns a result dict with
        ``ok=False`` and a stable ``error_code``.
        """
        # 1. Boundary validation. Any failure here is a
        #    ``VALIDATION_ERROR`` and we have NOT touched the secret
        #    store yet.
        if not isinstance(raw_payload, dict):
            return self._provider_err(
                _ERROR_VALIDATION, "Pošiljka nije objekat."
            )

        provider_code_raw = raw_payload.get("provider_code")
        api_key_raw = raw_payload.get("api_key")
        if not isinstance(provider_code_raw, str) or not provider_code_raw.strip():
            return self._provider_err(
                _ERROR_VALIDATION, "provider_code je obavezan (string)."
            )
        if not isinstance(api_key_raw, str) or not api_key_raw.strip():
            return self._provider_err(
                _ERROR_VALIDATION, "api_key je obavezan (string)."
            )

        provider_code = provider_code_raw.strip().upper()

        # 2. Call the existing ConfigureProvider use-case. This is the
        #    ONLY place in the bridge that actually writes to the
        #    SecretStore (real OS keyring in production thanks to the
        #    ``settings=AppSettings(environment="production")`` default
        #    in ``__init__``).
        try:
            ConfigureProvider(
                provider_registry=self._bootstrap.provider_registry,
                provider_config_repo=self._provider_config_repo,
                secret_store=self._bootstrap.secret_store,
            ).execute(provider_code, api_key_raw.strip())
        except (InvariantViolation, RegistryError) as exc:
            # ``RegistryError``: unknown provider_code (registry does
            # not know the code).
            # ``InvariantViolation``: provider exists but does not
            # require an API key (e.g. a future local-only provider).
            # Both map to VALIDATION_ERROR — the input was wrong, not
            # the backend. The provider_code is NOT a secret and is
            # safe to surface; the api_key never appears in the
            # message.
            return self._provider_err(_ERROR_VALIDATION, str(exc))
        except Exception as exc:
            # ``SecretStoreError`` from the keyring backend (or any
            # other backend error) lands here. We deliberately do NOT
            # surface ``str(exc)`` — the message could theoretically
            # contain backend-specific details.
            #
            # ACS-GUI-007 BF-3: we use ``logger.error`` (not
            # ``logger.exception``) so the traceback + ``str(exc)``
            # are NOT logged. ``logger.exception`` would log the full
            # exception text, which could contain the api_key if any
            # future SecretStore adapter / test backend / downstream
            # change accidentally inlined the value into the
            # exception message. The docstring promise "NEVER logged"
            # holds structurally: ``logger.error("format", *args)``
            # writes ONLY the formatted message + the (safe) args —
            # never the exception object, never traceback. Same shape
            # as the ``create_campaign_and_generate_plan``
            # GENERATION_FAILED branch.
            self._bootstrap.logger.error(
                "configure_provider failed for provider %s (err=%s)",
                provider_code,
                type(exc).__name__,
            )
            return self._provider_err(
                _ERROR_INTERNAL,
                "Konfiguracija provajdera nije uspjela (interna greška).",
            )

        return asdict(
            ProviderConfigResultUiModel(
                ok=True,
                provider_code=provider_code,
                error_code=None,
                error_message=None,
            )
        )

    @_with_call_resources
    def list_campaigns(self, raw_payload: dict | None = None) -> dict:
        """Read every campaign for the Kampanje list (ACS-F1-046).

        The FIRST read js_api method on the bridge (the other three are
        write-only). Returns every campaign, newest first, as
        ``CampaignSummaryUiModel`` dicts. No pagination (campaign count is
        small today). Never raises into JS and never leaks secret/path/
        exception text (PYWEBVIEW_SECURITY §3). ``raw_payload`` is accepted
        only for call-shape consistency with the other methods (app.js
        passes ``{}``); its contents are ignored.
        """
        del raw_payload
        try:
            campaigns = self._campaign_repo.list_campaigns()
            summaries: list[CampaignSummaryUiModel] = []
            for campaign in campaigns:
                brief = self._campaign_repo.get_brief(campaign.brief_id)
                name = brief.offer if brief is not None else str(campaign.id)
                plan = self._campaign_repo.get_latest_plan_for_campaign(
                    campaign.id
                )
                plan_item_count = len(plan.items) if plan is not None else 0
                brand = self._brand_repo.get_brand(campaign.brand_id)
                brand_name = brand.name if brand is not None else ""
                summaries.append(
                    CampaignSummaryUiModel(
                        id=str(campaign.id),
                        name=name,
                        status=campaign.status.value,
                        plan_item_count=plan_item_count,
                        brand=brand_name,
                        created_at=campaign.created_at.isoformat(),
                    )
                )
            return asdict(
                ListCampaignsResultUiModel(
                    ok=True,
                    campaigns=tuple(summaries),
                    error_code=None,
                    error_message=None,
                )
            )
        except Exception:
            self._bootstrap.logger.exception("list_campaigns failed")
            return self._list_err(
                _ERROR_INTERNAL,
                "Učitavanje kampanja nije uspjelo (interna greška).",
            )

    @_with_call_resources
    def get_brand_overview(self, raw_payload: dict | None = None) -> dict:
        """Read the single demo brand for the Brend screen (ACS-F1-049).

        Second read js_api method (after ``list_campaigns``). Resolves the
        demo brand/snapshot via ``_ensure_brand()`` (idempotent seed), then
        returns the brand name, primary audience, voice (formality + tone)
        and the usable approved facts. ``description`` is NOT returned
        (``BrandSnapshot`` has no brand-description field — the SSR fixture's
        description stays as-is). Never raises into JS; never leaks secret/
        path/exception text.
        """
        del raw_payload
        try:
            brand_id, snapshot_id = self._ensure_brand()
            brand = self._brand_repo.get_brand(brand_id)
            snapshot = self._brand_repo.get_snapshot(snapshot_id)
            if brand is None or snapshot is None:
                return self._brand_err(
                    _ERROR_INTERNAL,
                    "Brend nije pronađen u bazi (interna greška).",
                )

            primary_audience = ""
            if snapshot.audiences:
                audience = snapshot.audiences[0]
                primary_audience = (
                    f"{audience.name} — {audience.description}"
                    if audience.description
                    else audience.name
                )

            voice = (snapshot.voice.formality, *snapshot.voice.tone)

            facts = tuple(
                BrandFactUiModel(code=f.logical_fact_id, text=f.content)
                for f in self._fact_repo.list_snapshot_facts(snapshot_id)
                if is_fact_usable(f)
            )

            return asdict(
                BrandOverviewResultUiModel(
                    ok=True,
                    brand_name=brand.name,
                    primary_audience=primary_audience,
                    voice=voice,
                    facts=facts,
                    error_code=None,
                    error_message=None,
                )
            )
        except Exception:
            self._bootstrap.logger.exception("get_brand_overview failed")
            return self._brand_err(
                _ERROR_INTERNAL,
                "Učitavanje brenda nije uspjelo (interna greška).",
            )

    @_with_call_resources
    def get_dashboard_overview(self, raw_payload: dict | None = None) -> dict:
        """Read the Početna dashboard KPIs + recent campaigns (ACS-F1-051).

        Third read js_api method. Aggregates the 4 KPI counters across ALL
        campaigns (active = status != EXPORTED; posts planned/drafts/approved
        count ``ContentPiece`` rows by ``ContentStatus``) and returns the most
        recent campaigns (newest first, capped at 5). ``activity`` is NOT
        returned (no domain activity-log concept — that SSR panel stays
        fixture-only). Empty DB -> ``ok=True`` with all counters 0. Never
        raises into JS; never leaks secret/path/exception text.
        """
        del raw_payload
        try:
            campaigns = self._campaign_repo.list_campaigns()
            active = 0
            planned = 0
            drafts = 0
            approved = 0
            recent: list[DashboardRecentCampaignUiModel] = []
            for campaign in campaigns:
                # "Active" = any campaign not yet EXPORTED (the single
                # terminal state in CampaignStatus).
                if campaign.status is not CampaignStatus.EXPORTED:
                    active += 1
                for piece in self._content_repo.list_campaign_content(
                    campaign.id
                ):
                    if piece.status is ContentStatus.PLANNED:
                        planned += 1
                    elif piece.status is ContentStatus.DRAFT:
                        drafts += 1
                    elif piece.status is ContentStatus.APPROVED:
                        approved += 1
                brief = self._campaign_repo.get_brief(campaign.brief_id)
                name = brief.offer if brief is not None else str(campaign.id)
                recent.append(
                    DashboardRecentCampaignUiModel(
                        name=name,
                        status=campaign.status.value,
                    )
                )

            return asdict(
                DashboardOverviewResultUiModel(
                    ok=True,
                    active_campaigns=active,
                    posts_planned=planned,
                    drafts=drafts,
                    approved=approved,
                    recent_campaigns=tuple(recent[:5]),
                    error_code=None,
                    error_message=None,
                )
            )
        except Exception:
            self._bootstrap.logger.exception("get_dashboard_overview failed")
            return self._dashboard_err(
                _ERROR_INTERNAL,
                "Učitavanje pregleda nije uspjelo (interna greška).",
            )

    @_with_call_resources
    def get_campaign_performance(self, raw_payload: dict) -> dict:
        """Read the Campaign Performance summary for one campaign (ACS-F1-053).

        Fourth read js_api method. Calls the G6
        ``build_campaign_performance_summary`` for the given campaign and maps
        its ``DerivedMetricSet``/``CanonicalMetricSet`` onto presentation DTOs
        (derived + a raw subset + distribution count). Unknown campaign ->
        ``VALIDATION_ERROR``; existing campaign with no performance data ->
        ``ok=True`` with all metrics ``None`` and count 0. Never raises into
        JS; never leaks secret/path/exception text.
        """
        if not isinstance(raw_payload, dict):
            return self._performance_err(
                _ERROR_VALIDATION, "Pošiljka iz GUI-ja nije objekat."
            )
        campaign_id_raw = raw_payload.get("campaign_id")
        if not isinstance(campaign_id_raw, str) or not campaign_id_raw.strip():
            return self._performance_err(
                _ERROR_VALIDATION, "campaign_id je obavezan (string)."
            )
        campaign_id = CampaignId(campaign_id_raw.strip())
        try:
            if self._campaign_repo.get_campaign(campaign_id) is None:
                return self._performance_err(
                    _ERROR_VALIDATION, f"Kampanja {campaign_id} ne postoji."
                )
            summary = build_campaign_performance_summary(
                self._performance_repo, campaign_id
            )
            return asdict(
                CampaignPerformanceResultUiModel(
                    ok=True,
                    derived=DerivedMetricSetUiModel(
                        ctr=summary.derived.ctr,
                        cpc=summary.derived.cpc,
                        cpm=summary.derived.cpm,
                        cpa=summary.derived.cpa,
                        roas=summary.derived.roas,
                        conversion_rate=summary.derived.conversion_rate,
                    ),
                    raw=RawMetricSetUiModel(
                        impressions=summary.raw.impressions,
                        clicks=summary.raw.clicks,
                        spend=summary.raw.spend,
                    ),
                    distribution_instance_count=summary.distribution_instance_count,
                    error_code=None,
                    error_message=None,
                )
            )
        except Exception:
            self._bootstrap.logger.exception("get_campaign_performance failed")
            return self._performance_err(
                _ERROR_INTERNAL,
                "Učitavanje učinka nije uspjelo (interna greška).",
            )

    @_with_call_resources
    def get_campaign_content_performance(self, raw_payload: dict) -> dict:
        """Read per-content-piece performance rows (ACS-F1-054).

        Fifth read js_api method. For the given campaign, lists every
        ``ContentPiece`` via ``list_campaign_content`` and maps each one to
        a ``ContentPerformanceRowUiModel`` whose ``ctr``/``cpc`` come ONLY
        from the G6 ``build_content_performance_summary`` builder (G5/G6
        chain — no hand-written formula). Unknown campaign ->
        ``VALIDATION_ERROR``; a campaign with zero content pieces ->
        ``ok=True`` with an empty ``rows`` tuple (not an error); a piece
        with no performance data -> ``None`` metrics. Never raises into JS;
        never leaks secret/path/exception text.
        """
        if not isinstance(raw_payload, dict):
            return self._content_performance_err(
                _ERROR_VALIDATION, "Pošiljka iz GUI-ja nije objekat."
            )
        campaign_id_raw = raw_payload.get("campaign_id")
        if not isinstance(campaign_id_raw, str) or not campaign_id_raw.strip():
            return self._content_performance_err(
                _ERROR_VALIDATION, "campaign_id je obavezan (string)."
            )
        campaign_id = CampaignId(campaign_id_raw.strip())
        try:
            if self._campaign_repo.get_campaign(campaign_id) is None:
                return self._content_performance_err(
                    _ERROR_VALIDATION, f"Kampanja {campaign_id} ne postoji."
                )
            pieces = self._content_repo.list_campaign_content(campaign_id)
            rows_list: list[ContentPerformanceRowUiModel] = []
            for piece in pieces:
                summary = build_content_performance_summary(
                    self._performance_repo, piece.id
                )
                rows_list.append(
                    ContentPerformanceRowUiModel(
                        content_piece_id=str(piece.id),
                        label=_content_piece_label(piece),
                        ctr=summary.derived.ctr,
                        cpc=summary.derived.cpc,
                    )
                )
            return asdict(
                ContentPerformanceResultUiModel(
                    ok=True,
                    rows=tuple(rows_list),
                    error_code=None,
                    error_message=None,
                )
            )
        except Exception:
            self._bootstrap.logger.exception(
                "get_campaign_content_performance failed"
            )
            return self._content_performance_err(
                _ERROR_INTERNAL,
                "Učitavanje učinka po objavi nije uspjelo (interna greška).",
            )

    @_with_call_resources
    def pick_and_preview_performance_csv(
        self, raw_payload: dict | None = None
    ) -> dict:
        """Open a native file dialog and preview ONE CSV performance file
        (ACS-F1-055).

        First WRITE-path performance js_api method. Opens the OS file picker
        through ``webview.windows[0].create_file_dialog`` (single-window app),
        then runs the existing G3 ``PreviewPerformanceMapping`` use-case on the
        chosen file — persisting NOTHING. A cancelled dialog is a NORMAL
        outcome (``ok=True, cancelled=True``), not an error. A chosen file
        that fails to parse maps to ``VALIDATION_ERROR`` without leaking the
        exception text. ``file_path`` is returned deliberately (the confirm
        step re-references it without reopening the dialog); it is a path,
        not a secret. ``webview`` is imported locally so the bridge module
        stays importable in environments without pywebview (same pattern as
        ``presentation_webview/__main__.py``).
        """
        del raw_payload
        try:
            import webview  # type: ignore[import-not-found,import-untyped]
        except ImportError:
            return self._preview_err(
                _ERROR_INTERNAL,
                "GUI okruženje nije dostupno (interna greška).",
            )
        if not getattr(webview, "windows", None):
            return self._preview_err(
                _ERROR_INTERNAL,
                "Nema aktivnog prozora (interna greška).",
            )
        try:
            paths = webview.windows[0].create_file_dialog(
                webview.OPEN_DIALOG,
                file_types=("CSV Files (*.csv)", "All files (*.*)"),
            )
        except Exception as exc:
            self._bootstrap.logger.error(
                "create_file_dialog failed (%s)", type(exc).__name__
            )
            return self._preview_err(
                _ERROR_INTERNAL,
                "Otvaranje dijaloga nije uspjelo (interna greška).",
            )
        if not paths:
            return asdict(
                PerformanceCsvPreviewResultUiModel(
                    ok=True,
                    cancelled=True,
                    file_path=None,
                    columns=(),
                    total_rows=0,
                    valid_rows=0,
                    invalid_rows=0,
                    invalid_samples=(),
                    error_code=None,
                    error_message=None,
                )
            )
        file_path = paths[0]
        try:
            preview = PreviewPerformanceMapping().execute(file_path)
        except Exception as exc:
            self._bootstrap.logger.error(
                "preview csv failed (%s)", type(exc).__name__
            )
            return self._preview_err(
                _ERROR_VALIDATION,
                "Fajl nije moguće učitati kao CSV. Provjeri format i pokušaj ponovo.",
            )
        return asdict(
            PerformanceCsvPreviewResultUiModel(
                ok=True,
                cancelled=False,
                file_path=file_path,
                columns=tuple(
                    PerformanceCsvColumnUiModel(
                        canonical_field=c.canonical_field,
                        header=c.header,
                        status=c.status,
                        candidates=c.candidates,
                    )
                    for c in preview.columns
                ),
                total_rows=preview.total_rows,
                valid_rows=preview.valid_rows,
                invalid_rows=preview.invalid_rows,
                invalid_samples=tuple(
                    PerformanceCsvInvalidSampleUiModel(
                        row_number=s.row_number,
                        errors=s.errors,
                    )
                    for s in preview.invalid_samples
                ),
                error_code=None,
                error_message=None,
            )
        )

    @_with_call_resources
    def confirm_performance_import(self, raw_payload: dict) -> dict:
        """Persist + match a previously previewed CSV import (ACS-F1-055).

        Second WRITE-path performance js_api method. Re-runs the existing
        G3 ``ConfirmPerformanceImport`` (with ``column_overrides=None`` — no
        interactive remapping in v1) then the G4
        ``MatchPerformanceImportBatch`` for the given campaign, returning both
        the batch counts and the match counters. Unknown campaign ->
        ``VALIDATION_ERROR``. Never leaks secret/path/exception text (the
        ``file_path`` is an INPUT, not part of the response).
        """
        if not isinstance(raw_payload, dict):
            return self._confirm_err(
                _ERROR_VALIDATION, "Pošiljka iz GUI-ja nije objekat."
            )
        file_path_raw = raw_payload.get("file_path")
        campaign_id_raw = raw_payload.get("campaign_id")
        platform_code = raw_payload.get("platform_code")
        if not isinstance(file_path_raw, str) or not file_path_raw.strip():
            return self._confirm_err(
                _ERROR_VALIDATION, "file_path je obavezan (string)."
            )
        if not isinstance(campaign_id_raw, str) or not campaign_id_raw.strip():
            return self._confirm_err(
                _ERROR_VALIDATION, "campaign_id je obavezan (string)."
            )
        if platform_code is not None and not isinstance(platform_code, str):
            return self._confirm_err(
                _ERROR_VALIDATION,
                "platform_code mora biti string ili izostavljen.",
            )
        campaign_id = CampaignId(campaign_id_raw.strip())
        normalized_platform = (
            platform_code.strip()
            if isinstance(platform_code, str) and platform_code.strip()
            else None
        )
        try:
            if self._campaign_repo.get_campaign(campaign_id) is None:
                return self._confirm_err(
                    _ERROR_VALIDATION, f"Kampanja {campaign_id} ne postoji."
                )
            batch = ConfirmPerformanceImport(self._performance_repo).execute(
                file_path_raw.strip(),
                column_overrides=None,
                platform_code=normalized_platform,
            )
            match_result = MatchPerformanceImportBatch(
                self._performance_repo
            ).execute(batch.id, campaign_id)
            materialize_result = (
                materialize_performance_snapshots.MaterializePerformanceSnapshots(
                    self._performance_repo
                ).execute(batch.id)
            )
            return asdict(
                ConfirmPerformanceImportResultUiModel(
                    ok=True,
                    batch_id=str(batch.id),
                    row_count=batch.row_count,
                    valid_count=batch.matched_count,
                    invalid_count=batch.unmatched_count,
                    matched_count=match_result.matched_count,
                    ambiguous_count=match_result.ambiguous_count,
                    unmatched_count=match_result.unmatched_count,
                    skipped_count=match_result.skipped_count,
                    materialized_count=materialize_result.materialized_count,
                    skipped_invalid_count=materialize_result.skipped_invalid_count,
                    error_code=None,
                    error_message=None,
                )
            )
        except Exception:
            self._bootstrap.logger.exception("confirm_performance_import failed")
            return self._confirm_err(
                _ERROR_INTERNAL,
                "Uvoz performansi nije uspio (interna greška).",
            )

    @_with_call_resources
    def start_brand_ingestion(self, raw_payload: dict) -> dict:
        """Submit a website ingestion job for one brand (ACS-GUI-011).

        First bridge method that triggers ``IngestBrandSources`` (S2-G6) —
        every prior ingestion bridge method (``get_ingestion_review``,
        ``approve_fact_candidate``, ``reject_fact_candidate``) only reads or
        reviews candidates that already exist; nothing in production code
        called ``IngestBrandSources`` before this (confirmed by grep before
        writing this method — it only had test callers).

        ``raw_payload = {"brand_id": str | None, "urls": list[str]}``.
        ``brand_id=None`` resolves the seeded demo brand, same as
        ``get_ingestion_review``/``assemble_brand_snapshot``
        (``_resolve_review_brand_id``). Same STARTED-shape / JobManager
        pattern as ``generate_campaign_content`` (ACS-F1-047): this method
        only validates and submits; the actual DISCOVER->FETCH->EXTRACT->
        BUILD_FACTS run happens on a ``JobManager`` worker thread and is
        polled via the EXISTING ``get_job_status(job_id)`` — no new polling
        endpoint needed. Once the job reaches ``SUCCEEDED``, the JS caller
        calls the EXISTING ``get_ingestion_review`` to see what was built;
        this method does not return candidate data itself.
        """
        if not isinstance(raw_payload, dict):
            return self._start_ingestion_err(
                _ERROR_VALIDATION, "Pošiljka iz GUI-ja nije objekat."
            )
        brand_id = self._resolve_review_brand_id(raw_payload)
        if brand_id is None:
            return self._start_ingestion_err(
                _ERROR_VALIDATION, "brand_id mora biti string."
            )
        urls_raw = raw_payload.get("urls")
        if not isinstance(urls_raw, list) or not urls_raw:
            return self._start_ingestion_err(
                _ERROR_VALIDATION, "urls je obavezna neprazna lista."
            )
        urls: list[str] = []
        for item in urls_raw:
            if not isinstance(item, str) or not item.strip():
                return self._start_ingestion_err(
                    _ERROR_VALIDATION, "Svaki URL mora biti neprazan string."
                )
            urls.append(item.strip())
        try:
            if self._brand_repo.get_brand(brand_id) is None:
                return self._start_ingestion_err(
                    _ERROR_VALIDATION, f"Brend {brand_id} ne postoji."
                )
        except (EntityNotFound, ValueError, TypeError) as exc:
            return self._start_ingestion_err(_ERROR_VALIDATION, str(exc))

        source_scope = tuple(urls)
        try:
            job_id = self._bootstrap.job_manager.submit(
                "ingest_brand_sources",
                self._build_ingest_brand_sources_closure(brand_id, source_scope),
            )
        except RuntimeError as exc:
            self._bootstrap.logger.error(
                "start_brand_ingestion: JobManager.submit failed: %s", exc
            )
            return self._start_ingestion_err(
                _ERROR_INTERNAL,
                "Sistem je zauzet. Pokušaj ponovo za par sekundi.",
            )

        return asdict(
            StartIngestionResultUiModel(
                ok=True,
                brand_id=str(brand_id),
                job_id=job_id,
                error_code=None,
                error_message=None,
            )
        )

    def _build_ingest_brand_sources_closure(
        self, brand_id: BrandId, source_scope: tuple[str, ...]
    ):
        """Return the ``JobManager``-submitted closure for one ingestion run.

        Runs on a ``JobManager`` worker thread (NOT the pywebview thread that
        called ``start_brand_ingestion``), so it opens its OWN
        ``_resource_scope()`` — the bridge's per-call connection is closed
        before this closure ever starts (HOTFIX-002 pattern, same reason
        ``_build_generate_content_closure`` does this for content
        generation).
        """
        job_manager = self._bootstrap.job_manager

        def _run(token) -> None:  # type: ignore[no-untyped-def]
            with self._resource_scope():
                use_case = self._build_ingest_use_case(job_manager)
                run = use_case.execute(brand_id, source_scope, token=token)
                stats = run.stats
                if stats is not None:
                    job_manager.update_progress(
                        token.job_id,
                        stats.fetched_pages,
                        stats.discovered_urls,
                        phase="DONE",
                        message=(
                            f"fetched={stats.fetched_pages} "
                            f"extracted={stats.extracted_chunks} "
                            f"candidates={stats.built_candidates} "
                            f"failed={stats.failed_pages}"
                        ),
                    )

        return _run

    def _build_ingest_use_case(self, job_manager: Any) -> IngestBrandSources:
        """Wire a fresh ``IngestBrandSources`` with REAL G3/G4/G5 adapters.

        Mirrors exactly the wiring independently verified against a live
        external URL earlier in this session (see
        agent_reports/2026-09-11-ACS-GUI-011-claude.md) — same fetcher,
        discovery, classifier, extractor, filter, deduplicator, visual
        identity adapter. ``document_extractors={}`` is a deliberate v1
        scope boundary (task contract §"Šta NE SMIJE") — PDF/DOCX/XLSX (G9)
        URLs will simply produce zero chunks, not fail the run.
        """
        policy = UrlSafetyPolicy()
        fetcher = HttpFetcher(policy=policy)
        robots = RobotsReader(fetcher)
        sitemaps = SitemapReader(fetcher)
        budget = CrawlBudget()
        discovery = DomainDiscovery(
            fetcher=fetcher,
            robots=robots,
            sitemaps=sitemaps,
            policy=policy,
            budget=budget,
        )
        return IngestBrandSources(
            repository=self._ingestion_repo,
            fetcher=fetcher,
            classifier=UrlClassifier(),
            discovery=discovery,
            budget=budget,
            normalizer=normalize_url,
            visual_identity_extractor=VisualIdentityAdapter(),
            content_extractor=MainContentExtractor().extract,
            boilerplate_filter=BoilerplateFilter().filter,
            deduplicator=Deduplicator().deduplicate,
            document_extractors={},
            job_manager=job_manager,
        )

    @staticmethod
    def _start_ingestion_err(code: str, message: str) -> dict:
        """Error result for ``start_brand_ingestion`` only (ACS-GUI-011)."""
        return asdict(
            StartIngestionResultUiModel(
                ok=False,
                brand_id=None,
                job_id=None,
                error_code=code,
                error_message=message,
            )
        )

    @_with_call_resources
    def clear_brand_ingestion(self, raw_payload: dict) -> dict:
        """Delete every ingestion run for a brand (ACS-GUI-013).

        Lets a tester clear out previously-ingested pages so a new URL can
        be tried without the review list accumulating candidates from every
        prior attempt. Deletes ``ingestion_runs``/``crawl_targets``/
        ``source_snapshots``/``source_chunks``/``fact_candidates`` for the
        brand via ``IngestionRepositoryPort.delete_ingestion_data_for_brand``
        — does NOT touch ``approved_facts`` (a fact already approved keeps
        its own copy of the text, independent of the raw source data this
        removes). No confirmation prompt on the Python side — the JS caller
        is expected to confirm with the user before calling this (see
        ``static/app.js``), since this bridge method's whole contract is "do
        exactly what was asked, immediately".
        """
        if not isinstance(raw_payload, dict):
            return self._clear_ingestion_err(
                _ERROR_VALIDATION, "Pošiljka iz GUI-ja nije objekat."
            )
        brand_id = self._resolve_review_brand_id(raw_payload)
        if brand_id is None:
            return self._clear_ingestion_err(
                _ERROR_VALIDATION, "brand_id mora biti string."
            )
        try:
            if self._brand_repo.get_brand(brand_id) is None:
                return self._clear_ingestion_err(
                    _ERROR_VALIDATION, f"Brend {brand_id} ne postoji."
                )
            deleted = self._ingestion_repo.delete_ingestion_data_for_brand(brand_id)
        except (EntityNotFound, ValueError, TypeError) as exc:
            return self._clear_ingestion_err(_ERROR_VALIDATION, str(exc))
        except Exception:
            self._bootstrap.logger.exception("clear_brand_ingestion failed")
            return self._clear_ingestion_err(
                _ERROR_INTERNAL,
                "Brisanje preuzetih podataka nije uspjelo (interna greška).",
            )
        return asdict(
            ClearIngestionResultUiModel(
                ok=True,
                brand_id=str(brand_id),
                deleted_run_count=deleted,
                error_code=None,
                error_message=None,
            )
        )

    @staticmethod
    def _clear_ingestion_err(code: str, message: str) -> dict:
        """Error result for ``clear_brand_ingestion`` only (ACS-GUI-013)."""
        return asdict(
            ClearIngestionResultUiModel(
                ok=False,
                brand_id=None,
                deleted_run_count=None,
                error_code=code,
                error_message=message,
            )
        )

    @_with_call_resources
    def get_ingestion_review(self, raw_payload: dict) -> dict:
        """Return every ``FactCandidate`` for a brand (S2-G7b read path).

        First ingestion-review bridge method. Reads the brand's candidates
        through ``FactRepositoryPort.list_fact_candidates_by_brand`` and
        attaches each candidate's ``SourceSnapshot.url`` for provenance
        display. ``approved_count``/``rejected_count`` are separate counters
        (never folded into the candidate list). Never raises into JS; never
        leaks secret/path/exception text.
        """
        if not isinstance(raw_payload, dict):
            return self._ingestion_review_err(
                _ERROR_VALIDATION, "Pošiljka iz GUI-ja nije objekat."
            )
        brand_id = self._resolve_review_brand_id(raw_payload)
        if brand_id is None:
            return self._ingestion_review_err(
                _ERROR_VALIDATION, "brand_id mora biti string."
            )
        try:
            if self._brand_repo.get_brand(brand_id) is None:
                return self._ingestion_review_err(
                    _ERROR_VALIDATION, f"Brend {brand_id} ne postoji."
                )
            candidates = self._fact_repo.list_fact_candidates_by_brand(brand_id)
            approved_count = 0
            rejected_count = 0
            rows: list[IngestionReviewCandidateUiModel] = []
            for candidate in candidates:
                if candidate.status is FactStatus.APPROVED:
                    approved_count += 1
                elif candidate.status is FactStatus.REJECTED:
                    rejected_count += 1
                snapshot = self._ingestion_repo.get_source_snapshot(
                    candidate.snapshot_id
                )
                rows.append(
                    IngestionReviewCandidateUiModel(
                        candidate_id=str(candidate.id),
                        snapshot_id=str(candidate.snapshot_id),
                        snapshot_url=snapshot.url if snapshot is not None else "",
                        content=candidate.content,
                        chunk_id=(
                            str(candidate.chunk_id)
                            if candidate.chunk_id is not None
                            else None
                        ),
                        status=candidate.status.value,
                        created_at=candidate.created_at.isoformat(),
                    )
                )
            return asdict(
                IngestionReviewResultUiModel(
                    ok=True,
                    brand_id=str(brand_id),
                    candidates=tuple(rows),
                    approved_count=approved_count,
                    rejected_count=rejected_count,
                    error_code=None,
                    error_message=None,
                )
            )
        except Exception:
            self._bootstrap.logger.exception("get_ingestion_review failed")
            return self._ingestion_review_err(
                _ERROR_INTERNAL,
                "Učitavanje pregleda činjenica nije uspjelo (interna greška).",
            )

    @_with_call_resources
    def approve_fact_candidate(self, raw_payload: dict) -> dict:
        """Approve a PROPOSED candidate by delegating to G7a (S2-G7b).

        NO candidate mutation here and NO duplicate invariant check — the
        bridge only translates the payload and forwards to
        ``ApproveFactCandidate.execute``, which owns idempotency/atomicity.
        """
        if not isinstance(raw_payload, dict):
            return self._approve_err(
                _ERROR_VALIDATION, "Pošiljka iz GUI-ja nije objekat."
            )
        candidate_id_raw = raw_payload.get("candidate_id")
        if not isinstance(candidate_id_raw, str) or not candidate_id_raw.strip():
            return self._approve_err(
                _ERROR_VALIDATION, "candidate_id je obavezan (string)."
            )
        candidate_id = FactCandidateId(candidate_id_raw.strip())
        try:
            fact = ApproveFactCandidate(
                ingestion_repo=self._ingestion_repo,
                fact_repo=self._fact_repo,
                unit_of_work=self._uow,
            ).execute(candidate_id)
        except EntityNotFound:
            return self._approve_err(
                _ERROR_VALIDATION, f"Kandidat {candidate_id} ne postoji."
            )
        except InvariantViolation as exc:
            return self._approve_err(_ERROR_VALIDATION, str(exc))
        except Exception:
            self._bootstrap.logger.exception("approve_fact_candidate failed")
            return self._approve_err(
                _ERROR_INTERNAL,
                "Odobravanje činjenice nije uspjelo (interna greška).",
            )
        return asdict(
            ApproveFactResultUiModel(
                ok=True,
                approved_fact_id=str(fact.id),
                candidate_id=str(candidate_id),
                snapshot_url=fact.source_ref.uri,
                version=fact.version,
                error_code=None,
                error_message=None,
            )
        )

    @_with_call_resources
    def bulk_review_fact_candidates(self, raw_payload: dict) -> dict:
        """Approve or reject MANY candidates in one call (ACS-GUI-017).

        ``{"candidate_ids": [...], "action": "approve"|"reject"}``. A single
        ingested page can produce 100+ tiny PROPOSED candidates (deterministic
        1:1 paragraph mapping, no LLM synthesis — confirmed live on
        kingdomdoo.com/en/: 104 candidates from one page alone), so
        one-by-one review does not scale. Loops the EXISTING
        ``ApproveFactCandidate``/``RejectFactCandidate`` use-cases per id —
        no new domain logic, no new invariant. Each id's outcome is
        independent: one already-decided (by a concurrent action) or missing
        candidate does not abort the rest of the batch — partial success is
        the normal, expected outcome for a large batch, not a failure. Per-
        item exception text is logged, never returned (same no-leak rule as
        every other method) — only aggregate counts cross the js_api
        boundary.
        """
        if not isinstance(raw_payload, dict):
            return self._bulk_review_err(
                _ERROR_VALIDATION, "Pošiljka iz GUI-ja nije objekat."
            )
        action = raw_payload.get("action")
        if action not in ("approve", "reject"):
            return self._bulk_review_err(
                _ERROR_VALIDATION, "action mora biti 'approve' ili 'reject'."
            )
        ids_raw = raw_payload.get("candidate_ids")
        if not isinstance(ids_raw, list) or not ids_raw:
            return self._bulk_review_err(
                _ERROR_VALIDATION, "candidate_ids je obavezna neprazna lista."
            )
        candidate_ids: list[FactCandidateId] = []
        for item in ids_raw:
            if not isinstance(item, str) or not item.strip():
                return self._bulk_review_err(
                    _ERROR_VALIDATION,
                    "Svaki candidate_id mora biti neprazan string.",
                )
            candidate_ids.append(FactCandidateId(item.strip()))

        succeeded = 0
        failed = 0
        for candidate_id in candidate_ids:
            try:
                if action == "approve":
                    ApproveFactCandidate(
                        ingestion_repo=self._ingestion_repo,
                        fact_repo=self._fact_repo,
                        unit_of_work=self._uow,
                    ).execute(candidate_id)
                else:
                    RejectFactCandidate(
                        ingestion_repo=self._ingestion_repo,
                        unit_of_work=self._uow,
                    ).execute(candidate_id)
                succeeded += 1
            except (EntityNotFound, InvariantViolation):
                failed += 1
            except Exception:  # noqa: BLE001 - one bad item must not kill the batch
                self._bootstrap.logger.exception(
                    "bulk_review_fact_candidates item failed candidate_id=%s",
                    candidate_id,
                )
                failed += 1

        return asdict(
            BulkReviewResultUiModel(
                ok=True,
                action=action,
                succeeded_count=succeeded,
                failed_count=failed,
                error_code=None,
                error_message=None,
            )
        )

    @staticmethod
    def _bulk_review_err(code: str, message: str) -> dict:
        """Error result for ``bulk_review_fact_candidates`` only (ACS-GUI-017)."""
        return asdict(
            BulkReviewResultUiModel(
                ok=False,
                action=None,
                succeeded_count=None,
                failed_count=None,
                error_code=code,
                error_message=message,
            )
        )

    @_with_call_resources
    def reject_fact_candidate(self, raw_payload: dict) -> dict:
        """Reject a PROPOSED candidate by delegating to G7a (S2-G7b).

        ``reason`` is accepted for API stability but is NOT persisted (the
        G7a ``RejectFactCandidate`` documents this as an OUT_OF_SCOPE_FINDING).
        """
        if not isinstance(raw_payload, dict):
            return self._reject_err(
                _ERROR_VALIDATION, "Pošiljka iz GUI-ja nije objekat."
            )
        candidate_id_raw = raw_payload.get("candidate_id")
        if not isinstance(candidate_id_raw, str) or not candidate_id_raw.strip():
            return self._reject_err(
                _ERROR_VALIDATION, "candidate_id je obavezan (string)."
            )
        reason = raw_payload.get("reason")
        if reason is not None and not isinstance(reason, str):
            return self._reject_err(
                _ERROR_VALIDATION, "reason mora biti string ili izostavljen."
            )
        candidate_id = FactCandidateId(candidate_id_raw.strip())
        try:
            RejectFactCandidate(
                ingestion_repo=self._ingestion_repo,
                unit_of_work=self._uow,
            ).execute(candidate_id, reason)
        except EntityNotFound:
            return self._reject_err(
                _ERROR_VALIDATION, f"Kandidat {candidate_id} ne postoji."
            )
        except InvariantViolation as exc:
            return self._reject_err(_ERROR_VALIDATION, str(exc))
        except Exception:
            self._bootstrap.logger.exception("reject_fact_candidate failed")
            return self._reject_err(
                _ERROR_INTERNAL,
                "Odbijanje činjenice nije uspjelo (interna greška).",
            )
        return asdict(
            RejectFactResultUiModel(
                ok=True,
                candidate_id=str(candidate_id),
                status="REJECTED",
                error_code=None,
                error_message=None,
            )
        )

    @_with_call_resources
    def assemble_brand_snapshot(self, raw_payload: dict) -> dict:
        """Assemble a new immutable ``BrandSnapshot`` from approved facts.

        Does NOT create ``ApprovedFact`` rows (that is G7a's job) — it only
        gathers the already-APPROVED facts for the brand, copies the voice/
        audience/service/visual/restriction value objects from the latest
        snapshot (or defaults for the first), increments the version, and
        persists via ``save_snapshot``. A brand with zero approved facts is
        a validation error (never an empty snapshot).
        """
        if not isinstance(raw_payload, dict):
            return self._assemble_err(
                _ERROR_VALIDATION, "Pošiljka iz GUI-ja nije objekat."
            )
        brand_id = self._resolve_review_brand_id(raw_payload)
        if brand_id is None:
            return self._assemble_err(
                _ERROR_VALIDATION, "brand_id mora biti string."
            )
        try:
            with self._snapshot_assembly_lock_for(str(brand_id)):
                if self._brand_repo.get_brand(brand_id) is None:
                    return self._assemble_err(
                        _ERROR_VALIDATION, f"Brend {brand_id} ne postoji."
                    )
                facts = self._fact_repo.list_approved_facts_by_brand(brand_id)
                if not facts:
                    return self._assemble_err(
                        _ERROR_VALIDATION,
                        "Nema odobrenih činjenica za ovaj brend.",
                    )
                latest = self._brand_repo.get_latest_snapshot(brand_id)
                version = (latest.version + 1) if latest is not None else 1
                snapshot = BrandSnapshot(
                    id=BrandSnapshotId(new_id()),
                    brand_id=brand_id,
                    version=version,
                    language=latest.language if latest is not None else "en",
                    locale=latest.locale if latest is not None else "en_US",
                    script=latest.script if latest is not None else "Latin",
                    voice=(
                        latest.voice
                        if latest is not None
                        else BrandVoice(formality="")
                    ),
                    audiences=latest.audiences if latest is not None else (),
                    services=latest.services if latest is not None else (),
                    visual_identity=(
                        latest.visual_identity
                        if latest is not None
                        else VisualIdentity()
                    ),
                    restrictions=latest.restrictions if latest is not None else (),
                    approved_fact_ids=tuple(fact.id for fact in facts),
                    created_at=utc_now(),
                )
                self._brand_repo.save_snapshot(snapshot)
        except Exception:
            self._bootstrap.logger.exception("assemble_brand_snapshot failed")
            return self._assemble_err(
                _ERROR_INTERNAL,
                "Kreiranje snimka brenda nije uspjelo (interna greška).",
            )
        return asdict(
            AssembleSnapshotResultUiModel(
                ok=True,
                snapshot_id=str(snapshot.id),
                brand_id=str(brand_id),
                version=snapshot.version,
                approved_fact_count=len(snapshot.approved_fact_ids),
                created_at=snapshot.created_at.isoformat(),
                error_code=None,
                error_message=None,
            )
        )

    @_with_call_resources
    @_with_call_resources
    def activate_brand_snapshot(self, raw_payload: dict) -> dict:
        """Make a previously-assembled ``BrandSnapshot`` the active one
        (ACS-S2-018).

        Writes ``brand-seed.json`` so the next ``get_brand_overview`` /
        ``create_campaign_and_generate_plan`` read the activated version.
        Does NOT mutate the immutable snapshot rows themselves.

        No-op when the requested snapshot_id is already active (returns
        ``was_already_active=True`` so the GUI can show a calmer toast).
        Thread-safe against concurrent ``_ensure_brand`` reads via
        ``self._active_seed_lock`` — without the lock, an activate that
        races with a campaign creation could leave the campaign pinned
        to the older snapshot the user just replaced.
        """
        if not isinstance(raw_payload, dict):
            return self._activate_err(
                _ERROR_VALIDATION, "Pošiljka iz GUI-ja nije objekat."
            )
        snapshot_id = self._resolve_review_snapshot_id(raw_payload)
        if snapshot_id is None:
            return self._activate_err(
                _ERROR_VALIDATION, "snapshot_id mora biti string."
            )
        try:
            snapshot = self._brand_repo.get_snapshot(snapshot_id)
        except Exception:
            self._bootstrap.logger.exception("activate_brand_snapshot failed")
            return self._activate_err(
                _ERROR_INTERNAL,
                "Aktivacija snimka brenda nije uspjela (interna greška).",
            )
        if snapshot is None:
            return self._activate_err(
                _ERROR_VALIDATION,
                f"Snimak brenda {snapshot_id} ne postoji.",
            )
        seed_path = self._user_data_dir() / _BRAND_SEED_FILE
        try:
            with self._active_seed_lock:
                # ``_ensure_brand`` (which we deliberately do NOT call
                # here — it has self-healing reseed side effects) is the
                # only other writer of this file. Reading inside the lock
                # is enough to detect "already active" without risking a
                # reseed.
                already_active = self._read_active_snapshot_id()
                if already_active == snapshot_id:
                    was_already_active = True
                else:
                    self._write_seed(
                        seed_path,
                        {
                            "brand_id": str(snapshot.brand_id),
                            "brand_snapshot_id": str(snapshot.id),
                        },
                    )
                    was_already_active = False
        except Exception:
            self._bootstrap.logger.exception("activate_brand_snapshot failed")
            return self._activate_err(
                _ERROR_INTERNAL,
                "Aktivacija snimka brenda nije uspjela (interna greška).",
            )
        return asdict(
            ActivateBrandSnapshotResultUiModel(
                ok=True,
                snapshot_id=str(snapshot.id),
                brand_id=str(snapshot.brand_id),
                version=snapshot.version,
                approved_fact_count=len(snapshot.approved_fact_ids),
                created_at=snapshot.created_at.isoformat(),
                was_already_active=was_already_active,
                error_code=None,
                error_message=None,
            )
        )

    @_with_call_resources
    @_with_call_resources
    def list_brand_snapshots(self, raw_payload: dict | None = None) -> dict:
        """Return every assembled ``BrandSnapshot`` for the brand, newest
        first, with an ``is_active`` flag per row (ACS-S2-018).

        Reads the active-id via ``_read_active_snapshot_id`` (no
        self-healing side effects) so a brand with no activated
        snapshot yet shows the list with no row marked active.
        """
        if not isinstance(raw_payload, dict):
            return self._list_snapshots_err(
                _ERROR_VALIDATION, "Pošiljka iz GUI-ja nije objekat."
            )
        brand_id = self._resolve_review_brand_id(raw_payload)
        if brand_id is None:
            return self._list_snapshots_err(
                _ERROR_VALIDATION, "brand_id mora biti string."
            )
        try:
            snapshots = self._brand_repo.list_snapshots(brand_id)
            active_id = self._read_active_snapshot_id()
        except Exception:
            self._bootstrap.logger.exception("list_brand_snapshots failed")
            return self._list_snapshots_err(
                _ERROR_INTERNAL,
                "Učitavanje liste snimaka brenda nije uspjelo (interna greška).",
            )
        rows: list[dict] = []
        for snap in snapshots:
            rows.append(
                asdict(
                    BrandSnapshotSummaryUiModel(
                        snapshot_id=str(snap.id),
                        version=snap.version,
                        language=snap.language,
                        locale=snap.locale,
                        script=snap.script,
                        approved_fact_count=len(snap.approved_fact_ids),
                        created_at=snap.created_at.isoformat(),
                        is_active=(active_id == snap.id),
                    )
                )
            )
        return asdict(
            ListBrandSnapshotsResultUiModel(
                ok=True,
                brand_id=str(brand_id),
                snapshots=tuple(rows),
                error_code=None,
                error_message=None,
            )
        )

    # --- per-call SQLite resources ---

    @contextmanager
    def _resource_scope(self) -> Iterator[None]:
        """Bind a fresh connection graph to the current js_api call only.

        SQLite's default ``check_same_thread=True`` remains intact. The
        connection is created on the pywebview worker thread that uses it
        and is always closed there. ContextVar prevents concurrent calls
        from overwriting each other's repositories.
        """
        connection = create_connection(self._bootstrap.paths.database_path)
        resources = _CallResources(
            brand_repo=SqliteBrandRepository(connection),
            fact_repo=SqliteFactRepository(connection),
            ingestion_repo=SqliteIngestionRepository(connection),
            campaign_repo=SqliteCampaignRepository(connection),
            provider_config_repo=SqliteProviderConfigRepository(connection),
            content_repo=SqliteContentRepository(connection),
            revision_repo=SqliteRevisionRepository(connection),
            visual_repo=SqliteVisualRepository(connection),
            performance_repo=SqlitePerformanceRepository(connection),
            uow=SqliteUnitOfWork(connection),
        )
        token = self._active_resources.set(resources)
        try:
            yield
        finally:
            self._active_resources.reset(token)
            connection.close()

    def _resources(self) -> _CallResources:
        resources = self._active_resources.get()
        if resources is None:
            raise RuntimeError("SQLite resources require an active bridge call")
        return resources

    @property
    def _brand_repo(self) -> SqliteBrandRepository:
        return self._resources().brand_repo

    @property
    def _fact_repo(self) -> SqliteFactRepository:
        return self._resources().fact_repo

    @property
    def _ingestion_repo(self) -> SqliteIngestionRepository:
        return self._resources().ingestion_repo

    @property
    def _campaign_repo(self) -> SqliteCampaignRepository:
        return self._resources().campaign_repo

    @property
    def _provider_config_repo(self) -> SqliteProviderConfigRepository:
        return self._resources().provider_config_repo

    @property
    def _uow(self) -> SqliteUnitOfWork:
        return self._resources().uow

    @property
    def _content_repo(self) -> SqliteContentRepository:
        # ACS-GUI-008: ``generate_campaign_content`` reads existing
        # pieces (idempotency pre-check) and writes new ones (via
        # ``GenerateSocialPost``). Same per-call lifetime as the
        # other repos.
        return self._resources().content_repo

    @property
    def _revision_repo(self) -> SqliteRevisionRepository:
        # ACS-GUI-008: ``GenerateSocialPost`` writes one ``Revision``
        # row per generated piece. Same per-call lifetime.
        return self._resources().revision_repo

    @property
    def _visual_repo(self) -> SqliteVisualRepository:
        # ACS-GUI-009: ``export_campaign_package`` reads/writes visual
        # systems + layout specs. Same per-call lifetime.
        return self._resources().visual_repo

    @property
    def _performance_repo(self) -> SqlitePerformanceRepository:
        # ACS-GUI-009: ``ExportCampaign`` persists one
        # ``DistributionInstance`` per exported piece. Same per-call
        # lifetime.
        return self._resources().performance_repo

    # --- helpers (internal, not exposed to JS) ---

    def _lock_for(
        self, campaign_id: str, plan_id: str
    ) -> threading.Lock:
        """Return the per-``(campaign_id, plan_id)`` lock, creating it once.

        ACS-GUI-008 fix-brief-2 BF-3: serializes concurrent
        ``generate_campaign_content`` calls for the same plan so the
        "read existing pieces -> generate -> save" sequence is atomic
        with respect to other threads. Different pairs do not block
        each other (independent locks). Safe under
        ``threading.Lock`` (CPython GIL protects the dict mutation; the
        guard is belt-and-braces for free-threading Python).
        """
        key = (campaign_id, plan_id)
        with self._generation_locks_guard:
            lock = self._generation_locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._generation_locks[key] = lock
            return lock

    def _snapshot_assembly_lock_for(self, brand_id: str) -> threading.Lock:
        """Return the lock guarding one brand's snapshot version sequence."""
        with self._snapshot_assembly_locks_guard:
            lock = self._snapshot_assembly_locks.get(brand_id)
            if lock is None:
                lock = threading.Lock()
                self._snapshot_assembly_locks[brand_id] = lock
            return lock

    def _resolve_ai_adapter(self) -> tuple[Any, dict | None]:
        """Resolve a configured provider into a text-generation adapter.

        Returns ``(adapter, None)`` on success or ``(None, error_dict)`` on
        failure. Reuses ``_resolve_provider()`` and the existing
        ``build_text_generation_adapter`` factory so the provider-resolution
        logic (priority + fallback) has a single source of truth — no
        duplicated ordering code here.
        """
        provider_code, api_key = self._resolve_provider()
        if provider_code is None:
            return None, self._export_err(
                _ERROR_NO_PROVIDER,
                "Nijedan AI provajder nije podešen. Podesi API ključ.",
            )
        if not api_key:
            return None, self._export_err(
                _ERROR_KEY_MISSING,
                f"Provajder {provider_code} je konfigurisan ali API ključ "
                "nije dostupan.",
            )
        try:
            adapter = build_text_generation_adapter(provider_code, api_key)
        except Exception as exc:
            # BF-1 (Codex): the SDK may inline the credential into the
            # exception message. ``logger.exception`` would log the full
            # traceback + ``str(exc)`` (secret leak); ``logger.error`` with
            # only ``type(exc).__name__`` + the safe provider_code logs no
            # secret text. Same shape as ``configure_provider`` (ACS-GUI-007
            # BF-3).
            self._bootstrap.logger.error(
                "adapter factory failed for %s (%s)",
                provider_code,
                type(exc).__name__,
            )
            return None, self._export_err(
                _ERROR_KEY_MISSING,
                f"Ne mogu instancirati adapter za {provider_code}.",
            )
        return adapter, None

    def _get_cached_visual_system(
        self, campaign_id: CampaignId, plan_id: CampaignPlanId
    ) -> Any | None:
        """Return the in-process cached visual system for a plan, or None.

        ``VisualRepositoryPort`` has no ``get_visual_system_by_plan`` lookup,
        so the bridge keeps a small instance-level ``plan_id ->
        visual_system_id`` map (same style as ``_generation_locks``). The
        value is re-read through ``get_visual_system`` and verified to still
        belong to the campaign (self-healing if the DB row was wiped).
        """
        vs_id = self._visual_system_by_plan.get(str(plan_id))
        if vs_id is None:
            return None
        visual_system = self._visual_repo.get_visual_system(VisualSystemId(vs_id))
        if visual_system is None or str(visual_system.campaign_id) != str(campaign_id):
            return None
        return visual_system

    def _record_campaign_visual_system(
        self, plan_id: CampaignPlanId, visual_system_id: VisualSystemId
    ) -> None:
        """Best-effort in-process record of ``plan_id -> visual_system_id``.

        A double-click that (in theory) creates a SECOND CampaignVisualSystem
        for the same plan is an accepted low-risk edge case (an orphaned,
        unused row — NOT duplicated exported content, unlike the
        ContentPiece duplicates BF-3 protects against). No full DB-backed
        protection is warranted here. The map is guarded like
        ``_generation_locks``.
        """
        with self._visual_system_by_plan_guard:
            self._visual_system_by_plan[str(plan_id)] = str(visual_system_id)

    def _ensure_brand(self):
        """Read brand-seed.json; if missing or stale, re-seed from fixture.

        Self-healing on two failure modes:
        1. ``brand-seed.json`` does not exist (first launch).
        2. ``brand-seed.json`` exists but the snapshot it points to has been
           deleted from the DB (e.g. user wiped the SQLite file while the
           cache survived, or the brand was deleted by another tool).
        """
        from ai_campaign_studio.domain.common.ids import BrandId, BrandSnapshotId

        seed_path = self._user_data_dir() / _BRAND_SEED_FILE
        cached = self._read_seed(seed_path)
        if cached is not None:
            bid = cached.get("brand_id")
            sid = cached.get("brand_snapshot_id")
            if isinstance(bid, str) and isinstance(sid, str):
                snap = self._brand_repo.get_snapshot(BrandSnapshotId(sid))
                if snap is not None and str(snap.brand_id) == bid:
                    return BrandId(bid), BrandSnapshotId(sid)
                # Snapshot gone or brand_id mismatch -> fall through to re-seed.

        snapshot = LoadBrandFixture(
            brand_repo=self._brand_repo,
            fact_repo=self._fact_repo,
            unit_of_work=self._uow,
        ).execute(self._brand_fixture_path)
        self._write_seed(
            seed_path,
            {"brand_id": str(snapshot.brand_id), "brand_snapshot_id": str(snapshot.id)},
        )
        return snapshot.brand_id, snapshot.id

    def _read_seed(self, path: Path) -> dict | None:
        try:
            raw = path.read_text(encoding="utf-8")
        except (FileNotFoundError, OSError):
            return None
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return None
        return data if isinstance(data, dict) else None

    def _write_seed(self, path: Path, payload: dict) -> None:
        # Best-effort: a disk-full or perm-denied here just means the
        # next click re-seeds, which is a strictly better outcome than
        # refusing the user's "Sačuvaj i napravi plan" click.
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload), encoding="utf-8")
        except OSError:
            pass

    def _resolve_provider(self) -> tuple[str | None, str | None]:
        """Walk configured providers in priority order; return the first with a key.

        Returns ``(code, key)``:
        - no provider configured at all -> ``(None, None)``
        - every configured provider lacks a non-empty key in SecretStore ->
          ``(last_tried_code, None)``
        - first configured provider with a real key -> ``(code, key)``

        Does not raise — the caller maps absence to error codes.
        """
        configs = list(self._provider_config_repo.list_provider_configs())
        configured_codes = [c.provider_code for c in configs if c.configured]
        ordered_codes = _ordered_configured_codes(configured_codes)
        if not ordered_codes:
            return None, None

        last_code = ordered_codes[-1]
        for code in ordered_codes:
            config = next((c for c in configs if c.provider_code == code), None)
            if config is None or not config.credential_ref:
                last_code = code
                continue
            try:
                api_key = self._bootstrap.secret_store.get_secret(
                    config.credential_ref
                )
            except Exception:
                last_code = code
                continue
            if api_key:
                return code, api_key
            last_code = code

        return last_code, None

    def _user_data_dir(self) -> Path:
        """Resolve the per-user data dir, matching the package convention.

        Kept in sync with the rest of the project by going through
        ``AppPaths.data_dir`` which already does the right thing.
        """
        return self._bootstrap.paths.data_dir

    def _resolve_review_brand_id(self, raw_payload: dict) -> BrandId | None:
        """Resolve the brand for a fact-review/assemble call (S2-G7b).

        A non-empty ``brand_id`` payload wins; otherwise the single seeded
        demo brand is resolved via ``_ensure_brand()`` — the same pattern as
        ``get_brand_overview``. Returns ``None`` when ``brand_id`` is present
        but not a non-empty string (caller maps that to VALIDATION_ERROR).
        """
        brand_id_raw = raw_payload.get("brand_id")
        if brand_id_raw is None:
            return self._ensure_brand()[0]
        if not isinstance(brand_id_raw, str) or not brand_id_raw.strip():
            return None
        return BrandId(brand_id_raw.strip())

    def _resolve_review_snapshot_id(self, raw_payload: dict) -> BrandSnapshotId | None:
        """Resolve the snapshot for an ``activate_brand_snapshot`` call
        (ACS-S2-018).

        Unlike ``_resolve_review_brand_id``, there is NO default to the
        cached snapshot — activation is an explicit user action and
        falling back to "whatever is currently active" would silently
        no-op the request. A missing/non-string ``snapshot_id`` returns
        ``None`` and the caller maps that to VALIDATION_ERROR.
        """
        snapshot_id_raw = raw_payload.get("snapshot_id")
        if not isinstance(snapshot_id_raw, str) or not snapshot_id_raw.strip():
            return None
        return BrandSnapshotId(snapshot_id_raw.strip())

    def _read_active_snapshot_id(self) -> BrandSnapshotId | None:
        """Read the currently-active snapshot from ``brand-seed.json``,
        WITHOUT triggering the ``_ensure_brand`` self-healing reseed
        (ACS-S2-018).

        Used by ``list_brand_snapshots`` to label each row with an
        ``is_active`` flag. Returns ``None`` if the file is missing,
        unparseable, or does not contain a non-empty ``brand_snapshot_id``
        string — in all those cases the GUI shows no row as active,
        which matches user reality (nothing is active until they click
        "Aktiviraj").
        """
        seed_path = self._user_data_dir() / _BRAND_SEED_FILE
        cached = self._read_seed(seed_path)
        if cached is None:
            return None
        sid = cached.get("brand_snapshot_id")
        if not isinstance(sid, str) or not sid.strip():
            return None
        return BrandSnapshotId(sid.strip())

    def _compensate_orphan_campaign(self, campaign: Any) -> None:
        """Best-effort delete of a DRAFT campaign that never got its plan
        (ACS-GUI-006 compensating action).

        Bridge runs two independent use-cases back-to-back, each with
        its own ``with unit_of_work: ... commit()`` transaction:

        1. ``CreateCampaign`` (commits the campaign row in TX-A)
        2. ``GenerateCampaignPlan`` (commits the plan in TX-B, OR throws)

        If step 2 throws, step 1's row is permanently visible in the
        ``campaigns`` table as a DRAFT with no plan. The user's next
        click would create a SECOND such orphan (and a third, fourth…)
        because the GUI cannot see the orphan to retry it. This helper
        is the bridge's response: attempt to roll back step 1's row
        AND its brief (the brief exists only because this campaign was
        just created — ``CreateCampaign`` makes a fresh brief per call,
        so no other campaign can reference it).

        Best-effort: the original ``GENERATION_FAILED`` error must
        ALWAYS reach the JS caller, regardless of whether the
        compensating delete succeeded. Any exception raised by
        ``delete_campaign`` is caught and logged — the user sees the
        AI-generation failure, not a database error. The orphan row
        will be cleaned up by a later hygiene pass (or live with
        itself — it is invisible to the user via the GUI either way).
        """
        try:
            self._campaign_repo.delete_campaign(
                campaign.id, brief_id=campaign.brief_id
            )
        except Exception:
            self._bootstrap.logger.exception(
                "compensating delete failed for orphan campaign %s",
                campaign.id,
            )

    @staticmethod
    def _err(code: str, message: str) -> dict:
        return asdict(
            CampaignPlanResultUiModel(
                ok=False,
                campaign_id=None,
                # ACS-GUI-008: ``plan_id`` is None on error paths (the
                # bridge only knows the plan_id after a successful
                # ``GenerateCampaignPlan``).
                plan_id=None,
                plan_item_count=None,
                error_code=code,
                error_message=message,
            )
        )

    @staticmethod
    def _provider_err(code: str, message: str) -> dict:
        """Error result for ``configure_provider`` only.

        Uses ``ProviderConfigResultUiModel`` (NOT the shared
        ``_err()`` which is hard-coded to
        ``CampaignPlanResultUiModel``) so the return dict has the
        EXACT shape the JS caller expects: ``{ok, provider_code,
        error_code, error_message}`` and nothing else (no
        ``campaign_id`` / ``plan_item_count`` leakage from the
        campaign flow).

        ACS-GUI-007 BF-1: the prior code re-used ``_err()`` here and
        every ``configure_provider`` error came back with
        ``campaign_id`` / ``plan_item_count`` keys (both ``None``).
        That broke the contract for the JS caller (which keys to read)
        AND silently violated the structural no-``api_key``-field
        guarantee for the new DTO. Fixed by introducing this dedicated
        helper and routing all three error paths
        (validation / RegistryError+InvariantViolation / generic
        exception) through it.
        """
        return asdict(
            ProviderConfigResultUiModel(
                ok=False,
                provider_code=None,
                error_code=code,
                error_message=message,
            )
        )

    @staticmethod
    def _generate_err(code: str, message: str) -> dict:
        """Error result for ``generate_campaign_content`` only.

        ACS-F1-047: the DTO shrank to a STARTED-shape (5 fields). The
        per-piece outcome (``generated_count`` / ``failed_count`` /
        ``content_piece_ids``) is no longer in the sync response
        because the work now runs on a background job thread and
        reports via ``get_job_status`` instead. ``job_id`` is None on
        every error path (we never started a job to roll back).
        """
        return asdict(
            GenerateContentResultUiModel(
                ok=False,
                campaign_id=None,
                job_id=None,
                error_code=code,
                error_message=message,
            )
        )

    @staticmethod
    def _export_err(code: str, message: str) -> dict:
        """Error result for ``export_campaign_package`` only.

        Uses ``ExportCampaignResultUiModel`` (NOT ``_err()`` /
        ``_provider_err()`` / ``_generate_err()``) so the return dict has
        the EXACT shape the JS caller expects: ``{ok, campaign_id, zip_path,
        exported_count, skipped_count, error_code, error_message}`` and
        nothing else.
        """
        return asdict(
            ExportCampaignResultUiModel(
                ok=False,
                campaign_id=None,
                zip_path=None,
                exported_count=None,
                skipped_count=None,
                error_code=code,
                error_message=message,
            )
        )

    @staticmethod
    def _list_err(code: str, message: str) -> dict:
        """Error result for ``list_campaigns`` only.

        Uses ``ListCampaignsResultUiModel`` (NOT ``_err()`` /
        ``_provider_err()`` / ``_generate_err()``) so the return dict has
        the EXACT shape the JS caller expects: ``{ok, campaigns,
        error_code, error_message}`` and nothing else.
        """
        return asdict(
            ListCampaignsResultUiModel(
                ok=False,
                campaigns=(),
                error_code=code,
                error_message=message,
            )
        )

    @staticmethod
    def _brand_err(code: str, message: str) -> dict:
        """Error result for ``get_brand_overview`` only.

        Uses ``BrandOverviewResultUiModel`` (NOT ``_err()`` /
        ``_list_err()``) so the return dict has the EXACT shape the JS
        caller expects: ``{ok, brand_name, primary_audience, voice, facts,
        error_code, error_message}`` and nothing else.
        """
        return asdict(
            BrandOverviewResultUiModel(
                ok=False,
                brand_name=None,
                primary_audience=None,
                voice=(),
                facts=(),
                error_code=code,
                error_message=message,
            )
        )

    @staticmethod
    def _dashboard_err(code: str, message: str) -> dict:
        """Error result for ``get_dashboard_overview`` only.

        Uses ``DashboardOverviewResultUiModel`` so the return dict has the
        EXACT shape the JS caller expects: ``{ok, active_campaigns,
        posts_planned, drafts, approved, recent_campaigns, error_code,
        error_message}`` and nothing else.
        """
        return asdict(
            DashboardOverviewResultUiModel(
                ok=False,
                active_campaigns=0,
                posts_planned=0,
                drafts=0,
                approved=0,
                recent_campaigns=(),
                error_code=code,
                error_message=message,
            )
        )

    @staticmethod
    def _performance_err(code: str, message: str) -> dict:
        """Error result for ``get_campaign_performance`` only.

        Uses ``CampaignPerformanceResultUiModel`` so the return dict has the
        EXACT shape the JS caller expects, with ``derived``/``raw`` empty and
        count 0 — no other method's DTO keys leak through.
        """
        return asdict(
            CampaignPerformanceResultUiModel(
                ok=False,
                derived=DerivedMetricSetUiModel(),
                raw=RawMetricSetUiModel(),
                distribution_instance_count=0,
                error_code=code,
                error_message=message,
            )
        )

    @staticmethod
    def _content_performance_err(code: str, message: str) -> dict:
        """Error result for ``get_campaign_content_performance`` only.

        Uses ``ContentPerformanceResultUiModel`` so the return dict has the
        EXACT shape the JS caller expects: ``{ok, rows, error_code,
        error_message}`` with an empty ``rows`` tuple — no other method's
        DTO keys leak through.
        """
        return asdict(
            ContentPerformanceResultUiModel(
                ok=False,
                rows=(),
                error_code=code,
                error_message=message,
            )
        )

    @staticmethod
    def _preview_err(code: str, message: str) -> dict:
        """Error result for ``pick_and_preview_performance_csv`` only.

        Uses ``PerformanceCsvPreviewResultUiModel`` so the return dict has
        the EXACT shape the JS caller expects: ``{ok, cancelled, file_path,
        columns, total_rows, valid_rows, invalid_rows, invalid_samples,
        error_code, error_message}`` with empty preview fields.
        """
        return asdict(
            PerformanceCsvPreviewResultUiModel(
                ok=False,
                cancelled=False,
                file_path=None,
                columns=(),
                total_rows=0,
                valid_rows=0,
                invalid_rows=0,
                invalid_samples=(),
                error_code=code,
                error_message=message,
            )
        )

    @staticmethod
    def _confirm_err(code: str, message: str) -> dict:
        """Error result for ``confirm_performance_import`` only.

        Uses ``ConfirmPerformanceImportResultUiModel`` so the return dict has
        the EXACT shape the JS caller expects, with all counts 0 — no other
        method's DTO keys leak through.
        """
        return asdict(
            ConfirmPerformanceImportResultUiModel(
                ok=False,
                batch_id=None,
                row_count=0,
                valid_count=0,
                invalid_count=0,
                matched_count=0,
                ambiguous_count=0,
                unmatched_count=0,
                skipped_count=0,
                materialized_count=0,
                skipped_invalid_count=0,
                error_code=code,
                error_message=message,
            )
        )


    @staticmethod
    def _ingestion_review_err(code: str, message: str) -> dict:
        """Error result for ``get_ingestion_review`` only (S2-G7b)."""
        return asdict(
            IngestionReviewResultUiModel(
                ok=False,
                brand_id=None,
                candidates=(),
                approved_count=0,
                rejected_count=0,
                error_code=code,
                error_message=message,
            )
        )

    @staticmethod
    def _approve_err(code: str, message: str) -> dict:
        """Error result for ``approve_fact_candidate`` only (S2-G7b)."""
        return asdict(
            ApproveFactResultUiModel(
                ok=False,
                approved_fact_id=None,
                candidate_id=None,
                snapshot_url=None,
                version=None,
                error_code=code,
                error_message=message,
            )
        )

    @staticmethod
    def _reject_err(code: str, message: str) -> dict:
        """Error result for ``reject_fact_candidate`` only (S2-G7b)."""
        return asdict(
            RejectFactResultUiModel(
                ok=False,
                candidate_id=None,
                status=None,
                error_code=code,
                error_message=message,
            )
        )

    @staticmethod
    def _assemble_err(code: str, message: str) -> dict:
        """Error result for ``assemble_brand_snapshot`` only (S2-G7b)."""
        return asdict(
            AssembleSnapshotResultUiModel(
                ok=False,
                snapshot_id=None,
                brand_id=None,
                version=None,
                approved_fact_count=0,
                created_at=None,
                error_code=code,
                error_message=message,
            )
        )

    @staticmethod
    def _activate_err(code: str, message: str) -> dict:
        """Error result for ``activate_brand_snapshot`` only (ACS-S2-018)."""
        return asdict(
            ActivateBrandSnapshotResultUiModel(
                ok=False,
                snapshot_id=None,
                brand_id=None,
                version=None,
                approved_fact_count=0,
                created_at=None,
                was_already_active=False,
                error_code=code,
                error_message=message,
            )
        )

    @staticmethod
    def _list_snapshots_err(code: str, message: str) -> dict:
        """Error result for ``list_brand_snapshots`` only (ACS-S2-018)."""
        return asdict(
            ListBrandSnapshotsResultUiModel(
                ok=False,
                brand_id=None,
                snapshots=(),
                error_code=code,
                error_message=message,
            )
        )


# --- ACS-F1-047 module-level helpers for the job-backed bridge path ---


def _patch_terminal_state(
    job_manager,
    job_id: str,
    *,
    generated_count: int,
    failed_count: int,
    content_piece_ids: tuple[str, ...],
    message: str,
) -> None:
    """Record the per-piece outcome on a job's ``JobState``.

    Called by the per-piece loop right BEFORE the function returns
    (so the job is still ``RUNNING``). Uses the manager's own lock
    (same as ``_finish``) so the swap is atomic with the terminal
    transition. The replacement uses ``dataclasses.replace`` so the
    ``JobState`` stays frozen.
    """
    with job_manager._lock:  # type: ignore[attr-defined]
        state = job_manager._jobs.get(job_id)  # type: ignore[attr-defined]
        if state is None:
            return
        from dataclasses import replace as _dc_replace
        job_manager._jobs[job_id] = _dc_replace(  # type: ignore[attr-defined]
            state,
            generated_count=generated_count,
            failed_count=failed_count,
            content_piece_ids=content_piece_ids,
            message=message,
        )


__all__ = ["CampaignBridgeApi"]
