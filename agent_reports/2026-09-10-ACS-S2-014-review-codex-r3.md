---
verdict: REJECT
scope: PASS
acceptance: REJECT
architecture: PASS
security: PASS
tests: REJECT
gitnexus_impact: PASS
blocking_findings:
  - R3-BF-1
review_target: "PR #32 @ 3056818c48232a8904d3709807d334ec875ffba9"
reviewer: codex
date: 2026-09-10
---

# CILJ

Fresh adversarial Round 3 review R2-BF-1 refetch/recovery fix-a, sa posebnim
fokusom na ponašanje kada obavezni refetch poslije uspješnog prvog fetch-a ne
uspije.

# PROVJERENO

- GitHub PR head: `3056818` (runtime fix `f2c1d92` + task-specific review
  artefakti); PR je mergeable, CI `test` je PASS.
- `raw_content_ref` se više ne koristi kao inline payload; nema
  `base64`/`b64encode`/`b64decode` u use-case-u.
- `_fetch` requeue je prije claim petlje i claim se poziva tačno jednom po
  iteraciji.
- G-WI-RECOVER testovi koriste stvarnu migriranu SQLite bazu, pravi
  `claim_next_crawl_target`, te direktan SQL update `lease_until` na isteklu
  vrijednost. Nisu kozmetički mock `recover_expired_leases` testovi.
- `http_fetcher.py` i `url_safety_policy.py` nisu u PR diff-u; G6 i dalje koristi
  injektovani fetcher port.
- Nema LLM simbola u `application/ingestion/`; BUILD_FACTS ostaje
  deterministički 1:1 chunk→candidate.
- R2-BF-2 je zatvoren: `.agent/CURRENT_STATE.md` i generalni coordinator
  handoff nisu u diff-u. Diff sadrži 19 fajlova; dodatni fajlovi su
  task-specifični `agent_reports` artefakti.

# GITNEXUS / IMPACT

- Indeks iz glavnog checkout-a je svjež na `main@09650ce`.
- `SourceSnapshot`: MEDIUM, 37 impacted / 8 direct.
- `IngestionRepositoryPort`: HIGH, 24 impacted / 19 direct.
- `detect-changes` iz linked worktree-a nije dostupan (`Repository "." not
  found`), što je dokumentovano worktree-binding ograničenje. Kompenzovano je
  stvarnim `origin/main...origin/task/ACS-S2-014-ingestion-pipeline` diffom,
  `git diff --check` i `rg` pregledom relevantnih callera/state prelaza.

# BLOCKING FINDINGS

## R3-BF-1 — Neuspjeli recovery refetch se lažno pretvara u DONE/SUCCEEDED

**Severity: HIGH / blocking.**

Novi requeue path vraća prethodno uspješno fetchovan target iz `FETCHED` u
`PENDING`, ali `update_crawl_target_state(..., snapshot_id=None)` namjerno
zadržava postojeći `snapshot_id` preko SQL `COALESCE`. Ako svi refetch pokušaji
zatim padnu:

1. `_fetch` postavi target na `FAILED`, ali stari `snapshot_id` ostaje;
2. `_extract` ga ispravno preskoči jer nije `FETCHED`;
3. `_build_facts` pogrešno bira **svaki** target koji ima `snapshot_id`, bez
   provjere da je `EXTRACTED`;
4. `_build_facts` zatim postavi neuspjeli target na `DONE`;
5. `_compute_run_stats` prijavi `failed_pages=0`, i cijeli run završi kao
   `SUCCEEDED`, iako nema ni chunkova ni kandidata.

Relevantna mjesta:

- `ingest_brand_sources.py:340-349` — FETCHED→PENDING requeue;
- `ingest_brand_sources.py:372-393` — refetch failure→FAILED;
- `ingest_brand_sources.py:554-577` — BUILD_FACTS filter samo po
  `snapshot_id`, pa FAILED→DONE;
- `sqlite_ingestion_repository.py:343-353` — postojeći `snapshot_id` se
  zadržava kada novi nije proslijeđen.

Fresh reprodukcija je koristila pravu privremenu SQLite bazu i ove korake:

1. prvi fetch vrati HTTP success i zatraži cancel;
2. durable stanje ostane `FETCHED` sa snapshotom i bez inline body-ja;
3. resume istog `run_id`; sva tri dozvoljena refetch pokušaja vrate
   `error="network_down"`;
4. pročitaj finalni run/target/statistiku iz SQLite repository-ja.

Stvarni output:

```text
{'run_status': 'SUCCEEDED', 'target_state': 'DONE',
 'snapshot_id': 'r3-refetch-fail:0f115db062b7c0dd',
 'fetch_calls': 4, 'snapshots': 1, 'chunks': 0, 'candidates': 0,
 'stats': IngestionRunStats(discovered_urls=1, fetched_pages=1,
 extracted_chunks=0, built_candidates=0, failed_pages=0)}
```

Ovo vraća suštinski isti integritet problem koji je R2 happy-path trebalo da
zatvori: postojanje starog snapshot reda nije dokaz da je recovery obrada
uspjela.

**Potrebna korekcija:** BUILD_FACTS ne smije obrađivati niti označiti `DONE`
target koji nije uspješno završio EXTRACT (najmanje: eksplicitna eligibility
provjera stanja). Dodati integration regresioni test za gornji slijed koji
dokazuje da neuspjeli refetch ostaje vidljivo neuspješan i da statistika ne
prijavljuje `failed_pages=0`. Test mora mutation-provjerom pasti kada se ukloni
state eligibility guard. Pri fix-u provjeriti i parcijalno sačuvane chunkove iz
prethodnog, cancelovanog EXTRACT pokušaja, jer refetch može vratiti promijenjen
sadržaj.

# STANDARDNA VERIFIKACIJA

```text
python -m pytest -q tests/integration/application/ingestion/test_ingest_pipeline.py tests/integration/application/ingestion/test_real_adapter_pipeline.py tests/unit/application/ingestion/test_ingest_brand_sources.py tests/unit/infrastructure/web_ingestion/test_url_classifier.py
50 passed in 17.55s

python -m ruff check .
All checks passed!

python -m mypy src
Success: no issues found in 211 source files

AI_CAMPAIGN_STUDIO_DEEPSEEK_API_KEY unset; python -m pytest -q
1474 passed, 2 skipped, 1 warning in 240.26s

GitHub Actions / PR #32 / test
PASS (3m29s)
```

# ADVERSARIALNA PROVJERA

Postojeći `test_refetch_path_recovers_body_on_resume` jeste materijalan i
mutation-osjetljiv za uspješan refetch. Nije dovoljan za option-A recovery jer
fetch po prirodi može ponovo pasti. Fresh failure-path reprodukcija iznad
prolazi kroz produkcijski use-case i stvarni SQLite adapter i pokazuje lažno
terminalno stanje.

# NE DIRATI U FIX RUNDI

- Ne vraćati inline base64 u `raw_content_ref`.
- Ne mijenjati `HttpFetcher`/`UrlSafetyPolicy` niti G2 atomic claim/recovery.
- Ne širiti repository port ako se state eligibility može ispravno riješiti u
  G6 allowed pathu.
- Sačuvati postojeće cancel, hard-kill, MIME, visual i real-adapter regresije.

# SLJEDEĆE

Fix R3-BF-1 + regression/mutation dokaz, pa fresh Codex Round 4. HIGH task i
nakon PASS-a i dalje zahtijeva eksplicitno Human Owner odobrenje prije merge-a.
