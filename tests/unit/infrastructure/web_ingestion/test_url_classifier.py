"""Unit tests for the S2-G6 deterministic URL classifier."""

from __future__ import annotations

import pytest

from ai_campaign_studio.domain.ingestion.enums import PageType
from ai_campaign_studio.infrastructure.web_ingestion import UrlClassifier


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://example.com/", PageType.HOME),
        ("https://example.com", PageType.HOME),
        ("https://example.com/home", PageType.HOME),
        ("https://example.com/pocetna", PageType.HOME),
        # EN + BHS variants
        ("https://example.com/about", PageType.ABOUT),
        ("https://example.com/about-us", PageType.ABOUT),
        ("https://example.com/o-nama", PageType.ABOUT),
        ("https://example.com/o-nama.html", PageType.ABOUT),
        ("https://example.com/kontakt", PageType.CONTACT),
        ("https://example.com/contact-us", PageType.CONTACT),
        ("https://example.com/pricing", PageType.PRICING),
        ("https://example.com/cijene", PageType.PRICING),
        ("https://example.com/cenovnik", PageType.PRICING),
        ("https://example.com/faq", PageType.FAQ),
        ("https://example.com/cesta-pitanja", PageType.FAQ),
        ("https://example.com/dostava", PageType.SHIPPING),
        ("https://example.com/povrat-robe", PageType.RETURNS),
        ("https://example.com/usluge", PageType.SERVICE),
        ("https://example.com/proizvodi", PageType.PRODUCT),
        ("https://example.com/proizvod/123", PageType.PRODUCT),
        ("https://example.com/shop/artikal-1", PageType.PRODUCT),
        ("https://example.com/kategorije/obuca", PageType.CATEGORY),
        ("https://example.com/blog", PageType.BLOG),
        ("https://example.com/vijesti", PageType.BLOG),
        ("https://example.com/blog/moja-objava", PageType.BLOG),
        ("https://example.com/clanak/123", PageType.ARTICLE),
        ("https://example.com/privacy-policy", PageType.LEGAL),
        ("https://example.com/uslovi-koristenja", PageType.LEGAL),
        ("https://example.com/nepoznata-stranica-xyz", PageType.OTHER),
    ],
)
def test_classify(url: str, expected: PageType) -> None:
    assert UrlClassifier().classify(url) == expected


def test_basename_takes_priority_over_outer_segment() -> None:
    # The specific leaf page type wins over the section segment.
    assert UrlClassifier().classify("https://example.com/blog/o-nama") == PageType.ABOUT


def test_classifier_is_deterministic() -> None:
    classifier = UrlClassifier()
    url = "https://example.com/proizvod/42"
    assert classifier.classify(url) == classifier.classify(url)
