---
task_id: ACS-F1-043
phase: P1.5-G3 dio 2 -- CSV Import (Faza 1 v1.5 §18, nastavak ACS-F1-042)
title: "CSV performance import: perzistencija (PerformanceImportRow) + tri use-case-a (ImportPerformanceCsv / PreviewPerformanceMapping / ConfirmPerformanceImport)"
risk: MEDIUM
coordinator: claude
implementer: TBD
reviewers: [claude]
status: "OPEN -- contract written before code, čeka implementera"
created_at: 2026-09-06
dependencies: [ACS-F1-042]
allowed_paths:
  - src/ai_campaign_studio/domain/performance/entities.py
  - src/ai_campaign_studio/domain/common/ids.py
  - src/ai_campaign_studio/ports/repositories.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_performance_repository.py
  - resources/migrations/
  - src/ai_campaign_studio/application/performance/
  - tests/unit/domain/performance/
  - tests/unit/infrastructure/database/repositories/test_sqlite_performance_repository.py
  - tests/integration/application/performance/
  - tests/unit/application/performance/
forbidden_paths:
  - src/ai_campaign_studio/presentation/
  - src/ai_campaign_studio/presentation_webview/
  - src/ai_campaign_studio/application/campaigns/
  - src/ai_campaign_studio/application/posts/
  - src/ai_campaign_studio/application/visual/
  - src/ai_campaign_studio/application/rendering/
  - src/ai_campaign_studio/application/export/
  - src/ai_campaign_studio/application/evaluation/
  - src/ai_campaign_studio/domain/performance/enums.py
gitnexus_required: true
adversarial_required: false
gitnexus:
  required: true
  note: >
    Dopunjuje `PerformanceRepositoryPort` (novi metodi, aditivno) i
    `domain/performance/entities.py` (nov entitet, aditivno). Koordinator
    mora provjeriti da nijedan postojeći pozivalac tih fajlova nije
    pokvaren -- očekivano: samo ACS-F1-038's SQLite implementacija i
    testovi, ali provjeriti stvarno, ne pretpostaviti.
---

# Kontekst

Nastavak ACS-F1-042 (dio 1: čist kolona-mapping + row-parsing engine,
mergovan). Ovaj dio (dio 2) dodaje ono što dio 1 namjerno NIJE dirao:
stvaran fajl I/O, perzistencija, i tri imenovana use-case-a iz Faza 1
v1.5 §18.

**Ključna scope odluka (ista disciplina kao dio 1 -- review MORA
potvrditi da ima smisla):** Faza 0.7 §14 (Matching -- P1.5-G4) je
POTPUNO ODVOJEN gate od §18 (CSV Import -- ovaj task). Ovaj task
**NE MATCHUJE** uvezene redove na `DistributionInstance`. To znači:

- "matched"/"ambiguous"/"unmatched" iz §18 ODNOSE SE na kolona-mapping
  (već riješeno u dio 1 -- `ColumnMatch.status`).
- "invalid" iz §18 odnosi se na row-validaciju (već riješeno u dio 1 --
  `ParsedRow.errors`).
- Dio 2 samo UZIMA dio-1-ov engine, otvara stvaran fajl, i ČUVA
  rezultat u bazu. `PerformanceImportRow.distribution_instance_id`
  ostaje `None` za SVAKI red -- G4 (budući, zaseban task) će kasnije
  proći kroz nematchovane redove i popuniti to polje (prioritet
  `external_content_id → analytics_match_key → stable IDs → manual`,
  Faza 0.7 §14).

**Posljedica po `PerformanceImportBatch.matched_count`/`unmatched_count`
imenima polja** (Faza 0.7 §13): ova polja su NAZVANA za buduće
content-matching brojeve, ali u OVOM tasku nemamo tu informaciju još.
Privremeno tumačenje (implementer prati, dokumentuje, G4 će kasnije
rekoncilirati): `matched_count` = broj VALID redova (bez `errors`),
`unmatched_count` = broj INVALID redova. Ovo je NAMJERNA, dokumentovana
privremena semantika -- ne pravo "matched to content" značenje.

# Objective

## 1. Domain: `PerformanceImportRow` (`domain/performance/entities.py`)

```python
@dataclass(frozen=True)
class PerformanceImportRow:
    id: PerformanceImportRowId
    batch_id: PerformanceImportBatchId
    row_number: int
    raw_values: dict[str, str]
    mapped_values: dict[str, str]
    errors: tuple[str, ...]
    distribution_instance_id: DistributionInstanceId | None = None
```

