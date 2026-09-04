"""SelectDefaultModel use-case (A8, dio 2).

Owns persisting the chosen default text-generation model for a provider. Only
the ``"default_text_model"`` purpose is supported (AI-R8); other purposes are
not built here. The model id is validated against the registry first, so an
unknown model propagates ``RegistryError`` instead of silently persisting an
arbitrary id.
"""

from __future__ import annotations

from ai_campaign_studio.domain.common.timestamps import utc_now
from ai_campaign_studio.ports.ai_registry import ModelRegistryPort
from ai_campaign_studio.ports.provider_config import (
    ModelSelection,
    ModelSelectionRepositoryPort,
)

_DEFAULT_TEXT_MODEL_PURPOSE = "default_text_model"


class SelectDefaultModel:
    """Persist the default text-generation model selection for a provider."""

    def __init__(
        self,
        model_registry: ModelRegistryPort,
        model_selection_repo: ModelSelectionRepositoryPort,
    ) -> None:
        self._model_registry = model_registry
        self._model_selection_repo = model_selection_repo

    def execute(self, provider_code: str, model_id: str) -> ModelSelection:
        self._model_registry.get_model(provider_code, model_id)

        selection = ModelSelection(
            purpose=_DEFAULT_TEXT_MODEL_PURPOSE,
            provider_code=provider_code.strip().upper(),
            model_id=model_id,
            updated_at=utc_now(),
        )
        self._model_selection_repo.save_model_selection(selection)
        return selection
