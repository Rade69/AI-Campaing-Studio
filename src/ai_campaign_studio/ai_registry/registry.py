"""Data-driven AI provider registry + in-memory model registry (P0.14).

Loads provider definitions from ``resources/ai_providers/*.yaml``, validates
the schema and cross-file invariants (unique provider codes), and keeps an
in-memory model registry with manual registration, capability filtering and
duplicate detection.

The registry never performs network calls, never touches a provider SDK and
never stores secrets (D-AI-2/D-AI-3).
"""

from __future__ import annotations

from pathlib import Path

import yaml  # type: ignore[import-untyped]
from pydantic import ValidationError

from ai_campaign_studio.ai_registry.model_profiles import (
    ModelCapability,
    ModelProfile,
)
from ai_campaign_studio.ai_registry.provider_models import AIProviderDefinition
from ai_campaign_studio.domain.common.errors import RegistryError
from ai_campaign_studio.ports.ai_registry import (
    AIProviderRegistryPort,
    ModelRegistryPort,
)


class AIProviderRegistry(AIProviderRegistryPort, ModelRegistryPort):
    """Parsed, validated and cached AI provider/model registry."""

    def __init__(self, providers_dir: Path) -> None:
        self._providers_dir = providers_dir
        self._providers: dict[str, AIProviderDefinition] = {}
        self._models: dict[tuple[str, str], ModelProfile] = {}
        self._loaded = False

    @classmethod
    def from_bundled_resources(cls) -> AIProviderRegistry:
        """Point the registry at the bundled ``resources/ai_providers`` folder."""
        return cls(
            Path(__file__).resolve().parents[3] / "resources" / "ai_providers"
        )

    # --- provider definitions ---

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self._load()

    def _load(self) -> None:
        providers: dict[str, AIProviderDefinition] = {}
        for path in sorted(self._providers_dir.glob("*.yaml")):
            raw = self._read_yaml(path)
            provider = self._build_provider(raw, path)
            if provider.provider_code in providers:
                raise RegistryError(
                    f"duplicate provider code: {provider.provider_code}"
                )
            providers[provider.provider_code] = provider
        self._providers = providers
        self._loaded = True

    def list_providers(self) -> list[AIProviderDefinition]:
        self._ensure_loaded()
        return [p for p in self._providers.values() if p.enabled]

    def get_provider(self, provider_code: str) -> AIProviderDefinition:
        self._ensure_loaded()
        key = provider_code.strip().upper()
        provider = self._providers.get(key)
        if provider is None:
            raise RegistryError(f"unknown provider: {key}")
        return provider

    # --- model registry ---

    def list_models(self, provider_code: str | None = None) -> list[ModelProfile]:
        self._ensure_loaded()
        models = [m for m in self._models.values() if m.enabled]
        if provider_code is not None:
            key = provider_code.strip().upper()
            models = [m for m in models if m.provider_code == key]
        return models

    def get_model(self, provider_code: str, model_id: str) -> ModelProfile:
        self._ensure_loaded()
        key = (provider_code.strip().upper(), model_id)
        model = self._models.get(key)
        if model is None:
            raise RegistryError(f"unknown model: {provider_code}/{model_id}")
        return model

    def register_manual_model(self, model: ModelProfile) -> None:
        self._ensure_loaded()
        self.get_provider(model.provider_code)  # raises RegistryError if unknown
        self._register(model)

    def register_discovered_models(
        self, provider_code: str, models: list[ModelProfile]
    ) -> None:
        self._ensure_loaded()
        key = provider_code.strip().upper()
        self.get_provider(key)  # raises RegistryError if unknown provider
        for model in models:
            if model.provider_code != key:
                raise RegistryError(
                    f"model provider_code {model.provider_code!r} does not match "
                    f"provider {key!r}"
                )
            self._register(model)

    def resolve_default_text_model(
        self, provider_code: str | None = None
    ) -> ModelProfile:
        self._ensure_loaded()
        models = [
            m
            for m in self._models.values()
            if m.enabled and ModelCapability.TEXT_GENERATION in m.capabilities
        ]
        if provider_code is not None:
            key = provider_code.strip().upper()
            models = [m for m in models if m.provider_code == key]
        if not models:
            raise RegistryError("no default text model available")
        return models[0]

    def supports(
        self, capability: ModelCapability, provider_code: str | None = None
    ) -> bool:
        self._ensure_loaded()
        key = provider_code.strip().upper() if provider_code is not None else None
        for model in self._models.values():
            if not model.enabled:
                continue
            if key is not None and model.provider_code != key:
                continue
            if capability in model.capabilities:
                return True
        return False

    def _register(self, model: ModelProfile) -> None:
        key = (model.provider_code, model.model_id)
        if key in self._models:
            raise RegistryError(
                f"duplicate model: {model.provider_code}/{model.model_id}"
            )
        self._models[key] = model

    # --- loading helpers ---

    @staticmethod
    def _read_yaml(path: Path) -> dict:
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise RegistryError(f"malformed YAML in {path.name}: {exc}") from exc
        if not isinstance(raw, dict):
            raise RegistryError(f"provider file must be a mapping: {path.name}")
        return raw

    @staticmethod
    def _build_provider(raw: dict, path: Path) -> AIProviderDefinition:
        try:
            return AIProviderDefinition.model_validate(raw)
        except ValidationError as exc:
            raise RegistryError(
                f"invalid provider schema in {path.name}: {exc}"
            ) from exc