Nov ID tip `PerformanceImportRowId` u `domain/common/ids.py` (aditivno,
isti obrazac kao ostali).

## 2. Migracija -- `performance_import_rows` tabela

Sljedeći slobodan broj (provjeriti `resources/migrations/` -- trenutno
zadnji je `0006_performance_foundation.sql`, pa je ovo `0007_...`).
Kolone prate entitet: `id TEXT PRIMARY KEY`, `batch_id TEXT NOT NULL
REFERENCES performance_import_batches(id)`, `row_number INTEGER NOT
NULL`, `raw_values_json TEXT NOT NULL`, `mapped_values_json TEXT NOT
NULL`, `errors_json TEXT NOT NULL`, `distribution_instance_id TEXT NULL
REFERENCES distribution_instances(id)`.

## 3. `PerformanceRepositoryPort` + SQLite implementacija -- dopuna

Aditivno (postojećih 6 metoda netaknuto):
- `save_performance_import_row(row: PerformanceImportRow) -> None`
- `get_performance_import_row(row_id: PerformanceImportRowId) -> PerformanceImportRow | None`
- `list_performance_import_rows(batch_id: PerformanceImportBatchId) -> tuple[PerformanceImportRow, ...]`

## 4. `application/performance/` -- tri use-case-a

- **`ImportPerformanceCsv`** (`import_performance_csv.py`): čist
  orkestrator, NE persist. `execute(file_path: str, rules:
  ColumnAliasRules | None = None) -> tuple[tuple[ColumnMatch, ...],
  tuple[ParsedRow, ...]]`. Otvara fajl preko stdlib `csv.DictReader`
  (isto kao dio 1 pretpostavlja), poziva `map_columns`+`parse_rows` iz
  ACS-F1-042. `rules=None` -> `load_column_aliases()` (bundled
  default). JEDINO mjesto koje čita fajl sa diska.
- **`PreviewPerformanceMapping`** (`preview_performance_mapping.py`):
  poziva `ImportPerformanceCsv`, vraća sažetak (DTO ili dict --
  implementer bira oblik, ALI mora sadržati: kolona-mapping status po
  polju, broj valid/invalid redova, PAR primjer nevažećih redova sa
  njihovim `errors` za korisnika). NE PERSISTUJE ništa -- korisnik ovo
  vidi PRIJE potvrde.
- **`ConfirmPerformanceImport`** (`confirm_performance_import.py`):
  prima `file_path`, opciono `column_overrides: dict[str, str] | None`
  (kanonsko_polje -> ručno izabran header, za slučaj da je korisnik
  ispravio ambiguous/unmatched kolonu), `platform_code: str | None`,
  `performance_repo: PerformanceRepositoryPort`. Ponovo parsira (ili
  prima već-parsirane rezultate -- implementer bira), PRIMJENJUJE
  `column_overrides` na `map_columns` rezultat prije `parse_rows` (ako
  su dati), pa PERZISTUJE: jedan `PerformanceImportBatch`
  (`source=PerformanceSource.CSV_IMPORT`, `row_count=len(rows)`,
  `matched_count`=broj valid, `unmatched_count`=broj invalid,
  `mapping_version=rules.version`, `source_file_name=Path(file_path).name`)
  + jedan `PerformanceImportRow` PO REDU (`distribution_instance_id=None`
  za SVE). Vraća `PerformanceImportBatch`.

# Implementation steps

