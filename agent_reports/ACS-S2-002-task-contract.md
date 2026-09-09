---
task_id: ACS-S2-002
phase: "S2-G2 — Ingestion Persistence — drugi Slice 2 gate"
title: "migracija 0009_ingestion_foundation.sql + SqliteIngestionRepository + CrawlTarget lease queue"
coordinator: claude
implementer: TBD
reviewers: [claude, codex]
status: "OPEN -- contract written before code, čeka implementera"
created_at: 2026-09-09
dependencies: [ACS-S2-001]
risk: HIGH
allowed_paths:
  - resources/migrations/0009_ingestion_foundation.sql
  - src/ai_campaign_studio/domain/ingestion/entities.py
  - src/ai_campaign_studio/domain/ingestion/enums.py
  - src/ai_campaign_studio/domain/common/ids.py
  - src/ai_campaign_studio/ports/repositories.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_ingestion_repository.py
  - src/ai_campaign_studio/infrastructure/database/repositories/__init__.py
  - tests/unit/domain/ingestion/
  - tests/unit/ports/
  - tests/unit/infrastructure/database/repositories/
  - tests/integration/database/
  - tests/integration/database/repositories/
forbidden_paths:
  - src/ai_campaign_studio/domain/facts/
  - src/ai_campaign_studio/ports/web_ingestion.py
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/presentation_webview/
  - src/ai_campaign_studio/jobs/
gitnexus_required: true
adversarial_required: true
---

# Kontekst

Drugi Slice 2 gate. Kanonski plan §10 "S2-G2": migracija `0009` +
`sqlite_ingestion_repository.py`. Zavisi od ACS-S2-001 (MERGED,
`87b5385`) koji je fiksirao `domain/ingestion/` entitete i
`IngestionRepositoryPort`.

