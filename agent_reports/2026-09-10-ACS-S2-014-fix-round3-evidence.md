# Fix-round 3 evidence — ACS-S2-014 (S2-G6) — R2-BF-1

date: 2026-09-10
agent: pi
branch: task/ACS-S2-014-ingestion-pipeline
worktree: H:/ai-campaign-studio-worktrees/ACS-S2-014-ingestion-pipeline
fix_option: A (refetch/recovery, ne inline base64)

## Šta je popravljeno

R2-BF-1 (MEDIUM, contract breach na `raw_content_ref`): `raw_content_ref`
se više NE koristi kao inline base64 payload. Odabrana je opcija A iz
fix-round-3 brief-a.

1. `_fetch` — uklonjen `raw_content_ref=base64.b64encode(content).decode("ascii")`
   iz `SourceSnapshot` konstruktora; polje ostaje `None` (default referenca).
2. `_fetch` — na početku faze, svaki target koji je ostao `FETCHED` iz ranijeg
   run-a (body nije dostupan in-memory, `raw_content_ref` nije payload) vraća se
   u `PENDING` sa `last_error="missing_raw_body_refetch"`. `claim_next_crawl_target`
   ga ponovo podiže i `_fetch` refetchuje; `save_source_snapshot` sa istim
   determinističkim `id`-om je upsert (bez duplikata).
3. `_extract_snapshot` — uklonjeno `base64.b64decode` čitanje iz
   `raw_content_ref`. Missing in-memory body je sada defanzivni no-op (nikad
   tiho dekodiranje reference URI-ja kao website body).
4. `import base64` — uklonjen (nema više nijedne upotrebe u fajlu).
5. `_compute_run_stats` — semantika NEpromijenjena; dodan komentar koji
   dokumentuje da `fetched_pages` broji unique URL-ove sa `snapshot_id is not None`
   (u SUCCEEDED run-u svi takvi targeti su u DONE).

## Nije dirano

- `recover_expired_leases` / `claim_next_crawl_target` (G2 atomic claim/recovery)
- `HttpFetcher` / `UrlSafetyPolicy` (SSRF)
- `SourceSnapshot` contract u `domain/ingestion/entities.py` (polje i dalje `str | None`)
- `sqlite_ingestion_repository.py` (upsert i COALESCE asimetrija netaknuti)
- deterministički 1:1 chunk→candidate (BUILD_FACTS)
- `_checkpoint` logika (F1)
- BF-2/3/4/5 fix-ovi
- repository/port metode (nijedna nova)
- `application/ingestion/__init__.py` export lista

## Novi testovi

- `test_raw_content_ref_is_never_inline_body` (integration) — za svaki
  `SourceSnapshot` sačuvan tokom pipeline-a i za SQLite `source_snapshots`
  kolonu: `raw_content_ref is None`.
- `test_refetch_path_recovers_body_on_resume` (integration) — cancel poslije
  FETCH ostavlja snapshot sa `raw_content_ref=None`; resume poziva fetcher
  PONOVO (refetch, ne b64decode) i završava DONE sa `chunks=2, candidates=2`.
- `test_ingest_brand_sources_never_inlines_base64_body` (unit) — source fajl ne
  sadrži `base64`/`b64encode`/`b64decode`.

Postojeći `test_cancel_after_fetch_recovers_body_on_resume` i
`test_hard_kill_after_first_fetch_resumes_both_targets` i dalje prolaze.

## Verifikacija (stvarni output)

```text
python -m ruff check src/ai_campaign_studio/application/ingestion/ingest_brand_sources.py \
  tests/unit/application/ingestion/test_ingest_brand_sources.py \
  tests/integration/application/ingestion/test_ingest_pipeline.py
All checks passed!

python -m mypy src
Success: no issues found in 211 source files

python -m pytest -q
1475 passed, 1 skipped, 1 warning in 267.15s

python -m pytest -q tests/integration/application/ingestion/
20 passed in 16.64s

git diff --check
(clean — no output)
```

## Mutation-napomene za koordinatora (R2-BF-1)

Reverzija bilo koje komponente ruši reprodukcioni test:

1. Vraćanje `raw_content_ref=base64.b64encode(...)` u `_fetch` →
   `test_raw_content_ref_is_never_inline_body` pada (`raw_content_ref is not None`).
2. Uklanjanje requeue bloka (`FETCHED → PENDING`) u `_fetch` →
   `test_refetch_path_recovers_body_on_resume` pada (resume ne refetchuje,
   target ostaje bez body-ja → `chunks != 2`).
3. Vraćanje `b64decode` fallback-a u `_extract_snapshot` →
   `test_ingest_brand_sources_never_inlines_base64_body` pada (`b64decode` u source).
