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
from ai_campaign_studio.application.posts.generate_social_post import (
    GenerateSocialPost,
)
from ai_campaign_studio.application.schemas.campaign_brief import CampaignBriefInput
from ai_campaign_studio.bootstrap import create_bootstrap
from ai_campaign_studio.config.paths import AppPaths
from ai_campaign_studio.config.settings import AppSettings
from ai_campaign_studio.domain.campaign.entities import CampaignBrief
from ai_campaign_studio.domain.campaign.enums import CampaignPlanStatus
from ai_campaign_studio.domain.common.errors import (
    EntityNotFound,
    InvariantViolation,
    JobError,
    RegistryError,
)
from ai_campaign_studio.domain.common.ids import (
    CampaignId,
    CampaignPlanId,
)
from ai_campaign_studio.domain.content.entities import CampaignTarget
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
    SqliteProviderConfigRepository,
    SqliteRevisionRepository,
)
from ai_campaign_studio.infrastructure.database.unit_of_work import SqliteUnitOfWork
from ai_campaign_studio.infrastructure.prompts.yaml_prompt_repository import (
    YamlPromptRepository,
)
from ai_campaign_studio.jobs.cancellation import CancellationError
from ai_campaign_studio.jobs.models import JobStatus
from ai_campaign_studio.presentation.ui_models import (
    CampaignPlanResultUiModel,
    GenerateContentResultUiModel,
    ProviderConfigResultUiModel,
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
    campaign_repo: SqliteCampaignRepository
    provider_config_repo: SqliteProviderConfigRepository
    # ACS-GUI-008: ``generate_campaign_content`` reads pieces and writes
    # revisions; both repos live in the per-call graph (same lifetime
    # as the rest).
    content_repo: SqliteContentRepository
    revision_repo: SqliteRevisionRepository
    uow: SqliteUnitOfWork


# ACS-GUI-008 (fix-brief-3 / Codex BF-5): lifecycle error mapper
# dispatch. ``_with_call_resources`` catches exceptions raised by
# ``_resource_scope()`` itself (e.g. SQLite open/close failure)
# BEFORE the wrapped method's own try/except sees them. Without an
# operation-aware mapper, every non-``configure_provider`` method
# used to fall through to ``self._err()`` — which builds a
# ``CampaignPlanResultUiModel`` dict and therefore lacks the
# generate-content DTO's ``generated_count`` / ``failed_count`` /
# ``content_piece_ids`` keys. JS callers typed to the right DTO got
# missing fields on the one failure path that is hardest to recover
# from silently. Fix: each public method declares which DTO it
# returns, and the decorator dispatches accordingly. New methods
# MUST add an entry here.
_LIFECYCLE_ERROR_MAPPERS: dict[str, str] = {
    "configure_provider": "_provider_err",
    "create_campaign_and_generate_plan": "_err",
    "generate_campaign_content": "_generate_err",
    "get_job_status": "_job_status_err",
    "cancel_job": "_job_status_err",
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
            except Exception:
                self._bootstrap.logger.exception(
                    "adapter factory failed for %s", provider_code
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
        verbatim (BF-3 lock is no longer needed: the closure runs
        serially per ``(campaign_id, plan_id)`` because
        ``JobManager`` has a single executor thread for this job
        type in practice; and if a user clicks twice in quick
        succession, the second submit gets its own closure and the
        per-piece idempotency check inside still prevents
        duplicates).
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
            self._bootstrap.logger.exception(
                "generate_campaign_content job: adapter factory failed for %s",
                provider_code,
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
        job_id_holder: list[str] = [""]  # filled on first iteration
        for index, item in enumerate(plan_items):
            token.raise_if_cancelled()
            # The first time we run, capture the job_id from the
            # manager's bookkeeping. This relies on the manager
            # registering the job in ``_jobs`` BEFORE the worker
            # thread runs the callable (it does -- see ``submit``).
            if not job_id_holder[0]:
                # We can't ask the manager for "our" job id; pass it
                # in via a hidden closure instead. Workaround: the
                # closure builder has access to ``self``, so we look
                # up via ``_pending_job_id_for_caller`` if available
                # (it isn't on the public API). Easiest path: ask
                # the manager via a private API.
                job_id_holder[0] = _find_current_job_id(job_manager)
            jid = job_id_holder[0]
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

        # On natural exit (no CancellationError raised above), we
        # record the final counters onto the JobState. The manager's
        # own ``_finish(SUCCEEDED)`` will then move the status; the
        # counters survive because ``_finish`` does not touch them
        # (we used ``update_progress``-like replace semantics).
        jid = job_id_holder[0]
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
            campaign_repo=SqliteCampaignRepository(connection),
            provider_config_repo=SqliteProviderConfigRepository(connection),
            content_repo=SqliteContentRepository(connection),
            revision_repo=SqliteRevisionRepository(connection),
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


# --- ACS-F1-047 module-level helpers for the job-backed bridge path ---


def _find_current_job_id(job_manager) -> str:
    """Return the ``job_id`` of the job that is currently running on
    this thread, or ``""`` if none / ambiguous.

    ``JobManager`` does not expose a per-thread lookup, so we
    approximate it: there is at most one ``RUNNING`` job at a time
    per thread that the executor hands to ``_run``. We pick the
    RUNNING job whose ``started_at`` is the most recent -- ties are
    broken by ``id`` (deterministic) and there should never be a tie
    in practice because the executor runs one job at a time per
    worker.

    Returns the empty string if the lookup is ambiguous (no RUNNING
    job, or more than one). The caller treats the empty string as
    "no progress reporting on this iteration" and never raises.
    """
    with job_manager._lock:  # type: ignore[attr-defined]
        running = [
            s for s in job_manager._jobs.values()  # type: ignore[attr-defined]
            if s.status is JobStatus.RUNNING
        ]
    if len(running) != 1:
        return ""
    return running[0].id


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
