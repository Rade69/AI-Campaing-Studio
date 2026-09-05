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
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ai_campaign_studio.application.ai_provider.configure_provider import (
    ConfigureProvider,
)
from ai_campaign_studio.application.brands.load_brand_fixture import LoadBrandFixture
from ai_campaign_studio.application.campaigns.create_campaign import CreateCampaign
from ai_campaign_studio.application.campaigns.generate_campaign_plan import (
    GenerateCampaignPlan,
)
from ai_campaign_studio.application.schemas.campaign_brief import CampaignBriefInput
from ai_campaign_studio.bootstrap import create_bootstrap
from ai_campaign_studio.config.paths import AppPaths
from ai_campaign_studio.config.settings import AppSettings
from ai_campaign_studio.domain.common.errors import (
    EntityNotFound,
    InvariantViolation,
    RegistryError,
)
from ai_campaign_studio.infrastructure.ai.provider_adapter_factory import (
    _PROVIDER_PRIORITY,
    build_text_generation_adapter,
)
from ai_campaign_studio.infrastructure.database.repositories import (
    SqliteBrandRepository,
    SqliteCampaignRepository,
    SqliteFactRepository,
    SqliteProviderConfigRepository,
)
from ai_campaign_studio.infrastructure.database.unit_of_work import SqliteUnitOfWork
from ai_campaign_studio.infrastructure.prompts.yaml_prompt_repository import (
    YamlPromptRepository,
)
from ai_campaign_studio.presentation.ui_models import (
    CampaignPlanResultUiModel,
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


class CampaignBridgeApi:
    """Narrow pywebview ``js_api`` surface for the campaign workflow.

    Single public method for JS (``create_campaign_and_generate_plan``).
    Everything else is internal helper prefixed with ``_``.

    Lifetime: the bridge is constructed once in ``presentation_webview/
    __main__.py`` and passed to ``webview.create_window(..., js_api=self)``.
    It owns the full composition root for the click (use-cases,
    repositories, AI factory) — there is no per-call re-wire.
    """

    def __init__(
        self,
        *,
        paths: AppPaths | None = None,
        settings: AppSettings | None = None,
    ) -> None:
        # Bootstrap is the single source of truth for settings, paths,
        # secret store, DB connection, and the registries. Construct it
        # once; reuse across the lifetime of the bridge.
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
        conn = self._bootstrap.database_connection
        self._brand_repo = SqliteBrandRepository(conn)
        self._fact_repo = SqliteFactRepository(conn)
        self._campaign_repo = SqliteCampaignRepository(conn)
        self._provider_config_repo = SqliteProviderConfigRepository(conn)
        self._uow = SqliteUnitOfWork(conn)
        # YamlPromptRepository.from_bundled_resources() reads from the
        # repo's ``resources/prompts/`` dir; this is the same source the
        # integration test uses, so prompts are identical between
        # tests and the live app.
        self._prompt_repo = YamlPromptRepository.from_bundled_resources()
        self._brand_fixture_path = (
            self._bootstrap.paths.resources_dir / "fixtures" / "brightsmile.json"
        )

    # --- js_api surface (exactly ONE public method) ---

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

    # --- helpers (internal, not exposed to JS) ---

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


__all__ = ["CampaignBridgeApi"]
