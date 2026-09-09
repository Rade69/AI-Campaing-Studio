"""Facts domain enums (A3).

Owns ``FactStatus``. ``PROPOSED`` arrives with the Slice 2 ``FactCandidate``
workflow (S2-G1): a proposed candidate is separate from ``ApprovedFact`` and
must pass human review before it can become one.
"""

from enum import StrEnum


class FactStatus(StrEnum):
    """Lifecycle status of an approved fact version."""

    APPROVED = "APPROVED"
    SUPERSEDED = "SUPERSEDED"
    SOFT_DELETED = "SOFT_DELETED"
    PROPOSED = "PROPOSED"