1. Domain entitet + ID tip (Objective #1).
2. Migracija (Objective #2) -- provjeriti tačan slobodan broj prije
   pisanja fajla.
3. Repo port + SQLite implementacija (Objective #3) + testovi:
   save/get/list round-trip, `raw_values`/`mapped_values`/`errors`
   JSON serijalizacija bez gubitka (uključujući BHS dijakritike u
   vrijednostima), `distribution_instance_id=None` round-trip.
4. `ImportPerformanceCsv` (Objective #4a) + testovi: stvaran privremen
   CSV fajl (tmp_path), header+redovi, potvrditi ispravan
   `ColumnMatch`/`ParsedRow` rezultat.
5. `PreviewPerformanceMapping` (Objective #4b) + testovi: ambiguous
   kolona se VIDI u sažetku, invalid redovi se VIDE sa svojim
   `errors`, ništa nije perzistovano (baza prazna poslije poziva).
6. `ConfirmPerformanceImport` (Objective #4c) + testovi: happy path (bez
   override-a), `column_overrides` ispravlja ambiguous kolonu (test:
   header koji bez override-a daje `ambiguous`, sa override-om se
   ispravno mapira), `PerformanceImportBatch`+SVI `PerformanceImportRow`
   STVARNO postoje u bazi poslije poziva (round-trip dokaz preko
   repo-a, ne samo povratna vrijednost), invalid redovi se I DALJE
   perzistuju (ništa se ne izbacuje -- "ništa se ne gubi" iz §18).
7. Integration test: pun lanac
   `ImportPerformanceCsv`→`PreviewPerformanceMapping`→
   `ConfirmPerformanceImport` nad STVARNIM privremenim CSV fajlom sa
   MIJEŠANIM validnim/invalid redovima i BAR jednim BHS header-om
   (dokaz da cijeli lanac radi sa EN+BHS zajedno, ne odvojeno).

# Acceptance

- [ ] `PerformanceImportRow` postoji, sva polja round-trip preko
      repo-a bez gubitka.
- [ ] Migracija dodaje `performance_import_rows` tabelu, tačan sljedeći
      broj (provjeriti prije pisanja, ne pretpostaviti).
- [ ] `ImportPerformanceCsv`/`PreviewPerformanceMapping`/
      `ConfirmPerformanceImport` postoje, imena TAČNO kao u §18.
- [ ] `PreviewPerformanceMapping` NE PERZISTUJE ništa.
- [ ] `ConfirmPerformanceImport` STVARNO perzistuje batch + SVE redove
      (uključujući invalid), `distribution_instance_id=None` za sve.
- [ ] `column_overrides` STVARNO ispravlja ambiguous/unmatched kolonu
      (test dokaz, ne samo tvrdnja).
- [ ] Nijedan red se ne gubi (broj ulaznih CSV redova ==
      broj `PerformanceImportRow` redova u bazi, uvijek).
- [ ] `python -m pytest tests/unit/domain/performance/
      tests/unit/infrastructure/database/repositories/test_sqlite_performance_repository.py
      tests/unit/application/performance/ tests/integration/application/performance/ -v` prolazi.
- [ ] `python -m pytest -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema nove eksterne zavisnosti.
- [ ] Nema izmjena van `allowed_paths`.
- [ ] **CI provjeren preko PR-a** (obavezno otvoriti PR).

# Verification

```bash
python -m pytest tests/unit/domain/performance/ tests/unit/infrastructure/database/repositories/test_sqlite_performance_repository.py tests/unit/application/performance/ tests/integration/application/performance/ -v
python -m pytest -q
python -m ruff check .
python -m mypy src

git push -u origin task/ACS-F1-043-csv-import-persistence
gh pr create --base main --title "ACS-F1-043: P1.5-G3 dio 2 -- CSV import persistence + use-cases"
gh pr checks
```

# Review focus -- Claude

- Scope granica STVARNO ispoštovana -- nema poziva ka
  `DistributionInstance` matching logici bilo gdje u ovom diff-u (grep
  dokaz).
- "Ništa se ne gubi" STVARNO dokazano -- test sa mješovitim
  validnim/invalid redovima, provjeriti STVARAN broj redova u bazi ==
  broj ulaznih redova.
- `column_overrides` STVARNO testiran na pravom ambiguous slučaju, ne
  samo happy path.
- Migracija koristi STVARAN sljedeći slobodan broj (provjeriti
  `ls resources/migrations/` sam prije prihvatanja).
- GitNexus impact na `PerformanceRepositoryPort`/`entities.py` STVARNO
  pokrenut.

# Rollback

MEDIUM risk -- novi entitet + migracija + 3 nova use-case-a, ali
izolovano (aditivni portovi, nova tabela, nov `application/performance/`
sadržaj). Nema izmjena postojećeg ponašanja.

# Coordination

Zavisi od ACS-F1-042 (mergovano). **Otvara vrata P1.5-G4 Matching**
(zaseban, budući task -- prolazi kroz `PerformanceImportRow` redove sa
`distribution_instance_id IS NULL` i pokušava ih matchovati). Ne
preklapa se ni sa jednim trenutno otvorenim GUI taskom (ACS-GUI-008/009,
ACS-HOTFIX-002) -- potpuno druge putanje.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-043-csv-import-persistence
Branch:   task/ACS-F1-043-csv-import-persistence
Base:     main @ 4f4be8d
```
