"""Content extraction infrastructure (S2-G4).

Owns the S2-G6 EXTRACT-phase building blocks: ``MainContentExtractor`` reduces
one HTML document to its main text (Trafilatura, Q12 spike winner),
``BoilerplateFilter`` removes residual nav/footer/share noise from that text,
and ``Deduplicator`` removes exact-text duplicate ``SourceChunk``s. No
persistence and no orchestration here — G6 wires these together and registers
the surviving chunks through ``IngestionRepositoryPort``.
"""

from ai_campaign_studio.infrastructure.extraction.boilerplate_filter import (
    BoilerplateFilter,
)
from ai_campaign_studio.infrastructure.extraction.deduplicator import (
    Deduplicator,
)
from ai_campaign_studio.infrastructure.extraction.main_content_extractor import (
    MainContentExtractor,
)

__all__ = ["BoilerplateFilter", "Deduplicator", "MainContentExtractor"]
