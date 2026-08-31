"""Localization ports (interfaces implemented by adapters)."""

from typing import Any, Protocol

from ai_campaign_studio.localization.enums import AppLocale


class TranslatorPort(Protocol):
    """Framework-neutral translation contract."""

    def set_locale(self, locale: AppLocale) -> None: ...

    def get_locale(self) -> AppLocale: ...

    def t(self, key: str, **params: Any) -> str: ...
