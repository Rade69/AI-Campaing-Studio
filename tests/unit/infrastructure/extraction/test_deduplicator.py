"""Unit tests for Deduplicator (S2-G4)."""

from __future__ import annotations

from ai_campaign_studio.domain.common.ids import SourceChunkId, SourceSnapshotId
from ai_campaign_studio.domain.ingestion.entities import SourceChunk
from ai_campaign_studio.infrastructure.extraction import Deduplicator
from ai_campaign_studio.infrastructure.extraction.deduplicator import normalize_text

SNAP = SourceSnapshotId("snap-1")


def _chunk(i: int, text: str) -> SourceChunk:
    return SourceChunk(
        id=SourceChunkId(f"c{i}"),
        snapshot_id=SNAP,
        locator_type="paragraph_index",
        locator=f"p{i}",
        text=text,
    )


def test_normalize_text_casefold_and_whitespace() -> None:
    assert normalize_text("  Hello   World ") == "hello world"
    assert normalize_text("HELLO WORLD") == normalize_text("hello   world")
    assert normalize_text("  ") == ""


def test_five_chunks_three_unique_two_duplicates() -> None:
    chunks = (
        _chunk(1, "Prvi paragraf"),
        _chunk(2, "Drugi paragraf"),
        _chunk(3, "Prvi paragraf"),  # dup of c1
        _chunk(4, "Treći paragraf"),
        _chunk(5, "Drugi paragraf"),  # dup of c2
    )
    result = Deduplicator().deduplicate(chunks)
    assert [c.id for c in result] == ["c1", "c2", "c4"]


def test_duplicate_detection_is_case_and_whitespace_insensitive() -> None:
    chunks = (
        _chunk(1, "Isti tekst"),
        _chunk(2, "  ISTI   TEKST "),
    )
    result = Deduplicator().deduplicate(chunks)
    assert [c.id for c in result] == ["c1"]


def test_empty_input_returns_empty() -> None:
    assert Deduplicator().deduplicate(()) == ()


def test_single_chunk_returns_single_chunk() -> None:
    chunks = (_chunk(1, "Jedini"),)
    result = Deduplicator().deduplicate(chunks)
    assert result == chunks


def test_all_duplicates_returns_one() -> None:
    chunks = (
        _chunk(1, "Isti"),
        _chunk(2, "Isti"),
        _chunk(3, "isti"),
    )
    result = Deduplicator().deduplicate(chunks)
    assert len(result) == 1
    assert result[0].id == "c1"


def test_deterministic_same_input_same_output() -> None:
    chunks = (_chunk(1, "A"), _chunk(2, "B"), _chunk(3, "A"), _chunk(4, "C"))
    first = Deduplicator().deduplicate(chunks)
    second = Deduplicator().deduplicate(chunks)
    assert first == second
    assert [c.id for c in first] == ["c1", "c2", "c4"]
