"""Logging event categories."""

from enum import StrEnum


class EventCategory(StrEnum):
    """High-level event categories for structured logging."""

    UI = "UI"
    APPLICATION = "APPLICATION"
    DOMAIN = "DOMAIN"
    AI = "AI"
    RENDER = "RENDER"
    DATABASE = "DATABASE"
    SOURCE = "SOURCE"
    BACKUP = "BACKUP"
    SYSTEM = "SYSTEM"
    SECURITY = "SECURITY"
