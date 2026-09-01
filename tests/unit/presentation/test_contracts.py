"""Tests for the PresentationFacade protocol (P0.21)."""

from ai_campaign_studio.presentation.contracts import PresentationFacade

_EXPECTED_METHODS = {
    "set_app_locale",
    "get_app_state",
    "list_ai_providers",
    "get_provider_status",
    "run_health_check",
    "cancel_job",
}


def test_facade_declares_foundation_surface() -> None:
    for method in _EXPECTED_METHODS:
        assert hasattr(PresentationFacade, method)
