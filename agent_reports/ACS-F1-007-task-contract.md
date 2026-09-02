---
task_id: ACS-F1-007
phase: Faza-1
title: "A6 — LoadBrandFixture use-case"
risk: MEDIUM
coordinator: claude
implementer: pi
reviewers: [claude]
status: "OPEN — contract written before code"
created_at: 2026-09-02
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/application/brands/__init__.py
  - src/ai_campaign_studio/application/brands/load_brand_fixture.py
  - resources/fixtures/
  - tests/unit/application/brands/
  - tests/integration/application/brands/
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/schemas/
  - src/ai_campaign_studio/application/mappers/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/infrastructure/database/connection.py
  - src/ai_campaign_studio/infrastructure/database/migrations.py
  - src/ai_campaign_studio/infrastructure/database/unit_of_work.py
  - src/ai_campaign_studio/infrastructure/database/repositories/
  - src/ai_campaign_studio/presentation/
  - src/ai_campaign_studio/presentation_webview/
  - src/ai_campaign_studio/bootstrap.py
  - src/ai_campaign_studio/main.py
gitnexus_required: true
adversarial_required: false
gitnexus:
  required: true
  repository: "H:\\AI Campaing Studio"
  worktree: main (pre-branch pre-impact)
  branch: main
  head: b4b324f
  index_status: fresh (analyze re-run 2026-09-02 post ACS-GUI-001 merge)
  targets:
    - symbol: "new application/brands/ package"
      upstream_risk: NONE
      upstream_count: 0
      downstream_notes: "Brand-new directory, zero existing importers. Orchestrates already-merged, stable pieces: application/schemas/brand_fixture.py + application/mappers/brand_fixture_mapper.py (ACS-F1-003), ports/repositories.py + infrastructure SQLite adapters (ACS-F1-005). Does not modify any of them."
      affected_processes: []
  scope_fit: PASS
  unknowns: []
---

# Kontekst

Task **A6 — Fixture load use-case** (plan sekcija poslije 0A.3/repozitorijum
struktura, `application/brands/load_brand_fixture.py`). Prvi pravi
**application-layer orchestration** task u projektu — spaja tri već
merged, već review-ovana sloja u jedan realan tok:

```text
JSON fixture fajl
  -> BrandFixtureSchema (Pydantic validacija, ACS-F1-003)
  -> map_brand_fixture() (mapper u domain objekte, ACS-F1-003)
  -> BrandRepositoryPort.save_brand/save_snapshot +
     FactRepositoryPort.save_fact (SQLite adapteri, ACS-F1-005)
```

