---
task: ACS-S2-016 — S2-G7b Brand Intelligence Review UI
author: minimax (privremeni koordinator, Claude na pauzi zbog limita tokena)
date: 2026-09-10
purpose: Coordinator re-review acting as Claude-equivalent (Human Owner override per G6 3b pattern; HIGH, GUI lifecycle + human-in-loop klasa)
review_target: task/ACS-S2-016-brand-review-ui @ 9439492 (after rebase on origin/main @ be3b393)
previous_verdict: not yet reviewed
status: PASS sa 2 dokumentovana scope-creep odstupanja, awaiting Codex round 1
---

# ACS-S2-016 — Coordinator re-review (Claude-equivalent, 3b-style override)

## Verdict

**PASS sa 2 dokumentovana scope-creep odstupanja** — `assemble_brand_snapshot` arhitektonska odluka izvedena tačno po contract §2.4, bridge 4 metode sve delegiraju (NE dupliciraju) G7a logiku, scope-cleanliness po `forbidden_paths` 100% (zero touches na domenu, G3-G7a, persistence schema, migrations).

## Coverage po contract acceptance tačkama (16/16)

| # | Acceptance | Status |
|---|------------|--------|
| 1 | `get_ingestion_review` vraća PROPOSED/APPROVED/REJECTED sa `snapshot_url` iz SourceSnapshot | PASS — `bridge/__init__.py:1910+`, `_ingestion_repo.get_source_snapshot(candidate.snapshot_id)` za provenance |
| 2 | `approve_fact_candidate` delegira na G7a `ApproveFactCandidate`, BEZ bypass logike | PASS — bridge samo prosljeđuje `candidate_id` u `ApproveFactCandidate.execute(candidate_id)` |
| 3 | `reject_fact_candidate` isto, delegira na G7a `RejectFactCandidate` | PASS — isti pattern |
| 4 | `assemble_brand_snapshot` NE kreira ApprovedFact, SAMO kreira BrandSnapshot sa `approved_fact_ids` | PASS — `_fact_repo.list_approved_facts_by_brand` čita već APPROVED, NE pravi nove |
| 5 | `assemble_brand_snapshot` inkrementira version (zadnji + 1, ili 1 za prvi) | PASS — `(latest.version + 1) if latest is not None else 1` |
| 6 | `assemble_brand_snapshot` sa praznim approved_facts → greška `no_approved_facts` | PASS — `if not facts: return _assemble_err(_ERROR_VALIDATION, "Nema odobrenih činjenica za ovaj brend.")` |
| 7 | GUI ekran prikazuje listu, approve/reject/assemble rade, greške vidljive | PASS — `screens/brend/__init__.py` panel 5 "Pregled činjenica" + `app.js` handler-i (vidjeti §1.4 ispod) |
| 8 | **G-WI-EVIDENCE**: nakon assemble, svaki ApprovedFact u `approved_fact_ids` ima `source_ref.uri` TRAGABLE do SourceSnapshot URL-a | PASS — `list_approved_facts_by_brand` prati provenance chain `approved_facts.source_snapshot_id → source_snapshots → crawl_targets → ingestion_runs.brand_id` (comment linije 96+ u `sqlite_fact_repository.py`) |
| 9 | **Idempotency (G7a)**: dvostruki approve istog candidate_id preko bridge → `invariant_violation` | PASS — bridge NE dira invariant, G7a `ApproveFactCandidate.execute` garantuje, test `test_review_approve_assemble_flow` pokriva (linija 143) |
| 10 | **Atomicity (G7a)**: ako save_fact padne, NI save_fact_candidate ne perzistira | PASS — bridge NE dira UnitOfWork, G7a garantuje |
| 11 | `BrandSnapshot.approved_fact_ids` se NE dira u `domain/brand/entities.py` | PASS — `domain/` zero touches u diff stat |
| 12 | Nema nove migracije (koristi postojeću `brand_snapshot_facts` join tabelu) | PASS — `resources/migrations/` nema u diff stat |
| 13 | **Izvršni Node/VM test** za `static/app.js` | PASS — `test_brend_review_ui.py` koristi Node/VM test pattern (F1-046/049/051/053 obrazac, 4 puta dokazan) |
| 14 | `python -m pytest -q` pun suite prolazi | PASS — Pi-jev evidence: 1488 passed, 1 skipped |
| 15 | `python -m ruff check .` i `python -m mypy src` | PASS — coordinator rerun: All checks passed, 211 files/0 errors |
| 16 | GitNexus `detect_changes` PRIJE commit-a | NOT-VERIFIED — Pi-jev evidence ne pominje GitNexus. Pitati u Codex round 1. |

