---
task_id: ACS-BK-002
phase: "BK-G2 — Brand Knowledge Persistence"
title: "resources/migrations/0010_* + BrandKnowledgeRepositoryPort + SqliteBrandKnowledgeRepository"
coordinator: claude
implementer: TBD
reviewers: [claude, minimax]  # Codex privremeno nedostupan (2026-09-12) -- MiniMax preuzima adversarial rundu, isti status/sposobnosti (AGENTS.md "Uloge")
status: "OPEN -- contract written before code, čeka implementera"
created_at: 2026-09-12
dependencies: [ACS-BK-001]
risk: HIGH
allowed_paths:
  - resources/migrations/0010_brand_knowledge_foundation.sql
  - src/ai_campaign_studio/ports/repositories.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_brand_knowledge_repository.py
  - tests/integration/database/repositories/test_sqlite_brand_knowledge_repository.py
forbidden_paths:
  - src/ai_campaign_studio/domain/brand_knowledge/
  - src/ai_campaign_studio/domain/facts/
  - src/ai_campaign_studio/domain/brand/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/presentation_webview/
  - resources/migrations/0000_foundation.sql
  - resources/migrations/0001_brand_facts.sql
  - resources/migrations/0002_campaign_content_visual.sql
  - resources/migrations/0003_content_payload.sql
  - resources/migrations/0004_uniqueness_constraints.sql
  - resources/migrations/0005_layout_specs.sql
  - resources/migrations/0006_performance_foundation.sql
  - resources/migrations/0007_performance_import_rows.sql
  - resources/migrations/0008_performance_import_row_match_status.sql
  - resources/migrations/0009_ingestion_foundation.sql
graft_required: true
gitnexus_required: true
adversarial_required: true
---

# Kontekst

Drugi gate Brand Knowledge inicijative (`docs/AI Campaign Studio —
Brand Knowledge Implementation Plan.md`, §7/§8). BK-G1 (`ACS-BK-001`,
merge-ovan `88df6da`) je zaključao `domain/brand_knowledge/`
(`KnowledgeCategory`/`KnowledgeStatus`/`EvidenceType`, `KnowledgeEntry`,
`BrandKnowledgeSnapshot`, field registry) — **taj domain kod se ovdje
NE dira** (`forbidden_paths`). Ovaj task mu daje prvu SQLite tabelu i
repository port. I dalje NEMA ekstrakcije, LLM-a, GUI-ja ni Campaign
Engine integracije (to su BK-G3/G4/G6/G8 — budući taskovi).

**Zašto HIGH** (za razliku od BK-G1 koji je bio MEDIUM): ovaj task
dodaje pravu SQL migraciju (`resources/migrations/`) — shared-schema
izmjena koja utiče na svaku buduću instalaciju baze, nepovratna nakon
što neko primijeni migraciju na realne podatke. Prema
`docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md` §29 migracije ostaju na
punom review ciklusu (Claude → adversarial reviewer → eksplicitno
odobrenje Human Ownera), bez izuzetka. Adversarial rundu normalno
radi Codex; Codex je privremeno nedostupan (2026-09-12), pa je
zamjenjen MiniMax-om, koji ima isti status/sposobnosti za tu ulogu
(`AGENTS.md` "Uloge") — ako Codex postane dostupan prije nego što se
ovaj task otvori, Human Owner javlja i vraćamo se na Codex.

**Nezavisno verifikovano prije pisanja kontrakta** (ne pretpostavljeno
iz plana):

- Slijedeći slobodan migration broj je `0010` (`resources/migrations/`
  ide 0000-0009, auto-discover po `*.sql` glob + sort by version u
  `infrastructure/database/migrations.py` — nema registry fajla za
  ručno ažurirati, novi `.sql` fajl se pokupi sam).
- Tabele `brand_snapshots(id)` i `approved_facts(id)` već postoje
  (`0001_brand_facts.sql`) — FK referenca je direktna, ne treba nova
  migracija za njih.
