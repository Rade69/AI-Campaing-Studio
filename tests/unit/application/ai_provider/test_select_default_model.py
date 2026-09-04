"""Unit tests for SelectDefaultModel (A8, dio 2)."""

from __future__ import annotations

import pytest

from ai_campaign_studio.ai_registry.model_profiles import ModelProfile
from ai_campaign_studio.application.ai_provider.select_default_model import (
    SelectDefaultModel,
)
from ai_campaign_studio.domain.common.errors import RegistryError
from ai_campaign_studio.ports.provider_config import ModelSelection


class _FakeModelRegistry:
    def __init__(self, model: ModelProfile | None) -> None:
        self._model = model

    def get_model(self, provider_code: str, model_id: str) -> ModelProfile:
        if self._model is None:
            raise RegistryError(f"unknown model: {provider_code}/{model_id}")
        return self._model

    def list_models(self, provider_code: str | None = None) -> list[ModelProfile]:
        del provider_code
        return []


class _FakeModelSelectionRepo:
    def __init__(self) -> None:
        self.saved: ModelSelection | None = None

    def save_model_selection(self, selection: ModelSelection) -> None:
        self.saved = selection

    def get_model_selection(self, purpose: str) -> ModelSelection | None:
        del purpose
        return None


def _model() -> ModelProfile:
    return ModelProfile(
        provider_code="OPENAI",
        model_id="gpt-4o",
        display_name="GPT-4o",
    )


def test_select_persists_default_text_model() -> None:
    registry = _FakeModelRegistry(_model())
    repo = _FakeModelSelectionRepo()
    use_case = SelectDefaultModel(registry, repo)

    result = use_case.execute("OPENAI", "gpt-4o")

    assert result.purpose == "default_text_model"
    assert result.provider_code == "OPENAI"
    assert result.model_id == "gpt-4o"
    assert repo.saved == result


def test_unknown_model_raises_and_nothing_persisted() -> None:
    registry = _FakeModelRegistry(None)
    repo = _FakeModelSelectionRepo()
    use_case = SelectDefaultModel(registry, repo)

    with pytest.raises(RegistryError):
        use_case.execute("OPENAI", "unknown-model")

    assert repo.saved is None
