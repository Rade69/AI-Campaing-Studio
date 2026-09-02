---
task_id: ACS-F1-005
phase: Faza-1
title: "Repository ports + Brand/Facts SQLite persistence (A5, dio 1)"
risk: MEDIUM
coordinator: claude
implementer: pi
reviewers: [claude]
status: "OPEN — contract written before code"
created_at: 2026-09-02
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/ports/repositories.py
  - src/ai_campaign_studio/infrastructure/database/repositories/__init__.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_brand_repository.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_fact_repository.py
  - resources/migrations/0001_brand_facts.sql
  - tests/unit/ports/test_repositories.py
  - tests/integration/database/repositories/test_sqlite_brand_repository.py
  - tests/integration/database/repositories/test_sqlite_fact_repository.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/infrastructure/database/connection.py
  - src/ai_campaign_studio/infrastructure/database/migrations.py
  - src/ai_campaign_studio/infrastructure/database/unit_of_work.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_campaign_repository.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_content_repository.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_visual_repository.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_revision_repository.py
  - resources/migrations/0000_foundation.sql
  - resources/migrations/0002_campaign_content_visual.sql
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
  head: 940d963
  index_status: fresh (analyze re-run 2026-09-02 post A4 merge)
  targets:
    - symbol: "new ports/repositories.py, new infrastructure/database/repositories/ package"
      upstream_risk: NONE
      upstream_count: 0
      downstream_notes: "ports/repositories.py currently does not exist (grep confirmed no importers of a repositories port anywhere). New SQLite adapter files are brand new. Adds one new migration file (0001) on top of the existing, already-reviewed migration runner (P0.17) -- additive only, no existing business data in the schema yet (Brand/Campaign/Content have never been persisted), not a destructive migration."
      affected_processes: []
  scope_fit: PASS
  unknowns: []
---

# Kontekst

Task **A5 — business persistence**, prvi dio. Per plan 0A.3: P0 je već
završio SQLite connection/migration runner/UoW foundation — **A5 NE pravi
novi DB foundation**, samo nastavlja sa business/domain migracijama i
repository portovima/adapterima na postojećem, već review-ovanom temelju
(`infrastructure/database/connection.py`, `migrations.py`,
`unit_of_work.py` — sve `forbidden_paths`, ne diraju se).

**Risk tier razjašnjenje (bitno)**: `docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md`
§3 eksplicitno navodi "repository adapter" kao MEDIUM primjer. §4
("Privremeno pojačan standard za Implementation Phase 0") koji tretira
SQLite/migrations kao HIGH-ekvivalent VAŽI SAMO ZA P0 taskove — Faza 1 to
naslijeđuje. HIGH tier u §3 je rezervisan za "DB schema/migration sa
postojećim podacima" i "destructive migration" — ovaj task dodaje NOVU,
čisto aditivnu migraciju (`0001_brand_facts.sql`) na shemu koja još nikad
nije sadržavala Brand/Campaign/Content poslovne podatke (ništa dosad nije
pisalo u te tabele). Nije destruktivna, ne dira postojeće tabele
(`app_metadata`/`provider_configs`/`model_selections` iz `0000_foundation.sql`).
**Zaključak: MEDIUM, ne HIGH.** §29 politika: Claude-only review, PASS ->
odmah commit/push/merge, bez Codex runde i bez posebnog Human Owner
odobrenja.

Paralelno ide **ACS-F1-006** (Crush) — Campaign/Content/Visual/Revision
SQLite adapteri, sekvenciran da čeka ovaj task za `ports/repositories.py`
(vidi taj kontrakt za tačan redoslijed).

Prije koda pročitati:

```text
AGENTS.md
CLAUDE.md
docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md §3 (Risk tier — pažljivo, MEDIUM
  vs HIGH razlika za repository/migracije), §7 (GitNexus), §11 (evidence)
.agent/CURRENT_STATE.md
AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md
  sekcija 0A.3 (A5 — šta P0 već pokriva), 16 (Repository portovi)
```

Pročitati postojeći P0 SQLite kod (ne pogađati konvencije):

```text
src/ai_campaign_studio/infrastructure/database/connection.py
  (row_factory=sqlite3.Row, foreign_keys=ON, isolation_level=None —
  autocommit, pozivalac kontroliše BEGIN/COMMIT/ROLLBACK eksplicitno)
src/ai_campaign_studio/infrastructure/database/migrations.py
  (NNNN_name.sql konvencija, checksum tracking, transakciono apply)
src/ai_campaign_studio/infrastructure/database/unit_of_work.py
  (SqliteUnitOfWork — .connection property "for repository adapters in
  later phases" — ovaj task JE ta later phase)
resources/migrations/0000_foundation.sql (DDL stil: TEXT PRIMARY KEY za
  ID-jeve, TEXT za ISO timestamp-ove, INTEGER 0/1 za bool)
src/ai_campaign_studio/ports/database.py (postojeći port stil — Protocol,
  framework-neutral)
```