- Postojeći projekat-wide "immutable replace" idiom je potvrđen u
  `SqliteFactRepository.save_fact_candidate` i
  `SqliteBrandRepository.save_snapshot`: `INSERT ... ON CONFLICT(id)
  DO UPDATE SET ...` za glavni red, plus `DELETE FROM <join_table>
  WHERE parent_id = ?` + re-`INSERT` petlja za child/join tabelu
  (vidi `brand_snapshot_facts` u `save_snapshot`). **Ovaj isti obrazac
  se prenosi 1:1 na `brand_knowledge_entries`/`brand_knowledge_entry_facts`
  i `brand_knowledge_snapshots`/`brand_knowledge_snapshot_entries`** —
  plan §8 eksplicitno traži da se ne izmišlja `update_*`/`replace_*`
  ako postoji jasan `save_*` obrazac, i on postoji.
  Isto potvrđeno: `test_foreign_keys_are_enforced` u postojećim
  integration testovima znači `PRAGMA foreign_keys=ON` je aktivan na
  konekciji — FK-ovi ispod se STVARNO provjeravaju, ne samo deklarativni.
- Repository konstruktor konvencija: `def __init__(self, connection:
  sqlite3.Connection) -> None` (isto kao `SqliteBrandRepository`/
  `SqliteFactRepository`) — nema DI kontejnera, nema factory sloja.
- Novi repo se **ne wire-uje** u `CampaignBridgeApi._CallResources`
  (jedino mjesto gdje se `SqliteBrandRepository`/`SqliteFactRepository`
  danas instanciraju zajedno) — nijedan use-case još ne konzumira
  `BrandKnowledgeRepositoryPort` (to dolazi sa BK-G3+), pa dodavanje u
  bridge sada bi bio unused-import scope creep. Testovi instanciraju
  repo direktno, isto kao ostali integration testovi.

**Graft je primarni alat od 2026-09-12** (`.agent/GRAFT_PROTOCOL.md`)
— `graft callers`/`graft grep`/`graft blast` obavezni prije i poslije
izmjene `ports/repositories.py` (shared contract fajl — svaki drugi
repo port živi u istom fajlu, blast radius provjera je obavezna da se
potvrdi da apend novog `Protocol`-a ne dira postojeće). GitNexus
sekundarna probaciona provjera, raditi obje ako je moguće.

# Objective

## 1. Migracija `resources/migrations/0010_brand_knowledge_foundation.sql`

Doslovno iz plana §7 (4 tabele):

```sql
CREATE TABLE brand_knowledge_entries (
    id TEXT PRIMARY KEY,
    brand_snapshot_id TEXT NOT NULL REFERENCES brand_snapshots(id),
    category TEXT NOT NULL,
    field_name TEXT NOT NULL,
    value TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    status TEXT NOT NULL,
    confidence REAL NULL,
    conflict_group_id TEXT NULL,
    created_at TEXT NOT NULL,
    reviewed_at TEXT NULL
);

CREATE TABLE brand_knowledge_entry_facts (
    entry_id TEXT NOT NULL REFERENCES brand_knowledge_entries(id),
    fact_id TEXT NOT NULL REFERENCES approved_facts(id),
    position INTEGER NOT NULL,
    PRIMARY KEY (entry_id, fact_id)
);

CREATE TABLE brand_knowledge_snapshots (
    id TEXT PRIMARY KEY,
    brand_snapshot_id TEXT NOT NULL REFERENCES brand_snapshots(id),
    version INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(brand_snapshot_id, version)
);

CREATE TABLE brand_knowledge_snapshot_entries (
    knowledge_snapshot_id TEXT NOT NULL
        REFERENCES brand_knowledge_snapshots(id),
    entry_id TEXT NOT NULL REFERENCES brand_knowledge_entries(id),
    position INTEGER NOT NULL,
    PRIMARY KEY (knowledge_snapshot_id, entry_id)
);
```

