"""Unit tests for deterministic_metrics (A16)."""

from __future__ import annotations

from ai_campaign_studio.application.evaluation.deterministic_metrics import (
    compute_metrics,
)
from ai_campaign_studio.application.evaluation.evaluation_post import EvaluationPost
from ai_campaign_studio.domain.content.claims import ContentClaim
from ai_campaign_studio.domain.content.enums import ClaimStatus, ClaimType


def _claim(
    status: ClaimStatus = ClaimStatus.VERIFIED_BY_FACT,
    type_: ClaimType = ClaimType.FACT,
    fact_ids: tuple = ("fact-1",),
    reason_codes: tuple = (),
) -> ContentClaim:
    return ContentClaim(
        id="c1",
        text="text",
        type=type_,
        status=status,
        fact_ids=fact_ids,
        reason_codes=reason_codes,
    )


def _post(
    role: str | None = "PROBLEM",
    topic: str | None = "topic",
    headline: str = "headline",
    caption: str = "caption",
    cta: str = "cta",
    claims: tuple = (),
    platform_code: str | None = None,
    format_code: str | None = None,
) -> EvaluationPost:
    return EvaluationPost(
        role=role,
        topic=topic,
        headline=headline,
        caption=caption,
        hook="",
        body="",
        cta=cta,
        hashtags=(),
        platform_code=platform_code,
        format_code=format_code,
        claims=claims,
    )


def test_control_a_none_role_and_topic() -> None:
    m = compute_metrics((_post(role=None, topic=None),))

    assert m.unique_role_count is None
    assert m.duplicate_topic_count is None
    assert m.layout_failure_count is None


def test_system_b_role_and_topic_counts() -> None:
    posts = (
        _post(role="PROBLEM", topic="a"),
        _post(role="PROBLEM", topic="a"),
        _post(role="ACTION", topic="b"),
    )
    m = compute_metrics(posts)

    assert m.unique_role_count == 2  # PROBLEM, ACTION
    assert m.duplicate_topic_count == 1  # "a" appears twice -> 1 duplicate


def test_exact_duplicate_caption_count() -> None:
    posts = (
        _post(caption="c1"),
        _post(caption="c1"),
        _post(caption="c2"),
    )
    m = compute_metrics(posts)

    assert m.exact_duplicate_caption_count == 1  # c1 x2 -> 1 beyond first


def test_claim_based_metrics() -> None:
    posts = (
        _post(
            claims=(
                _claim(status=ClaimStatus.PROHIBITED),
                _claim(
                    status=ClaimStatus.UNSUPPORTED,
                    reason_codes=("unsupported-number",),
                ),
                _claim(
                    status=ClaimStatus.UNSUPPORTED,
                    reason_codes=("fact-not-found",),
                ),
                _claim(
                    status=ClaimStatus.UNSUPPORTED,
                    fact_ids=(),
                    reason_codes=("missing-fact-id",),
                ),
            )
        ),
    )
    m = compute_metrics(posts)

    assert m.forbidden_phrase_hits == 1
    assert m.numeric_claim_violations == 1
    assert m.unsupported_fact_claim_count == 2  # fact-not-found + missing-fact-id
    assert m.missing_fact_ids == 1  # FACT with empty fact_ids


def test_cta_unique_count_casefold() -> None:
    posts = (_post(cta="CTA"), _post(cta="cta"), _post(cta="Other"))
    m = compute_metrics(posts)

    assert m.cta_unique_count == 2  # "cta", "other"


def test_heuristic_near_duplicate() -> None:
    posts = (
        _post(headline="Same", caption="Text"),
        _post(headline="Same", caption="Text"),
    )
    m = compute_metrics(posts)

    assert m.heuristic_near_duplicate_count == 1


def test_headline_overflow_zero_when_no_platform_limit() -> None:
    # Control A (no platform) and Instagram (max_chars null) both -> 0.
    posts = (
        _post(headline="x" * 500, platform_code=None, format_code=None),
        _post(headline="x" * 500, platform_code="INSTAGRAM", format_code="FEED_POST"),
    )
    m = compute_metrics(posts)

    assert m.headline_overflow_count == 0
    assert m.schema_failure_count == 0
