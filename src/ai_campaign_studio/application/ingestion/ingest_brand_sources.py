"""Website/Brand ingestion pipeline use-case (S2-G6).

Owns the DISCOVER→CLASSIFY→FETCH→RENDER→EXTRACT→BUILD_FACTS→DONE
orchestration over the existing S2-G1/G2 ports and G3/G4/G5/G9 adapters
(canonical plan §10 S2-G6). Every dependency is injected (ports + small
structural callables) because the application layer MUST NOT import
``infrastructure`` (architecture boundary); the composition root wires the
concrete G3/G4/G5/G9 objects. A checkpoint is written AFTER each phase
("honest cancellation"), ``recover_expired_leases`` runs at start so a killed
run resumes with zero duplicate/lost work (G-WI-RECOVER), and BUILD_FACTS is a
deterministic 1:1 chunk→candidate mapping (NO LLM). Does not fetch HTTP,
parse HTML, or persist SQL itself — never bypasses those reviewed layers.
"""

from __future__ import annotations

import hashlib
import logging
import tempfile
from collections.abc import Callable
from datetime import datetime
from functools import partial
from pathlib import Path
from urllib.parse import urlsplit

from ai_campaign_studio.application.ingestion.dependencies import (
    BoilerplateFilterCallable,
    ContentExtractCallable,
    CrawlBudgetDependency,
    DeduplicatorCallable,
    DiscoveryDependency,
    DocumentExtractCallable,
)
from ai_campaign_studio.domain.common.ids import (
    BrandId,
    CrawlTargetId,
    FactCandidateId,
    IngestionCheckpointId,
    IngestionRunId,
    SourceChunkId,
    SourceSnapshotId,
)
from ai_campaign_studio.domain.common.timestamps import utc_now
from ai_campaign_studio.domain.facts.entities import FactCandidate
from ai_campaign_studio.domain.facts.enums import FactStatus
from ai_campaign_studio.domain.ingestion.entities import (
    CrawlTarget,
    IngestionCheckpoint,
    IngestionRun,
    IngestionRunStats,
    SourceChunk,
    SourceSnapshot,
)
from ai_campaign_studio.domain.ingestion.enums import (
    CrawlTargetState,
    IngestionPhase,
    IngestionRunStatus,
    PageType,
)
from ai_campaign_studio.jobs.cancellation import CancellationError, CancellationToken
from ai_campaign_studio.jobs.manager import JobManager
from ai_campaign_studio.ports.repositories import IngestionRepositoryPort
from ai_campaign_studio.ports.web_ingestion import (
    HttpFetcherPort,
    UrlClassifierPort,
    VisualIdentityExtractorPort,
)

_LOGGER = logging.getLogger(__name__)

_DEFAULT_LEASE_SECONDS = 120
_DEFAULT_MAX_FETCH_ATTEMPTS = 3
_DOCUMENT_EXTENSIONS = frozenset({"pdf", "docx", "xlsx"})

# Content-Type → document extractor key for extensionless URLs (BF-3).
_DOCUMENT_MIME_TYPES: dict[str, str] = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
}

# Coarse fetch priority by page type (higher = claimed first).
_PRIORITY_BY_PAGE_TYPE: dict[PageType, int] = {
    PageType.HOME: 100,
    PageType.ABOUT: 90,
    PageType.CONTACT: 85,
    PageType.PRICING: 85,
    PageType.FAQ: 80,
    PageType.SHIPPING: 80,
    PageType.RETURNS: 80,
    PageType.SERVICE: 75,
    PageType.PRODUCT: 70,
    PageType.CATEGORY: 65,
    PageType.BLOG: 60,
    PageType.ARTICLE: 60,
    PageType.LEGAL: 50,
    PageType.OTHER: 40,
}


def _stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}:{digest}"


