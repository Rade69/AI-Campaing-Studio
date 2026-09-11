---
task: ACS-S2-016 — S2-G7b Brand Intelligence Review UI
author: minimax (privremeni koordinator, Claude na pauzi zbog limita tokena)
date: 2026-09-10
codex_verdict_round1: REJECT
review_file: agent_reports/2026-09-10-ACS-S2-016-review-codex-r1.md
worktree: H:/ai-campaign-studio-worktrees/ACS-S2-016-brand-review-ui
branch: task/ACS-S2-016-brand-review-ui
current_HEAD: 4de9948 (Codex R1 commit; chain bez scope-creep kontaminacije)
status: FIX-ROUND 1 BRIEF — čeka Pi-jev odgovor
---

# Fix-round 1 brief — ACS-S2-016 (S2-G7b) — Codex R1 findings

## Coordinator nezavisna verifikacija (inspekcija koda, ne samo Codex izvještaj)

Sva 3 blocking findings VERIFIKOVANA:

| BF | Linija u kodu | Verifikacija |
|----|---------------|--------------|
| **R1-BF-1** (HIGH race) | `bridge/__init__.py:2109-2110` (read+compute) i `:2130` (save) bez locka. `:426` ContextVar za izolaciju resursa, `:2153-2159` eksplicitno kaže "pywebview dispatches calls on worker threads". `:439-448` `_generation_locks` per-key pattern. `:635-637` "The closure runs on a `ThreadPoolExecutor` worker thread". | TRIGGER reproducer potvrđen: 2 thread + barrier + bridge, observe `[(ok=True, version=1), (ok=True, version=1)]`, `row_count=2` |
| **R1-BF-2** (HIGH status) | `sqlite_fact_repository.py:97-106` SQL: `SELECT approved_facts.* FROM approved_facts JOIN source_snapshots ...` BEZ `WHERE approved_facts.status = 'APPROVED'` | TRIGGER reproducer potvrđen: status='SOFT_DELETED' → assemble `ok=True, approved_fact_count=1` |
| **R1-BF-3** (MEDIUM silent) | `static/app.js:1254-1259`: `catch (err) { return; }` (silent) + `if (!result || result.ok !== true) return;` (silent) | KONTRAKT §4.2 zahtijeva: "Svi error-response-ovi MORAJU biti vidljivi korisniku (toast / inline error). NE tiho swallow-ati greške." |

Codex-ov deterministički reproducer-based verification (sa realnom SQLite, threading.Barrier, monkeypatch) je STROŽI od moje §8 mutation-test preporuke. R1-BF-1 i R1-BF-2 NISU mutation-ovi — to su reproduceri koji zahtijevaju specifičan test pattern.

## R1-BF-1 (HIGH) — concurrent Assemble persists duplicate snapshot versions

**Codex reproducer (verbatim iz izvještaja)**:
1. Seed one brand and approve one fact
2. Wrap `SqliteBrandRepository.get_latest_snapshot` with a two-party
   `threading.Barrier` immediately after the read
3. Invoke the same bridge instance's `assemble_brand_snapshot({})` from
   two `ThreadPoolExecutor` workers
4. **Observed**: `results: [(ok=True, version=1), (ok=True, version=1)]`,
   `persisted_versions: [1, 1]`, `row_count: 2`

**Codex required fix** (verbatim):
> "Serialize the entire fact-read/latest-read/version/save critical
> section with an instance-level per-brand lock (matching the existing
> bridge lock pattern), or provide an equally strong atomic repository
> operation. Because migrations are forbidden for G7b, the minimal
> in-scope fix is the per-brand bridge lock. Add a deterministic
> two-thread regression test using a barrier; it must return/persist
> versions `[1, 2]`."

**Acceptance za R1-BF-1**:
1. Per-brand lock pattern (matching `_generation_locks` u
   `bridge/__init__.py:439-448`). Lock key = `str(brand_id)`, lock
   scope = cijeli `assemble_brand_snapshot` body (od `_resolve_review_brand_id`
   do `save_snapshot`).
