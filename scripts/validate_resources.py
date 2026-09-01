"""Validate bundled resources: i18n, regional, platforms, providers, migrations.

Usage:

    python scripts/validate_resources.py [--repo-root .]

Exit code 0 when every resource is valid, 1 otherwise.

Reuses the existing ``PlatformRegistry`` / ``AIProviderRegistry`` /
``discover_migrations`` loaders so the same schema/invariant logic that
runs at application startup is the source of truth — this script only
adds checks the registries do not perform themselves (e.g. i18n key
parity, BHS diacritics, secret-like field scan in provider YAMLs,
migration ordering and checksum shape).
"""

import argparse
import json
import re
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

# Secret-like field names that must NOT carry a value in AI provider YAMLs.
# Keys in provider YAMLs are about *config shape* (e.g. requires_api_key),
# never about credentials; an inline api_key/secret/token/password value
# would be a hard violation.
_SECRET_LIKE_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "secret",
        "token",
        "password",
        "passwd",
        "credential",
        "credentials",
        "access_key",
        "private_key",
    }
)

_PLACEHOLDER_TOKENS = (
    "example",
    "exampledummy",
    "redacted",
    "xxx",
    "your-key",
    "your_key",
    "placeholder",
    "changeme",
    "<key>",
    "<your",
    "todo",
    "fixme",
    "dummy",
    "fakekey",
    "fake-key",
    "not-a-real",
    "notareal",
)

_MIGRATION_FILENAME_RE = re.compile(r"^(?P<version>\d+)_(?P<name>[a-z0-9_]+)\.sql$")
_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


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


def _is_placeholder(value: object) -> bool:
    """True when a string scalar is an obvious placeholder, not a real secret.

    Uses substring matching so ``"your-key-here-1234"``, ``"EXAMPLEKEY..."``,
    ``"REDACTED-vault"`` etc. are caught even when wrapped in framing chars.
    """
    if not isinstance(value, str):
        return False
    stripped = value.strip().strip("\"'<>`")
    lowered = stripped.lower()
    if not lowered:
        return True
    return any(token in lowered for token in _PLACEHOLDER_TOKENS)


def _scan_for_secret_like_fields(raw: Any, path: Path) -> list[str]:
    """Walk a parsed YAML/JSON tree; flag secret-like keys that carry a value."""
    errors: list[str] = []
    if isinstance(raw, dict):
        for key, value in raw.items():
            if not isinstance(key, str):
                continue
            key_lower = key.lower()
            if key_lower in _SECRET_LIKE_KEYS:
                if value is None:
                    continue  # explicit null is fine
                if isinstance(value, str) and _is_placeholder(value):
                    continue
                if isinstance(value, (dict, list)) and not value:
                    continue
                errors.append(
                    f"{path}: secret-like field {key!r} carries a value "
                    f"(providers must never embed credentials)"
                )
            errors.extend(_scan_for_secret_like_fields(value, path))
    elif isinstance(raw, list):
        for item in raw:
            errors.extend(_scan_for_secret_like_fields(item, path))
    return errors


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


def validate_platforms(platforms_dir: Path) -> list[str]:
    """Validate every ``platforms/*.yaml`` via the bundled ``PlatformRegistry``.

    The registry enforces schema validity, unique codes, valid ``channel``
    enum members and valid ``supported_formats`` references. This function
    adds the checks the registry does not perform itself (raw YAML shape,
    secret-like field scan, presence of at least one platform).
    """
    errors: list[str] = []
    if not platforms_dir.is_dir():
        return [f"{platforms_dir}: not a directory"]

    yaml_paths = sorted(platforms_dir.glob("*.yaml"))
    if not yaml_paths:
        return [f"{platforms_dir}: no platform YAML files found"]

    # 1. Raw YAML shape + secret-like field scan (registry does not look at
    #    the raw dict; it only sees the validated model).
    for path in yaml_paths:
        raw_text = _read_utf8(path)
        if raw_text is None:
            errors.append(f"{path}: UTF-8 decoding failed")
            continue
        try:
            data = yaml.safe_load(raw_text)
        except yaml.YAMLError as exc:
            errors.append(f"{path}: invalid YAML: {exc}")
            continue
        if not isinstance(data, dict):
            errors.append(f"{path}: platform file must be a mapping")
            continue
        errors.extend(_scan_for_secret_like_fields(data, path))

    # 2. Schema + cross-file invariants via the real registry.
    try:
        # Imported lazily so that the script can still report YAML-level
        # errors above even when the registry import path is unhealthy.
        from ai_campaign_studio.channels.registry import PlatformRegistry

        registry = PlatformRegistry(platforms_dir)
        platforms = registry.list_platforms()
    except Exception as exc:  # noqa: BLE001 — surface any registry error
        errors.append(f"platform registry failed: {exc}")
        return errors

    if not platforms:
        errors.append(f"{platforms_dir}: no enabled platforms found")

    return errors


