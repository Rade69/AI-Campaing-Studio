"""Framework-neutral presentation facade contract (P0.21).

Owns the ``PresentationFacade`` protocol that the future PySide6/pywebview
frontends implement on top of the composition root. No Qt/Flask/JavaScript
import here — direct or transitive.
"""

from __future__ import annotations

from typing import Any, Protocol

from ai_campaign_studio.localization.enums import AppLocale
from ai_campaign_studio.presentation.state import AppRuntimeState
from ai_campaign_studio.presentation.ui_models import (
    CampaignPlanResultUiModel,
    ProviderConfigResultUiModel,
    ProviderStatusUiModel,
)


class PresentationFacade(Protocol):
    """Foundation surface the presentation framework implements.

    A concrete facade wires these methods to the composition root
    (``bootstrap``) without the UI framework leaking into the foundation
    modules.

    As of ACS-GUI-005, one campaign-related method is now part of the
    foundation surface: ``create_campaign_and_generate_plan``. It is
    documented here as part of the contract but is NOT a hard
    requirement for every concrete facade to implement (Protocol is
    structural in Python — see ACS-GUI-005 contract §"Ne implementirati
    cijeli ``PresentationFacade`` Protocol"). pywebview's actual
    ``js_api`` bridge is a narrow class that exposes only this one
    method, not the full ``PresentationFacade`` set.
    """

    def set_app_locale(self, locale: AppLocale) -> None: ...

    def get_app_state(self) -> AppRuntimeState: ...

    def list_ai_providers(self) -> list[ProviderStatusUiModel]: ...

    def get_provider_status(self, provider_code: str) -> ProviderStatusUiModel: ...

    def run_health_check(self) -> dict[str, Any]: ...

    def cancel_job(self, job_id: str) -> None: ...

    def create_campaign_and_generate_plan(
        self, raw_brief: dict[str, Any]
    ) -> CampaignPlanResultUiModel: ...

    def configure_provider(
        self, raw_payload: dict[str, Any]
    ) -> ProviderConfigResultUiModel: ...
