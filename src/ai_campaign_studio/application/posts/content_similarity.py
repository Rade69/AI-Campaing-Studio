"""Cross-post text similarity (A11, dio 2).

Owns a deterministic, dependency-free word-set Jaccard similarity used to
detect near-duplicate generated posts within a campaign. No I/O, no embeddings,
no vector store — same pure-function style as ``claim_linter.py``.
"""

from __future__ import annotations

import re


def jaccard_similarity(text_a: str, text_b: str) -> float:
    """Word-set Jaccard similarity, casefold-normalized. 0.0 if either
    text has zero words after normalization."""
    words_a = set(re.findall(r"\w+", text_a.casefold()))
    words_b = set(re.findall(r"\w+", text_b.casefold()))
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


SIMILARITY_THRESHOLD = 0.6


def is_too_similar_to_any(
    candidate_text: str, existing_texts: tuple[str, ...]
) -> bool:
    return any(
        jaccard_similarity(candidate_text, existing) >= SIMILARITY_THRESHOLD
        for existing in existing_texts
    )
