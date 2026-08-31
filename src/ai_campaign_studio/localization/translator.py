"""Framework-neutral EN/BHS translator backed by JSON catalogs.

Loads ``en.json`` and ``bhs.json`` from a supplied directory, supports runtime
locale switching, simple ``{name}`` interpolation, and falls back to English
when a key is missing from the active (BHS) catalog. A key missing from every
catalog returns ``[missing:<key>]`` and logs a warning instead of raising.
"""

import json
import logging
from pathlib import Path
from typing import Any

from ai_campaign_studio.localization.enums import AppLocale

logger = logging.getLogger("ai_campaign_studio.localization.translator")


class Translator:
    """Concrete, stdlib-only implementation of the translation contract."""

    def __init__(self, translations_dir: Path) -> None:
        self._catalogs: dict[AppLocale, dict[str, str]] = {
            AppLocale.EN: self._load(translations_dir / "en.json"),
            AppLocale.BHS_LATIN: self._load(translations_dir / "bhs.json"),
        }
        self._locale: AppLocale = AppLocale.EN

    @staticmethod
    def _load(path: Path) -> dict[str, str]:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError(f"Translation catalog must be a JSON object: {path}")
        return data

    def set_locale(self, locale: AppLocale) -> None:
        if locale not in self._catalogs:
            raise ValueError(f"Unsupported locale: {locale!r}")
        self._locale = locale

    def get_locale(self) -> AppLocale:
        return self._locale

    def t(self, key: str, **params: Any) -> str:
        active = self._catalogs[self._locale]
        if key in active:
            template = active[key]
        elif key in self._catalogs[AppLocale.EN]:
            logger.warning(
                "Missing key %r in %s catalog; falling back to EN",
                key,
                self._locale.value,
            )
            template = self._catalogs[AppLocale.EN][key]
        else:
            logger.warning("Missing key %r in all catalogs", key)
            return f"[missing:{key}]"

        try:
            return template.format(**params)
        except (KeyError, IndexError) as exc:
            logger.warning("Interpolation failed for key %r: %s", key, exc)
            return template