def _host_of(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def _document_extension(url: str) -> str | None:
    path = urlsplit(url).path.lower()
    suffix = Path(path).suffix.lstrip(".")
    return suffix if suffix in _DOCUMENT_EXTENSIONS else None


def _document_mime_extension(content_type: str | None) -> str | None:
    if content_type is None:
        return None
    mime = content_type.split(";")[0].strip().lower()
    return _DOCUMENT_MIME_TYPES.get(mime)


class IngestBrandSources:
    """DISCOVER→DONE ingestion pipeline for one brand, job-backed on demand."""

    def __init__(
        self,
        *,
        repository: IngestionRepositoryPort,
        fetcher: HttpFetcherPort,
        classifier: UrlClassifierPort,
        discovery: DiscoveryDependency,
        budget: CrawlBudgetDependency,
        normalizer: Callable[[str], str],
        visual_identity_extractor: VisualIdentityExtractorPort,
        content_extractor: ContentExtractCallable,
        boilerplate_filter: BoilerplateFilterCallable,
        deduplicator: DeduplicatorCallable,
        document_extractors: dict[str, DocumentExtractCallable],
        job_manager: JobManager | None = None,
        lease_duration_seconds: int = _DEFAULT_LEASE_SECONDS,
        max_fetch_attempts: int = _DEFAULT_MAX_FETCH_ATTEMPTS,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._repository = repository
        self._fetcher = fetcher
        self._classifier = classifier
        self._discovery = discovery
        self._budget = budget
        self._normalizer = normalizer
        self._visual_identity = visual_identity_extractor
        self._content_extractor = content_extractor
        self._boilerplate_filter = boilerplate_filter
        self._deduplicator = deduplicator
        self._document_extractors = document_extractors
        self._job_manager = job_manager
        self._lease_duration_seconds = lease_duration_seconds
        self._max_fetch_attempts = max_fetch_attempts
        self._clock = clock
        # Per-execute in-memory state (raw bodies for the EXTRACT phase and
        # retry accounting). Reset at the start of every ``execute`` call.
        self._raw_bodies: dict[str, bytes] = {}
        self._attempts: dict[str, int] = {}

    # --- public entry points ---

    def submit(
        self,
        brand_id: BrandId,
        source_scope: tuple[str, ...],
        *,
        run_id: str | None = None,
    ) -> str:
        """Schedule ``execute`` on the ``JobManager`` and return its job id."""
        if self._job_manager is None:
            raise RuntimeError("IngestBrandSources.submit requires a JobManager")
        func = partial(self.execute, brand_id, source_scope, run_id=run_id)
        return self._job_manager.submit("ingest_brand_sources", func)

    def execute(
        self,
        brand_id: BrandId,
        source_scope: tuple[str, ...],
        *,
        run_id: str | None = None,
        token: CancellationToken | None = None,
    ) -> IngestionRun:
        """Run the full pipeline synchronously and return the final run.

        ``token`` is injected by ``JobManager.submit`` when available; it is
        checked at least once per loop iteration so cancellation is
        cooperative. ``run_id`` allows resuming an existing run.
        """
        self._raw_bodies = {}
        self._attempts = {}

        resolved_run_id = (
            IngestionRunId(run_id)
            if run_id
            else IngestionRunId(
                _stable_id("run", f"{brand_id}:{utc_now().isoformat()}")
            )
        )
        run = IngestionRun(
            id=resolved_run_id,
            brand_id=brand_id,
            status=IngestionRunStatus.RUNNING,
            started_at=self._clock(),
            source_scope=tuple(source_scope),
        )
        self._repository.save_ingestion_run(run)

        # G-WI-RECOVER: requeue any LEASED target whose lease expired (a run
        # killed mid-FETCH) BEFORE the fetch loop claims anything.
        recovered = self._repository.recover_expired_leases(resolved_run_id)
        if recovered:
            _LOGGER.info(
                "recovered_expired_leases run=%s count=%d", resolved_run_id, recovered
            )

        try:
            discovered = self._discover(resolved_run_id, run.source_scope, token)
            self._progress(token, 0, discovered, IngestionPhase.DISCOVER)
            # Checkpoint AFTER the phase completes (honest cancellation): a
            # cancel raised during discovery must NOT mark DISCOVER done.
            self._checkpoint(run, IngestionPhase.DISCOVER, token)

            # CLASSIFY is folded into DISCOVER (page_type_hint is set on the
            # registered CrawlTarget); the checkpoint keeps the state machine
            # complete for later content-signal refinement.
            self._checkpoint(run, IngestionPhase.CLASSIFY, token)

            _fetched, _failed = self._fetch(resolved_run_id, discovered, token)
            self._checkpoint(run, IngestionPhase.FETCH, token)

            # RENDER is a no-op in v1 (Playwright fallback is S2-G8).
            self._checkpoint(run, IngestionPhase.RENDER, token)

            chunks_saved = self._extract(resolved_run_id, token)
            self._checkpoint(run, IngestionPhase.EXTRACT, token)

            self._build_facts(resolved_run_id, chunks_saved, token)
            self._checkpoint(run, IngestionPhase.BUILD_FACTS, token)

            run = IngestionRun(
                id=run.id,
                brand_id=run.brand_id,
                status=IngestionRunStatus.SUCCEEDED,
                started_at=run.started_at,
                finished_at=self._clock(),
                source_scope=run.source_scope,
                stats=self._compute_run_stats(resolved_run_id),
            )
            self._repository.save_ingestion_run(run)
            self._checkpoint(run, IngestionPhase.DONE, token)
            return run
        except CancellationError:
            cancelled_run = IngestionRun(
                id=run.id,
                brand_id=run.brand_id,
                status=IngestionRunStatus.CANCELLED,
                started_at=run.started_at,
                finished_at=self._clock(),
                source_scope=run.source_scope,
            )
            self._repository.save_ingestion_run(cancelled_run)
            raise
        except Exception:
            failed_run = IngestionRun(
                id=run.id,
                brand_id=run.brand_id,
                status=IngestionRunStatus.FAILED,
                started_at=run.started_at,
                finished_at=self._clock(),
                source_scope=run.source_scope,
            )
            self._repository.save_ingestion_run(failed_run)
            raise

    # --- phases ---

    def _discover(
        self,
        run_id: IngestionRunId,
        source_scope: tuple[str, ...],
        token: CancellationToken | None,
    ) -> int:
        unique: dict[str, None] = {}
        for start_url in source_scope:
            self._raise_if_cancelled(token)
            try:
                found = self._discovery.discover(start_url)
            except Exception as exc:  # noqa: BLE001 - discovery misses are non-fatal
                _LOGGER.warning("discovery_failed url=%s error=%s", start_url, exc)
                continue
            for candidate in found:
                try:
                    normalized = self._normalizer(candidate)
                except ValueError:
                    continue
                unique.setdefault(normalized, None)

        targets: list[CrawlTarget] = []
        for normalized in unique:
            try:
                page_type = self._classifier.classify(normalized)
            except Exception:  # noqa: BLE001
                page_type = PageType.OTHER
            targets.append(
                CrawlTarget(
                    id=CrawlTargetId(_stable_id(run_id, normalized)),
                    run_id=run_id,
                    normalized_url=normalized,
                    depth=0,
                    priority=_PRIORITY_BY_PAGE_TYPE.get(page_type, 40),
                    state=CrawlTargetState.PENDING,
                    attempts=0,
                    page_type_hint=page_type,
                )
            )
        # Idempotent (ON CONFLICT DO NOTHING) — safe for restart/recrawl.
        self._repository.register_crawl_targets(targets)
        return len(targets)

    def _fetch(
        self,
        run_id: IngestionRunId,
        total: int,
        token: CancellationToken | None,
    ) -> tuple[int, int]:
        fetched = 0
        failed = 0
        processed = 0
        # R2-BF-1 (opcija A): the raw body is deliberately NOT persisted in
        # ``raw_content_ref`` (that field is a reference, not inline payload),
        # so a resume has no in-memory bytes for any target an earlier run
        # left FETCHED. Requeue those targets to PENDING so the claim loop
        # below refetches them (``save_source_snapshot`` upserts on the same
        # deterministic id).
        for stale in self._repository.list_crawl_targets_by_run(run_id):
            if (
                stale.state is CrawlTargetState.FETCHED
                and stale.snapshot_id is not None
            ):
                self._repository.update_crawl_target_state(
                    stale.id,
                    CrawlTargetState.PENDING,
                    last_error="missing_raw_body_refetch",
                )
        while True:
            self._raise_if_cancelled(token)
            target = self._repository.claim_next_crawl_target(
                run_id, self._lease_duration_seconds
            )
            if target is None:
                break
            processed += 1
            domain = _host_of(target.normalized_url)

            if not self._budget.can_crawl(domain):
                self._repository.update_crawl_target_state(
                    target.id,
                    CrawlTargetState.CANCELLED,
                    last_error="crawl_budget_exceeded",
                )
                continue

            self._budget.wait_politeness(domain)
            result = self._fetcher.fetch(target.normalized_url)
            self._budget.record_fetch(domain)

            if result.error is not None:
                failed += 1
                if result.error.startswith("unsafe:"):
                    self._repository.update_crawl_target_state(
                        target.id,
                        CrawlTargetState.SKIPPED_UNSAFE,
                        last_error=result.error,
                    )
                    continue
                attempts = self._attempts.get(str(target.id), 0) + 1
                self._attempts[str(target.id)] = attempts
                if attempts >= self._max_fetch_attempts:
                    self._repository.update_crawl_target_state(
                        target.id, CrawlTargetState.FAILED, last_error=result.error
                    )
                else:
                    # Requeue for another attempt within this run.
                    self._repository.update_crawl_target_state(
                        target.id,
                        CrawlTargetState.PENDING,
                        last_error=result.error,
                    )
                self._progress(token, processed, total, IngestionPhase.FETCH)
                continue

            content = result.content or b""
            content_hash = hashlib.sha256(content).hexdigest()
            base_snapshot_id = SourceSnapshotId(
                _stable_id(run_id, target.normalized_url)
            )
            previous_snapshot_id = target.snapshot_id or base_snapshot_id
            previous_snapshot = self._repository.get_source_snapshot(
                previous_snapshot_id
            )
            snapshot_id = base_snapshot_id
            if previous_snapshot is not None:
                if previous_snapshot.content_hash == content_hash:
                    # Same bytes after a crash: reuse the prior identity so
                    # save remains an idempotent upsert.
                    snapshot_id = previous_snapshot.id
                else:
                    # A recovery refetch can observe newer page content. Keep
                    # the earlier snapshot/chunks immutable and start a fresh
                    # provenance chain for the new bytes.
                    snapshot_id = SourceSnapshotId(
                        _stable_id(
                            run_id,
                            f"{target.normalized_url}:{content_hash}",
                        )
                    )
            snapshot = SourceSnapshot(
                id=snapshot_id,
                url=target.normalized_url,
                fetched_at=self._clock(),
                content_hash=content_hash,
                content_type=result.content_type,
                status_code=result.status_code,
            )
            self._repository.save_source_snapshot(snapshot)
            self._raw_bodies[str(snapshot.id)] = content
            self._repository.update_crawl_target_state(
                target.id, CrawlTargetState.FETCHED, snapshot_id=snapshot.id
            )
            fetched += 1
            # Honest cancellation: a cancel requested DURING fetch propagates
            # only AFTER the snapshot+state are durable, so the run reports
            # CANCELLED while the persisted work is recoverable on resume (BF-1).
            self._raise_if_cancelled(token)
            self._progress(token, processed, total, IngestionPhase.FETCH)
        return fetched, failed

    def _extract(
        self, run_id: IngestionRunId, token: CancellationToken | None
    ) -> int:
        targets = [
            target
            for target in self._repository.list_crawl_targets_by_run(run_id)
            if target.snapshot_id is not None
            and target.state is CrawlTargetState.FETCHED
        ]
        total = len(targets)
        saved = 0
        for index, target in enumerate(targets, start=1):
            self._raise_if_cancelled(token)
            snapshot_id = target.snapshot_id
            if snapshot_id is None:
                continue
            snapshot = self._repository.get_source_snapshot(snapshot_id)
            if snapshot is None:
                continue
            chunks = self._extract_snapshot(snapshot, run_id, target, token)
            for chunk in chunks:
                self._raise_if_cancelled(token)
                self._repository.save_source_chunk(chunk)
                saved += 1
            self._repository.update_crawl_target_state(
                target.id, CrawlTargetState.EXTRACTED
            )
            self._progress(token, index, total, IngestionPhase.EXTRACT)
        return saved

    def _extract_snapshot(
        self,
        snapshot: SourceSnapshot,
        run_id: IngestionRunId,
        target: CrawlTarget,
        token: CancellationToken | None,
    ) -> tuple[SourceChunk, ...]:
        content = self._raw_bodies.get(str(snapshot.id))
        if content is None:
            # R2-BF-1: the raw body is never stored inline in
            # ``raw_content_ref`` (that field is a reference), so a resume
            # recovers the bytes via refetch (see ``_fetch`` requeue). A
            # missing in-memory body here is a defensive no-op — we never
            # decode ``raw_content_ref`` as if it were a payload.
            _LOGGER.warning("extract_missing_raw_body snapshot=%s", snapshot.id)
            return ()

        extension = _document_extension(target.normalized_url)
        if extension is None:
            extension = _document_mime_extension(snapshot.content_type)
        if extension is not None and extension in self._document_extractors:
            return self._extract_document(
                content, extension, run_id, snapshot.id, token
            )

        content_type = (snapshot.content_type or "").lower()
        if "text/html" not in content_type and "html" not in content_type:
            return ()

        html = content.decode("utf-8", errors="replace")
        if target.page_type_hint in (PageType.HOME, PageType.ABOUT):
            self._extract_visual_identity(html, snapshot.url)
        text = self._content_extractor(html, snapshot.url)
        text = self._boilerplate_filter(text)
        paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
        chunks = tuple(
            SourceChunk(
                id=SourceChunkId(f"{snapshot.id}:c{position}"),
                snapshot_id=snapshot.id,
                locator_type="paragraph",
                locator=f"p{position}",
                text=paragraph,
            )
            for position, paragraph in enumerate(paragraphs)
        )
        return self._deduplicator(chunks)

    def _extract_visual_identity(self, html: str, url: str) -> None:
        """Call the injected visual-identity extractor for HOME/ABOUT (BF-4).

        G6 scope is only to invoke and log the signal — NOT to persist it.
        """
        try:
            identity = self._visual_identity.extract(html, url)
        except Exception as exc:  # noqa: BLE001 - visual signal must not kill run
            _LOGGER.warning(
                "visual_identity_extraction_failed url=%s error=%s", url, exc
            )
            return
        _LOGGER.info(
            "visual_identity_extracted url=%s logo=%s colors=%d",
            url,
            identity.logo_path,
            len(identity.primary_colors) + len(identity.secondary_colors),
        )

    def _extract_document(
        self,
        content: bytes,
        extension: str,
        run_id: IngestionRunId,
        snapshot_id: SourceSnapshotId,
        token: CancellationToken | None,
    ) -> tuple[SourceChunk, ...]:
        extractor = self._document_extractors[extension]
        tmp_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                suffix=f".{extension}", delete=False
            ) as handle:
                handle.write(content)
                tmp_path = handle.name
            return extractor(tmp_path, run_id, snapshot_id)
        except Exception as exc:  # noqa: BLE001 - bad document must not kill run
            _LOGGER.warning(
                "document_extraction_failed snapshot=%s error=%s", snapshot_id, exc
            )
            return ()
        finally:
            if tmp_path is not None:
                try:
                    Path(tmp_path).unlink(missing_ok=True)
                except OSError:
                    pass

    def _build_facts(
        self,
        run_id: IngestionRunId,
        _chunks_saved: int,
        token: CancellationToken | None,
    ) -> int:
        # Deterministic 1:1 chunk→candidate mapping. NO LLM (coordinator
        # decision, contract §2) — G-WI-FACT-FIRST only needs the explicit
        # human-review path, not a smarter builder.
        built = 0
        targets = [
            target
            for target in self._repository.list_crawl_targets_by_run(run_id)
            if target.snapshot_id is not None
            and target.state is CrawlTargetState.EXTRACTED
        ]
        total = len(targets)
        for index, target in enumerate(targets, start=1):
            self._raise_if_cancelled(token)
            assert target.snapshot_id is not None
            chunks = self._repository.list_source_chunks_by_snapshot(target.snapshot_id)
            for chunk in chunks:
                self._raise_if_cancelled(token)
                candidate = FactCandidate(
                    id=FactCandidateId(f"cand:{chunk.id}"),
                    snapshot_id=chunk.snapshot_id,
                    content=chunk.text,
                    created_at=self._clock(),
                    status=FactStatus.PROPOSED,
                    chunk_id=chunk.id,
                )
                self._repository.save_fact_candidate(candidate)
                built += 1
            self._repository.update_crawl_target_state(target.id, CrawlTargetState.DONE)
            self._progress(token, index, total, IngestionPhase.BUILD_FACTS)
        return built

    # --- helpers ---

    def _compute_run_stats(self, run_id: IngestionRunId) -> IngestionRunStats:
        """Derive final stats from durable state, not per-call counters (BF-1)."""
        targets = self._repository.list_crawl_targets_by_run(run_id)
        fetched = 0
        failed = 0
        for target in targets:
            # ``fetched_pages`` = unique URLs whose fetch produced a durable
            # snapshot. In a SUCCEEDED run every such target has reached DONE
            # (``_build_facts`` marks every snapshot-bearing target DONE), so
            # this equals the count of DONE targets with a snapshot.
            if target.snapshot_id is not None:
                fetched += 1
            if target.state in (
                CrawlTargetState.FAILED,
                CrawlTargetState.SKIPPED_ROBOTS,
                CrawlTargetState.SKIPPED_UNSAFE,
                CrawlTargetState.TOO_LARGE,
                CrawlTargetState.CANCELLED,
            ):
                failed += 1
        extracted_chunks = 0
        built_candidates = 0
        for snapshot in self._repository.list_source_snapshots_by_run(run_id):
            extracted_chunks += len(
                self._repository.list_source_chunks_by_snapshot(snapshot.id)
            )
            built_candidates += len(
                self._repository.list_fact_candidates_by_snapshot(snapshot.id)
            )
        return IngestionRunStats(
            discovered_urls=len(targets),
            fetched_pages=fetched,
            extracted_chunks=extracted_chunks,
            built_candidates=built_candidates,
            failed_pages=failed,
        )

    def _checkpoint(
        self,
        run: IngestionRun,
        phase: IngestionPhase,
        token: CancellationToken | None,
    ) -> None:
        # A cancel requested during a phase propagates BEFORE its checkpoint
        # is written, so the checkpoint always reflects completed work only.
        self._raise_if_cancelled(token)
        checkpoint = IngestionCheckpoint(
            id=IngestionCheckpointId(_stable_id(str(run.id), phase.value)),
            run_id=run.id,
            phase=phase,
            finished_at=self._clock(),
        )
        self._repository.save_ingestion_checkpoint(checkpoint)

    def _progress(
        self,
        token: CancellationToken | None,
        current: int,
        total: int,
        phase: IngestionPhase,
    ) -> None:
        if self._job_manager is None or token is None or not token.job_id:
            return
        self._job_manager.update_progress(
            token.job_id, current, total, phase=phase.value
        )

    @staticmethod
    def _raise_if_cancelled(token: CancellationToken | None) -> None:
        if token is not None:
            token.raise_if_cancelled()


__all__ = ["IngestBrandSources"]
