"""Integration checks for the real i18n and regional-language resources."""

import json
from pathlib import Path
from typing import Any

from ai_campaign_studio.localization.enums import AppLocale
from ai_campaign_studio.localization.translator import Translator

REPO_ROOT = Path(__file__).resolve().parents[3]
I18N_DIR = REPO_ROOT / "resources" / "i18n"

REQUIRED_KEYS = frozenset(
    {
        "app.title",
        "app.starting",
        "app.ready",
        "settings.title",
        "settings.language",
        "settings.ai_providers",
        "settings.api_key",
        "settings.test_connection",
        "settings.connected",
        "settings.not_configured",
        "common.save",
        "common.cancel",
        "common.close",
        "common.retry",
        "error.generic",
        "error.configuration",
        "error.database",
    }
)


def _load(path: Path) -> dict[str, str]:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_duplicate_keys(raw: str) -> list[str]:
    duplicates: list[str] = []

    def hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        seen: set[str] = set()
        for key, _value in pairs:
            if key in seen:
                duplicates.append(key)
            seen.add(key)
        return dict(pairs)

    json.loads(raw, object_pairs_hook=hook)
    return duplicates


def test_i18n_json_valid_utf8_and_same_key_set() -> None:
    en = _load(I18N_DIR / "en.json")
    bhs = _load(I18N_DIR / "bhs.json")
    assert set(en) == set(bhs)
    assert REQUIRED_KEYS <= set(en)
    assert REQUIRED_KEYS <= set(bhs)


def test_bhs_diacritics_survive() -> None:
    bhs = _load(I18N_DIR / "bhs.json")
    all_text = json.dumps(bhs, ensure_ascii=False)
    assert "\ufffd" not in all_text
    # The full alphabet (č ć š ž đ + uppercase) is covered by the translator
    # unit test ``test_diacritics_survive_roundtrip``; here we assert the
    # naturally present Latin diacritics load exactly, with no mojibake.
    assert bhs["common.save"] == "Sačuvaj"  # č
    assert bhs["common.retry"] == "Pokušaj ponovo"  # š
    assert bhs["common.cancel"] == "Otkaži"  # ž


def test_no_duplicate_keys() -> None:
    for name in ("en.json", "bhs.json"):
        raw = (I18N_DIR / name).read_text(encoding="utf-8")
        assert _find_duplicate_keys(raw) == []


def test_translator_loads_real_resources() -> None:
    translator = Translator(I18N_DIR)
    assert translator.get_locale() is AppLocale.EN
    assert translator.t("app.title") == "AI Campaign Studio"
    translator.set_locale(AppLocale.BHS_LATIN)
    assert translator.t("common.save") == "Sačuvaj"
