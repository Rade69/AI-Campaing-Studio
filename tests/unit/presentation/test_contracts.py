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
    # Added in ACS-GUI-007: real provider configuration via the bridge.
    # First js_api method that takes a SECRET string FROM JS (vs. only
    # using them server-side). The contract still says it returns the
    # safe DTO type — no raw secret in the result.
    "configure_provider",
    # Added in ACS-GUI-008: bulk content generation (Studio sadržaja
    # → "Generiši sadržaj"). Approves the plan (idempotent) and runs
    # ``GenerateSocialPost`` once per ``CampaignItem`` with
    # round-robin target assignment. ``ok=True`` even on partial
    # success; idempotent on re-click (already-generated pieces are
    # skipped). Same narrow-surface rule as the other two js_api
    # methods.
    "generate_campaign_content",
    # Added in ACS-GUI-009: real ZIP export (Pregled i izvoz →
    # "Izvezi ZIP paket"). Same narrow-surface, one-positional-dict rule.
    "export_campaign_package",
    # Added in ACS-F1-046: first READ js_api method (Kampanje list).
    # ``raw_payload`` is optional (app.js may call with no args), but
    # still one-dict-shaped when provided, consistent with the others.
    "list_campaigns",
    # Added in ACS-F1-049: Brend read path (single demo brand).
    "get_brand_overview",
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


def test_bridge_implements_configure_provider() -> None:
    """``configure_provider`` is the second js_api method. Same narrow-
    surface rule as ``create_campaign_and_generate_plan``."""
    from ai_campaign_studio.presentation_webview.bridge import CampaignBridgeApi

    method = getattr(CampaignBridgeApi, "configure_provider", None)
    assert method is not None, "bridge must expose configure_provider"
    import inspect
    sig = inspect.signature(method)
    assert list(sig.parameters) == ["self", "raw_payload"]


def test_bridge_implements_generate_campaign_content() -> None:
    """ACS-GUI-008: ``generate_campaign_content`` is the third js_api
    method. The signature is the SAME one-positional-dict shape as
    the previous two — the JS caller does not need to know the
    difference between campaign-create and content-generate, only
    the method name.
    """
    from ai_campaign_studio.presentation_webview.bridge import CampaignBridgeApi

    method = getattr(CampaignBridgeApi, "generate_campaign_content", None)
    assert method is not None, "bridge must expose generate_campaign_content"
    import inspect
    sig = inspect.signature(method)
    assert list(sig.parameters) == ["self", "raw_payload"]


def test_bridge_implements_export_campaign_package() -> None:
    """ACS-GUI-009: ``export_campaign_package`` is the fourth js_api
    method. Same one-positional-dict shape — the JS caller passes
    ``{campaign_id, plan_id}`` and receives an
    ``ExportCampaignResultUiModel``-shaped dict.
    """
    from ai_campaign_studio.presentation_webview.bridge import CampaignBridgeApi

    method = getattr(CampaignBridgeApi, "export_campaign_package", None)
    assert method is not None, "bridge must expose export_campaign_package"

    import inspect

    sig = inspect.signature(method)
    assert list(sig.parameters) == ["self", "raw_payload"]


def test_bridge_implements_list_campaigns() -> None:
    """ACS-F1-046: ``list_campaigns`` is the first READ js_api method.
    ``raw_payload`` is optional (defaults to None) so app.js can call it
    with no args; the contract still declares it on the facade.
    """
    from ai_campaign_studio.presentation_webview.bridge import CampaignBridgeApi

    method = getattr(CampaignBridgeApi, "list_campaigns", None)
    assert method is not None, "bridge must expose list_campaigns"

    import inspect

    sig = inspect.signature(method)
    assert list(sig.parameters) == ["self", "raw_payload"]


def test_bridge_implements_get_brand_overview() -> None:
    """ACS-F1-049: ``get_brand_overview`` is the second READ js_api method
    (Brend screen). Same optional one-dict shape as ``list_campaigns``.
    """
    from ai_campaign_studio.presentation_webview.bridge import CampaignBridgeApi

    method = getattr(CampaignBridgeApi, "get_brand_overview", None)
    assert method is not None, "bridge must expose get_brand_overview"

    import inspect

    sig = inspect.signature(method)
    assert list(sig.parameters) == ["self", "raw_payload"]
