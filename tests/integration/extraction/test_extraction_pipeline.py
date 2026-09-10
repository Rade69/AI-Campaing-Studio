"""Integration tests for the S2-G4 extraction pipeline."""

from __future__ import annotations

from ai_campaign_studio.domain.common.ids import SourceChunkId, SourceSnapshotId
from ai_campaign_studio.domain.ingestion.entities import SourceChunk
from ai_campaign_studio.infrastructure.extraction import (
    BoilerplateFilter,
    Deduplicator,
    MainContentExtractor,
)

SNAP = SourceSnapshotId("snap-1")

ARTICLE_HTML = """<html>
<head><title>Vijest</title></head>
<body>
<nav>Naslovna | Sport | Kontakt</nav>
<main>
<h1>Apple predstavio iPhone 18 Pro</h1>
<p>Kompanija je predstavila novu generaciju telefona sa unapređenim kamerama.</p>
<p>Uređaje pokreće novi A20 Pro čip izrađen u dvonanometarskoj tehnologiji.</p>
<p>Cijene počinju od 1.199 dolara.</p>
</main>
<footer>© 2026 Sva prava zadržana</footer>
</body>
</html>"""


def _chunk(i: int, text: str) -> SourceChunk:
    return SourceChunk(
        id=SourceChunkId(f"c{i}"),
        snapshot_id=SNAP,
        locator_type="paragraph_index",
        locator=f"p{i}",
        text=text,
    )


def test_extract_filter_dedup_pipeline() -> None:
    extractor = MainContentExtractor()
    boiler = BoilerplateFilter()
    dedup = Deduplicator()

    # Works with real Trafilatura when installed, else falls back to raw text.
    text = extractor.extract(ARTICLE_HTML)
    assert text.strip()

    cleaned = boiler.filter(text)
    assert cleaned.strip()

    # Materialise paragraphs into chunks (simulating the G6 chunking step),
    # then de-duplicate: an injected exact duplicate must be removed.
    paragraphs = [p for p in cleaned.split("\n\n") if p.strip()]
    chunks = tuple(_chunk(i, p) for i, p in enumerate(paragraphs, start=1))
    assert chunks

    duplicate = _chunk(len(chunks) + 1, chunks[0].text)
    deduped = dedup.deduplicate((*chunks, duplicate))
    assert deduped == chunks
    assert len(deduped) == len(chunks)


def test_extract_preserves_core_content_with_trafilatura() -> None:
    import pytest

    pytest.importorskip("trafilatura")
    text = MainContentExtractor().extract(ARTICLE_HTML)
    assert "A20 Pro" in text
    assert "1.199 dolara" in text
    assert "Kontakt" not in text
    assert "Sva prava zadržana" not in text
