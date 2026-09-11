"""Reproducer tests for ``PageClassifier`` (S2-G8, canonical plan §8).

Deterministic and offline. Verifies URL-path priority, the non-HTML
content-type refinement, and the SPA-shell override (a client-routed SPA
"/blog/x" is HOME, not BLOG).
"""

from __future__ import annotations

import pytest

from ai_campaign_studio.domain.ingestion.enums import PageType
from ai_campaign_studio.infrastructure.web_ingestion.page_classifier import (
    PageClassifier,
)


@pytest.fixture()
def classifier() -> PageClassifier:
    return PageClassifier()


def test_products_path_is_product(classifier: PageClassifier) -> None:
    result = classifier.classify(
        "https://example.com/products/foo", "text/html", ""
    )
    assert result is PageType.PRODUCT


def test_blog_path_is_blog(classifier: PageClassifier) -> None:
    result = classifier.classify(
        "https://example.com/blog/2024/why-x", "text/html", ""
    )
    assert result is PageType.BLOG


def test_root_with_react_marker_is_home(classifier: PageClassifier) -> None:
    result = classifier.classify(
        "https://example.com/", "text/html", '<div id="root"></div>'
    )
    assert result is PageType.HOME


def test_spa_blog_path_collapses_to_home(classifier: PageClassifier) -> None:
    # A client-routed SPA "/blog/x" is a client route, not a real blog post.
    result = classifier.classify(
        "https://example.com/blog/why-x",
        "text/html",
        "<html><body><div id=\"root\"></div></body></html>",
    )
    assert result is PageType.HOME


def test_non_html_content_type_blog_is_not_blog(classifier: PageClassifier) -> None:
    result = classifier.classify(
        "https://example.com/blog/why-x", "application/json", "{}"
    )
    assert result is PageType.OTHER


def test_about_path_is_about(classifier: PageClassifier) -> None:
    result = classifier.classify("https://example.com/about", "text/html", "")
    assert result is PageType.ABOUT
