"""Deterministic metrics (A16, §48).

Owns the 11 (plus one heuristic) campaign-level metrics applied identically to
Control A and System B output. Claim-based metrics read the already-linted
``claims`` (status/reason_codes) — they never reimplement linter logic. Text
near-duplicate detection reuses ``content_similarity.jaccard_similarity``.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from ai_campaign_studio.application.evaluation.evaluation_post import EvaluationPost
from ai_campaign_studio.application.posts.content_similarity import (
    SIMILARITY_THRESHOLD,
    jaccard_similarity,
)
from ai_campaign_studio.channels.registry import PlatformRegistry
from ai_campaign_studio.domain.common.errors import RegistryError
from ai_campaign_studio.domain.content.enums import ClaimStatus, ClaimType


@dataclass(frozen=True)
class DeterministicMetrics:
    unique_role_count: int | None
    duplicate_topic_count: int | None
    exact_duplicate_caption_count: int
    unsupported_fact_claim_count: int
    forbidden_phrase_hits: int
    numeric_claim_violations: int
    missing_fact_ids: int
    schema_failure_count: int
    layout_failure_count: None
    headline_overflow_count: int
    cta_unique_count: int
    heuristic_near_duplicate_count: int


def compute_metrics(posts: tuple[EvaluationPost, ...]) -> DeterministicMetrics:
    return DeterministicMetrics(
        unique_role_count=_unique_role_count(posts),
        duplicate_topic_count=_duplicate_topic_count(posts),
        exact_duplicate_caption_count=_exact_duplicate_caption_count(posts),
        unsupported_fact_claim_count=_unsupported_fact_claim_count(posts),
        forbidden_phrase_hits=_forbidden_phrase_hits(posts),
        numeric_claim_violations=_numeric_claim_violations(posts),
        missing_fact_ids=_missing_fact_ids(posts),
        schema_failure_count=0,  # posts arrive already Pydantic-validated
        layout_failure_count=None,  # visual system does not exist yet
        headline_overflow_count=_headline_overflow_count(posts),
        cta_unique_count=_cta_unique_count(posts),
        heuristic_near_duplicate_count=_heuristic_near_duplicate_count(posts),
    )


def _unique_role_count(posts: tuple[EvaluationPost, ...]) -> int | None:
    roles = [post.role for post in posts]
    if any(role is None for role in roles):
        return None
    return len(set(roles))


def _duplicate_topic_count(posts: tuple[EvaluationPost, ...]) -> int | None:
    topics = [post.topic for post in posts]
    if any(topic is None for topic in topics):
        return None
    counts = Counter(topics)
    return sum(count - 1 for count in counts.values() if count > 1)


def _exact_duplicate_caption_count(posts: tuple[EvaluationPost, ...]) -> int:
    # Count posts beyond the first occurrence of each exact caption.
    counts = Counter(post.caption for post in posts)
    return sum(count - 1 for count in counts.values() if count > 1)


def _unsupported_fact_claim_count(posts: tuple[EvaluationPost, ...]) -> int:
    total = 0
    for post in posts:
        for claim in post.claims:
            if claim.status is ClaimStatus.UNSUPPORTED and not any(
                r.startswith("unsupported-") for r in claim.reason_codes
            ):
                total += 1
    return total


def _forbidden_phrase_hits(posts: tuple[EvaluationPost, ...]) -> int:
    return sum(
        1
        for post in posts
        for claim in post.claims
        if claim.status is ClaimStatus.PROHIBITED
    )


def _numeric_claim_violations(posts: tuple[EvaluationPost, ...]) -> int:
    return sum(
        1
        for post in posts
        for claim in post.claims
        if claim.status is ClaimStatus.UNSUPPORTED
        and any(r.startswith("unsupported-") for r in claim.reason_codes)
    )


def _missing_fact_ids(posts: tuple[EvaluationPost, ...]) -> int:
    return sum(
        1
        for post in posts
        for claim in post.claims
        if claim.type is ClaimType.FACT and not claim.fact_ids
    )


def _headline_overflow_count(posts: tuple[EvaluationPost, ...]) -> int:
    registry = PlatformRegistry.from_bundled_resources()
    total = 0
    for post in posts:
        if post.platform_code is None or post.format_code is None:
            continue
        try:
            fmt = registry.get_format(post.platform_code, post.format_code)
        except RegistryError:
            continue
        max_chars = fmt.text_constraints.max_chars
        if max_chars is not None and len(post.headline) > max_chars:
            total += 1
    return total


def _cta_unique_count(posts: tuple[EvaluationPost, ...]) -> int:
    return len({post.cta.casefold() for post in posts})


def _heuristic_near_duplicate_count(posts: tuple[EvaluationPost, ...]) -> int:
    texts = [f"{post.headline} {post.caption}" for post in posts]
    total = 0
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            if jaccard_similarity(texts[i], texts[j]) >= SIMILARITY_THRESHOLD:
                total += 1
    return total
