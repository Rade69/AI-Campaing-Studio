"""Normalized evaluation post (A16).

Owns the single shape that both Control A and System B map their output into,
so ``deterministic_metrics.py`` never has to know where the data came from.
"""

from __future__ import annotations

from dataclasses import dataclass

from ai_campaign_studio.domain.content.claims import ContentClaim


@dataclass(frozen=True)
class EvaluationPost:
    """One generated post, normalized for metric computation.

    ``role``/``topic``/``platform_code``/``format_code`` are ``None`` for
    Control A (which has no role/topic/target concept); the metric module
    treats ``None`` as "not measurable" rather than "zero".
    """

    role: str | None
    topic: str | None
    headline: str
    caption: str
    hook: str
    body: str
    cta: str
    hashtags: tuple[str, ...]
    platform_code: str | None
    format_code: str | None
    claims: tuple[ContentClaim, ...]
