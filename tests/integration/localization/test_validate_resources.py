"""Regression tests for the resource validator (BF-2/BF-3)."""

import importlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
validate_resources = importlib.import_module("validate_resources")


def _catalog(**overrides: object) -> dict[str, object]:
    catalog: dict[str, object] = {
        key: f"value_{key}" for key in validate_resources.REQUIRED_I18N_KEYS
    }
    catalog.update(overrides)
    return catalog


def _write(tmp_path: Path, en: dict[str, object], bhs: dict[str, object]) -> None:
    (tmp_path / "en.json").write_text(
        json.dumps(en, ensure_ascii=False), encoding="utf-8"
    )
    (tmp_path / "bhs.json").write_text(
        json.dumps(bhs, ensure_ascii=False), encoding="utf-8"
    )


def test_validate_i18n_rejects_non_string_values(tmp_path: Path) -> None:
    en = _catalog()
    bhs = _catalog(**{"app.title": {"nested": "bad"}})
    _write(tmp_path, en, bhs)

    errors = validate_resources.validate_i18n(
        tmp_path / "en.json", tmp_path / "bhs.json"
    )

    assert any("must be a string" in error for error in errors)


def test_validate_i18n_invalid_json_returns_error(tmp_path: Path) -> None:
    (tmp_path / "en.json").write_text("{ invalid", encoding="utf-8")
    (tmp_path / "bhs.json").write_text("{}", encoding="utf-8")

    errors = validate_resources.validate_i18n(
        tmp_path / "en.json", tmp_path / "bhs.json"
    )

    assert any("invalid JSON" in error for error in errors)
