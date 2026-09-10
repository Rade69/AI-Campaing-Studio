# Fix-round 2 evidence — ACS-S2-014 (S2-G6)

date: 2026-09-10
agent: pi
branch: task/ACS-S2-014-ingestion-pipeline
worktree: H:/ai-campaign-studio-worktrees/ACS-S2-014-ingestion-pipeline

## Šta je popravljeno

| BF | Fix | Lokacija |
|----|-----|----------|
| BF-1 (HIGH) | raw body trajno u `source_snapshots.raw_content_ref` (base64), resume čita iz baze; cancel poslije FETCH propagira tek nakon perzistencije; finalne stats izvedene iz durable stanja (`_compute_run_stats`) | `ingest_brand_sources.py` |
| BF-2 (MEDIUM) | `_raise_if_cancelled(token)` na početku svake iteracije chunk/candidate petlje | `_extract`, `_build_facts` |
| BF-3 (MEDIUM) | `_DOCUMENT_MIME_TYPES` + `_document_mime_extension`; suffix first, pa Content-Type mapping | `ingest_brand_sources.py` |
| BF-4 (MEDIUM) | `_extract_visual_identity` pozvan za HOME/ABOUT (po `page_type_hint`), samo log, bez persistence/port promjena | `_extract_snapshot` |
| BF-5 (MEDIUM) | novi integration test sa stvarnim `HttpFetcher`/`DomainDiscovery`/`MainContentExtractor`/`VisualIdentityAdapter` na lokalnom `http.server` koji servira `spikes/extraction-benchmark/corpus/klix.ba-article.html` | `tests/integration/application/ingestion/test_real_adapter_pipeline.py` |

## Nije dirano

- `recover_expired_leases` / `claim_next_crawl_target` (G2 atomic claim)
- `HttpFetcher` / `UrlSafetyPolicy` SSRF kod (u testu je samo injektovan `dns_resolver`/`allowed_ports`)
- deterministički 1:1 chunk→candidate (BUILD_FACTS)
- S2-G7a (Approve/Reject)
- `_checkpoint` logika (F1)
- repository/port metode potpisi
- `application/ingestion/__init__.py` export lista (nije dodan novi javni symbol)

## Verifikacija (stvarni output)

```
python -m ruff check .
All checks passed!

python -m mypy src
Success: no issues found in 211 source files

python -m pytest -q
1472 passed, 1 skipped, 1 warning in 267.68s

git diff --check
(clean — no output)
```

Ciljani testovi (BF-1..BF-5 + postojeći):

```
python -m pytest tests/unit/application/ingestion/test_ingest_brand_sources.py \
  tests/integration/application/ingestion/test_ingest_pipeline.py \
  tests/integration/application/ingestion/test_real_adapter_pipeline.py -q
16 passed in 16.47s
```

## Mutation-napomene za koordinatora (BF-1)

Reverzija bilo koje od tri komponente BF-1 fix-a ruši reproducione testove:

1. `raw_content_ref=base64(...)` u `_fetch` — `test_cancel_after_fetch_recovers_body_on_resume` pada na `chunks == 2` (dobija `chunks == 0`).
2. `_extract_snapshot` fallback čitanje iz `raw_content_ref` — isti test pada na `chunks == 2`.
3. `_compute_run_stats` — `test_hard_kill_after_first_fetch_resumes_both_targets` pada na `stats.fetched_pages == 2` (dobija `1`).