2. ALI: bridge poziv ide kroz `_resource_scope` (ContextVar).
   `assemble_brand_snapshot` je `@_with_call_resources` decorator, ALI
   `@_with_call_resources` MORA pozvati `_resource_scope()` i prije
   i poslije — vidjeti `_resource_scope` u Faza 1 pattern.
3. Lock mora biti HELD across the entire bridge body, NE samo unutar
   `_resource_scope`. **Provjeriti** da `_with_call_resources` NE
   poziva lock.
4. **Regression test**: `tests/integration/presentation_webview/test_assemble_brand_snapshot_concurrency.py`
   (NOVI). Threading.Barrier pattern kao Codex reproducer.
   Assertion: `results == [(ok=True, version=1), (ok=True, version=2)]`,
   `persisted_versions == [1, 2]`, `row_count == 2`.

**NE SMIJE** (za G7b scope):
- Migracije (forbidden) — zato lock-only, NE UNIQUE constraint
- Port metoda potpisa — `get_latest_snapshot` ostaje isti
- `_resource_scope` ContextVar pattern (već pravi)
- `_generation_locks` pattern (drugi lock za drugi flow)

## R1-BF-2 (HIGH) — snapshot assembly includes non-APPROVED facts

**Codex reproducer (verbatim)**:
1. Seed and approve a candidate through G7a
2. Set the resulting `approved_facts.status` to `SOFT_DELETED` through SQL
3. Query `list_approved_facts_by_brand`, then assemble a snapshot
4. **Observed**: `repository_statuses: ['SOFT_DELETED']`,
   `assemble: ok=True, approved_fact_count=1`

**Codex required fix** (verbatim):
> "Add an APPROVED-status predicate to this repository query. Add
> real-SQLite coverage proving APPROVED is included while SOFT_DELETED
> and SUPERSEDED are excluded, and proving assembly uses only the
> remaining APPROVED IDs."

**Acceptance za R1-BF-2**:
1. SQL upit `list_approved_facts_by_brand` MORA sadržavati
   `WHERE approved_facts.status = 'APPROVED'`. Provjeriti da
   `FactStatus` enum ima `APPROVED` (već postoji), koristiti
   njegov `value` (string literal) u SQL.
2. ALTERNATIVNO: koristiti `FactStatus.APPROVED.value` kao bind
   parametar (sigurnije od hardcoded string).
3. **Regression test**: `tests/integration/infrastructure/database/test_sqlite_fact_repository_status_filter.py`
   (NOVI). 3 sub-testova:
   - APPROVED uključen ✅
   - SOFT_DELETED isključen ✅
   - SUPERSEDED isključen ✅
4. Integration test: `tests/integration/presentation_webview/test_ingestion_review_flow.py` —
   NOVI scenario: assemble sa SOFT_DELETED fact → `assembled.approved_fact_count == 0`
   ili `_assemble_err("no_approved_facts")` (odlučiti koja semantika,
   vjerovatno drugo — NE prazan snapshot, NE silent skip).

**NE SMIJE**:
- Migracije (forbidden)
- Port metoda potpisa — `list_approved_facts_by_brand` ostaje isti
- Promjena `FactStatus` enum

## R1-BF-3 (MEDIUM) — initial review-load failures are invisible

**Codex reproducer (verbatim)**:
1. `loadFactReview` silently returns on bridge throw
2. `loadFactReview` silently returns on `ok !== true`
3. Comment kaže "offline/debug preview: keep the SSR fixture" —
   namjerno, ALI contract §4.2 zahtijeva vidljivost

**Codex required fix** (verbatim):
> "Display a safe generic toast for thrown errors and the returned
> `error_message` (with a safe fallback) for error DTOs. Extend the
> executable Node/VM test with both negative paths and assert the
> user-visible notification."

**Acceptance za R1-BF-3**:
1. `loadFactReview` u `static/app.js`:
   - Na `catch (err)`: prikaži toast (sigurnosni fallback, NE
     `err.message` koji može sadržavati stack trace)
   - Na `if (!result || result.ok !== true)`: prikaži
     `result.error_message` ako postoji, inače generički "Učitavanje
     pregleda činjenica nije uspjelo."
