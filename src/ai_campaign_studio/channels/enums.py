"""Stable marketing channel taxonomy."""

from enum import StrEnum


class Channel(StrEnum):
    """Broad marketing distribution category.

    Only the stable channel taxonomy lives here. Platforms and formats are
    data-driven (see ``channels.definitions`` and ``channels.registry``), so
    there is deliberately no social-platform enum in this module.
    """

    SOCIAL = "SOCIAL"
    EMAIL = "EMAIL"
    WEB = "WEB"
    PAID_AD = "PAID_AD"
    PRINT = "PRINT"
    DIRECT_MESSAGE = "DIRECT_MESSAGE"
