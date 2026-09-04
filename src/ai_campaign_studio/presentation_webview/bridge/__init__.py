"""pywebview ``js_api`` bridge (ACS-GUI-005).

The first real GUI→backend wiring in the project. Exposes a narrow class
(``CampaignBridgeApi``) to the WebView2 JavaScript context via pywebview's
``js_api=`` argument. Per ``docs/PYWEBVIEW_SECURITY.md`` §3:

- Only a single public method is exposed (``create_campaign_and_generate_plan``).
- Every payload from JS is validated at the boundary (Pydantic schema on
  the inner ``CampaignBriefInput``; we do NOT trust JS types/values).
- The return ``dict`` is JSON-serializable, never contains API keys, tokens,
  SecretStore contents, file paths, or raw Python exception text.

The bridge is the ONLY component that knows how to translate the
form-shaped GUI input into the application-layer shape
(``CampaignBriefInput``). It is composition: it wires use-cases, repositories,
the AI provider factory, and a brand-seeding cache.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from ai_campaign_studio.application.brands.load_brand_fixture import LoadBrandFixture
from ai_campaign_studio.application.campaigns.create_campaign import CreateCampaign
from ai_campaign_studio.application.campaigns.generate_campaign_plan import (
    GenerateCampaignPlan,
)
from ai_campaign_studio.application.schemas.campaign_brief import CampaignBriefInput
from ai_campaign_studio.bootstrap import create_bootstrap
from ai_campaign_studio.config.paths import AppPaths
from ai_campaign_studio.domain.common.errors import EntityNotFound, InvariantViolation
from ai_campaign_studio.infrastructure.ai.provider_adapter_factory import (
    build_text_generation_adapter,
    pick_configured_provider,
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
from ai_campaign_studio.presentation.ui_models import CampaignPlanResultUiModel

_BRAND_SEED_FILE = "brand-seed.json"

# Stable error codes that flow back to JS. These are PART OF THE
# BRIDGE'S PUBLIC API — changing them is a breaking change for the
# frontend (app.js). Always map internal exceptions to one of these.
_ERROR_NO_PROVIDER = "NO_PROVIDER_CONFIGURED"
_ERROR_KEY_MISSING = "PROVIDER_KEY_MISSING"
_ERROR_VALIDATION = "VALIDATION_ERROR"
_ERROR_GENERATION = "GENERATION_FAILED"
_ERROR_INTERNAL = "INTERNAL_ERROR"


class CampaignBridgeApi:
    """Narrow pywebview ``js_api`` surface for the campaign workflow.

    Single public method for JS (``create_campaign_and_generate_plan``).
    Everything else is internal helper prefixed with ``_``.

    Lifetime: the bridge is constructed once in ``presentation_webview/
    __main__.py`` and passed to ``webview.create_window(..., js_api=self)``.
    It owns the full composition root for the click (use-cases,
    repositories, AI factory) — there is no per-call re-wire.
    """

    def __init__(self, *, paths: AppPaths | None = None) -> None:
        # Bootstrap is the single source of truth for settings, paths,
        # secret store, DB connection, and the registries. Construct it
        # once; reuse across the lifetime of the bridge.
        #
        # ``paths`` is an explicit seam for tests. Production code
        # passes nothing and ``create_bootstrap()`` builds the canonical
        # ``AppPaths`` (resolved via ``AppSettings`` -> env -> defaults).
        self._bootstrap = create_bootstrap(paths=paths)
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
                return self._err(_ERROR_GENERATION, str(exc))
            except Exception as exc:
                # AI/network/SDK errors land here. Per PYWEBVIEW_SECURITY
                # §3, do NOT leak the SDK exception verbatim — map to a
                # generic message and log the detail server-side.
                self._bootstrap.logger.exception(
                    "GenerateCampaignPlan failed (provider=%s, err=%s)",
                    provider_code, type(exc).__name__,
                )
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
        """Pick the highest-priority configured provider and pull its key.

        Returns ``(code, key)`` where either may be ``None``:
        - no provider configured at all -> ``(None, None)``
        - provider configured but key not in SecretStore -> ``(code, None)``

        Does not raise — the caller maps absence to error codes.
        """
        configs = list(self._provider_config_repo.list_provider_configs())
        configured_codes = [c.provider_code for c in configs if c.configured]
        code = pick_configured_provider(configured_codes)
        if code is None:
            return None, None
        config = next((c for c in configs if c.provider_code == code), None)
        if config is None or not config.credential_ref:
            return code, None
        try:
            api_key = self._bootstrap.secret_store.get_secret(config.credential_ref)
        except Exception:
            return code, None
        return code, (api_key or None)

    def _user_data_dir(self) -> Path:
        """Resolve the per-user data dir, matching the package convention.

        Kept in sync with the rest of the project by going through
        ``AppPaths.data_dir`` which already does the right thing.
        """
        return self._bootstrap.paths.data_dir

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


__all__ = ["CampaignBridgeApi"]
