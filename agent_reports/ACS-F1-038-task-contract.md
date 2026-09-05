---
task_id: ACS-F1-038
phase: Slice 1.5 — P1.5-G2 Persistence (Faza 1 v1.5 §17)
title: "Performance perzistencija: migracija 0004 + PerformanceRepositoryPort + SqlitePerformanceRepository"
risk: MEDIUM
coordinator: claude
implementer: TBD
reviewers: [claude]
status: "OPEN — contract written before code, čeka implementera"
created_at: 2026-09-05
dependencies: [ACS-F1-037]
allowed_paths:
  - resources/migrations/0004_performance_foundation.sql
  - src/ai_campaign_studio/ports/repositories.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_performance_repository.py
  - src/ai_campaign_studio/infrastructure/database/repositories/__init__.py
  - tests/integration/database/repositories/test_sqlite_performance_repository.py
  - tests/integration/database/test_migrations.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/
  - resources/migrations/0000_foundation.sql
  - resources/migrations/0001_brand_facts.sql
  - resources/migrations/0002_campaign_content_visual.sql
  - resources/migrations/0003_content_payload.sql
  - src/ai_campaign_studio/ports/ai.py
  - src/ai_campaign_studio/ports/rendering.py
  - src/ai_campaign_studio/ports/export.py
gitnexus_required: true
adversarial_required: false
gitnexus:
  required: true
  note: >
    Per `.agent/TASK_ROUTING.md` — GitNexus obavezan za svaki Slice 1.5
    task. Proširuje `ports/repositories.py` (aditivno, nov port, nijedan
    postojeći port/metoda se ne mijenja) i dodaje novu migraciju
    (aditivna, tri nove tabele, ne dira postojeće). Koordinator pokreće
    detect-changes/impact prije merge-a (GitNexus MCP dostupan, indeks
    stale — re-index prije provjere).
  repository: "H:\\AI Campaing Studio"
  branch: main
  head: c67447d
  scope_fit: "PENDING — popuniti kad se GitNexus indeks osvježi prije merge-a."
---

# Kontekst

**P1.5-G2** (Faza 1 v1.5 §17) — dati mjesto u bazi pojmovima koje je
`ACS-F1-037` (mergovano) definisao kao čiste domain klase:
`DistributionInstance`, `PerformanceSnapshot`, `PerformanceImportBatch`.