2. Koristiti `showToast(...)` (već postoji pattern u app.js, vidjeti
   `showToast('Nedostaje candidate_id.')` u `approveFact`)
3. Ukloniti "offline/debug preview: keep the SSR fixture" komentar
   ILI ga zadržati samo za SPECIFIČNE uvjete (npr. explicit
   `?offline=1` URL parametar), ne za SVE catch slučajeve
4. **Regression test (Node/VM, executable)**: proširiti
   `tests/unit/presentation_webview/screens/test_brend_review_ui.py`
   sa dva nova test case-a:
   - `test_load_fact_review_shows_toast_on_bridge_throw`: mock
     `api.get_ingestion_review` da baci Error → assert
     `showToast` pozvan
   - `test_load_fact_review_shows_error_message_on_failed_dto`:
     mock `api.get_ingestion_review` da vrati `{ok: false,
     error_message: "Brend ne postoji."}` → assert
     `showToast("Brend ne postoji.")` pozvan

**NE SMIJE**:
- Izlaganje `err.message` korisniku (može sadržavati stack trace
  ili SQL detalje)
- Izlaganje generičkog "Greška" — uvijek koristiti `error_message` ako
  postoji, fallback na BHS latinica poruku koja NE otkriva internals
- Preskakanje toast-a zbog UX-a — contract eksplicitno zahtijeva
  vidljivost

## Scope-cleanliness (za fix-rundu)

**ALLOWED additions** (samo ova 3 fajla van `allowed_paths` contract-a):
- `src/ai_campaign_studio/presentation_webview/bridge/__init__.py`
  (lock pattern, **samo** u `assemble_brand_snapshot`)
- `src/ai_campaign_studio/infrastructure/database/repositories/sqlite_fact_repository.py`
  (status filter, **samo** u `list_approved_facts_by_brand`)
- `src/ai_campaign_studio/presentation_webview/static/app.js`
  (toast prikazivanje, **samo** u `loadFactReview`)

**ALLOWED novi test fajlovi**:
- `tests/integration/presentation_webview/test_assemble_brand_snapshot_concurrency.py`
  (R1-BF-1 regression)
- `tests/integration/infrastructure/database/test_sqlite_fact_repository_status_filter.py`
  (R1-BF-2 regression)
- Proširenje `tests/unit/presentation_webview/screens/test_brend_review_ui.py`
  (R1-BF-3 negative paths, NIJE novi fajl)

**FORBIDDEN** (sve iz originalnog contract §1 + extension):
- Domain sloj (BrandSnapshot, FactCandidate, ApprovedFact)
- G6/G7a use-case-ovi (`approve_fact_candidates.py`,
  `reject_fact_candidates.py`, `ingest_brand_sources.py`)
- G3/G4/G5 adapteri (web_ingestion, extraction, visual_extraction,
  document_ingestion)
- Persistence schema (`brand_snapshots`, `approved_facts`,
  `fact_candidates` tables i JOIN-ovi)
- Migracije (`resources/migrations/`)
- `_resolve_review_brand_id` (Faza 1 pattern, NE dirati)
- `_resource_scope` (Faza 1 pattern, NE dirati)
- `_generation_locks` (drugi flow, NE dirati)
- Bridge 3 druge metode (get_ingestion_review, approve, reject)
  koje nisu subject ovog fix-a

## Acceptance (fix-round 1 PASS kada)

### Obavezno za svaki BF:

1. **R1-BF-1**:
   - `assemble_brand_snapshot` koristi per-brand lock
   - Lock drži cijeli body (od read do save)
   - Test `test_assemble_brand_snapshot_concurrency` PASS:
     2 thread + barrier, versions `[1, 2]`, `row_count=2`
   - 11/11 G7b testova i dalje PASS (nema regresije)