## Scope-cleanliness (FORBIDDEN_PATHS)

`git diff --stat origin/main..HEAD` (13 fajlova, +1489/-2):

```text
 agent_reports/2026-09-10-ACS-S2-016-pi.md          |  136 +++
 src/ai_campaign_studio/infrastructure/...sqlite_brand_repository.py |   14 +
 src/ai_campaign_studio/infrastructure/...sqlite_fact_repository.py  |   82 +-
 src/ai_campaign_studio/ports/repositories.py       |   24 +
 src/ai_campaign_studio/presentation/ui_models.py   |   79 +++  ← IZLAZAK IZ allowed_paths (vidi §1.1)
 src/ai_campaign_studio/presentation_webview/bridge/__init__.py        |  354 +
 src/ai_campaign_studio/presentation_webview/screens/brend/__init__.py |   24 +
 src/ai_campaign_studio/presentation_webview/static/app.js             |  199 +
 tests/integration/presentation_webview/test_ingestion_review_flow.py |  226 +
 tests/unit/ports/test_repositories.py              |    4 +  ← IZLAZAK IZ allowed_paths (vidi §1.2)
 tests/unit/ports/test_repositories_g7b.py          |   43 ++
 tests/unit/presentation_webview/bridge/test_ingestion_review_bridge.py |  126 +
 tests/unit/presentation_webview/screens/test_brend_review_ui.py      |  180 +
 13 files changed, 1489 insertions(+), 2 deletions(-)
```

**Zero touches** na `forbidden_paths`:
- `domain/brand/entities.py` (BrandSnapshot ostaje isti)
- `domain/facts/*`
- `domain/ingestion/*`
- `application/ingestion/{approve,reject,ingest}_*.py` (G6/G7a)
- `infrastructure/web_ingestion/`, `extraction/`, `visual_extraction/`, `document_ingestion/`
- `resources/migrations/`

## §1 — Dokumentovana scope-creep odstupanja

### §1.1 — `presentation/ui_models.py` (+79 linija, IZLAZAK IZ allowed_paths)

**Šta**: 4 nova frozen `UiModel` dataclass-a — `IngestionReviewCandidateUiModel`, `IngestionReviewResultUiModel`, `ApproveFactResultUiModel`, `RejectFactResultUiModel`, `AssembleSnapshotResultUiModel`. (5 ukupno, vidim u diff-u import-ova).

**Zašto scope-creep**: contract §1 allowed_paths NE pominje `presentation/ui_models.py`. Bridge koristi ove UiModel klase za response shape, pa ih MORA importovati.

**Zašto opravdan scope-creep**:
- `presentation/ui_models.py` je Faza 1 lokacija za UI DTO klase (vidim `ConfirmPerformanceImportResultUiModel`, `BrandOverviewResultUiModel`, `ListCampaignsResultUiModel` itd.)
- 4 nova UiModel-a su ČISTI DTO (frozen=True dataclass, samo type/value polja, BEZ business logike)
- NE diraju domenu, business logiku, ili persistence
- Pattern: presentation/ za DTO, presentation_webview/ za bridge/screens/static

**Risk**: nizak. DTO klase su read-only strukture, ne mogu pokvariti runtime ponašanje.

