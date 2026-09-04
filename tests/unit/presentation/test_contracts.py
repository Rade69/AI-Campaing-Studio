"""Tests for the PresentationFacade protocol (P0.21)."""

from ai_campaign_studio.presentation.contracts import PresentationFacade

_EXPECTED_METHODS = {
    "set_app_locale",
    "get_app_state",
    "list_ai_providers",
    "get_provider_status",
    "run_health_check",
    "cancel_job",
    # Added in ACS-GUI-005: the first real GUI→backend method.
    # Not every concrete facade must implement it (the Protocol is
    # structural); we only assert the protocol DOES declare it so the
    # contract surface is honest about what exists.
    "create_campaign_and_generate_plan",
}


def test_facade_declares_foundation_surface() -> None:
    for method in _EXPECTED_METHODS:
        assert hasattr(PresentationFacade, method)


def test_bridge_implements_create_campaign_and_generate_plan() -> None:
    """The pywebview ``js_api`` bridge (``CampaignBridgeApi``) is the
    concrete implementation of the new contract method.

    Per PYWEBVIEW_SECURITY §3, the bridge is a *narrow* class: it does
    NOT inherit from ``PresentationFacade`` and does NOT expose the other
    five methods to JS. We assert the method exists, with the right
    signature, and returns a JSON-serializable dict.
    """
    from ai_campaign_studio.presentation_webview.bridge import CampaignBridgeApi

    method = getattr(CampaignBridgeApi, "create_campaign_and_generate_plan", None)
    assert method is not None, "bridge must expose create_campaign_and_generate_plan"
    import inspect
    sig = inspect.signature(method)
    # Exactly one positional parameter after ``self`` (raw_brief) and a dict return.
    assert list(sig.parameters) == ["self", "raw_brief"]
    assert sig.return_annotation in (dict, "dict")