**Namjerna dizajn odluka — `performance_import_rows` NIJE u ovom
tasku**, iako ga Faza 1 v1.5 §17 nabraja kao četvrtu "predloženu tabelu".
Razlog: ta tabela čuva PO-REDU audit trag CSV uvoza ("matched, unmatched,
ambiguous, invalid" po redu, §18) — njen STVARAN oblik zavisi od kako
P1.5-G3 (CSV Import, budući task) parsira i klasifikuje redove, a
`ACS-F1-037` (P1.5-G1) NIJE definisao domain entitet za pojedinačan
uvezen red (namjerno, taj task je pokrio samo tri entiteta koje Faza 0.7
§3/§5/§13 eksplicitno modeluje). Praviti tabelu BEZ domain entiteta i
BEZ stvarnog pozivaoca bi bilo "apstrakcija za svaki slučaj" (CLAUDE.md
zabranjeno) — isti obrazac kao ranije odgođena `render_artifacts` tabela
(A14) dok nije postojao stvaran konzument. `performance_import_rows`
ide u P1.5-G3, zajedno sa entitetom koji će je stvarno koristiti.

**Ovaj task pokriva TAČNO tri tabele** koje odgovaraju POSTOJEĆIM
`ACS-F1-037` domain entitetima — ništa više, ništa manje.

# Objective

## 1. `resources/migrations/0004_performance_foundation.sql`

Redoslijed (svaka tabela referencira SAMO prethodno kreirane, uključujući
POSTOJEĆE `campaigns`/`campaign_items`/`content_pieces`/`revisions` iz
`0002_campaign_content_visual.sql`):

```sql
CREATE TABLE performance_import_batches (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    matched_count INTEGER NOT NULL,
    unmatched_count INTEGER NOT NULL,
    mapping_version TEXT NOT NULL,
    source_file_name TEXT NULL,
    platform_code TEXT NULL,
    raw_source_snapshot_ref TEXT NULL
);

CREATE TABLE distribution_instances (
    id TEXT PRIMARY KEY,
    campaign_id TEXT NOT NULL REFERENCES campaigns(id),
    campaign_item_id TEXT NOT NULL REFERENCES campaign_items(id),
    content_piece_id TEXT NOT NULL REFERENCES content_pieces(id),
    content_revision_id TEXT NOT NULL REFERENCES revisions(id),
    channel_code TEXT NOT NULL,
    platform_code TEXT NOT NULL,
    format_code TEXT NOT NULL,
    distribution_source TEXT NOT NULL,
    external_account_id TEXT NULL,
    external_content_id TEXT NULL,
    published_at TEXT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE performance_snapshots (
    id TEXT PRIMARY KEY,
    distribution_instance_id TEXT NOT NULL REFERENCES distribution_instances(id),
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    source TEXT NOT NULL,
    source_batch_id TEXT NULL REFERENCES performance_import_batches(id),
    reach INTEGER NULL,
    impressions INTEGER NULL,
    engagements INTEGER NULL,
    clicks INTEGER NULL,
    conversions INTEGER NULL,
    spend REAL NULL,
    revenue REAL NULL,
    video_views INTEGER NULL,
    watch_time_seconds REAL NULL,
    raw_metrics_json TEXT NOT NULL
);
```

`raw_metrics_json` — kolona ime TAČNO kako Faza 1 v1.5 §17 navodi
("raw_metrics_json ostaje dozvoljen"). Devet `CanonicalMetricSet` polja
su ZASEBNE kolone (NE JSON blob) — to je namjerna odluka Faza 0.7 §6
("dva sloja: COMMON CANONICAL METRICS + RAW PLATFORM METRICS"), canonical
metrike su prvoklasne kolone, platform-specific idu u `raw_metrics_json`.

Bez `ON DELETE CASCADE` (projekat je append-only/audit-trail orijentisan,
isti obrazac kao SVE postojeće migracije — nema presedana za cascade
delete nigdje u bazi).

## 2. `ports/repositories.py` — nov `PerformanceRepositoryPort` (aditivno)

```python
@runtime_checkable
class PerformanceRepositoryPort(Protocol):
    """Persistence for the Performance domain (P1.5-G1 entiteti).

    Namjerno MINIMALAN sada — samo save/get po sopstvenom id-u za svaki
    od tri entiteta. Metode koje traže po VEZANOM entitetu (npr. "sve
    snapshotove za jedan distribution_instance") DODAJU SE KASNIJE, kad
    stvaran pozivalac (P1.5-G3/G4/G5/G6) to zatraži — isti obrazac kao
    `VisualRepositoryPort.get_layout_spec_by_content_piece` koja je
    dodata TEK kad je `RenderPost` (ACS-F1-033) stvarno zatrebala, ne
    unaprijed.
    """

    def save_distribution_instance(self, instance: DistributionInstance) -> None: ...
    def get_distribution_instance(
        self, distribution_instance_id: DistributionInstanceId
    ) -> DistributionInstance | None: ...

    def save_performance_import_batch(self, batch: PerformanceImportBatch) -> None: ...
    def get_performance_import_batch(
        self, batch_id: PerformanceImportBatchId
    ) -> PerformanceImportBatch | None: ...

    def save_performance_snapshot(self, snapshot: PerformanceSnapshot) -> None: ...
    def get_performance_snapshot(
        self, snapshot_id: PerformanceSnapshotId
    ) -> PerformanceSnapshot | None: ...
```

Postojeći portovi (`CampaignRepositoryPort`, `ContentRepositoryPort`,
`VisualRepositoryPort`, `RevisionRepositoryPort`,
`TelemetryRepositoryPort`) OSTAJU NETAKNUTI (aditivna izmjena istog
fajla — nov `Protocol` blok, isti stil/uvod kao postojeći, novi importi
u vrhu fajla za `DistributionInstance`/`PerformanceSnapshot`/
`PerformanceImportBatch`/tri nova ID tipa).

## 3. `infrastructure/database/repositories/sqlite_performance_repository.py`
   — `SqlitePerformanceRepository`

Implementira `PerformanceRepositoryPort`, isti stil kao
`sqlite_visual_repository.py` (upsert preko `INSERT ... ON CONFLICT(id)
DO UPDATE`, enum→`.value` pri snimanju, `EnumType(row[...])` pri
čitanju, `json.dumps`/`json.loads` za `raw_metrics_json`,
`datetime.fromisoformat` za sva vremenska polja, rekonstrukcija
`MetricPeriod`/`CanonicalMetricSet` value objekata iz flat kolona pri
čitanju `PerformanceSnapshot`-a nazad).

**`upsert` za `performance_snapshots` MORA NEUTRALNO tretirati
`created_at`-stil kolonu**: `PerformanceSnapshot` NEMA `created_at`
polje (nema audit-timestamp problem kao ACS-F1-030 — nijedna kolona
ovdje nije "kad je red prvi put nastao" a da domain objekat to ne nosi;
`observed_at` je DIO domain objekta, ne adapter-generisan). Implementer
NE treba `ACS-F1-030`-stil "izostavi iz UPDATE seta" fix — provjeriti da
li je uopšte relevantno prije nego što se doda nepotrebna zaštita.

## 4. `infrastructure/database/repositories/__init__.py` — re-export

Dodati `SqlitePerformanceRepository` u postojeći `__all__`/import blok
(isti stil, aditivno).

# Implementation steps

1. `resources/migrations/0004_performance_foundation.sql` po Objective #1.
2. `ports/repositories.py` dopuna po Objective #2.
3. `sqlite_performance_repository.py` po Objective #3.
4. `infrastructure/database/repositories/__init__.py` re-export.
5. Testovi:
   - `tests/integration/database/test_migrations.py`: nov test —
     `run_migrations` na svježoj bazi → `4 in applied`, sve tri tabele
     postoje (`sqlite_master`), `schema_migrations` ima red za verziju 4.
   - `tests/integration/database/repositories/test_sqlite_performance_repository.py`
     (NOV fajl, isti stil kao `test_sqlite_visual_repository.py`):
     - `test_repository_is_a_performance_repository_port` (isinstance).
     - Round-trip za SVA TRI entiteta (save→get vraća identičan objekat,
       uključujući enum tipove kao PRAVE enume, ne stringove; nested
       `MetricPeriod`/`CanonicalMetricSet` ispravno rekonstruisani).
     - `get_*` na nepostojeći id → `None` za SVA TRI entiteta.
     - `PerformanceSnapshot` sa SVIM `CanonicalMetricSet` poljima `None`
       (osim identiteta/perioda) → round-trip i dalje radi (sve NULL
       kolone).
     - `PerformanceSnapshot.raw_metrics` sa stvarnim platform-specific
       podacima (npr. `{"instagram_saves": 42}`) → round-trip čuva TAČAN
       sadržaj.
     - FK provjera: `distribution_instances`/`performance_snapshots`
       zahtijevaju POSTOJEĆE redove u `campaigns`/`campaign_items`/
       `content_pieces`/`revisions` (seed-ovati preko postojećih
       repozitorija, isti obrazac kao `_seed_campaign`/`_seed_content_piece`
       helperi u drugim test fajlovima) — NE testirati bez FK reda,
       stvaran FK constraint mora biti provjeren `PRAGMA foreign_keys=ON`.

# Acceptance

- [ ] `0004_performance_foundation.sql` postoji, tačno tri tabele (BEZ
      `performance_import_rows` — namjerno odloženo).
- [ ] `run_migrations` primjenjuje verziju 4 bez greške na bazi koja već
      ima `0000`-`0003`.
- [ ] `PerformanceRepositoryPort` postoji, `CampaignRepositoryPort`/
      `ContentRepositoryPort`/`VisualRepositoryPort`/`RevisionRepositoryPort`/
      `TelemetryRepositoryPort` NETAKNUTI (git diff dokaz).
- [ ] `SqlitePerformanceRepository` implementira sve 6 metoda, round-trip
      dokazan za sva tri entiteta (test dokaz, uključujući enum tipove i
      nested value objekte).
- [ ] `get_*` na nepostojeći id → `None` (sva tri entiteta).
- [ ] `raw_metrics_json` stvarno čuva proizvoljan platform-specific
      sadržaj (test dokaz).
- [ ] FK constraint-i stvarno rade (`PRAGMA foreign_keys=ON`, test protiv
      prave seed-ovane baze).
- [ ] `domain/`, `application/`, postojeće migracije (`0000`-`0003`),
      `ports/ai.py`, `ports/rendering.py`, `ports/export.py` NISU DIRANI.
- [ ] `python -m pytest tests/integration/database/repositories/test_sqlite_performance_repository.py tests/integration/database/test_migrations.py -v`
      prolazi.
- [ ] `python -m pytest tests -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema nove eksterne zavisnosti.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest tests/integration/database/repositories/test_sqlite_performance_repository.py -v
python -m pytest tests/integration/database/test_migrations.py -v
python -m pytest tests -q
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- Migracija STVARNO aditivna, NE dira postojeće tabele — pokrenuti
  `run_migrations` na bazi koja već ima `0000`-`0003` i potvrditi da
  NIJEDNA postojeća tabela nije promijenjena;
- Round-trip STVARNO čuva enum tipove (ne string-ove) i nested value
  objekte (`MetricPeriod`/`CanonicalMetricSet`) na povratku — provjeriti
  ovo direktno, ne samo da test prolazi;
- FK constraint-i stvarno testirani protiv prave, seed-ovane baze (ne
  fake/mock);
- `performance_import_rows` STVARNO NIJE kreirana (namjerna odluka,
  provjeriti da implementer nije "za svaki slučaj" ipak dodao praznu
  tabelu);
- `PerformanceRepositoryPort` metode STVARNO minimalne (samo save/get
  po sopstvenom id-u, bez query-po-vezanom-entitetu metoda koje niko
  još ne treba).

# Rollback

MEDIUM risk — nova migracija (aditivna, nove tabele) + nov port +
nova infrastructure adapter. Nema domain/application izmjene, nema
brisanja/izmjene postojećeg ponašanja. Fix na istoj branch bez
proširenja scope-a. §29: Claude-only review, PASS → odmah merge.

# Coordination

Zavisi od ACS-F1-037 (mergovano) — UNBLOCKED. Sljedeći korak: **P1.5-G3
CSV Import** (Faza 1 v1.5 §18 — `ImportPerformanceCsv`,
`PreviewPerformanceMapping`, `ConfirmPerformanceImport`; TU se tek
definiše `PerformanceImportRow` domain entitet i njegova tabela, kad
stvaran oblik postane jasan iz stvarnog CSV parsing koda).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-038-performance-persistence
Branch:   task/ACS-F1-038-performance-persistence
Base:     main @ c67447d
```
