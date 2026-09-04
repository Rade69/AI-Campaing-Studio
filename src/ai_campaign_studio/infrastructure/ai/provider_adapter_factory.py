"""Provider adapter factory (A8, dio — bridge wiring).

Owns the runtime dispatch from ``provider_code`` to a concrete
``TextGenerationPort`` implementation. Called by the GUI→backend bridge
(``presentation_webview/bridge/``) after resolving which provider the user
has actually configured.

Design notes
------------
- **Factory is dumb about secrets.** It receives a *ready* ``api_key`` string
  (already pulled from ``SecretStore`` by the caller). It NEVER touches
  ``SecretStorePort`` directly — that is the bridge's job. This keeps the
  factory's signature trivially mockable and avoids passing ``SecretStore``
  references through the composition root into the infrastructure layer.
- **Hardcoded model_id table.** Per ACS-GUI-005 contract: no model
  discovery/registration at this stage (no ``resolve_default_text_model``
  integration). The dispatch returns a fixed ``model_id`` for each
  ``provider_code``; the comment next to each entry cites the source of
  the string (live-verified A8 evidence file, or "verified against the
  installed SDK Literal type" for ``ANTHROPIC`` which has no live test
  in this project).
- **ACS-F1-017 (DeepSeek/OpenRouter) is NOT YET MERGED** in this task's base
  (``main @ 73f52b1``). Per the contract, we ship 3 entries (OPENAI,
  ANTHROPIC, GOOGLE) and raise a clear internal error for any other code.
  The coordinator will add DeepSeek/OpenRouter entries in a follow-up
  fix round once ACS-F1-017 lands on main.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_campaign_studio.domain.common.errors import ConfigurationError
from ai_campaign_studio.ports.ai import TextGenerationPort

if TYPE_CHECKING:
    pass


# Hardcoded provider→model_id table (per ACS-GUI-005 contract).
# Each comment is the source of the string; if the string ever changes,
# update the comment too so the next person can verify.
_DEFAULT_MODEL_IDS: dict[str, str] = {
    # Live-verified in ACS-F1-016 evidence (`agent_reports/.../ACS-F1-016-*.md`).
    "OPENAI": "gpt-4o-mini",
    # Not live-tested in this project. Verified against the installed
    # ``anthropic`` 1.3.0 SDK ``Message.model`` Literal type
    # (``claude-3-haiku-20240307`` appears in the official Literal set and
    # has been the recommended stable Claude model for production use
    # since 2024). If this needs to change, follow the same discipline
    # as ACS-F1-018: check the SDK Literal type AND/OR the official
    # Anthropic docs page; never guess a string.
    "ANTHROPIC": "claude-3-haiku-20240307",
    # Live-verified in ACS-F1-019 (full LoadBrandFixture → CreateCampaign
    # → GenerateCampaignPlan → ApproveCampaignPlan → GenerateSocialPost end-
    # to-end against a real Gemini API key). Source of truth:
    # `agent_reports/2026-09-04-ACS-F1-019-review-claude.md` (line 16:
    # "Pun end-to-end tok ... pokrenut protiv PRAVOG Gemini API-ja
    # (`gemini-2.5-flash`)"). NOT `gemini-1.5-flash` — that string was
    # mistakenly copied from an older draft and rejected at runtime
    # (404 NOT_FOUND, models/gemini-1.5-flash is not supported for
    # generateContent) — see ACS-GUI-005 BF-1 in
    # `agent_reports/2026-09-04-ACS-GUI-005-minimax.md` §"Fix runda (BF-1)".
    "GOOGLE": "gemini-2.5-flash",
}

# Hardcoded priority — ACS-GUI-005 contract: pick the first configured
# provider in this order; if a configured provider falls outside the list,
# fall back to any configured one (do not fail just because the priority
# list is incomplete).
_PROVIDER_PRIORITY: tuple[str, ...] = ("OPENAI", "ANTHROPIC", "GOOGLE")


def pick_configured_provider(
    configured_provider_codes: list[str],
) -> str | None:
    """Return the highest-priority configured provider, or ``None``.

    Walks ``_PROVIDER_PRIORITY`` first; if no priority provider is
    configured, returns the first entry of ``configured_provider_codes``
    (whichever it is — per contract we don't fail just because our
    priority list is incomplete). Returns ``None`` if no provider is
    configured.
    """
    if not configured_provider_codes:
        return None
    by_code = {code.upper() for code in configured_provider_codes}
    for code in _PROVIDER_PRIORITY:
        if code in by_code:
            return code
    return configured_provider_codes[0]


def resolve_model_id(provider_code: str) -> str:
    """Return the hardcoded ``model_id`` for a provider, or raise.

    Raises ``ConfigurationError`` (not ``KeyError``) so the bridge can
    map this directly to a user-facing message without inspecting the
    exception type. The error message is generic — it does NOT leak
    the internal model-id table.
    """
    code = provider_code.upper()
    if code not in _DEFAULT_MODEL_IDS:
        raise ConfigurationError(
            f"provider {provider_code!r} is not supported by the GUI bridge yet"
        )
    return _DEFAULT_MODEL_IDS[code]


def build_text_generation_adapter(
    provider_code: str,
    api_key: str,
    *,
    base_url: str | None = None,
) -> TextGenerationPort:
    """Instantiate the concrete ``TextGenerationPort`` for ``provider_code``.

    The factory only constructs the production adapter — never a mock
    or test double. Tests must inject a fake client via the adapter's
    own DI seam (see ``OpenAIAdapter(client=...)`` and equivalents),
    or build their own adapter subclass, not call this function.

    ``api_key`` is passed through unchanged; the bridge is responsible
    for having already pulled the secret from the store. The factory
    does NOT validate that ``api_key`` is non-empty (a non-empty
    sentinel is the caller's responsibility; the SDK will surface a
    clear ``AuthenticationError`` on the first real call if the key
    is bad).
    """
    code = provider_code.upper()
    if code == "OPENAI":
        # Imported lazily so that provider modules are only loaded when
        # actually needed (saves startup time + lets the factory import
        # without all 3 SDKs available in test envs that mock the
        # adapter entirely).
        from ai_campaign_studio.infrastructure.ai.openai_adapter import OpenAIAdapter
        return OpenAIAdapter(
            api_key=api_key,
            model=resolve_model_id(code),
            base_url=base_url,
        )
    if code == "ANTHROPIC":
        from ai_campaign_studio.infrastructure.ai.anthropic_adapter import (
            AnthropicAdapter,
        )
        return AnthropicAdapter(
            api_key=api_key,
            model=resolve_model_id(code),
            base_url=base_url,
        )
    if code == "GOOGLE":
        from ai_campaign_studio.infrastructure.ai.google_adapter import GoogleAdapter
        # GoogleAdapter has no base_url parameter (Gemini uses Google's
        # own endpoint; the SDK does not accept a custom base URL the
        # way OpenAI/Anthropic do). Pass through and ignore base_url
        # if the caller supplies one — this is a deliberate design
        # choice of the Gemini SDK, not a missing feature here.
        del base_url  # explicit: Gemini does not support base_url overrides
        return GoogleAdapter(
            api_key=api_key,
            model=resolve_model_id(code),
        )
    raise ConfigurationError(
        f"no adapter implementation is registered for provider {provider_code!r}"
    )


__all__ = [
    "build_text_generation_adapter",
    "pick_configured_provider",
    "resolve_model_id",
]
