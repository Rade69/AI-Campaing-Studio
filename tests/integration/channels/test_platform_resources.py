"""Integration tests for the bundled platform resources (P0.13)."""

from __future__ import annotations

from pathlib import Path

from ai_campaign_studio.channels.enums import Channel
from ai_campaign_studio.channels.registry import PlatformRegistry

RESOURCES_DIR = Path(__file__).resolve().parents[3] / "resources" / "platforms"

EXPECTED_PLATFORM_CODES = {
    "INSTAGRAM",
    "FACEBOOK",
    "LINKEDIN",
    "X",
    "TIKTOK",
    "YOUTUBE",
    "PINTEREST",
    "THREADS",
    "SNAPCHAT",
}

NEW_PLATFORM_YAML = """\
code: TEST_PLATFORM
display_name: Test Platform
channel: SOCIAL
supported_formats:
  - TEST_FORMAT
content_rules: []
enabled: true
formats:
  - code: TEST_FORMAT
    display_name: Test Format
"""


def test_all_nine_yaml_files_load() -> None:
    registry = PlatformRegistry.from_bundled_resources()

    platforms = registry.list_platforms()

    assert {p.code for p in platforms} == EXPECTED_PLATFORM_CODES


def test_platform_codes_unique() -> None:
    registry = PlatformRegistry.from_bundled_resources()

    codes = [p.code for p in registry.list_platforms()]

    assert len(codes) == len(set(codes))


def test_format_codes_unique_per_platform() -> None:
    registry = PlatformRegistry.from_bundled_resources()

    for platform in registry.list_platforms():
        codes = [f.code for f in registry.list_formats(platform.code)]
        assert len(codes) == len(set(codes)), platform.code


def test_all_channels_valid() -> None:
    registry = PlatformRegistry.from_bundled_resources()

    for platform in registry.list_platforms():
        assert isinstance(platform.channel, Channel)


def test_adding_yaml_platform_requires_no_code_change(tmp_path: Path) -> None:
    for source in sorted(RESOURCES_DIR.glob("*.yaml")):
        text = source.read_text(encoding="utf-8")
        (tmp_path / source.name).write_text(text, encoding="utf-8")
    (tmp_path / "testplatform.yaml").write_text(NEW_PLATFORM_YAML, encoding="utf-8")

    registry = PlatformRegistry(tmp_path)
    codes = {p.code for p in registry.list_platforms()}

    assert "TEST_PLATFORM" in codes
    assert len(codes) == len(EXPECTED_PLATFORM_CODES) + 1