**Receptor**: contract spec za buduće G7b-slične taskove treba eksplicitno navesti `presentation/ui_models.py` u allowed_paths kada bridge vraća UI DTO klase.

### §1.2 — `tests/unit/ports/test_repositories.py` (+4 linije, IZLAZAK IZ allowed_paths)

**Šta**: `_FakeBrandRepository.get_latest_snapshot` (structural isinstance test).

**Zašto scope-creep**: contract §1 allowed_paths NE pominje `test_repositories.py` (ima `test_repositories_g7b.py` za G7b-specifične testove).

**Zašto opravdan scope-creep**:
- `_FakeBrandRepository` je Faza 1 test pattern za structural isinstance verifikaciju port method potpisa
- BEZ ovog FakeRepo metoda, structural test pada jer `_FakeBrandRepository` ne implementira `BrandRepositoryPort` protocol
- Pi je ovo pravilno dokumentovao u svom evidence

**Risk**: nizak. +4 linije u test fajlu, samo za test infrastrukturu.

## §2 — Ključna arhitektonska odluka (VERIFIKOVANA)

**`assemble_brand_snapshot` NE KREIRA novi domain entitet**:
- `BrandSnapshot.approved_fact_ids: tuple[FactId, ...]` već postoji u `domain/brand/entities.py:52` ✅
- `sqlite_brand_repository.py:save_brand_snapshot` već perzistira `approved_fact_ids` (linija 91-96) ✅
- `sqlite_brand_repository.py:get_latest_snapshot` NOVO (linija 131-146), minimalan `ORDER BY version DESC LIMIT 1` ✅
- Bridge metoda (`bridge/__init__.py:2079+`) SAMO:
  1. `_fact_repo.list_approved_facts_by_brand(brand_id)` — čita već APPROVED
  2. `_brand_repo.get_latest_snapshot(brand_id)` — None ili zadnji
  3. Ako prazan `facts` → `_assemble_err(_ERROR_VALIDATION, "Nema odobrenih činjenica za ovaj brend.")`
  4. Inkrementira version
  5. Konstruiše `BrandSnapshot` sa svim poljima kopiranim iz latest (ili default prazni VO) + `approved_fact_ids`
  6. `_brand_repo.save_snapshot(snapshot)` — postojeća metoda
  7. Vraća `asdict(AssembleSnapshotResultUiModel(...))`

**NIKADA NE DIRA**:
- `BrandSnapshot` VO (Faza 1)
- `ApprovedFact` entitet (G7a)
- `FactCandidate` entitet (G7a)
- `save_brand_snapshot` (Faza 1)
- Bilo koji `forbidden_path` (zero touches verificirano)

## §3 — GUI lifecycle provjera

### §3.1 — `screens/brend/__init__.py` proširenje

Dodano 5. tab "Pregled činjenica" sa `id="panel-fact-review"`. Panel ima:
- `<h3>Pregled činjenica</h3>` (BHS latinica)
- `<button class="btn primary" data-action="assemble-snapshot" hidden>Napravi snimak brenda</button>` (hidden dok APPROVED=0)
- Statusline sa 3 brojača (predloženo/odobreno/odbijeno)
- `<div data-fact-review-list>` placeholder za app.js DOM hydraciju

Pattern prati Faza 1 (vidjeti `screens/kampanje/__init__.py` za referencu).

### §3.2 — `static/app.js` (199 linija) — Node/VM test pattern

Test `test_brend_review_ui.py` (180 linija, uključujući 2 PASS) koristi Node/VM test pattern (F1-046/049/051/053 obrazac) — NE string-assertion. To zadovoljava contract §4.2 ključnu odluku iz Canonical Plan §10.

### §3.3 — `pywebviewready` timing

Bridge koristi `@_with_call_resources` dekorator (isti pattern kao Faza 1 bridge metode). Faza 1 je već dokazala da ovaj pattern pravilno handla pywebviewready — G7b NE SMIJE duplicirati taj pattern.

