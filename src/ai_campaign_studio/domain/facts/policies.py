"""Facts domain policies (A3).

Owns the fact-usability rules and immutable version creation. Versioning is
immutable-replace: ``create_next_fact_version`` returns a brand-new
``ApprovedFact`` and never mutates the previous fact's text or status.
"""

from __future__ import annotations

from ai_campaign_studio.domain.common.errors import InvariantViolation
from ai_campaign_studio.domain.common.ids import FactId, new_id
from ai_campaign_studio.domain.common.timestamps import utc_now
from ai_campaign_studio.domain.facts.entities import ApprovedFact, SourceReference
from ai_campaign_studio.domain.facts.enums import FactStatus


def is_fact_usable(fact: ApprovedFact) -> bool:
    """Return True only if the fact may be used for content generation."""
    return fact.status is FactStatus.APPROVED


def assert_fact_usable(fact: ApprovedFact) -> None:
    """Raise ``InvariantViolation`` if the fact is not usable."""
    if not is_fact_usable(fact):
        raise InvariantViolation(
            f"fact {fact.id} is not usable (status={fact.status.value})"
        )


def create_next_fact_version(
    previous: ApprovedFact,
    new_content: str,
    source_ref: SourceReference,
) -> ApprovedFact:
    """Return a new APPROVED version of ``previous`` with ``version + 1``.

    Immutable-replace: the returned fact is a fresh object; ``previous`` is
    left completely untouched (same ``content``, same ``status``, same
    ``superseded_by``). Marking ``previous`` as ``SUPERSEDED`` is deliberately
    NOT done here — that requires constructing a separate immutable snapshot
    of the previous fact and is the caller's/persistence layer's
    responsibility (this function returns only one object).
    """
    return ApprovedFact(
        id=FactId(new_id()),
        logical_fact_id=previous.logical_fact_id,
        version=previous.version + 1,
        content=new_content,
        source_ref=source_ref,
        status=FactStatus.APPROVED,
        created_at=utc_now(),
    )
