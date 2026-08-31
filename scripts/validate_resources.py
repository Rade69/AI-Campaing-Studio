"""Validate i18n JSON and BHS regional-language YAML resources.

Usage:

    python scripts/validate_resources.py [--repo-root .]

Exit code 0 when every resource is valid, 1 otherwise.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

REQUIRED_I18N_KEYS = frozenset(
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

EXPECTED_REGIONAL_FILES = frozenset(
    {
        "bhs_neutral_v1.yaml",
        "bhs_bs_v1.yaml",
        "bhs_sr_v1.yaml",
        "bhs_hr_v1.yaml",
    }
)

_REGIONAL_LIST_FIELDS = (
    "preferred_terms",
    "forbidden_terms",
    "regional_vocabulary",
    "notes",
)


def _read_utf8(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        print(f"{path}: not valid UTF-8: {exc}", file=sys.stderr)
        return None


def _parse_json(raw: str) -> tuple[Any, list[str]]:
    """Parse JSON, returning ``(data, duplicate_keys)``.

    Raises ``json.JSONDecodeError`` for syntactically invalid JSON so callers
    can report a readable error instead of a traceback.
    """
    duplicates: list[str] = []

    def hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        seen: set[str] = set()
        for key, _value in pairs:
            if key in seen:
                duplicates.append(key)
            seen.add(key)
        return dict(pairs)

    data = json.loads(raw, object_pairs_hook=hook)
    return data, duplicates


def _expected_variant(path: Path) -> str | None:
    stem = path.stem  # e.g. bhs_bs_v1
    parts = stem.split("_")
    if len(parts) == 3 and parts[0] == "bhs" and parts[2] == "v1":
        return parts[1].upper()
    return None


def validate_i18n(en_path: Path, bhs_path: Path) -> list[str]:
    errors: list[str] = []

    en_raw = _read_utf8(en_path)
    bhs_raw = _read_utf8(bhs_path)
    if en_raw is None:
        errors.append(f"{en_path}: UTF-8 decoding failed")
    if bhs_raw is None:
        errors.append(f"{bhs_path}: UTF-8 decoding failed")
    if en_raw is None or bhs_raw is None:
        return errors

    catalogs: dict[Path, Any] = {}
    for path, raw in ((en_path, en_raw), (bhs_path, bhs_raw)):
        try:
            data, duplicates = _parse_json(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"{path}: invalid JSON: {exc}")
            continue
        if duplicates:
            errors.append(f"{path}: duplicate JSON keys: {sorted(set(duplicates))}")
        catalogs[path] = data

    if en_path not in catalogs or bhs_path not in catalogs:
        return errors

    en = catalogs[en_path]
    bhs = catalogs[bhs_path]

    if not isinstance(en, dict) or not isinstance(bhs, dict):
        errors.append("i18n catalogs must be JSON objects")
        return errors

    missing_en = REQUIRED_I18N_KEYS - set(en)
    missing_bhs = REQUIRED_I18N_KEYS - set(bhs)
    if missing_en:
        errors.append(f"{en_path}: missing required keys: {sorted(missing_en)}")
    if missing_bhs:
        errors.append(f"{bhs_path}: missing required keys: {sorted(missing_bhs)}")
    if set(en) != set(bhs):
        errors.append("i18n catalogs must have the same key set")

    # Values must be plain strings: the translator interpolates them with
    # ``str.format``, so any non-string value would break at runtime.
    for path, catalog in ((en_path, en), (bhs_path, bhs)):
        for key, value in catalog.items():
            if not isinstance(value, str):
                errors.append(
                    f"{path}: value for {key!r} must be a string, "
                    f"got {type(value).__name__}"
                )

    # Latin-script MVP: BHS diacritics must survive UTF-8 loading intact.
    bhs_text = json.dumps(bhs, ensure_ascii=False)
    if "\ufffd" in bhs_text:
        errors.append(f"{bhs_path}: contains Unicode replacement characters")
    if not any(ch in bhs_text for ch in "čćšžđ"):
        errors.append(f"{bhs_path}: no BHS diacritics found (č ć š ž đ)")

    return errors


def validate_regional_yaml(path: Path) -> list[str]:
    errors: list[str] = []

    raw = _read_utf8(path)
    if raw is None:
        return [f"{path}: UTF-8 decoding failed"]

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        return [f"{path}: invalid YAML: {exc}"]

    if not isinstance(data, dict):
        return [f"{path}: must be a YAML mapping"]

    if data.get("language_family") != "BHS":
        errors.append(f"{path}: language_family must be 'BHS'")

    expected = _expected_variant(path)
    if expected is None:
        errors.append(f"{path}: filename does not match bhs_<variant>_v1.yaml")
    elif data.get("regional_variant") != expected:
        errors.append(
            f"{path}: regional_variant must be {expected!r} "
            f"(got {data.get('regional_variant')!r})"
        )

    if "version" not in data:
        errors.append(f"{path}: missing 'version'")
    elif not isinstance(data["version"], int):
        errors.append(f"{path}: 'version' must be an integer")

    for field in _REGIONAL_LIST_FIELDS:
        if field not in data:
            errors.append(f"{path}: missing {field!r}")
        elif not isinstance(data[field], list):
            errors.append(f"{path}: {field!r} must be a list")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args(argv)

    root = args.repo_root
    i18n_dir = root / "resources" / "i18n"
    regional_dir = root / "resources" / "regional_language"

    errors = list(validate_i18n(i18n_dir / "en.json", i18n_dir / "bhs.json"))

    regional_files = sorted(regional_dir.glob("bhs_*_v1.yaml"))
    found = {path.name for path in regional_files}
    if found != EXPECTED_REGIONAL_FILES:
        errors.append(
            f"{regional_dir}: expected regional files {sorted(EXPECTED_REGIONAL_FILES)}"
            f", found {sorted(found)}"
        )
    for path in regional_files:
        errors.extend(validate_regional_yaml(path))

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("All localization resources are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
