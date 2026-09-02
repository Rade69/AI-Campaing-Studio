"""Unit tests for the fact-ID claim validator (A11)."""

from datetime import UTC, datetime

from ai_campaign_studio.application.posts.claim_validator import validate_claim
from ai_campaign_studio.application.posts.select_allowed_facts import AllowedFactSet
from ai_campaign_studio.application.schemas.social_post_generation_output import (
    ContentClaimOutput,
)
from ai_campaign_studio.domain.common.ids import FactId
from ai_campaign_studio.domain.content.enums import ClaimStatus, ClaimType
from ai_campaign_studio.domain.facts.entities import ApprovedFact, SourceReference
from ai_campaign_studio.domain.facts.enums import FactStatus

_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def _fact(fact_id: str) -> ApprovedFact:
    return ApprovedFact(
        id=FactId(fact_id),
        logical_fact_id=f"logical-{fact_id}",
        version=1,
        content="content",
        source_ref=SourceReference(source_type="fixture", uri="fixture://x"),
        status=FactStatus.APPROVED,
        created_at=_CREATED_AT,
    )


class _FakeFactRepository:
    def __init__(self, facts: dict[str, ApprovedFact]) -> None:
        self._facts = facts

    def get_fact(self, fact_id):  # noqa: ANN001
        return self._facts.get(fact_id)

    def save_fact(self, fact) -> None:  # noqa: ANN001
        del fact

    def list_snapshot_facts(self, snapshot_id):  # noqa: ANN001
        del snapshot_id
        return ()


def _allowed(*ids: str) -> AllowedFactSet:
    return AllowedFactSet(fact_ids=tuple(FactId(i) for i in ids), selection_reasons={})


def _claim(type_: ClaimType, *fact_ids: str) -> ContentClaimOutput:
    return ContentClaimOutput(text="claim text", type=type_, fact_ids=list(fact_ids))


def test_fact_not_in_allowed_set_is_unsupported() -> None:
    repo = _FakeFactRepository({"f1": _fact("f1")})
    result = validate_claim(_claim(ClaimType.FACT, "f1"), _allowed(), repo)
    assert result.status is ClaimStatus.UNSUPPORTED
    assert "fact-not-offered" in result.reason_codes


def test_fact_missing_is_unsupported() -> None:
    repo = _FakeFactRepository({})
    result = validate_claim(_claim(ClaimType.FACT, "nope"), _allowed("nope"), repo)
    assert result.status is ClaimStatus.UNSUPPORTED
    assert "fact-not-found" in result.reason_codes


def test_valid_allowed_approved_fact_is_verified() -> None:
    repo = _FakeFactRepository({"f1": _fact("f1")})
    result = validate_claim(_claim(ClaimType.FACT, "f1"), _allowed("f1"), repo)
    assert result.status is ClaimStatus.VERIFIED_BY_FACT
    assert result.fact_ids == (FactId("f1"),)


def test_missing_fact_id_is_unsupported() -> None:
    repo = _FakeFactRepository({"f1": _fact("f1")})
    result = validate_claim(_claim(ClaimType.FACT), _allowed("f1"), repo)
    assert result.status is ClaimStatus.UNSUPPORTED
    assert "missing-fact-id" in result.reason_codes


def test_non_fact_claims_are_non_factual() -> None:
    repo = _FakeFactRepository({})
    for type_ in (ClaimType.CTA, ClaimType.OPINION, ClaimType.CREATIVE):
        result = validate_claim(_claim(type_, "f1"), _allowed(), repo)
        assert result.status is ClaimStatus.NON_FACTUAL