def validate_ai_providers(providers_dir: Path) -> list[str]:
    """Validate every ``ai_providers/*.yaml`` via the bundled registry + a
    raw-tree secret-like field scan (the registry only sees the validated
    model, so it cannot detect ``api_key: sk-...`` style leakage in extras).
    """
    errors: list[str] = []
    if not providers_dir.is_dir():
        return [f"{providers_dir}: not a directory"]

    yaml_paths = sorted(providers_dir.glob("*.yaml"))
    if not yaml_paths:
        return [f"{providers_dir}: no provider YAML files found"]

    for path in yaml_paths:
        raw_text = _read_utf8(path)
        if raw_text is None:
            errors.append(f"{path}: UTF-8 decoding failed")
            continue
        try:
            data = yaml.safe_load(raw_text)
        except yaml.YAMLError as exc:
            errors.append(f"{path}: invalid YAML: {exc}")
            continue
        if not isinstance(data, dict):
            errors.append(f"{path}: provider file must be a mapping")
            continue
        errors.extend(_scan_for_secret_like_fields(data, path))

    try:
        from ai_campaign_studio.ai_registry.registry import AIProviderRegistry

        registry = AIProviderRegistry(providers_dir)
        providers = registry.list_providers()
    except Exception as exc:  # noqa: BLE001
        errors.append(f"provider registry failed: {exc}")
        return errors

    if not providers:
        errors.append(f"{providers_dir}: no enabled providers found")

    return errors


def validate_migrations(migrations_dir: Path) -> list[str]:
    """Validate every ``migrations/*.sql`` file: filename format, unique
    versions, strictly ascending on-disk order, and a readable SHA-256
    checksum shape. Delegates actual SQL parsing to ``discover_migrations``.
    """
    errors: list[str] = []
    if not migrations_dir.is_dir():
        return [f"{migrations_dir}: not a directory"]

    sql_paths = sorted(migrations_dir.glob("*.sql"))
    if not sql_paths:
        return [f"{migrations_dir}: no migration SQL files found"]

    # Filename format check covers what discover_migrations raises on.
    versions: list[int] = []
    for path in sql_paths:
        match = _MIGRATION_FILENAME_RE.match(path.name)
        if match is None:
            errors.append(
                f"{path}: filename must match NNNN_<name>.sql "
                "(digits version, lowercase name, .sql extension)"
            )
            continue
        versions.append(int(match.group("version")))

    if versions:
        # Strictly ascending on-disk order (already enforced by glob sort,
        # but explicit so the intent is documented and testable).
        if versions != sorted(versions):
            errors.append(
                f"{migrations_dir}: migration files are not in ascending "
                f"version order (found {versions})"
            )
        seen: set[int] = set()
        duplicates = sorted(v for v in versions if v in seen or seen.add(v))  # type: ignore[func-returns-value]
        if duplicates:
            errors.append(
                f"{migrations_dir}: duplicate migration versions: {duplicates}"
            )

    # Delegate to the real discovery function for a real checksum.
    try:
        from ai_campaign_studio.infrastructure.database.migrations import (
            discover_migrations,
        )

        discovered = discover_migrations(migrations_dir)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"migration discovery failed: {exc}")
        return errors

    for migration in discovered:
        if not _SHA256_HEX_RE.match(migration.checksum):
            migration_path = (
                migrations_dir / f"{migration.version}_{migration.name}.sql"
            )
            errors.append(
                f"{migration_path}: checksum {migration.checksum!r} "
                "is not a 64-char hex SHA-256"
            )

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args(argv)

    root = args.repo_root
    i18n_dir = root / "resources" / "i18n"
    regional_dir = root / "resources" / "regional_language"
    platforms_dir = root / "resources" / "platforms"
    providers_dir = root / "resources" / "ai_providers"
    migrations_dir = root / "resources" / "migrations"

    errors: list[str] = []
    errors.extend(validate_i18n(i18n_dir / "en.json", i18n_dir / "bhs.json"))

    regional_files = sorted(regional_dir.glob("bhs_*_v1.yaml"))
    found = {path.name for path in regional_files}
    if found != EXPECTED_REGIONAL_FILES:
        errors.append(
            f"{regional_dir}: expected regional files {sorted(EXPECTED_REGIONAL_FILES)}"
            f", found {sorted(found)}"
        )
    for path in regional_files:
        errors.extend(validate_regional_yaml(path))

    errors.extend(validate_platforms(platforms_dir))
    errors.extend(validate_ai_providers(providers_dir))
    errors.extend(validate_migrations(migrations_dir))

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("All resources are valid (i18n, regional, platforms, providers, migrations).")
    return 0


# Re-export the per-section validators so the gate report generator and the
# unit tests can run each section in isolation (e.g. ``validate_i18n(en, bhs)``).
__all__ = [
    "main",
    "validate_i18n",
    "validate_regional_yaml",
    "validate_platforms",
    "validate_ai_providers",
    "validate_migrations",
    "REQUIRED_I18N_KEYS",
    "EXPECTED_REGIONAL_FILES",
]


if __name__ == "__main__":
    raise SystemExit(main())
