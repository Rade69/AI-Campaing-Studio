"""Visual identity adapter (S2-G5).

Owns wiring ``VisualIdentityExtractor`` behind the existing S2-G1
``VisualIdentityExtractorPort`` (no new port, no new VO). Thin adapter:
delegates ``extract(html, base_url)`` and returns ``VisualIdentity``.
"""

from __future__ import annotations

from ai_campaign_studio.domain.brand.value_objects import VisualIdentity
from ai_campaign_studio.infrastructure.visual_extraction.visual_identity_extractor import (  # noqa: E501
    VisualIdentityExtractor,
)
from ai_campaign_studio.ports.web_ingestion import VisualIdentityExtractorPort


class VisualIdentityAdapter(VisualIdentityExtractorPort):
    """``VisualIdentityExtractorPort`` implementation."""

    def __init__(self) -> None:
        self._extractor = VisualIdentityExtractor()

    def extract(self, html: str, base_url: str) -> VisualIdentity:
        return self._extractor.extract(html, base_url)


__all__ = ["VisualIdentityAdapter"]
