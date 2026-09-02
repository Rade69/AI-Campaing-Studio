"""Allowed fact selection (A11).

Owns the deterministic, AI-free selection of facts a campaign item is allowed
to cite. Only ``is_fact_usable`` facts can be selected; matching is a simple
case-insensitive substring check against fact content/logical id.
"""

from __future__ import annotations

from dataclasses import dataclass

from ai_campaign_studio.domain.campaign.entities import CampaignItem
from ai_campaign_studio.domain.common.ids import FactId
from ai_campaign_studio.domain.facts.entities import ApprovedFact
from ai_campaign_studio.domain.facts.policies import is_fact_usable


@dataclass(frozen=True)
class AllowedFactSet:
    """The facts a campaign item is allowed to cite.

    ``selection_reasons`` maps each selected fact id to the ``facts_needed``
    phrase that matched it (kept as a plain dict per the task contract).
    """

    fact_ids: tuple[FactId, ...]
    selection_reasons: dict[FactId, str]


def select_allowed_facts(
    campaign_item: CampaignItem, snapshot_facts: tuple[ApprovedFact, ...]
) -> AllowedFactSet:
    """Select usable facts matching ``campaign_item.facts_needed``.

    Deterministic lexical matching only — no AI, embeddings or vector DB.
    An empty ``facts_needed`` (or zero matches) yields an empty set, which is
    not an error: the post may still use CTA/OPINION/CREATIVE claims.
    """
    usable = [fact for fact in snapshot_facts if is_fact_usable(fact)]

    fact_ids: list[FactId] = []
    reasons: dict[FactId, str] = {}

    for fact in usable:
        haystacks = (fact.content.casefold(), fact.logical_fact_id.casefold())
        for phrase in campaign_item.facts_needed:
            needle = phrase.casefold()
            if any(needle in haystack for haystack in haystacks):
                if fact.id not in reasons:
                    fact_ids.append(fact.id)
                    reasons[fact.id] = phrase
                break

    return AllowedFactSet(fact_ids=tuple(fact_ids), selection_reasons=reasons)
