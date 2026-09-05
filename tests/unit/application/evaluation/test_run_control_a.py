"""Unit tests for run_control_a (A16)."""

from __future__ import annotations

from datetime import UTC, datetime

from ai_campaign_studio.application.evaluation.run_control_a import run_control_a
from ai_campaign_studio.application.posts.claim_linter import ClaimRules
from ai_campaign_studio.domain.brand.entities import BrandSnapshot
from ai_campaign_studio.domain.brand.value_objects import (
    Audience,
    BrandVoice,
    Restriction,
    ServiceDefinition,
    VisualIdentity,
)
from ai_campaign_studio.domain.campaign.entities import CampaignBrief
from ai_campaign_studio.domain.common.ids import (
    BrandId,
    BrandSnapshotId,
    FactId,
)
from ai_campaign_studio.domain.content.entities import CampaignTarget
from ai_campaign_studio.domain.content.enums import ClaimStatus
from ai_campaign_studio.domain.facts.entities import ApprovedFact, SourceReference
from ai_campaign_studio.domain.facts.enums import FactStatus
from ai_campaign_studio.ports.ai import AIRequest, AIResponse
from ai_campaign_studio.ports.prompts import PromptDefinition

_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


class _FakeAiPort:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.request: AIRequest | None = None

    def generate(self, request: AIRequest) -> AIResponse:
        self.request = request
        return AIResponse(
            provider="fake",
            model="fake",
            latency_ms=1,
            structured_payload=self._payload,
        )


class _FakePromptRepository:
    def get(self, name: str, version: str) -> PromptDefinition:
        return PromptDefinition(
            name=name,
            version=version,
            purpose="ab_control",
            input_contract="...",
            output_contract="...",
            language_support="EN/BHS",
            instructions="Write posts.",
        )


def _snapshot() -> BrandSnapshot:
    return BrandSnapshot(
        id=BrandSnapshotId("snap-1"),
        brand_id=BrandId("brand-1"),
        version=1,
        language="BHS",
        locale="BHS_LATIN",
        script="LATIN",
        voice=BrandVoice(formality="friendly"),
        audiences=[Audience(id="a1", name="Adults", description="d")],
        services=[ServiceDefinition(id="s1", name="Implants", description="d")],
        visual_identity=VisualIdentity(),
        restrictions=[Restriction(description="No guarantees.")],
        approved_fact_ids=(FactId("fact-1"),),
        created_at=_CREATED_AT,
    )


def _brief() -> CampaignBrief:
    return CampaignBrief(
        id="brief-1",
        offer="Implants",
        goal="Book consultations",
        audience_text="Adults",
        targets=[
            CampaignTarget(
                channel="SOCIAL", platform_code="INSTAGRAM", format_code="FEED_POST"
            )
        ],
        content_piece_count=2,
        content_language_context="BHS_LATIN",
        created_at=_CREATED_AT,
    )


def _fact() -> ApprovedFact:
    return ApprovedFact(
        id=FactId("fact-1"),
        logical_fact_id="logical-1",
        version=1,
        content="We offer dental implants",
        source_ref=SourceReference(source_type="fixture", uri="fixture://x"),
        status=FactStatus.APPROVED,
        created_at=_CREATED_AT,
    )


def _post_payload() -> dict:
    return {
        "posts": [
            {
                "headline": "H1",
                "caption": "C1",
                "hook": "",
                "body": "",
                "cta": "CTA",
                "hashtags": [],
                "claims": [],
            },
            {
                "headline": "H2",
                "caption": "C2",
                "hook": "",
                "body": "",
                "cta": "CTA",
                "hashtags": [],
                "claims": [],
            },
        ]
    }


def test_run_control_a_returns_normalized_posts() -> None:
    ai = _FakeAiPort(_post_payload())
    posts = run_control_a(
        _snapshot(), (_fact(),), _brief(), _FakePromptRepository(), ai,
        ClaimRules(prohibited_terms=(), currency_symbols=()),
    )

    assert len(posts) == 2
    assert all(p.role is None and p.topic is None for p in posts)
    assert all(p.platform_code is None and p.format_code is None for p in posts)
    assert ai.request is not None
    assert ai.request.prompt_name == "ab_control"


def test_run_control_a_lints_claims() -> None:
    payload = {
        "posts": [
            {
                "headline": "H",
                "caption": "C",
                "hook": "",
                "body": "",
                "cta": "CTA",
                "hashtags": [],
                "claims": [
                    {"text": "Mi smo najbolji", "type": "FACT", "fact_ids": ["fact-1"]}
                ],
            }
        ]
    }
    ai = _FakeAiPort(payload)
    rules = ClaimRules(prohibited_terms=("najbolji",), currency_symbols=())

    posts = run_control_a(
        _snapshot(), (_fact(),), _brief(), _FakePromptRepository(), ai, rules
    )

    assert posts[0].claims[0].status is ClaimStatus.PROHIBITED