Napomene (obavezno ispoštovati, plan §7):

- `field_name` je kolona (ne `field`) jer domain atribut zove se
  `field` — ime kolone `field_name` izbjegava dvosmislenost u SQL-u,
  isto kao što plan doslovno kaže.
- `brand_knowledge_entry_facts` je **stvarna FK relacija**
  (`entry_id`/`fact_id`), NE JSON blob unutar `brand_knowledge_entries`
  reda — plan §7 eksplicitno: "Ova tabela je veoma važna. NE čuvati
  provenance samo unutar JSON-a." Ovo je isti obrazac kao postojeći
  `brand_snapshot_facts`.
- `category`/`evidence_type`/`status` su TEXT (enum `.value`), isti
  stil kao `approved_facts.status`, `crawl_targets.state`.
- `UNIQUE(brand_snapshot_id, version)` na `brand_knowledge_snapshots`
  — plan §7 eksplicitna constraint.
- NE mijenjati nijednu postojeću `.sql` migraciju — ovo je aditivna,
  potpuno nova datoteka.

## 2. `BrandKnowledgeRepositoryPort` (`ports/repositories.py`, append)

Dodati NA KRAJ fajla (posle postojeće zadnje `Protocol` klase), isti
stil kao `BrandRepositoryPort`/`FactRepositoryPort` (docstring na
klasi, `...` tijela metoda, kratki komentar tamo gdje semantika nije
očigledna iz imena):

```python
@runtime_checkable
class BrandKnowledgeRepositoryPort(Protocol):
    """Persistence for ``KnowledgeEntry`` and ``BrandKnowledgeSnapshot``."""

    def save_entry(self, entry: KnowledgeEntry) -> None: ...

    def get_entry(self, entry_id: KnowledgeEntryId) -> KnowledgeEntry | None: ...

    def list_entries_for_brand_snapshot(
        self, brand_snapshot_id: BrandSnapshotId
    ) -> tuple[KnowledgeEntry, ...]: ...

    def list_entries_by_status(
        self, brand_snapshot_id: BrandSnapshotId, status: KnowledgeStatus
    ) -> tuple[KnowledgeEntry, ...]: ...

    def save_knowledge_snapshot(
        self, snapshot: BrandKnowledgeSnapshot
    ) -> None: ...

    def get_knowledge_snapshot(
        self, snapshot_id: BrandKnowledgeSnapshotId
    ) -> BrandKnowledgeSnapshot | None: ...

    def get_latest_knowledge_snapshot(
        self, brand_snapshot_id: BrandSnapshotId
    ) -> BrandKnowledgeSnapshot | None:
        """Highest-version BrandKnowledgeSnapshot for a BrandSnapshot, or
        None. Isti obrazac kao ``BrandRepositoryPort.get_latest_snapshot``
        — buduća builder logika (BK-G7) ga koristi za sljedeći version."""
```

Nema `replace_entry_status`/`update_*` metode — plan §8 sam kaže da
se prati postojeći `save_*` idiom ako postoji, a potvrđeno je da
postoji (Kontekst iznad). Status promjena je samo poziv `save_entry`
sa istim `id`, novim `status` (upsert).

Dodati potrebne importe na vrh fajla:
`KnowledgeEntry`, `BrandKnowledgeSnapshot` (iz
`domain.brand_knowledge.entities`), `KnowledgeStatus` (iz
`domain.brand_knowledge.enums`), `KnowledgeEntryId`,
`BrandKnowledgeSnapshotId` (iz `domain.common.ids` — već postoje od
BK-G1).

## 3. `SqliteBrandKnowledgeRepository`

Novi fajl:
`infrastructure/database/repositories/sqlite_brand_knowledge_repository.py`

Isti stil kao `SqliteBrandRepository`/`SqliteFactRepository`:

