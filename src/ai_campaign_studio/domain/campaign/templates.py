"""Campaign templates (A3).

The initial template lives here as a plain domain constant, not a resource
file. Rationale: there is exactly one template in Slice 1, and the template is
a semantic role sequence (a domain concept), not extensible data-driven
configuration like the platform/provider registries from P0. If templates
become user-extensible later, move them under ``resources/campaign_templates/``
and load them through a small mapper.
"""

from dataclasses import dataclass

from ai_campaign_studio.domain.campaign.roles import CampaignRole


@dataclass(frozen=True)
class CampaignTemplate:
    """A named, ordered sequence of message roles."""

    id: str
    name: str
    role_sequence: tuple[CampaignRole, ...]


LEAD_GENERATION_V1 = CampaignTemplate(
    id="lead_generation_v1",
    name="Lead Generation",
    role_sequence=(
        CampaignRole.PROBLEM,
        CampaignRole.EDUCATION,
        CampaignRole.PROOF,
        CampaignRole.OBJECTION,
        CampaignRole.BENEFIT,
        CampaignRole.OFFER,
        CampaignRole.ACTION,
    ),
)
