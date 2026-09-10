"""Chunk deduplicator (S2-G4).

Owns removing exact-text duplicate ``SourceChunk``s. "Duplicate" = identical
text after case-folding + whitespace normalization; the FIRST occurrence (in
input order) is kept and later ones are dropped. Pure Python, no dependencies,
fully deterministic (same input -> same output order). Does NOT persist
anything — the S2-G6 pipeline registers the surviving chunks through
``IngestionRepositoryPort``.

Near-duplicate (Jaccard) matching is deliberately OUT of scope: the S2-G4
contract says exact match is sufficient for this gate; a similarity threshold
would require tuning and is deferred.
"""

from __future__ import annotations

from ai_campaign_studio.domain.ingestion.entities import SourceChunk


def normalize_text(text: str) -> str:
    """Case-fold + collapse whitespace to a single canonical token sequence."""
    return " ".join(text.casefold().split())


class Deduplicator:
    """Remove exact-text duplicate chunks, preserving input order."""

    def deduplicate(self, chunks: tuple[SourceChunk, ...]) -> tuple[SourceChunk, ...]:
        """Return ``chunks`` with exact-text duplicates removed.

        Deterministic: input order is preserved and the first chunk of each
        distinct normalized text is kept. Empty input -> empty output.
        """
        seen: set[str] = set()
        kept: list[SourceChunk] = []
        for chunk in chunks:
            key = normalize_text(chunk.text)
            if key in seen:
                continue
            seen.add(key)
            kept.append(chunk)
        return tuple(kept)


__all__ = ["Deduplicator", "normalize_text"]