**MIGRACIJA = UVIJEK HIGH** (workflow §6, CLAUDE.md non-negotiable
pravilo — "HIGH/bezbjednosno-kritični taskovi ostaju na punom ciklusu
bez izuzetka"). Ovaj task ide na PUN review ciklus: Claude → Codex →
Human Owner, NE §29.

**Zašto ovaj task ipak dira `domain/ingestion/` i `ports/repositories.py`
ponovo** (a ne SAMO migraciju + adapter): §7 kanonskog plana
(durability, SQLite lease queue) je EKSPLICITNO dio S2-G2 scope-a, a
`CrawlTarget` (lease-queue red) NIJE dobio domain entitet u S2-G1 —
ACS-S2-001 kontrakt je EKSPLICITNO ostavio tu odluku ovom gate-u
("Ne uvoditi `CrawlTarget`/lease-queue polja ovdje... ako se pokaže da
`CrawlTarget` treba biti domain entitet, dodati ga OVDJE [S2-G2] ali
dokumentovati zašto"). Odluka je sada donesena (§1 ispod). Isto važi za
lease-queue port metode (`claim_next_crawl_target` itd.) — one ne mogu
postojati bez sheme koju TEK OVAJ task pravi, pa je `ports/repositories.py`
ponovo aditivno u scope-u, iz istog razloga kao S2-G1 (shema i port
metoda koja je čita/piše su neraskidiv par, pregledavaju se zajedno).

**Šta OVAJ task NAMJERNO NE radi**: kanonski plan §10 S2-G2 opis
pominje i `structured_data_records` tabelu. Koordinator je odlučio
DA SE ONA NE PRAVI SADA — nijedan trenutno kontraktovan gate je ne
konzumira (S2-G4/G5, koji bi je stvarno trebali za JSON-LD/schema.org
podatke, nisu ni otvoreni), pa bi to bila prazna, nekorišćena šema
(kosi se sa CLAUDE.md "ne uvoditi framework/abstrakciju za svaki
slučaj"). Dodati je KAO ADITIVNU migraciju kad S2-G4 (Content
Extraction) stvarno stigne do JSON-LD ekstrakcije — SQLite migracije su
inkrementalne, nema arhitektonske štete u odgađanju.

# §1 — CrawlTarget dobija domain entitet (odluka, koordinator, 2026-09-09)

`CrawlTarget` ide u `domain/ingestion/entities.py` (frozen dataclass) +
`CrawlTargetState` u `domain/ingestion/enums.py` + `CrawlTargetId` u
`domain/common/ids.py`. Razlog: state mašina
(`PENDING→LEASED→FETCHED→EXTRACTED→DONE`, `LEASED→FAILED_RETRYABLE→PENDING`,
terminalni `FAILED`/`SKIPPED_ROBOTS`/`SKIPPED_UNSAFE`/`TOO_LARGE`/
`CANCELLED`) je domain-relevantan koncept koji će S2-G6 orkestracija
(application layer) čitati/mijenjati preko tipizovanih vrijednosti, ne
preko sirovih SQL redova — ISTI princip kao zašto `IngestionRun`/
`IngestionCheckpoint` imaju entitete umjesto da su "samo SQL".

```python
class CrawlTargetState(StrEnum):
    PENDING = "PENDING"
    LEASED = "LEASED"
    FETCHED = "FETCHED"
    EXTRACTED = "EXTRACTED"
    DONE = "DONE"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED = "FAILED"
    SKIPPED_ROBOTS = "SKIPPED_ROBOTS"
    SKIPPED_UNSAFE = "SKIPPED_UNSAFE"
    TOO_LARGE = "TOO_LARGE"
    CANCELLED = "CANCELLED"
```

`CrawlTarget` polja (kanonski plan §7, doslovno): `id`, `run_id`
(`IngestionRunId`), `normalized_url: str`, `depth: int`,
`page_type_hint: PageType | None`, `priority: int`,
`state: CrawlTargetState`, `attempts: int`, `lease_until: datetime |
None`, `next_attempt_at: datetime | None`, `last_error: str | None`.

# Objective

## 1. Migracija `resources/migrations/0009_ingestion_foundation.sql`

Isti stil kao `0006_performance_foundation.sql` (referenca — pročitati
prije pisanja): `TEXT PRIMARY KEY`, `REFERENCES` BEZ `ON DELETE CASCADE`
(postojeća konvencija), `NULL`/`NOT NULL` eksplicitno, `_json` sufiks za
JSON blob kolone.

Tabele:

- `source_snapshots` (id, url, fetched_at, content_hash, raw_content_ref
  NULL, content_type NULL, status_code NULL).
- `source_chunks` (id, snapshot_id REFERENCES source_snapshots(id),
  locator_type, locator, text).
- `ingestion_runs` (id, brand_id REFERENCES brands(id) — potvrđeno
  ime tabele u `0001_brand_facts.sql`, status, started_at,
  finished_at NULL, source_scope_json, plus FLATTENED
  `IngestionRunStats` kolone: discovered_urls, fetched_pages,
  extracted_chunks, built_candidates, failed_pages — isti stil kao
  `performance_import_batches` koji flatten-uje counter-e kao kolone,
  ne JSON).
- `ingestion_checkpoints` (id, run_id REFERENCES ingestion_runs(id),
  phase, finished_at).
- `fact_candidates` (id, snapshot_id REFERENCES source_snapshots(id),
  chunk_id NULL REFERENCES source_chunks(id), content, created_at,
  status).
- `crawl_targets` (§7 lease queue, §1 ova kontrakta): id, run_id
  REFERENCES ingestion_runs(id), normalized_url, depth, page_type_hint
  NULL, priority, state, attempts, lease_until NULL, next_attempt_at
  NULL, last_error NULL. **`UNIQUE(run_id, normalized_url)`** (§7 —
  idempotentno re-discovery, `INSERT ... ON CONFLICT DO NOTHING` u
  adapteru).

Indeksi: bar jedan na `crawl_targets(run_id, state, priority)` (worker
claim query), `source_chunks(snapshot_id)`, `fact_candidates(snapshot_id)`.

## 2. Domain aditivno (§1 odluka)

`CrawlTarget`/`CrawlTargetState`/`CrawlTargetId` kako je gore
specificirano. Unit testovi (frozen, state enum kompletnost) — isti
stil kao S2-G1 (`tests/unit/domain/ingestion/test_entities.py`,
proširiti postojeći fajl, ne duplirati).

## 3. `IngestionRepositoryPort` — lease-queue metode (aditivno)

Dodati u postojeću `IngestionRepositoryPort` klasu (`ports/repositories.py`,
NE dirati postojećih 13 metoda iz S2-G1):

- `register_crawl_targets(targets: Sequence[CrawlTarget]) -> int` —
  idempotentan batch insert (`ON CONFLICT DO NOTHING`), vraća broj
  STVARNO ubačenih (ne duplikata).
- `claim_next_crawl_target(run_id: IngestionRunId, lease_duration_seconds:
  int) -> CrawlTarget | None` — ATOMSKI claim najvišeg-prioriteta
  `PENDING` reda, postavlja `state=LEASED`, `lease_until=now+duration`.
  Preporučen SQLite mehanizam: JEDAN `UPDATE ... WHERE id = (SELECT id
  FROM crawl_targets WHERE run_id=? AND state='PENDING' ORDER BY
  priority DESC, id ASC LIMIT 1) RETURNING *` (SQLite 3.35+
  `RETURNING`, provjeriti da projekat već koristi `RETURNING` negdje —
  ako ne, potvrditi min. SQLite verziju prije oslanjanja na to;
  alternativa je eksplicitan `BEGIN IMMEDIATE`/`SELECT`/`UPDATE`/`COMMIT`
  blok). MORA biti dokazano atomsko (§ Acceptance ispod — konkurentni
  claim test).
- `update_crawl_target_state(target_id: CrawlTargetId, state:
  CrawlTargetState, *, last_error: str | None = None) -> None`.
- `recover_expired_leases(run_id: IngestionRunId) -> int` — `LEASED
  WHERE lease_until < now → PENDING`, vraća broj oporavljenih (§7
  "Startup recovery").
- `get_crawl_target(target_id: CrawlTargetId) -> CrawlTarget | None`.
- `list_crawl_targets_by_run(run_id: IngestionRunId) -> tuple[CrawlTarget, ...]`.

## 4. `SqliteIngestionRepository` (nov fajl)

Implementira CIJELI `IngestionRepositoryPort` (svih 13 S2-G1 metoda +
6 novih lease-queue metoda). Isti stil kao
`sqlite_performance_repository.py` (referenca — pročitati prije
pisanja): `ON CONFLICT(id) DO UPDATE` upsert za save-metode, enum
`.value`/rekonstrukcija, `datetime.isoformat()`/`fromisoformat()` za
timestamp kolone, JSON text kolone za `source_scope`.

Registrovati u `infrastructure/database/repositories/__init__.py`
(dodati `SqliteIngestionRepository` u `__all__`, isti stil kao
postojećih 9 export-a).

# Acceptance

- [ ] Migracija se primjenjuje čisto na svježu bazu I na bazu koja već
      ima 0000-0008 (postojeći `tests/integration/database/test_migrations.py`
      obrazac — dodati novi test slučaj za 0009, ne izmišljati novi
      test fajl ako postojeći pokriva sekvencijalnu primjenu generički).
- [ ] Migracija je idempotentna kroz postojeći migration-runner checksum
      mehanizam (ista provjera kao svaka prethodna migracija).
- [ ] `UNIQUE(run_id, normalized_url)` na `crawl_targets` DOKAZANO
      radi — test koji pokuša duplo insertovati isti `(run_id, url)`
      i potvrđuje `ON CONFLICT DO NOTHING` ponašanje (broj redova
      ostaje 1, `register_crawl_targets` vraća 0 za duplikat).
- [ ] **`claim_next_crawl_target` je DOKAZANO atomsko pod konkurencijom**
      — test sa 2+ threads (isti stil kao ACS-HOTFIX-001 race-condition
      test) koji pozivaju `claim_next_crawl_target` na ISTOM `run_id`
      sa VIŠE `PENDING` targeta, potvrđuje da NIJEDAN target nije
      claimovan dvaput. Ovo je NAJVAŽNIJI test u ovom tasku (G-WI-RECOVER
      hard gate zavisi od ovoga kad S2-G6 stigne).
- [ ] `recover_expired_leases` dokazano vraća `LEASED` redove sa isteklim
      `lease_until` nazad na `PENDING`, NE dira `LEASED` redove sa
      budućim `lease_until`.
- [ ] Sve postojeće `IngestionRepositoryPort` metode (S2-G1, 13 komada)
      implementirane i testirane round-trip (save → get/list vraća
      identičan entitet).
- [ ] `SqliteIngestionRepository` registrovan u `__init__.py`.
- [ ] `IngestionRepositoryPort` runtime-checkable test proširen (isti
      obrazac kao `test_all_repository_ports_are_defined`).
- [ ] GitNexus: `detect_changes` PRIJE commit-a pokazuje SAMO nove
      simbole + čisto aditivne izmjene na `ports/repositories.py`/
      `domain/ingestion/entities.py`/`domain/ingestion/enums.py`/
      `domain/common/ids.py` — nula izmjena S2-G1 metoda/polja.
- [ ] `python -m pytest -q` cijeli suite prolazi (poznati flaky
      `test_gate_report_against_current_repo_passes` MOŽE se pojaviti
      nezavisno — sada bi `stdout_tail=` u
      `artifacts/phase0_foundation_gate.json` trebao pokazati koji test
      je stvarno pao, provjeriti da li se poklapa sa dosadašnjim
      zapažanjima ako se pojavi).
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.
- [ ] `tests/architecture/test_import_boundaries.py` zelen (infrastructure
      smije uvoziti domain/ports, provjeriti da nema obrnutog importa).
- [ ] **CI provjeren preko PR-a.**

# Implementation steps

1. Pročitati `resources/migrations/0006_performance_foundation.sql`,
   `infrastructure/database/migrations.py`,
   `infrastructure/database/repositories/sqlite_performance_repository.py`,
   `tests/integration/database/test_migrations.py`,
   `tests/unit/infrastructure/database/repositories/test_sqlite_performance_repository.py`
   (ili `tests/integration/database/repositories/` ekvivalent — provjeriti
   koji je aktuelni obrazac za nove repository adaptere) PRIJE koda.
2. Provjeriti stvarno ime brand tabele (`brands`? `brand_snapshots`?)
   za `ingestion_runs.brand_id` FK — ne pretpostaviti.
3. Napisati migraciju 0009.
4. Dodati `CrawlTarget`/`CrawlTargetState`/`CrawlTargetId` (§1/§2).
5. Proširiti `IngestionRepositoryPort` (§3).
6. Napisati `SqliteIngestionRepository` (§4), implementirati SVIH 19
   metoda porta.
7. Napisati atomicity test za `claim_next_crawl_target` PRIJE nego što
   se implementacija smatra gotovom (test-first za ovaj specifičan dio
   — najveći rizik u tasku).
8. GitNexus `detect_changes` prije commit-a.

# Review focus — Claude PRVO, PA Codex (HIGH, pun ciklus)

- **`claim_next_crawl_target` atomicity pod konkurencijom** — glavni
  fokus. Provjeriti da SQL mehanizam stvarno sprječava double-claim
  (ne osloniti se na "izgleda ispravno", tražiti stvaran concurrent
  test rezultat).
- Migracija je additive, ne dira postojeće tabele/kolone.
- `UNIQUE(run_id, normalized_url)` + `ON CONFLICT DO NOTHING` stvarno
  testirano, ne samo tvrđeno.
- `recover_expired_leases` granični slučajevi (`lease_until` tačno
  `now`, `lease_until IS NULL` na ne-LEASED redu).
- Nijedna S2-G1 port metoda/domain entitet nije mijenjana (GitNexus
  `detect_changes` + ručni diff).
- Round-trip testovi za SVE 19 metoda, ne samo nove.

**Codex adversarial fokus**: konkurentni claim test — pokušati
smisliti scenario koji bi implementerov test propustio (npr. race
između `claim_next_crawl_target` i `recover_expired_leases` na istom
redu, ili claim tačno na granici `lease_until` isteka).

# Rollback

HIGH risk (migracija, non-negotiable per workflow §6) — PUN ciklus:
Claude review → Codex adversarial review → Human Owner eksplicitno
odobrenje PRIJE merge-a. Migracija je aditivna (nove tabele, nema
`ALTER` na postojećim) — rollback je brisanje 0009 fajla + ručno
`DROP TABLE` ako je greškom primijenjena na dev bazu (nema podataka u
produkciji da se izgubi, projekat je pre-launch).

# Coordination

Zavisi od ACS-S2-001 (MERGED). Blokira S2-G3/G4/G5/G9 (svi zavise od
ove sheme, kanonski plan §3 DAG). Nema poznatih nezavisnih paralelnih
kandidata trenutno otvorenih — ako se pojavi novi nezavisan
maintenance task (van `domain/ingestion/`, `ports/repositories.py`,
`infrastructure/database/`), provjeriti `allowed_paths` presjek prije
paralelnog pokretanja (workflow §10).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-S2-002-ingestion-persistence
Branch:   task/ACS-S2-002-ingestion-persistence
Base:     main @ 8a6eb7c
```