- `__init__(self, connection: sqlite3.Connection) -> None`.
- `save_entry`: `INSERT ... ON CONFLICT(id) DO UPDATE SET ...` u
  `brand_knowledge_entries`, zatim `DELETE FROM
  brand_knowledge_entry_facts WHERE entry_id = ?` + re-`INSERT` petlja
  po `entry.source_fact_ids` (position = enumerate index) — identičan
  obrazac kao `SqliteBrandRepository.save_snapshot` +
  `brand_snapshot_facts`.
- `get_entry`: `SELECT * FROM brand_knowledge_entries WHERE id = ?` +
  posebna query za `brand_knowledge_entry_facts` da rekonstruiše
  `source_fact_ids` tuple (ORDER BY position).
- `list_entries_for_brand_snapshot` / `list_entries_by_status`:
  `SELECT ... WHERE brand_snapshot_id = ? [AND status = ?] ORDER BY
  created_at` — svaki red rekonstruiše `source_fact_ids` isto kao
  `get_entry` (izdvojiti u privatni helper `_entry_from_row` +
  posebnu funkciju/petlju za fact_ids da se ne duplicira kod).
- `save_knowledge_snapshot` / `get_knowledge_snapshot` /
  `get_latest_knowledge_snapshot`: isti obrazac kao gore, koristeći
  `brand_knowledge_snapshots` + `brand_knowledge_snapshot_entries`
  (join tabela rekonstruiše `approved_entry_ids` tuple po `position`).
- Enum rekonstrukcija: `KnowledgeCategory(row["category"])`,
  `KnowledgeStatus(row["status"])`, `EvidenceType(row["evidence_type"])`
  — isti stil kao `FactStatus(row["status"])` u postojećem
  `_fact_from_row`.
- Datumi: `datetime.fromisoformat(...)`, isti stil kao svugdje drugo
  u repo sloju.

## 4. Testovi

Novi fajl:
`tests/integration/database/repositories/test_sqlite_brand_knowledge_repository.py`

Minimalno (isti stil/fixture obrazac kao
`test_sqlite_brand_repository.py` — `_setup_db(tmp_path)` helper,
`sqlite3.Connection` sa primijenjenim migracijama):

- round-trip `save_entry`/`get_entry` (svi field-ovi, uključujući
  `confidence=None` i `conflict_group_id=None`).
- `source_fact_ids` redoslijed očuvan kroz save/get (position kolona
  radi).
- `save_entry` na isti `id` je upsert (status promjena PROPOSED→
  APPROVED preko drugog `save_entry` poziva, `get_entry` vraća novi
  status, `reviewed_at` popunjen).
- `list_entries_for_brand_snapshot` vraća sve, `list_entries_by_status`
  filtrira tačno.
- FK enforcement: `entry_id`/`fact_id` koji ne postoje → `IntegrityError`
  (isti stil kao postojeći `test_foreign_keys_are_enforced`).
- round-trip `save_knowledge_snapshot`/`get_knowledge_snapshot`,
  `approved_entry_ids` redoslijed očuvan.
- `get_latest_knowledge_snapshot` vraća najviši `version` za dati
  `brand_snapshot_id`.
- `UNIQUE(brand_snapshot_id, version)` constraint stvarno baca grešku
  na duplikat (isto testirati kao integrity test).

# Šta NE raditi (eksplicitno, plan §7/§8/§45)

- NE dirati `domain/brand_knowledge/` (BK-G1 je zaključan,
  `forbidden_paths` sprječava, ali eksplicitno: čak i "sitna"
  poboljšanja tipova idu kroz novi kontrakt, ne ovdje).
- NE dodavati `update_*`/`replace_*` metode — `save_*` upsert je
  dovoljan (Kontekst iznad).
- NE praviti JSON kolonu za `source_fact_ids`/`approved_entry_ids` —
  MORA biti prava FK join tabela (plan §7 eksplicitno).
