"""Facts domain enums (A3).

Owns ``FactStatus``. Slice 1 has no ``PROPOSED`` status — that arrives with
the Slice 2 ``FactCandidate`` workflow.
"""

from enum import StrEnum


class FactStatus(StrEnum):
    """Lifecycle status of an approved fact version."""

    APPROVED = "APPROVED"
    SUPERSEDED = "SUPERSEDED"
    SOFT_DELETED = "SOFT_DELETED"
