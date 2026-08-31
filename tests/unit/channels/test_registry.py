"""Unit tests for the platform registry (P0.13)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_campaign_studio.channels.enums import Channel
from ai_campaign_studio.channels.registry import PlatformRegistry
from ai_campaign_studio.domain.common.errors import RegistryError

VALID_PLATFORM = """\
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


def _write(tmp_path: Path, name: str, content: str) -> None:
    (tmp_path / name).write_text(content, encoding="utf-8")


def test_loads_and_lists_platform(tmp_path: Path) -> None:
    _write(tmp_path, "test.yaml", VALID_PLATFORM)
    registry = PlatformRegistry(tmp_path)

    platforms = registry.list_platforms()

    assert [p.code for p in platforms] == ["TEST_PLATFORM"]


def test_duplicate_platform_code_rejected(tmp_path: Path) -> None:
    _write(tmp_path, "a.yaml", VALID_PLATFORM)
    _write(tmp_path, "b.yaml", VALID_PLATFORM)
    registry = PlatformRegistry(tmp_path)

    with pytest.raises(RegistryError):
        registry.list_platforms()


def test_duplicate_format_code_rejected(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "test.yaml",
        """\
code: TEST_PLATFORM
display_name: Test Platform
channel: SOCIAL
supported_formats:
  - TEST_FORMAT
content_rules: []
enabled: true
formats:
  - code: TEST_FORMAT
    display_name: First
  - code: TEST_FORMAT
    display_name: Second
""",
    )
    registry = PlatformRegistry(tmp_path)

    with pytest.raises(RegistryError):
        registry.list_platforms()


def test_unknown_channel_rejected(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "test.yaml",
        """\
code: TEST_PLATFORM
display_name: Test Platform
channel: NOT_A_CHANNEL
supported_formats:
  - TEST_FORMAT
content_rules: []
enabled: true
formats:
  - code: TEST_FORMAT
    display_name: Test Format
""",
    )
    registry = PlatformRegistry(tmp_path)

    with pytest.raises(RegistryError):
        registry.list_platforms()


def test_unknown_format_reference_rejected(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "test.yaml",
        """\
code: TEST_PLATFORM
display_name: Test Platform
channel: SOCIAL
supported_formats:
  - MISSING_FORMAT
content_rules: []
enabled: true
formats:
  - code: TEST_FORMAT
    display_name: Test Format
""",
    )
    registry = PlatformRegistry(tmp_path)

    with pytest.raises(RegistryError):
        registry.list_platforms()


def test_unknown_platform_raises(tmp_path: Path) -> None:
    _write(tmp_path, "test.yaml", VALID_PLATFORM)
    registry = PlatformRegistry(tmp_path)

    with pytest.raises(RegistryError):
        registry.get_platform("NOPE")


def test_unknown_format_raises(tmp_path: Path) -> None:
    _write(tmp_path, "test.yaml", VALID_PLATFORM)
    registry = PlatformRegistry(tmp_path)

    with pytest.raises(RegistryError):
        registry.get_format("TEST_PLATFORM", "NOPE")


def test_disabled_platform_excluded_from_default_list(tmp_path: Path) -> None:
    _write(tmp_path, "enabled.yaml", VALID_PLATFORM)
    _write(
        tmp_path,
        "disabled.yaml",
        """\
code: DISABLED_PLATFORM
display_name: Disabled Platform
channel: SOCIAL
supported_formats:
  - TEST_FORMAT
content_rules: []
enabled: false
formats:
  - code: TEST_FORMAT
    display_name: Test Format
""",
    )
    registry = PlatformRegistry(tmp_path)

    codes = {p.code for p in registry.list_platforms()}

    assert codes == {"TEST_PLATFORM"}
    # Disabled platform is still reachable by explicit code lookup.
    assert registry.get_platform("DISABLED_PLATFORM").enabled is False


def test_list_platforms_filter_by_channel(tmp_path: Path) -> None:
    _write(tmp_path, "social.yaml", VALID_PLATFORM)
    _write(
        tmp_path,
        "email.yaml",
        """\
code: EMAIL_PLATFORM
display_name: Email Platform
channel: EMAIL
supported_formats:
  - NEWSLETTER
content_rules: []
enabled: true
formats:
  - code: NEWSLETTER
    display_name: Newsletter
""",
    )
    registry = PlatformRegistry(tmp_path)

    social = registry.list_platforms(channel=Channel.SOCIAL)

    assert [p.code for p in social] == ["TEST_PLATFORM"]


def test_codes_normalized_to_uppercase(tmp_path: Path) -> None:
    _write(tmp_path, "test.yaml", VALID_PLATFORM)
    registry = PlatformRegistry(tmp_path)

    assert registry.get_platform("test_platform").code == "TEST_PLATFORM"
    assert registry.get_format("test_platform", "test_format").code == "TEST_FORMAT"


def test_list_and_get_format(tmp_path: Path) -> None:
    _write(tmp_path, "test.yaml", VALID_PLATFORM)
    registry = PlatformRegistry(tmp_path)

    formats = registry.list_formats("TEST_PLATFORM")

    assert [f.code for f in formats] == ["TEST_FORMAT"]
    fmt = registry.get_format("TEST_PLATFORM", "TEST_FORMAT")
    assert fmt.display_name == "Test Format"


def test_blank_formats_key_raises_registry_error(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "test.yaml",
        """\
code: TEST_PLATFORM
display_name: Test Platform
channel: SOCIAL
supported_formats:
  - TEST_FORMAT
content_rules: []
enabled: true
formats:
""",
    )
    registry = PlatformRegistry(tmp_path)

    with pytest.raises(RegistryError):
        registry.list_platforms()


def test_returned_collections_are_immutable(tmp_path: Path) -> None:
    _write(tmp_path, "test.yaml", VALID_PLATFORM)
    registry = PlatformRegistry(tmp_path)

    platform = registry.get_platform("TEST_PLATFORM")
    assert isinstance(platform.supported_formats, tuple)

    with pytest.raises(AttributeError):
        platform.supported_formats.clear()  # type: ignore[attr-defined]

    assert [f.code for f in registry.list_formats("TEST_PLATFORM")] == ["TEST_FORMAT"]


def test_duplicate_supported_format_reference_rejected(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "test.yaml",
        """\
code: TEST_PLATFORM
display_name: Test Platform
channel: SOCIAL
supported_formats:
  - STORY
  - story
content_rules: []
enabled: true
formats:
  - code: STORY
    display_name: Story
""",
    )
    registry = PlatformRegistry(tmp_path)

    with pytest.raises(RegistryError):
        registry.list_platforms()