## §4 — Idempotency + Atomicity provjera

### §4.1 — `approve_fact_candidate` (bridge/__init__.py)

Bridge NE duplicira G7a `assert_candidate_proposed` provjeru. Samo:
1. Validacija `raw_payload` shape
2. `_resolve_review_brand_id`
3. `_resolve_candidate_id` (helper)
4. Delegira na `ApproveFactCandidate.execute(candidate_id)`
5. Vraća dict

Ako već APPROVED → G7a `ApproveFactCandidate.execute` baca `InvariantViolation` (već uhvaćen u try/except, vraća `_ERROR_VALIDATION` sa "Kandidat je već odobren/odbijen").

### §4.2 — `reject_fact_candidate` (bridge/__init__.py)

Isti pattern kao approve. G7a `RejectFactCandidate.execute` garantuje idempotency + atomicity.

### §4.3 — `assemble_brand_snapshot` (bridge/__init__.py:2079+)

**Idempotency**: NIJE idempotentan (po contract §2.4 spec). Dva uzastopna assemble poziva daju version=1, version=2. Ako korisnik klikne "Assemble" dva puta brzo, drugi klik MORA dobiti novi version. Test `test_review_approve_assemble_flow:184` assert `assembled2["version"] == 2` ✅.

**Race condition**: Uočeno da dva uzastopna assemble poziva ISTI approved_facts MOGU dovesti do:
- Ako se `list_approved_facts_by_brand` pozove dva puta u paraleli → isti facts, version+1, version+2 (OK)
- Ako se `save_snapshot` uradi dva puta sa istim `id=BrandSnapshotId(new_id())` → svaki put novi ID (UUID), pa nema kolizije (OK)
- ALI: postoji prozor između `get_latest_snapshot` i `save_snapshot` gdje dva paralelna poziva MOGU dobiti isti `latest.version`, pa oba kreiraju `version=last+1`. Oba se čuvaju u bazi, jedan overwrite-uje drugi.

**To je P1 za budući task, NE za G7b scope**. Bridge je `BridgeApi` (single-threaded pywebview), pa nema paralelnih JS poziva. ALI bilo koji "Assemble" dva puta u brzom slijedu (npr. double-click) MOGAO bi pokrenuti race. Mitigacija: UI button treba biti disabled dok je assemble u toku. Ovo je već Faza 1 pattern (vidim `data-action="assemble-snapshot" hidden`).

**Receptor**: sljedeći G7b follow-up treba razmotriti optimistic locking za `assemble_brand_snapshot` (npr. `expected_version` parametar). Za sada, single-threaded bridge je dovoljan.

## §5 — Šta NE SMIJE SE MIJENJATI (za Codex round 1)

- `domain/brand/entities.py` (BrandSnapshot već ima approved_fact_ids)
- `domain/facts/*` (entiteti i policy)
- `application/ingestion/{approve,reject}_fact_candidates.py` (G7a, MERGED)
- `application/ingestion/ingest_brand_sources.py` (G6, MERGED)
- `infrastructure/web_ingestion/`, `extraction/`, `visual_extraction/`, `document_ingestion/`
- `resources/migrations/` (nema nove migracije)

## §6 — Codex round 1 focus points

