"""Data-driven ``Channel -> Platform -> Format`` registry (P0.13).

Loads platform definitions from ``resources/platforms/*.yaml``, validates the
schema and cross-file invariants (unique codes, valid channel, existing format
references), and caches the parsed result after a valid load. The registry
never performs network calls, never hardcodes platform behaviour, and never
contains Campaign/Content logic.
"""

from __future__ import annotations

from pathlib import Path

import yaml  # type: ignore[import-untyped]
from pydantic import ValidationError

from ai_campaign_studio.channels.definitions import FormatDefinition, PlatformDefinition
from ai_campaign_studio.channels.enums import Channel
from ai_campaign_studio.domain.common.errors import RegistryError
from ai_campaign_studio.ports.channels import PlatformRegistryPort


class PlatformRegistry(PlatformRegistryPort):
    """Parsed, validated and cached platform registry."""

    def __init__(self, platforms_dir: Path) -> None:
        self._platforms_dir = platforms_dir
        self._platforms: dict[str, PlatformDefinition] = {}
        self._formats: dict[tuple[str, str], FormatDefinition] = {}
        self._loaded = False

    @classmethod
    def from_bundled_resources(cls) -> PlatformRegistry:
        """Point the registry at the bundled ``resources/platforms`` folder."""
        return cls(Path(__file__).resolve().parents[3] / "resources" / "platforms")

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self._load()

    def _load(self) -> None:
        platforms: dict[str, PlatformDefinition] = {}
        formats: dict[tuple[str, str], FormatDefinition] = {}

        for path in sorted(self._platforms_dir.glob("*.yaml")):
            raw = self._read_yaml(path)
            platform = self._build_platform(raw, path)

            if platform.code in platforms:
                raise RegistryError(f"duplicate platform code: {platform.code}")
            platforms[platform.code] = platform

            by_code: dict[str, FormatDefinition] = {}
            for raw_format in raw.get("formats", []):
                fmt = self._build_format(raw_format, path)
                if fmt.code in by_code:
                    raise RegistryError(
                        f"duplicate format code: {platform.code}/{fmt.code}"
                    )
                by_code[fmt.code] = fmt
                formats[(platform.code, fmt.code)] = fmt

            for format_code in platform.supported_formats:
                if format_code not in by_code:
                    raise RegistryError(
                        f"unknown format reference: {platform.code}/{format_code}"
                    )

        self._platforms = platforms
        self._formats = formats
        self._loaded = True

    def list_platforms(
        self, channel: Channel | None = None
    ) -> list[PlatformDefinition]:
        self._ensure_loaded()
        platforms = [p for p in self._platforms.values() if p.enabled]
        if channel is not None:
            platforms = [p for p in platforms if p.channel == channel]
        return platforms

    def get_platform(self, code: str) -> PlatformDefinition:
        self._ensure_loaded()
        key = code.strip().upper()
        platform = self._platforms.get(key)
        if platform is None:
            raise RegistryError(f"unknown platform: {key}")
        return platform

    def list_formats(self, platform_code: str) -> list[FormatDefinition]:
        self._ensure_loaded()
        platform = self.get_platform(platform_code)
        formats = [
            self._formats[(platform.code, code)]
            for code in platform.supported_formats
            if (platform.code, code) in self._formats
        ]
        return [f for f in formats if f.enabled]

    def get_format(self, platform_code: str, format_code: str) -> FormatDefinition:
        self._ensure_loaded()
        platform = self.get_platform(platform_code)
        key = (platform.code, format_code.strip().upper())
        fmt = self._formats.get(key)
        if fmt is None:
            raise RegistryError(f"unknown format: {platform.code}/{key[1]}")
        return fmt

    @staticmethod
    def _read_yaml(path: Path) -> dict:
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise RegistryError(f"malformed YAML in {path.name}: {exc}") from exc
        if not isinstance(raw, dict):
            raise RegistryError(f"platform file must be a mapping: {path.name}")
        return raw

    @staticmethod
    def _build_platform(raw: dict, path: Path) -> PlatformDefinition:
        try:
            return PlatformDefinition.model_validate(raw)
        except ValidationError as exc:
            raise RegistryError(
                f"invalid platform schema in {path.name}: {exc}"
            ) from exc

    @staticmethod
    def _build_format(raw: dict, path: Path) -> FormatDefinition:
        try:
            return FormatDefinition.model_validate(raw)
        except ValidationError as exc:
            raise RegistryError(f"invalid format schema in {path.name}: {exc}") from exc
