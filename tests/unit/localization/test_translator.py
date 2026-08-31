"""Tests for the framework-neutral ``Translator``."""

import json
import logging
from pathlib import Path

import pytest

from ai_campaign_studio.localization.enums import AppLocale
from ai_campaign_studio.localization.translator import Translator


@pytest.fixture
def translator(tmp_path: Path) -> Translator:
    en = {
        "app.title": "AI Campaign Studio",
        "common.save": "Save",
        "greeting": "Hello, {name}!",
        "en.only": "English only",
        "diacritics": "čćšžđ ČĆŠŽĐ",
    }
    bhs = {
        "app.title": "AI Campaign Studio",
        "common.save": "Sačuvaj",
        "greeting": "Zdravo, {name}!",
        "diacritics": "čćšžđ ČĆŠŽĐ",
    }
    (tmp_path / "en.json").write_text(
        json.dumps(en, ensure_ascii=False), encoding="utf-8"
    )
    (tmp_path / "bhs.json").write_text(
        json.dumps(bhs, ensure_ascii=False), encoding="utf-8"
    )
    return Translator(tmp_path)


def test_en_translation(translator: Translator) -> None:
    assert translator.t("common.save") == "Save"


def test_bhs_translation(translator: Translator) -> None:
    translator.set_locale(AppLocale.BHS_LATIN)
    assert translator.t("common.save") == "Sačuvaj"


def test_runtime_locale_switch(translator: Translator) -> None:
    assert translator.t("common.save") == "Save"
    translator.set_locale(AppLocale.BHS_LATIN)
    assert translator.t("common.save") == "Sačuvaj"
    translator.set_locale(AppLocale.EN)
    assert translator.t("common.save") == "Save"


def test_get_locale_roundtrip(translator: Translator) -> None:
    assert translator.get_locale() is AppLocale.EN
    translator.set_locale(AppLocale.BHS_LATIN)
    assert translator.get_locale() is AppLocale.BHS_LATIN


def test_fallback_to_en(translator: Translator) -> None:
    translator.set_locale(AppLocale.BHS_LATIN)
    assert translator.t("en.only") == "English only"


def test_parameter_interpolation(translator: Translator) -> None:
    assert translator.t("greeting", name="World") == "Hello, World!"


def test_parameter_interpolation_empty_params(translator: Translator) -> None:
    # Keys without placeholders must work with no params at all.
    assert translator.t("common.save") == "Save"


def test_diacritics_survive_roundtrip(translator: Translator) -> None:
    expected = "čćšžđ ČĆŠŽĐ"
    assert translator.t("diacritics") == expected
    translator.set_locale(AppLocale.BHS_LATIN)
    assert translator.t("diacritics") == expected


def test_unknown_key_returns_marker_and_warns(
    translator: Translator, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        result = translator.t("does.not.exist")
    assert result == "[missing:does.not.exist]"
    assert any("does.not.exist" in record.message for record in caplog.records)


def test_fallback_logs_warning(
    translator: Translator, caplog: pytest.LogCaptureFixture
) -> None:
    translator.set_locale(AppLocale.BHS_LATIN)
    with caplog.at_level(logging.WARNING):
        result = translator.t("en.only")
    assert result == "English only"
    assert any("en.only" in record.message for record in caplog.records)


def test_malformed_format_template_is_graceful(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    catalog = {"broken": "Broken {", "plain": "ok"}
    (tmp_path / "en.json").write_text(json.dumps(catalog), encoding="utf-8")
    (tmp_path / "bhs.json").write_text(json.dumps(catalog), encoding="utf-8")
    translator = Translator(tmp_path)

    with caplog.at_level(logging.WARNING):
        result = translator.t("broken")

    assert result == "Broken {"
    assert any(
        "Interpolation failed" in record.message for record in caplog.records
    )


def test_non_string_value_is_treated_as_missing(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    catalog = {"app.title": {"nested": "bad"}}
    (tmp_path / "en.json").write_text(json.dumps(catalog), encoding="utf-8")
    (tmp_path / "bhs.json").write_text(json.dumps(catalog), encoding="utf-8")
    translator = Translator(tmp_path)

    with caplog.at_level(logging.WARNING):
        result = translator.t("app.title")

    assert result == "[missing:app.title]"
    assert any("Non-string" in record.message for record in caplog.records)