2. **R1-BF-2**:
   - SQL: `WHERE approved_facts.status = 'APPROVED'` (ili bind
     parametar sa `FactStatus.APPROVED.value`)
   - Test `test_sqlite_fact_repository_status_filter` PASS:
     3 sub-testova (APPROVED uključen, SOFT_DELETED isključen,
     SUPERSEDED isključen)
   - Integration test: assemble sa SOFT_DELETED →
     `approved_fact_count=0` ili `_assemble_err("no_approved_facts")`
   - 11/11 G7b testova i dalje PASS

3. **R1-BF-3**:
   - `loadFactReview` prikazuje toast na throw
   - `loadFactReview` prikazuje `error_message` na `ok !== true`
   - `showToast` koristi BHS latinica fallback ako `error_message` None
   - 2 nova Node/VM test case-a PASS
   - 11/11 G7b testova i dalje PASS

### Standardna verifikacija (mora i dalje vrijediti)

```text
python -m ruff check .: All checks passed
python -m mypy src: 211 source files, 0 errors
python -m pytest -q: 1488+ passed, 1 skipped, 0 failed
git diff --check origin/main...HEAD: clean
GitNexus detect_changes: PASS (acceptance #16)
```

## Šta NE SMIJE (fix-runda NE SMIJE dirati)

- `domain/brand/entities.py` (BrandSnapshot ostaje isti)
- `domain/facts/*` (entiteti, policy, enum)
- `application/ingestion/{approve,reject}_fact_candidates.py` (G7a)
- `application/ingestion/ingest_brand_sources.py` (G6)
- `infrastructure/web_ingestion/`, `extraction/`, `visual_extraction/`,
  `document_ingestion/`
- `resources/migrations/` (nema nove migracije)
- `_resolve_review_brand_id` (Faza 1 helper)
- `_resource_scope` (Faza 1 pattern)
- `_generation_locks` (drugi flow, NE dirati — samo referenca za
  per-brand lock pattern)
- 3 druge bridge metode (`get_ingestion_review`, `approve`,
  `reject`) — samo `assemble_brand_snapshot` je subject fix-a
- Scope-cleanliness odstupanja 1 i 2 iz coordinator Claude re-review
  (`presentation/ui_models.py` i `tests/unit/ports/test_repositories.py`)
  — već prihvaćena, NE dirati

## CI koordinator napomena

PR #29 (CI install follow-up) MERGED, CI zelen za S2-G3/G4 testove.
Fix-runda 1 treba zadržati CI zeleno — svi testovi koji su prolazili
u prethodnoj rundi MORAJU i dalje prolaziti.

## Vraćanje

Ako imaš pitanja, javi sa **output-om komande**, ne opisom:

- "R1-BF-1 fix: per-brand lock u `assemble_brand_snapshot`" → output
  `git diff main..HEAD -- bridge/__init__.py` i `python -m pytest
  -q tests/integration/presentation_webview/test_assemble_brand_snapshot_concurrency.py`
- "R1-BF-2 fix: WHERE status = 'APPROVED'" → output SQL diff i
  pytest output za status_filter test
- "R1-BF-3 fix: toast u `loadFactReview`" → output `git diff
  main..HEAD -- static/app.js` i test output

Bez outputa = bez odgovora.

## Poslije tvog fix-a (koordinator protocol)

1. Pull-ati tvoj branch, `git diff --stat main..HEAD`
2. Pročitati tvoj novi evidence fajl
3. Pokrenuti: mypy, pytest (puni suite), ruff
4. **Nezavisni reproducer verification** (NE samo mutation test):
   - R1-BF-1 reproducer (2 thread + barrier) — MORA pasti na
     reverziran lock, PROĆI na restore
   - R1-BF-2 reproducer (SOFT_DELETED status) — MORA pasti na
     reverziran WHERE klauzulu, PROĆI na restore
   - R1-BF-3 reproducer (silent throw) — MORA pasti na reverziran
     toast, PROĆI na restore
5. Poslati Codex-u round 2 izvještaj
6. Ako Codex PASS: sažeti za Human Owner-a, tražiti eksplicitno
   odobrenje za squash-merge
7. Merge tek nakon Human Owner odobrenja
