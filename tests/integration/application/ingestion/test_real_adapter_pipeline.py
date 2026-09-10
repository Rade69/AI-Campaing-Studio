"""BF-5: full DISCOVER→DONE pipeline on REAL G3/G4/G5 adapters.

Spins up a small local ``http.server`` fixture that serves the S2-G4 corpus
article (klix.ba-article.html, reused from disk — not duplicated) and drives
the pipeline with the real ``HttpFetcher``, ``DomainDiscovery``,
``MainContentExtractor``, ``VisualIdentityAdapter``, ``UrlClassifier`` and
``CrawlBudget``. The SSRF policy stays untouched: its injectable
``dns_resolver``/``allowed_ports`` are overridden so the loopback fixture is
reachable without weakening the production guard.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from ai_campaign_studio.application.ingestion import IngestBrandSources
from ai_campaign_studio.domain.common.ids import BrandId
from ai_campaign_studio.domain.ingestion.enums import (
    CrawlTargetState,
    IngestionRunStatus,
)
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories import (
    SqliteIngestionRepository,
)
from ai_campaign_studio.infrastructure.extraction import (
    BoilerplateFilter,
    Deduplicator,
    MainContentExtractor,
)
from ai_campaign_studio.infrastructure.visual_extraction import VisualIdentityAdapter
from ai_campaign_studio.infrastructure.web_ingestion import (
    CrawlBudget,
    DomainDiscovery,
    HttpFetcher,
    RobotsReader,
    SitemapReader,
    UrlClassifier,
    UrlSafetyPolicy,
    normalize_url,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]
_MIGRATIONS_DIR = _REPO_ROOT / "resources" / "migrations"
_CORPUS_ARTICLE = (
    _REPO_ROOT
    / "spikes"
    / "extraction-benchmark"
    / "corpus"
    / "klix.ba-article.html"
)


def _make_server(article_html: bytes) -> tuple[ThreadingHTTPServer, str]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/":
                body = article_html
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()

        def log_message(self, fmt: str, *args: object) -> None:  # noqa: ARG002
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    return server, f"http://localhost:{server.server_address[1]}/"


def test_real_adapter_full_pipeline(tmp_path: Path) -> None:
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)
    connection.execute(
        "INSERT OR IGNORE INTO brands (id, name, created_at) VALUES (?, ?, ?)",
        ("brand-1", "Brand", datetime(2026, 1, 1, tzinfo=UTC).isoformat()),
    )
    connection.commit()

    article_html = _CORPUS_ARTICLE.read_bytes()
    server, base_url = _make_server(article_html)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        policy = UrlSafetyPolicy(
            allowed_ports=frozenset({port}),
            dns_resolver=lambda host: ("93.184.216.34",),
        )
        fetcher = HttpFetcher(policy=policy)
        budget = CrawlBudget(politeness_seconds=0.0, sleeper=lambda _s: None)
        discovery = DomainDiscovery(
            fetcher=fetcher,
            robots=RobotsReader(fetcher),
            sitemaps=SitemapReader(fetcher),
            policy=policy,
            budget=budget,
            max_urls=1,
        )
        main_extractor = MainContentExtractor()
        use_case = IngestBrandSources(
            repository=SqliteIngestionRepository(connection),
            fetcher=fetcher,
            classifier=UrlClassifier(),
            discovery=discovery,
            budget=budget,
            normalizer=normalize_url,
            visual_identity_extractor=VisualIdentityAdapter(),
            content_extractor=main_extractor.extract,
            boilerplate_filter=BoilerplateFilter().filter,
            deduplicator=Deduplicator().deduplicate,
            document_extractors={},
        )

        run = use_case.execute(BrandId("brand-1"), (base_url,))

        assert run.status is IngestionRunStatus.SUCCEEDED
        repository = SqliteIngestionRepository(connection)
        targets = repository.list_crawl_targets_by_run(run.id)
        assert len(targets) == 1
        assert targets[0].state is CrawlTargetState.DONE
        assert run.stats.fetched_pages == 1
        assert run.stats.extracted_chunks >= 1
        assert run.stats.built_candidates >= 1
    finally:
        server.shutdown()
        server.server_close()
