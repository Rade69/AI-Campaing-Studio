"""Page-classification use-case (S2-G8).

Owns the application-layer wrapper around page classification so a future
pipeline step (G6 ``_classify_target``) can depend on a stable application
contract instead of the infrastructure ``PageClassifier``. The classifier is
injected through a local ``Protocol`` (same pattern as
``application/ingestion/dependencies.py``) — the application layer MUST NOT
import ``infrastructure``. Pure delegation: URL + content signals in, one
``PageType`` out. No I/O, no persistence, no orchestration here.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ai_campaign_studio.domain.ingestion.enums import PageType


@runtime_checkable
class PageClassifierPort(Protocol):
    """The one method the use-case needs from a classifier."""

    def classify(
        self, url: str, content_type: str | None, body_preview: str
    ) -> PageType: ...


class ClassifyPage:
    """Application-layer use-case delegating to the injected classifier."""

    def __init__(self, classifier: PageClassifierPort) -> None:
        self._classifier = classifier

    def classify(
        self, url: str, content_type: str | None, body_preview: str
    ) -> PageType:
        return self._classifier.classify(url, content_type, body_preview)


__all__ = ["ClassifyPage", "PageClassifierPort"]