sve u JEDNOJ transakciji (`SqliteUnitOfWork`) — ako bilo šta faila,
NIŠTA se ne perzistira (plan acceptance: "load nije partial ako jedna
stavka faila").

**Fixture fajl**: plan pominje `dental_clinic_v1.json`, ali
`resources/fixtures/brightsmile.json` (ACS-F1-003, dental brend,
BrightSmile Dental) već postoji i već validira/mapira ispravno. Po
0A.5 (pravilo protiv dupliranja): **koristiti postojeći
`brightsmile.json`, ne praviti drugi paralelni dental fixture fajl.**
Ako implementer smatra da treba dodatni/drugačiji fixture primjer
(npr. da pokrije edge case koji `brightsmile.json` ne pokriva), to je
dozvoljeno DODATI kao novi fajl uz jasno obrazloženje, ne kao zamjenu.

**Risk**: MEDIUM — orchestration logika nad već review-ovanim slojevima,
ne dira SecretStore/bootstrap/registry contracts. §29 politika:
Claude-only review, PASS -> odmah commit/push/merge.

Prije koda pročitati:

```text
AGENTS.md
CLAUDE.md
docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md
.agent/CURRENT_STATE.md
AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md
  sekcija "A6 — Fixture load use-case", sekcija 5 (repo struktura —
  application/brands/), AR3 (nema services/ kante za sve — use-case
  ostaje fokusiran na TAČNO ovaj tok, ne postaje generički "BrandService")
```

Pročitati postojeći kod koji se orkestrira (ne pogađati potpise):

```text
src/ai_campaign_studio/application/schemas/brand_fixture.py
src/ai_campaign_studio/application/mappers/brand_fixture_mapper.py
src/ai_campaign_studio/ports/repositories.py
src/ai_campaign_studio/infrastructure/database/unit_of_work.py
src/ai_campaign_studio/infrastructure/database/repositories/sqlite_brand_repository.py
src/ai_campaign_studio/infrastructure/database/repositories/sqlite_fact_repository.py
resources/fixtures/brightsmile.json
```

# Objective

1. `application/brands/load_brand_fixture.py` — `LoadBrandFixture`
   use-case klasa/funkcija.
2. Testovi: unit (mock/fake repositories, brzo) + integration (prava
   SQLite baza, pravi fixture fajl, pun round-trip).

# Implementation steps

## `LoadBrandFixture`

Konstruktor prima repository portove (dependency injection — TIPOVI su
`BrandRepositoryPort`/`FactRepositoryPort` iz `ports.repositories`, NE
konkretne SQLite klase — use-case ne zna da je SQLite ispod). Npr.:

```text
class LoadBrandFixture:
    def __init__(self, brand_repo: BrandRepositoryPort,
                 fact_repo: FactRepositoryPort) -> None: ...
    def execute(self, fixture_path: Path) -> BrandSnapshot: ...
```

(implementer bira tačan potpis/naziv metode — `execute`/`run`/`__call__`,
dokumentovati izbor; vratiti barem `BrandSnapshot` da pozivalac ima
referencu na rezultat).

Tok:

1. Pročitati JSON fajl sa `fixture_path`.
2. Validirati kroz `BrandFixtureSchema.model_validate_json(...)` — ako
   ne validira, propagirati grešku (ne gutati je), ništa nije
   perzistirano (validacija se dešava PRIJE bilo kakvog repository
   poziva).
3. Mapirati kroz `map_brand_fixture(...)`.
4. Perzistirati SVE (brand + facts + snapshot) unutar JEDNE
   `SqliteUnitOfWork` transakcije — koristiti UoW-ov `.connection` da
   konstruišeš repository adaptere AKO use-case sam pravi konkretne
   adaptere (alternativa: pozivalac injektuje već-konstruisane
   repository instance vezane za istu konekciju/UoW — implementer bira,
   ali MORA garantovati da su brand/facts/snapshot pozivi na ISTOJ
   konekciji unutar iste transakcije, inače atomicity ne radi).
5. `uow.commit()` samo ako SVI pozivi uspiju; bilo koji exception prije
   commit-a mora ostaviti bazu bez ijednog reda iz ovog load-a (UoW-ov
   `__exit__` već radi ROLLBACK ako `commit()` nije pozvan — provjeriti
   da se use-case oslanja na taj mehanizam, ne pravi svoj paralelni
   try/except koji bi mogao promašiti neki slučaj).

# Acceptance

- [ ] Uspješan load: brand + svaki fact + snapshot su perzistirani
      (provjereno čitanjem nazad kroz repository portove nakon load-a).
- [ ] Svaki perzistovani fact ima `source_ref.uri` koji počinje sa
      `fixture://` (plan acceptance — provjeriti da `brightsmile.json`
      stvarno ima taj prefiks za sve facts; ako ne, to je nalaz za
      prijaviti, ne tiho zaobići).
- [ ] Atomicity test: simulirati failure NA POLA puta (npr. mock
      repository čiji treći `save_fact` poziv baca exception) i
      dokazati da NIŠTA nije u bazi poslije (ni brand, ni ijedan fact,
      ni snapshot) — ovo je adversarial-style test, obavezan iako
      `adversarial_required` nije formalno true za cijeli task, jer je
      to DIREKTNO plan acceptance kriterijum.
- [ ] Nevalidan fixture JSON (npr. prazan `facts` niz) baca grešku PRIJE
      bilo kakvog repository poziva (test dokazuje da je repository
      mock/fake netaknut).
- [ ] `LoadBrandFixture` NE zna da je ispod SQLite — zavisi samo od
      `BrandRepositoryPort`/`FactRepositoryPort` protokola (test sa
      fake/in-memory implementacijom tih portova prolazi jednako dobro
      kao test sa pravim SQLite adapterima).
- [ ] Integration test koristi pravu SQLite bazu (kao u ACS-F1-005/006
      testovima — `create_connection` + `run_migrations` na `tmp_path`).
- [ ] `python -m pytest -q`, `ruff check .`, `mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest -q
python -m pytest tests/architecture/test_import_boundaries.py -v
python -m pytest tests/unit/application/brands tests/integration/application/brands -v
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- atomicity je STVARNO testirana (mid-failure rollback), ne samo
  tvrđena u docstring-u;
- use-case zavisi od Protocol-a (portova), ne konkretnih SQLite klasa —
  provjeriti import-e u `load_brand_fixture.py`;
- ne dupira validaciju/mapping logiku koja već postoji u
  `application/schemas/`/`application/mappers/` — samo je orkestrira;
- `fixture://` provenance prefiks provjeren, ne pretpostavljen;
- scope discipline — nema dirania `application/schemas/`,
  `application/mappers/`, `ports/repositories.py`, postojećih SQLite
  adaptera.

# Rollback

MEDIUM risk — nova, izolovana orchestration klasa bez postojećih
importera. Fix na istoj branch bez proširenja scope-a. STOP i vrati na
puni ciklus samo ako se pokaže potreba da task dira nešto sa HIGH liste.

# Coordination

Nezavisno od **ACS-F1-008** (Crush, A7 — Prompt repository + AI port +
mock adapter) — potpuno disjoint `allowed_paths`, nema zavisnosti, oba
mogu ići paralelno odmah. Nezavisno i od **ACS-GUI-002** (MiniMax).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-007-load-brand-fixture
Branch:   task/ACS-F1-007-load-brand-fixture
Base:     main @ b4b324f
```
