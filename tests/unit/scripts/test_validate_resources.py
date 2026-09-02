"""Unit tests for ``scripts/validate_resources.py``.

Covers the per-section validators that were added on top of the
existing i18n/regional checks. Each test builds a tiny in-memory
fixture directory, runs the validator, and asserts the expected
errors (or no errors).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Make the scripts directory importable.
_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import validate_resources as vr  # type: ignore[import-not-found]  # noqa: E402

# Runtime-constructed key fixture so the source has no key-shaped
# literal in the tracked test scope (Codex review BF-1). Mirrors the
# helper in ``test_check_no_secrets.py``.
_FILLER = "abcdefghijklmnop"  # 16 chars, no prefix on its own


def _real_openai_key() -> str:
    return "sk-" + _FILLER * 2  # 32 alphanumerics after "sk-"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _platform_yaml(
    code: str = "TEST",
    formats: list[dict] | None = None,
) -> str:
    fmt = formats or [
        {
            "code": "FEED_POST",
            "display_name": "Feed Post",
            "required_fields": [],
            "optional_fields": [],
            "text_constraints": {
                "max_chars": None,
                "supports_hashtags": True,
                "supports_links": True,
            },
            "visual_constraints": {
                "supported_aspect_ratios": [],
                "supports_static_image": True,
                "supports_video": False,
                "supports_carousel": False,
            },
            "enabled": True,
        }
    ]
    return (
        f"code: {code}\n"
        "display_name: Test\n"
        "channel: SOCIAL\n"
        "supported_formats:\n"
        f"  - {fmt[0]['code']}\n"
        "content_rules: []\n"
        "enabled: true\n"
        "formats:\n"
        + "\n".join(
            f"  - code: {f['code']}\n"
            f"    display_name: {f.get('display_name', f['code'])}\n"
            "    required_fields: []\n"
            "    optional_fields: []\n"
            "    text_constraints:\n"
            "      max_chars: null\n"
            "      max_caption_chars: null\n"
            "      max_title_chars: null\n"
            "      supports_hashtags: true\n"
            "      supports_links: true\n"
            "    visual_constraints:\n"
            "      supported_aspect_ratios: []\n"
            "      supports_static_image: true\n"
            "      supports_video: false\n"
            "      supports_carousel: false\n"
            "    enabled: true\n"
            for f in fmt
        )
    )


# --- i18n ---------------------------------------------------------------


def test_validate_i18n_passes_on_minimal_canonical(tmp_path: Path) -> None:
    en = {key: f"en-{key}" for key in vr.REQUIRED_I18N_KEYS}
    en_path = tmp_path / "en.json"
    bhs_path = tmp_path / "bhs.json"
    en_path.write_text(json.dumps(en), encoding="utf-8")
    bhs = {key: f"bhs-{key}-čćšžđ" for key in vr.REQUIRED_I18N_KEYS}
    bhs_path.write_text(json.dumps(bhs, ensure_ascii=False), encoding="utf-8")
    assert vr.validate_i18n(en_path, bhs_path) == []


def test_validate_i18n_flags_missing_required_key(tmp_path: Path) -> None:
    en = {"app.title": "x"}  # missing most required keys
    bhs = {"app.title": "x"}
    en_path = tmp_path / "en.json"
    bhs_path = tmp_path / "bhs.json"
    en_path.write_text(json.dumps(en), encoding="utf-8")
    bhs_path.write_text(json.dumps(bhs), encoding="utf-8")
    errors = vr.validate_i18n(en_path, bhs_path)
    assert any("missing required keys" in e for e in errors)


def test_validate_i18n_flags_mismatched_key_sets(tmp_path: Path) -> None:
    en = {key: f"v-{key}" for key in vr.REQUIRED_I18N_KEYS}
    bhs = {key: f"v-{key}" for key in vr.REQUIRED_I18N_KEYS}
    bhs["extra.key"] = "extra"
    en_path = tmp_path / "en.json"
    bhs_path = tmp_path / "bhs.json"
    en_path.write_text(json.dumps(en), encoding="utf-8")
    bhs_path.write_text(json.dumps(bhs), encoding="utf-8")
    errors = vr.validate_i18n(en_path, bhs_path)
    assert any("same key set" in e for e in errors)


# --- platforms ----------------------------------------------------------


def test_validate_platforms_passes_on_minimal_canonical(tmp_path: Path) -> None:
    platforms = tmp_path / "platforms"
    _write(platforms / "okplatform.yaml", _platform_yaml(code="OKPLAT"))
    assert vr.validate_platforms(platforms) == []


def test_validate_platforms_flags_secret_like_field(tmp_path: Path) -> None:
    platforms = tmp_path / "platforms"
    key = _real_openai_key()
    body = (
        _platform_yaml(code="LEAKY")
        + f"\n# someone tried to sneak a key in:\napi_key: {key}\n"
    )
    _write(platforms / "leaky.yaml", body)
    errors = vr.validate_platforms(platforms)
    assert any("api_key" in e and "secret-like" in e for e in errors)


def test_validate_platforms_flags_placeholder_secret_field(tmp_path: Path) -> None:
    """A secret-like field with a placeholder value should NOT be flagged."""
    platforms = tmp_path / "platforms"
    body = (
        _platform_yaml(code="OKPLAT")
        + "\napi_key: your-key-here-1234567890123456\n"
    )
    _write(platforms / "okplusextraline.yaml", body)
    assert vr.validate_platforms(platforms) == []


def test_validate_platforms_flags_invalid_channel(tmp_path: Path) -> None:
    platforms = tmp_path / "platforms"
    _write(
        platforms / "badchan.yaml",
        _platform_yaml(code="BADCHAN").replace(
            "channel: SOCIAL", "channel: NOT_A_CHANNEL"
        ),
    )
    errors = vr.validate_platforms(platforms)
    # Either the platform-registry raises RegistryError or a key error is reported.
    assert errors, "expected at least one error for invalid channel"


# --- AI providers -------------------------------------------------------


def test_validate_ai_providers_passes_on_minimal_canonical(tmp_path: Path) -> None:
    providers = tmp_path / "providers"
    _write(
        providers / "okprovider.yaml",
        (
            "provider_code: OKPROV\n"
            "display_name: OK Provider\n"
            "adapter_type: openai\n"
            "requires_api_key: true\n"
            "supports_model_discovery: false\n"
            "base_url_mode: NONE\n"
            "enabled: true\n"
        ),
    )
    assert vr.validate_ai_providers(providers) == []


def test_validate_ai_providers_flags_secret_like_field(tmp_path: Path) -> None:
    providers = tmp_path / "providers"
    _write(
        providers / "leaky.yaml",
        (
            "provider_code: LEAKY\n"
            "display_name: Leaky\n"
            "adapter_type: openai\n"
            "requires_api_key: true\n"
            "supports_model_discovery: false\n"
            "base_url_mode: NONE\n"
            "enabled: true\n"
            f"api_key: {_real_openai_key()}\n"
        ),
    )
    errors = vr.validate_ai_providers(providers)
    assert any("api_key" in e and "secret-like" in e for e in errors)


# --- migrations ---------------------------------------------------------


def test_validate_migrations_passes_on_canonical(tmp_path: Path) -> None:
    migs = tmp_path / "migrations"
    _write(migs / "0000_init.sql", "CREATE TABLE foo (id INTEGER);\n")
    _write(migs / "0001_more.sql", "ALTER TABLE foo ADD COLUMN bar TEXT;\n")
    assert vr.validate_migrations(migs) == []


def test_validate_migrations_flags_bad_filename(tmp_path: Path) -> None:
    migs = tmp_path / "migrations"
    _write(migs / "NotNumbered.sql", "SELECT 1;\n")
    errors = vr.validate_migrations(migs)
    assert any("filename must match" in e for e in errors)


def test_validate_migrations_flags_duplicate_versions(tmp_path: Path) -> None:
    migs = tmp_path / "migrations"
    _write(migs / "0000_first.sql", "SELECT 1;\n")
    _write(migs / "0000_second.sql", "SELECT 2;\n")
    errors = vr.validate_migrations(migs)
    assert any("duplicate migration versions" in e for e in errors)


# --- top-level main() end-to-end ----------------------------------------


def test_main_against_bundled_repo_passes(repo_root: Path) -> None:
    """The validator against the actual repo resources should pass clean."""
    assert vr.main(["--repo-root", str(repo_root)]) == 0


# --- fixtures -----------------------------------------------------------


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]
