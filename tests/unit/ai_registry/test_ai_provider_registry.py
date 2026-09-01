"""Unit tests for the AI provider/model registry."""

import pytest
import yaml  # type: ignore[import-untyped]

from ai_campaign_studio.ai_registry.model_profiles import (
    ModelCapability,
    ModelProfile,
)
from ai_campaign_studio.ai_registry.registry import AIProviderRegistry
from ai_campaign_studio.domain.common.errors import RegistryError

PROVIDER_CODES = (
    "OPENAI",
    "ANTHROPIC",
    "GOOGLE",
    "DEEPSEEK",
    "OPENROUTER",
    "OPENAI_COMPATIBLE",
)


def _write_provider(tmp_path, code: str = "OPENAI", **overrides) -> None:
    data = {
        "provider_code": code,
        "display_name": "Test Provider",
        "adapter_type": "test",
        "requires_api_key": True,
        "supports_model_discovery": False,
        "base_url_mode": "NONE",
        "enabled": True,
    }
    data.update(overrides)
    (tmp_path / f"{code.lower()}.yaml").write_text(
        yaml.safe_dump(data, sort_keys=False), encoding="utf-8"
    )


def _model(model_id: str, *capabilities: ModelCapability) -> ModelProfile:
    return ModelProfile(
        provider_code="OPENAI",
        model_id=model_id,
        display_name=model_id,
        capabilities=tuple(capabilities),
    )


def test_providers_load_with_unique_codes(tmp_path) -> None:
    for code in PROVIDER_CODES:
        _write_provider(tmp_path, code)
    registry = AIProviderRegistry(tmp_path)

    providers = registry.list_providers()
    codes = [p.provider_code for p in providers]

    assert len(providers) == 6
    assert len(codes) == len(set(codes)) == 6


def test_duplicate_provider_code_rejected(tmp_path) -> None:
    _write_provider(tmp_path, "OPENAI")
    (tmp_path / "openai_copy.yaml").write_text(
        "provider_code: OPENAI\n"
        "display_name: OpenAI Copy\n"
        "adapter_type: openai\n"
        "requires_api_key: true\n"
        "supports_model_discovery: false\n"
        "base_url_mode: FIXED\n"
        "enabled: true\n",
        encoding="utf-8",
    )
    registry = AIProviderRegistry(tmp_path)

    with pytest.raises(RegistryError):
        registry.list_providers()


def test_invalid_base_url_mode_rejected(tmp_path) -> None:
    _write_provider(tmp_path, "OPENAI", base_url_mode="INVALID")
    registry = AIProviderRegistry(tmp_path)

    with pytest.raises(RegistryError):
        registry.list_providers()


def test_unknown_provider_raises(tmp_path) -> None:
    _write_provider(tmp_path, "OPENAI")
    registry = AIProviderRegistry(tmp_path)

    with pytest.raises(RegistryError):
        registry.get_provider("UNKNOWN")


def test_manual_model_registration(tmp_path) -> None:
    _write_provider(tmp_path, "OPENAI")
    registry = AIProviderRegistry(tmp_path)

    registry.register_manual_model(_model("gpt-test", ModelCapability.TEXT_GENERATION))

    assert registry.get_model("OPENAI", "gpt-test").model_id == "gpt-test"
    assert [m.model_id for m in registry.list_models("OPENAI")] == ["gpt-test"]


def test_duplicate_model_rejected(tmp_path) -> None:
    _write_provider(tmp_path, "OPENAI")
    registry = AIProviderRegistry(tmp_path)

    registry.register_manual_model(_model("gpt-test"))
    with pytest.raises(RegistryError):
        registry.register_manual_model(_model("gpt-test"))


def test_capability_filter(tmp_path) -> None:
    _write_provider(tmp_path, "OPENAI")
    registry = AIProviderRegistry(tmp_path)

    registry.register_manual_model(_model("text", ModelCapability.TEXT_GENERATION))
    registry.register_manual_model(_model("vision", ModelCapability.VISION))

    assert registry.supports(ModelCapability.TEXT_GENERATION) is True
    assert registry.supports(ModelCapability.VISION) is True
    assert registry.supports(ModelCapability.TOOL_USE) is False
    assert registry.supports(ModelCapability.VISION, provider_code="OPENAI") is True
    assert registry.supports(ModelCapability.VISION, provider_code="ANTHROPIC") is False


def test_resolve_default_text_model(tmp_path) -> None:
    _write_provider(tmp_path, "OPENAI")
    registry = AIProviderRegistry(tmp_path)

    registry.register_manual_model(_model("text", ModelCapability.TEXT_GENERATION))
    registry.register_manual_model(_model("vision", ModelCapability.VISION))

    assert registry.resolve_default_text_model().model_id == "text"
    with pytest.raises(RegistryError):
        registry.resolve_default_text_model(provider_code="ANTHROPIC")


def test_register_discovered_models_rejects_provider_mismatch(tmp_path) -> None:
    _write_provider(tmp_path, "OPENAI")
    registry = AIProviderRegistry(tmp_path)

    mismatched = ModelProfile(
        provider_code="ANTHROPIC",
        model_id="claude-test",
        display_name="Claude Test",
    )
    with pytest.raises(RegistryError):
        registry.register_discovered_models("OPENAI", [mismatched])


def test_register_manual_model_unknown_provider_rejected(tmp_path) -> None:
    _write_provider(tmp_path, "OPENAI")
    registry = AIProviderRegistry(tmp_path)

    model = ModelProfile(provider_code="UNKNOWN", model_id="m", display_name="M")
    with pytest.raises(RegistryError):
        registry.register_manual_model(model)


def test_register_discovered_models_unknown_provider_rejected(tmp_path) -> None:
    _write_provider(tmp_path, "OPENAI")
    registry = AIProviderRegistry(tmp_path)

    model = ModelProfile(provider_code="UNKNOWN", model_id="m", display_name="M")
    with pytest.raises(RegistryError):
        registry.register_discovered_models("UNKNOWN", [model])