# Objective

1. `ports/repositories.py` — svih 7 Protocol interfejsa iz plan sekcije 16:
   `BrandRepositoryPort`, `FactRepositoryPort`, `CampaignRepositoryPort`,
   `ContentRepositoryPort`, `VisualRepositoryPort`, `RevisionRepositoryPort`,
   `TelemetryRepositoryPort`. Definicije SAMO (nema implementacije ovdje —
   to je infrastructure sloj).
2. `resources/migrations/0001_brand_facts.sql` — tabele za Brand,
   BrandSnapshot, ApprovedFact.
3. `infrastructure/database/repositories/sqlite_brand_repository.py` +
   `sqlite_fact_repository.py` — konkretni SQLite adapteri koji
   implementiraju `BrandRepositoryPort`/`FactRepositoryPort`.
4. Round-trip integracioni testovi (save -> get -> uporedi) na pravoj
   SQLite bazi (in-memory ili temp fajl, koristeći postojeći
   `create_connection` + `run_migrations`).

# Implementation steps

## `ports/repositories.py`

Definisati sve 7 kao `typing.Protocol` klase (framework-neutral, ne
importuje `sqlite3` ni bilo šta iz `infrastructure/`). Detaljni potpisi
za 4 (iz plana, tačno):

```text
BrandRepositoryPort: save_brand(brand), save_snapshot(snapshot),
                      get_snapshot(snapshot_id)
FactRepositoryPort: save_fact(fact), get_fact(fact_id),
                     list_snapshot_facts(snapshot_id)
CampaignRepositoryPort: save_campaign(campaign), save_brief(brief),
                         save_plan(plan), get_campaign(campaign_id),
                         get_plan(plan_id)
ContentRepositoryPort: save_content_piece(content_piece),
                        get_content_piece(content_piece_id),
                        list_campaign_content(campaign_id)
```

Za preostala 3 (plan ne daje detaljne potpise — implementer projektuje
razumno, konzistentno sa gornjim obrascem, dokumentovati izbor):

```text
VisualRepositoryPort: save_visual_system(system),
                       get_visual_system(visual_system_id)
                       (minimalno za CampaignVisualSystem; LayoutSpec je
                       value object unutar njega, ne zaseban repository)
RevisionRepositoryPort: save_revision(revision), get_revision(revision_id),
                         list_entity_revisions(entity_type, entity_id)
TelemetryRepositoryPort: DEFINISATI INTERFACE SAMO, bez SQLite adaptera i
                         bez migracije u ovom tasku (Performance/Analytics
                         je arhitektonski planiran ali runtime modul nije
                         dio ranog Campaign Engine MVP-a — vidi CLAUDE.md.
                         Minimalan razuman potpis, npr.
                         record_event(event) — implementer bira, ali NE
                         pravi tabelu/adapter za njega sada).
```

Ne izlagati SQL detalje kroz Protocol (nema `cursor`/`connection`
parametara u potpisima).

## `resources/migrations/0001_brand_facts.sql`

Tabele (nazivi/kolone — implementer prilagođava tačnim domain poljima iz
`domain/brand/entities.py`, `domain/brand/value_objects.py`,
`domain/facts/entities.py`, ali mora pokriti SVA polja bez gubitka
podataka pri round-trip-u):

```text
brands (id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL)

brand_snapshots (id TEXT PRIMARY KEY, brand_id TEXT NOT NULL REFERENCES brands(id),
                  version INTEGER NOT NULL, language TEXT NOT NULL,
                  locale TEXT NOT NULL, script TEXT NOT NULL,
                  created_at TEXT NOT NULL)
  -- voice/audiences/services/visual_identity/restrictions su
  -- vrijednosni objekti sa listama unutar liste (npr. Audience.needs) —
  -- implementer bira: JSON kolona (TEXT, serijalizovan) za cijeli value
  -- object graf JE prihvatljivo ovdje (ovo je infrastructure serializacija,
  -- ne domain sloj, Pydantic/dataclass ostaju izvor istine) UMJESTO
  -- potpune normalizacije u posebne tabele — dokumentovati izbor jasno.
  -- approved_fact_ids: posebna join tabela
  -- (brand_snapshot_facts(snapshot_id, fact_id)) radi FK integriteta.

approved_facts (id TEXT PRIMARY KEY, logical_fact_id TEXT NOT NULL,
                 version INTEGER NOT NULL, content TEXT NOT NULL,
                 source_type TEXT NOT NULL, source_uri TEXT NOT NULL,
                 source_snapshot_id TEXT NULL, source_chunk_id TEXT NULL,
                 status TEXT NOT NULL, created_at TEXT NOT NULL,
                 superseded_by TEXT NULL, deleted_at TEXT NULL)

brand_snapshot_facts (snapshot_id TEXT NOT NULL REFERENCES brand_snapshots(id),
                       fact_id TEXT NOT NULL REFERENCES approved_facts(id),
                       PRIMARY KEY (snapshot_id, fact_id))
```

