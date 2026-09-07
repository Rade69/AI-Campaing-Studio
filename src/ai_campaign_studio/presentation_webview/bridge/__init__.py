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
}
# Per-method fallback message used ONLY when the resource-lifecycle
# fails (we never want to surface the underlying exception text;
# provider secrets could in theory end up in a downstream
# adapter's exception message).
_LIFECYCLE_ERROR_MESSAGES: dict[str, str] = {
    "configure_provider": "Konfiguracija provajdera nije uspjela (interna greška).",
    "create_campaign_and_generate_plan": "Interna greška — pogledajte log aplikacije.",
    "generate_campaign_content": "Generisanje sadržaja nije uspjelo (interna greška).",
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
        """End-to-end: approve plan (idempotent), generate every content piece.

        NEW: bulk generation for the Studio sadržaja screen
        (ACS-GUI-008). Different from ``create_campaign_and_generate_plan``
        in two important ways:

        1. **Partial success is allowed** — one piece failing (network,
           quota, bad-luck timeout) MUST NOT abort the rest of the loop.
           The user sees ``generated_count`` / ``failed_count`` and can
           click "Generiši" again to retry the failed items.
        2. **Idempotent on the content side** — if a piece for a
           ``CampaignItem`` already exists, the bridge MUST NOT call
           ``GenerateSocialPost`` again (avoids duplicate posts in the
           user's pipeline). ``ok=True`` is returned even when
           ``generated_count == 0`` (everything was already done).

        The method never raises into JS: every error path returns a
        result ``dict`` with ``ok=False`` and a stable ``error_code``.
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

        # -- 2. The rest of the method runs under a per-pair lock.
        #    BF-3 (fix-brief-2): two pywebview worker threads calling
        #    ``generate_campaign_content`` for the SAME
        #    ``(campaign_id, plan_id)`` MUST be serialized -- the
        #    "read existing pieces -> generate -> save" sequence is
        #    otherwise a TOCTOU race that duplicates content. The lock
        #    is acquired AFTER boundary validation (so a malformed
        #    payload returns cheaply without holding the lock for the
        #    caller) and BEFORE any DB read (so the lookup of the
        #    plan that we are about to approve+generate is consistent
        #    with the save).
        with self._lock_for(str(campaign_id), str(plan_id)):
            return self._generate_campaign_content_locked(
                campaign_id, plan_id
            )

    def _generate_campaign_content_locked(
        self,
        campaign_id: CampaignId,
        plan_id: CampaignPlanId,
    ) -> dict:
        """Inner body of ``generate_campaign_content``; runs under the
        per-``(campaign_id, plan_id)`` lock (BF-3). Split out so the
        lock scope is small and explicit, and the locked region can be
        reasoned about (and tested) independently of the JS-facing
        boundary-validation prologue.
        """
        # -- 2. Campaign + brief + plan + targets (all-or-nothing up
        #    to this point -- still inside the per-method try/except
        #    so a domain error here maps to VALIDATION_ERROR).
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
            # Plan lookup: ACS-GUI-008 review feedback. The plan_id
            # is REQUIRED in the payload (validated above); the bridge
            # uses the existing ``CampaignRepositoryPort.get_plan``
            # (already in the allowed path of the project) instead of
            # raw SQL. This keeps the bridge inside the
            # ``ports -> infrastructure`` boundary AND lets the JS
            # caller tell the bridge which plan to operate on (the
            # same plan it just created two clicks ago).
            plan = self._campaign_repo.get_plan(plan_id)
            if plan is None:
                return self._generate_err(
                    _ERROR_VALIDATION,
                    f"Plan {plan_id} ne postoji. "
                    "Ponovo pokreni 'Sačuvaj i napravi plan'.",
                )
            if plan.campaign_id != campaign_id:
                # The plan does not belong to this campaign -- the JS
                # caller mixed up ids (or someone tampered with the
                # payload). Same defensive pattern as
                # ``ExportCampaign._validate_plan_campaign_match``.
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

        # -- 3. Approve plan (idempotent). The plan is the SAME
        #    object we already loaded in step 2, so a quick status
        #    check skips the ``ApproveCampaignPlan`` call when the
        #    plan is already APPROVED — that use-case throws
        #    ``InvariantViolation`` for non-DRAFT plans, which would
        #    needlessly fail the click in the "approve once, generate
        #    many" case (a partial-success click that finished
        #    approving but still had pieces to render). We reuse the
        #    already-loaded plan as-is.
        if plan.status is CampaignPlanStatus.DRAFT:
            try:
                approved = ApproveCampaignPlan(
                    campaign_repo=self._campaign_repo,
                    unit_of_work=self._uow,
                ).execute(plan_id)
            except (EntityNotFound, InvariantViolation) as exc:
                # Domain-level failure: the plan is in an unexpected
                # state (race with another writer, or a non-DRAFT,
                # non-APPROVED status like REJECTED). Either way, the
                # user-facing message is the domain detail.
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
            # Already APPROVED (or any other non-DRAFT state — we are
            # tolerant on the read path, strict on the write path).
            approved = plan

        # -- 3b. BF-4 (fix-brief-2): explicit rejection of plans in a
        #    non-APPROVED state (today: ``SUPERSEDED``, replaced by a
        #    newer version via the future ``EditCampaignPlan`` flow).
        #    Without this, a ``SUPERSEDED`` plan falls through the
        #    ``else: approved = plan`` branch and the bridge calls
        #    ``GenerateSocialPost`` for a plan the user is no longer
        #    expected to publish -- wasting AI calls, and creating
        #    content_pieces that point at a "tombstoned" plan. We
        #    reject up-front with VALIDATION_ERROR (the input is
        #    semantically wrong: the plan id is valid but not the
        #    active one) and 0 AI calls are made.
        if approved.status is not CampaignPlanStatus.APPROVED:
            return self._generate_err(
                _ERROR_VALIDATION,
                f"Plan {plan_id} je u stanju {approved.status.value}, "
                "očekivano APPROVED. Napravi novi plan.",
            )

        # -- 4. Provider resolution (reused helper).
        try:
            provider_code, api_key = self._resolve_provider()
        except Exception as exc:
            self._bootstrap.logger.exception("provider resolution failed")
            return self._generate_err(
                _ERROR_INTERNAL,
                f"Greška pri čitanju provajdera: {type(exc).__name__}.",
            )
        if provider_code is None:
            return self._generate_err(
                _ERROR_NO_PROVIDER,
                "Nijedan AI provajder nije podešen.",
            )
        if not api_key:
            return self._generate_err(
                _ERROR_KEY_MISSING,
                f"Provajder {provider_code} je konfigurisan ali API ključ "
                "nije dostupan u SecretStore-u.",
            )

        try:
            adapter = build_text_generation_adapter(provider_code, api_key)
        except Exception:
            self._bootstrap.logger.exception(
                "adapter factory failed for %s", provider_code
            )
            return self._generate_err(
                _ERROR_KEY_MISSING,
                f"Ne mogu instancirati adapter za {provider_code}.",
            )

        # -- 5. Build the generator (per-bridge construction, not a
        #    constructor dep on the bridge, per the same "compose use
        #    cases in the bridge" pattern as
        #    ``create_campaign_and_generate_plan``).
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

        # -- 6. The per-piece loop. Idempotency: skip items that
        #    already have a ``ContentPiece``. Partial success:
        #    ``except Exception`` catches one piece's failure and
        #    CONTINUES with the next item (the contract explicitly
        #    differentiates this from the all-or-nothing
        #    ``create_campaign_and_generate_plan``).
        existing_pieces = self._content_repo.list_campaign_content(
            campaign_id
        )
        existing_item_ids = {
            str(p.campaign_item_id) for p in existing_pieces
        }

        generated_ids: list[str] = []
        failed_count = 0
        first_error: str | None = None
        for index, item in enumerate(approved.items):
            # Idempotency: this item already has a piece; skip.
            if str(item.id) in existing_item_ids:
                continue
            # Round-robin target assignment (same shape as
            # ``run_system_b.py:86``).
            target = _target_for_item(index, targets)
            if target is None:
                # No targets in the brief at all — the campaign was
                # created without any platform. This is a user
                # error, not an AI failure. Mark as failed and
                # continue.
                failed_count += 1
                if first_error is None:
                    first_error = (
                        "Nema definisanih targeta u briefu — "
                        "objave ne mogu biti generisane."
                    )
                continue
            try:
                piece = generator.execute(
                    campaign.id, approved.id, item.id, target
                )
                generated_ids.append(str(piece.id))
            except Exception as exc:
                # Per contract: a single piece's failure MUST NOT
                # abort the rest of the loop. We collect the first
                # error message for the result, log the rest, and
                # continue. ``str(exc)`` may contain a provider SDK
                # message that the contract is OK to surface here
                # (no API key is in it; the secret is in the
                # ``get_secret`` call, never in the adapter's
                # exception text).
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

        # -- 7. Build the result. ``ok=True`` whenever AT LEAST ONE
        #    piece landed (or zero were needed because everything was
        #    already generated). ``ok=False`` only when zero pieces
        #    landed and there were piece-slots that needed work
        #    (i.e. genuine failure).
        generated_count = len(generated_ids)
        if generated_count == 0 and failed_count == 0:
            # Everything was already generated (idempotent re-click).
            # Return ``ok=True`` with zero counts so the JS shows a
            # "Sadržaj je već generisan" toast.
            ok = True
        elif generated_count == 0:
            ok = False
        else:
            ok = True

        return asdict(
            GenerateContentResultUiModel(
                ok=ok,
                campaign_id=str(campaign.id),
                generated_count=generated_count,
                failed_count=failed_count,
                content_piece_ids=tuple(generated_ids),
                error_code=None if ok else _ERROR_GENERATION,
                error_message=(
                    None if ok
                    else (first_error or "Generisanje sadržaja nije uspjelo.")
                ),
            )
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

        Same shape logic as ``_provider_err``: a dedicated helper
        because ``_err()`` is hard-coded to
        ``CampaignPlanResultUiModel`` and the generate-content DTO
        has different fields (``generated_count`` /
        ``failed_count`` / ``content_piece_ids``).
        """
        return asdict(
            GenerateContentResultUiModel(
                ok=False,
                campaign_id=None,
                generated_count=0,
                failed_count=0,
                content_piece_ids=(),
                error_code=code,
                error_message=message,
            )
        )


__all__ = ["CampaignBridgeApi"]