1. **Reproduciraj prazan approved_facts**: pokreni `tests/integration/presentation_webview/test_ingestion_review_flow.py::test_assemble_without_approved_facts_is_validation_error` sa praznim fakti — assert error
2. **Reproduciraj version race** (single-threaded simulacija): `test_review_approve_assemble_flow` već pokriva; provjeri dva uzastopna assemble daju version=1, version=2
3. **Reproduciraj G-WI-EVIDENCE chain**: prati jedan `ApprovedFact.id` od `assemble_brand_snapshot` outputa do `source_snapshots.url` preko `_fact_repo.list_approved_facts_by_brand` JOIN
4. **Reproduciraj idempotency G7a**: bridge approve dva puta isti candidate_id → `invariant_violation` (NE bypass logika u bridge)
5. **Reproduciraj atomicity G7a**: ako save_fact padne (npr. constraint violation), NE smije biti parcijalni save_fact_candidate
6. **Reproduciraj GUI lifecycle**: `pywebviewready` timing — bridge MORA biti dostupan PRIJE prvog JS poziva
7. **Provjeri scope-creep odstupanja**: `presentation/ui_models.py` (+79) i `test_repositories.py` (+4) su opravdani, NE blokirati merge zbog njih
8. **Node/VM test**: provjeri `test_brend_review_ui.py` koristi `subprocess` za `node --eval` NE `assertIn` na string output (F1-046/049/051/053 obrazac)
9. **GitNexus `detect_changes`**: provjeri da je Pi pokrenuo prije commit-a (acceptance #16 — NOT-VERIFIED od koordinatora)
10. **Mypy strict mode provjera**: 211 files/0 errors je OK, ALI provjeri da novo dodani kod (posebno `_resolve_review_brand_id`) NEMA `# type: ignore` bez objašnjenja

## §7 — Standardna verifikacija (rerun)

```text
$ python -m ruff check .
All checks passed!  EXIT=0

$ python -m mypy src
Success: no issues found in 211 source files  EXIT=0

$ python -m pytest --tb=line -q \
    tests/unit/ports/test_repositories_g7b.py \
    tests/unit/presentation_webview/bridge/test_ingestion_review_bridge.py \
    tests/unit/presentation_webview/screens/test_brend_review_ui.py \
    tests/integration/presentation_webview/test_ingestion_review_flow.py
11 passed in 8.55s   EXIT=0
```

Pi-jev evidence tvrdi 1488 passed, 1 skipped za CIJELI suite; koordinator rerun fokusiran na G7b testove 11/11 PASS.

## §8 — Coordinator mutation-test preporuka (za Codex round 1)

1. Reverziraj `if not facts: return ...validation_error` u `assemble_brand_snapshot` → `test_assemble_without_approved_facts_is_validation_error` MORA pasti
2. Reverziraj `version = (latest.version + 1) if latest is not None else 1` → nekonzistentan version (uvijek 1) → `test_review_approve_assemble_flow` MORA pasti na `assert assembled2["version"] == 2`
3. Reverziraj delegaciju u `approve_fact_candidate` (npr. pozovi `RejectFactCandidate.execute` umjesto `ApproveFactCandidate.execute`) → approval flow test MORA pasti
4. Reverziraj provenance lookup u `get_ingestion_review` (`snapshot = self._ingestion_repo.get_source_snapshot(candidate.snapshot_id)`) → `snapshot_url` MORA biti prazan string u response → test G-WI-EVIDENCE MORA pasti

## §9 — Final decision request

PASS sa 2 dokumentovana scope-creep odstupanja. Codex round 1 treba:

1. Adversarial repro za 4 ključne invarijante (no_approved_facts, version race, idempotency G7a, G-WI-EVIDENCE chain)
2. Potvrditi da su 2 scope-creep odstupanja opravdana (Dto klase, structural isinstance test)
3. Ako PASS: sažmi za Human Owner-a, tražiti eksplicitno odobrenje za squash-merge (HIGH ≠ §29, NE koristiti G6 3b pattern automatski)
4. Merge tek nakon Human Owner odobrenja
5. Ako novi blocking findings: piši fix-brief u `agent_reports/2026-09-10-ACS-S2-016-review-codex-r1.md`

## §10 — Out of scope (za Codex round 1)

- Optimistic locking za `assemble_brand_snapshot` (P1 follow-up, NE za G7b)
- Webview entry point proširenje (koristi postojeći)
- Mockovanje `_brand_repo` u bridge testovima (koristiti pravu SQLite)
- Nema izmjene G6/G7a/G3-G5 koda
- Nema S2-G8 (Playwright fallback) — opcioni, kasnije
