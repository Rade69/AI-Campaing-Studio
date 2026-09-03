"""Unit tests for provider config / model selection ports (A8, dio 1)."""

from typing import Protocol

from ai_campaign_studio.ports import provider_config

_ALL_PORTS = [
    "ProviderConfigRepositoryPort",
    "ModelSelectionRepositoryPort",
]


def test_both_ports_are_defined() -> None:
    for name in _ALL_PORTS:
        cls = getattr(provider_config, name)
        assert issubclass(cls, Protocol)


def test_ports_are_runtime_checkable() -> None:
    class _FakeProviderConfigRepository:
        def save_provider_config(self, config) -> None:
            del config

        def get_provider_config(self, provider_code):
            del provider_code
            return None

        def list_provider_configs(self):
            return ()

    class _FakeModelSelectionRepository:
        def save_model_selection(self, selection) -> None:
            del selection

        def get_model_selection(self, purpose):
            del purpose
            return None

    assert isinstance(
        _FakeProviderConfigRepository(),
        provider_config.ProviderConfigRepositoryPort,
    )
    assert isinstance(
        _FakeModelSelectionRepository(),
        provider_config.ModelSelectionRepositoryPort,
    )
