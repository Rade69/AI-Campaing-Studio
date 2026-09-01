"""Channel / Platform / Format registry port.

Owns the ``PlatformRegistryPort`` contract only. Does not load YAML or
implement registry logic — the concrete adapter is ``channels/registry.py``.
"""

from typing import Protocol

from ai_campaign_studio.channels.definitions import FormatDefinition, PlatformDefinition
from ai_campaign_studio.channels.enums import Channel


class PlatformRegistryPort(Protocol):
    """Framework-neutral interface to the data-driven platform registry."""

    def list_platforms(
        self, channel: Channel | None = None
    ) -> list[PlatformDefinition]:
        """Return enabled platforms, optionally filtered by channel."""
        ...

    def get_platform(self, code: str) -> PlatformDefinition:
        """Return a single platform by code, or raise ``RegistryError``."""
        ...

    def list_formats(self, platform_code: str) -> list[FormatDefinition]:
        """Return enabled formats for a platform."""
        ...

    def get_format(self, platform_code: str, format_code: str) -> FormatDefinition:
        """Return a single format, or raise ``RegistryError``."""
        ...