Poravnati sa `PRAGMA foreign_keys = ON` (već postavljeno u
`create_connection`) — FK reference moraju biti validne, testovi moraju
insert-ovati u ispravnom redoslijedu (brand pa snapshot pa facts pa join).

## SQLite adapteri

`sqlite_brand_repository.py` / `sqlite_fact_repository.py` — konstruktor
prima `sqlite3.Connection` (ili `SqliteUnitOfWork`, implementer bira i
dokumentuje — konzistentno sa `unit_of_work.py`-jevim `.connection`
property komentarom "for repository adapters in later phases"). Metode
implementiraju odgovarajući Protocol tačno. `save_*` metode su
insert-or-replace (idempotentne po primarnom ključu) — ne mora biti
puni upsert-svih-slučajeva, ali "save pa save opet isti objekat" ne smije
pući. Serijalizacija/deserijalizacija JSON kolona (ako se taj pristup
koristi) mora biti simetrična — round-trip test je dokaz.

# Acceptance

- [ ] Svih 7 Protocol interfejsa definisano u `ports/repositories.py`,
      framework-neutral (nema `sqlite3`/infrastructure importa).
- [ ] `SqliteBrandRepository`/`SqliteFactRepository` implementiraju svoje
      portove (provjerivo: `isinstance(x, BrandRepositoryPort)` structural
      check ili eksplicitan `Protocol` runtime_checkable test).
- [ ] Round-trip test: `save_brand` + `save_snapshot` + `save_fact` pa
      `get_snapshot`/`list_snapshot_facts` vraća objekat identičan
      originalu (svako polje, uključujući ugniježdene value objekte i
      tuple kolekcije).
- [ ] `save_snapshot` pozvan dvaput sa istim ID-jem ne baca gresku niti
      duplira redove (idempotentnost testirana).
- [ ] Migracija se primjenjuje čisto na svježoj bazi (`run_migrations`
      radi 0000 pa 0001 redom, testirano).
- [ ] `PRAGMA foreign_keys = ON` poštovan — insert u pogrešnom redoslijedu
      (npr. fact prije snapshot-a) baca FK violation, ne tiho prolazi
      (test dokazuje).
- [ ] `TelemetryRepositoryPort` postoji kao interface, BEZ SQLite
      adaptera/migracije u ovom tasku.
- [ ] Nema infrastructure importa u `ports/repositories.py` (architecture
      suite).
- [ ] `python -m pytest -q`, `ruff check .`, `mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest -q
python -m pytest tests/architecture/test_import_boundaries.py -v
python -m pytest tests/integration/database -v
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- Protocol definicije ne izlažu SQL/connection detalje (framework-neutral
  granica poštovana);
- round-trip testovi stvarno provjeravaju SVAKO polje, ne samo da "nešto
  vrati", posebno ugniježdene value objekte (voice/audiences/services/
  visual_identity/restrictions) i tuple kolekcije;
- FK poredak/idempotentnost stvarno testirani, ne samo tvrđeni;
- `TelemetryRepositoryPort` nema adapter/migraciju (scope discipline —
  Performance/Analytics deferral poštovan);
- migracija ne dira `0000_foundation.sql` niti postojeće P0 tabele;
- scope discipline — ne dira `connection.py`/`migrations.py`/
  `unit_of_work.py` (već review-ovan P0 foundation).

# Rollback

MEDIUM risk. Nova migracija je additive (nova tabela), lako se
"un-apply"-uje brisanjem baze u dev okruženju ako nešto pođe po zlu prije
merge-a — nema postojećih production/user podataka koji bi bili
ugroženi. Fix na istoj branch bez proširenja scope-a. STOP i vrati na
puni ciklus SAMO ako se pokaže da migracija mora biti destruktivna
(DROP/ALTER postojeće tabele) — to bi promijenilo risk tier na HIGH.

# Coordination

Paralelno sa **ACS-F1-006** (Crush), sekvencirano: Crush može odmah raditi
na migration schema dizajnu za Campaign/Content/Visual/Revision (bez
zavisnosti), ali implementacija SQLite adaptera mora čekati da ovaj task
merge-uje `ports/repositories.py` (Protocol definicije koje implementira).
`allowed_paths` disjoint (odvojeni fajlovi po domenu).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-005-brand-facts-persistence
Branch:   task/ACS-F1-005-brand-facts-persistence
Base:     main @ 940d963
```
