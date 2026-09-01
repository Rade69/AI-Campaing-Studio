"""Framework-neutral presentation facade contract (P0.21).

Owns the ``PresentationFacade`` protocol that the future PySide6/pywebview
frontends implement on top of the composition root. No Qt/Flask/JavaScript
import here — direct or transitive.
"""

from __future__ import annotations

from typing import Any, Protocol

from ai_campaign_studio.localization.enums import AppLocale
from ai_campaign_studio.presentation.state import AppRuntimeState
from ai_campaign_studio.presentation.ui_models import ProviderStatusUiModel


class PresentationFacade(Protocol):
    """Foundation surface the presentation framework implements.

    A concrete facade wires these methods to the composition root
    (``bootstrap``) without the UI framework leaking into the foundation
    modules. Campaign UI actions are intentionally absent in P0.
    """

    def set_app_locale(self, locale: AppLocale) -> None: ...

    def get_app_state(self) -> AppRuntimeState: ...

    def list_ai_providers(self) -> list[ProviderStatusUiModel]: ...

    def get_provider_status(self, provider_code: str) -> ProviderStatusUiModel: ...

    def run_health_check(self) -> dict[str, Any]: ...

    def cancel_job(self, job_id: str) -> None: ...
