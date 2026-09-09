"""Unit tests for the web-ingestion ports (S2-G1)."""

import inspect
from dataclasses import FrozenInstanceError
from typing import Protocol

import pytest

from ai_campaign_studio.ports import web_ingestion

_ALL_PORTS = [
    "HttpFetcherPort",
    "SitemapReaderPort",
    "UrlClassifierPort",
    "MainContentExtractorPort",
    "VisualIdentityExtractorPort",
    "DocumentExtractorPort",
]


def test_six_web_ingestion_ports_are_defined() -> None:
    for name in _ALL_PORTS:
        cls = getattr(web_ingestion, name)
        assert issubclass(cls, Protocol)


def test_all_port_signatures_are_synchronous() -> None:
    """§5 decision (fixed in ACS-S2-001): every port method is ``def``,
    never ``async def``."""
    methods = [
        web_ingestion.HttpFetcherPort.fetch,
        web_ingestion.SitemapReaderPort.list_urls,
        web_ingestion.UrlClassifierPort.classify,
        web_ingestion.MainContentExtractorPort.extract,
        web_ingestion.VisualIdentityExtractorPort.extract,
        web_ingestion.DocumentExtractorPort.extract,
    ]
    for method in methods:
        assert not inspect.iscoroutinefunction(method), (
            f"{method.__qualname__} must be synchronous"
        )


def test_transport_shapes_are_frozen() -> None:
    fetch = web_ingestion.FetchResult(
        url="https://example.com/", final_url="https://example.com/",
        status_code=200, content=b"<html></html>",
    )
    with pytest.raises(FrozenInstanceError):
        fetch.status_code = 500

    chunk = web_ingestion.ExtractedChunk(
        locator_type="css_selector", locator="#main", text="text",
    )
    with pytest.raises(FrozenInstanceError):
        chunk.text = "changed"
