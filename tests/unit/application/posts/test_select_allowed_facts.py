"""Unit tests for allowed fact selection (A11)."""

from datetime import UTC, datetime

from ai_campaign_studio.application.posts.select_allowed_facts import (
    select_allowed_facts,
)
from ai_campaign_studio.domain.campaign.entities import CampaignItem
from ai_campaign_studio.domain.campaign.enums import CampaignItemStatus
from ai_campaign_studio.domain.campaign.roles import CampaignRole
from ai_campaign_studio.domain.common.ids import CampaignItemId, FactId
from ai_campaign_studio.domain.facts.entities import ApprovedFact, SourceReference
from ai_campaign_studio.domain.facts.enums import FactStatus

_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def _fact(
    fact_id: str, content: str, status: FactStatus = FactStatus.APPROVED
) -> ApprovedFact:
    return ApprovedFact(
        id=FactId(fact_id),
        logical_fact_id=f"logical-{fact_id}",
        version=1,
        content=content,
        source_ref=SourceReference(source_type="fixture", uri="fixture://x"),
        status=status,
        created_at=_CREATED_AT,
    )


def _item(*facts_needed: str) -> CampaignItem:
    return CampaignItem(
        id=CampaignItemId("item-1"),
        order=1,
        role=CampaignRole.PROBLEM,
        topic="Cost",
        goal="Awareness",
        status=CampaignItemStatus.PLANNED,
        facts_needed=facts_needed,
    )


def test_only_usable_facts_selected() -> None:
    facts = (
        _fact("f1", "We offer dental implants", FactStatus.APPROVED),
        _fact("f2", "We offer veneers", FactStatus.SUPERSEDED),
        _fact("f3", "We offer braces", FactStatus.SOFT_DELETED),
    )
    result = select_allowed_facts(_item("implant"), facts)
    assert result.fact_ids == (FactId("f1"),)
    assert FactId("f2") not in result.fact_ids
    assert FactId("f3") not in result.fact_ids


def test_lexical_matching_selects_relevant_fact() -> None:
    facts = (
        _fact("f1", "We offer dental implants"),
        _fact("f2", "We offer teeth whitening"),
    )
    result = select_allowed_facts(_item("IMPLANT"), facts)  # case-insensitive
    assert result.fact_ids == (FactId("f1"),)
    assert result.selection_reasons[FactId("f1")] == "IMPLANT"


def test_empty_facts_needed_yields_empty_set() -> None:
    facts = (_fact("f1", "We offer dental implants"),)
    result = select_allowed_facts(_item(), facts)
    assert result.fact_ids == ()
    assert result.selection_reasons == {}