- NE wire-ovati novi repo u `CampaignBridgeApi`/`_CallResources` —
  nijedan use-case ga još ne koristi (BK-G3+ ga povezuje).
- NE dodavati validaciju "da li su entries stvarno APPROVED" u
  `save_knowledge_snapshot` — to je aplikativni sloj (budući BK-G7),
  repository samo perzistira šta mu se da.
- NE dirati postojećih 10 `.sql` migracija (0000-0009).
- NEMA LLM koda, NEMA ekstrakcije, NEMA GUI-ja, NEMA Campaign Engine
  integracije.

# Acceptance

- [ ] `0010_brand_knowledge_foundation.sql` — tačno 4 tabele iznad,
      nijedna postojeća migracija netaknuta.
- [ ] `BrandKnowledgeRepositoryPort` dodan na kraj `ports/repositories.py`,
      postojeći portovi netaknuti.
- [ ] `SqliteBrandKnowledgeRepository` implementira sve metode porta,
      `save_*` upsert obrazac, join tabele za provenance (ne JSON).
- [ ] Svi novi integration testovi prolaze, uključujući FK enforcement
      i `UNIQUE(brand_snapshot_id, version)`.
- [ ] `python -m pytest -q` (pun suite, DeepSeek key unset) — 0
      regresija na postojećim testovima (posebno
      `test_sqlite_brand_repository.py`,
      `test_sqlite_fact_repository.py` ako postoji).
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths` — posebno nula u
      `domain/`, `application/`, `presentation_webview/`, i van nove
      `0010_*.sql`.
- [ ] Graft `callers`/`blast` na `ports/repositories.py` prije i
      poslije izmjene (shared-contract fajl, blast radius mora
      pokazati da su pogođeni SAMO novi simboli, ne postojeći
      portovi).
- [ ] Mutation test na bar jednu constraint (npr. privremeno ukloniti
      `UNIQUE(brand_snapshot_id, version)`, potvrditi da odgovarajući
      test padne, vratiti).
- [ ] **MiniMax adversarial round** (Codex privremeno nedostupan, vidi
      napomena ispod frontmatter-a; HIGH risk, `adversarial_required:
      true`) — posebno: race na `save_entry` upsert (dva paralelna
      poziva istim `id`), FK cascade/orphan scenariji, prazan
      `source_fact_ids` na entry koji dolazi iz baze (da li repo sloj
      vjeruje domain invarijanti ili je re-provjerava).
- [ ] **CI provjeren preko PR-a.**
- [ ] **Eksplicitno odobrenje Human Ownera prije merge-a** (HIGH,
      §29 izuzetak ne važi za migracije).

# Implementation steps

1. Pročitati `resources/migrations/0001_brand_facts.sql` i
   `0009_ingestion_foundation.sql` kao stil-referencu.
2. Pročitati `SqliteBrandRepository.save_snapshot` u cjelini
   (join-tabela replace obrazac) — ovo je jedini pravi predložak.
3. Pročitati `domain/brand_knowledge/entities.py`/`enums.py` (BK-G1,
   READ-ONLY) da se potvrde tačna imena polja.
4. Napisati `0010_brand_knowledge_foundation.sql`.
5. Dodati `BrandKnowledgeRepositoryPort` u `ports/repositories.py`.
6. Napisati `sqlite_brand_knowledge_repository.py`.
7. Napisati integration testove (checklist iznad).
8. `PYTHONPATH=src python -m pytest tests/integration/database/repositories/test_sqlite_brand_knowledge_repository.py -v`.
9. Pun suite + ruff + mypy.
10. Graft `callers`/`grep`/`blast` na `ports/repositories.py` prije
    commit-a (`.agent/GRAFT_PROTOCOL.md`) — potvrditi da apend ne
    mijenja postojeće simbole.

# Review focus — Claude prvo, zatim MiniMax (Codex zamjena, HIGH, puni ciklus)

- Migracija: FK reference tačne, `UNIQUE` constraint prisutan, nijedna
  stara `.sql` datoteka nije dirana, novi fajl se stvarno pokupi
  auto-discover-om (provjeriti `discover_migrations` glob).
- Provenance je STVARNA FK relacija, ne JSON (plan §7 non-negotiable).
- `save_*` upsert obrazac dosljedno primijenjen (bez novih
  `update_*`/`replace_*` metoda).
- Repository NE validira domain invarijante koje entiteti već
  garantuju (ne duplicirati `KnowledgeEntry.__post_init__` logiku u
  repo sloju) niti ne validira aplikativne invarijante koje mu ne
  pripadaju (npr. "je li entry APPROVED" za snapshot).
- Mutation test na `UNIQUE(brand_snapshot_id, version)` i na FK
  enforcement.
- Graft `blast` na `ports/repositories.py` potvrđuje da su pogođeni
  SAMO novi simboli.
- MiniMax adversarial: concurrent upsert, orphan/cascade edge cases,
  malformed row rekonstrukcija (npr. `category` vrijednost u bazi koja
  više ne postoji u enumu — da li repo baca jasnu grešku ili silently
  puca).

# Rollback

HIGH risk (prava SQL migracija, shared-contract fajl
`ports/repositories.py`). Puni ciklus bez izuzetka: Claude PASS →
MiniMax adversarial round (Codex privremeno nedostupan, 2026-09-12 —
ako se vrati u toku ovog taska, Human Owner javlja i MiniMax se može
zamijeniti/dopuniti sa Codex rundom) → eksplicitno odobrenje Human
Ownera prije merge-a. Ako se nađe blokirajući nalaz, fix-round pa
ponovna nezavisna verifikacija (isti obrazac kao ACS-S2-002 BF-1).

# Coordination

Zavisi od `ACS-BK-001` (merge-ovan, `88df6da`) — domain tipovi moraju
biti zaključani prije nego što se pišu za njih tabele. Blokira BK-G3
(deterministička ekstrakcija — treba repo da perzistira predložene
entry-je).

**Paralelni rad**: `allowed_paths` ovog taska (nova migracija, append
na `ports/repositories.py`, nov repo fajl, nov test fajl) se NE
preklapa sa `domain/brand_knowledge/` (zaključano BK-G1) niti sa bilo
kojim trenutno otvorenim GUI/bridge taskom
(`ACS-S2-018` dira `presentation_webview/`+`sqlite_brand_repository.py`,
potpuno izvan ovog scope-a). Jedini rizik je ako neki drugi paralelni
task istovremeno apenduje na `ports/repositories.py` (shared fajl) —
provjeriti prije starta da li je taj fajl već "u igri" na drugom
worktree-u (u ovom trenutku nije). Ako se GUI/bridge task završi prije
ovog, nema uticaja — različiti dijelovi istog fajla u najgorem slučaju
znače trivijalan merge/rebase, ne pravi konflikt logike.

**Napomena (predaja implementeru)**: u glavnom repo working tree-u
(ne u ovom worktree-u) postoji NEKOMITOVANA izmjena na
`src/ai_campaign_studio/ports/repositories.py` (dodaje
`BrandRepositoryPort.list_snapshots` — ostatak iz ACS-S2-018 sesije).
Implementer ovog taska radi u SVOM čistom worktree-u ogranatom sa
`main` (gdje ta nekomitovana izmjena ne postoji), pa nema uticaja na
BK-G2 — ali koordinator treba riješiti taj nekomitovani ostatak u
main repou (odbaciti ili komitovati kroz ACS-S2-018) prije nego što
BK-G2 worktree kasnije rebase-uje na main, da izbjegne konfuziju.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-BK-002-persistence
Branch:   task/ACS-BK-002-persistence
Base:     main @ 28cc8ef
```
