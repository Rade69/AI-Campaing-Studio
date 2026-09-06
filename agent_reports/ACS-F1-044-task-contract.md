---
task_id: ACS-F1-044
phase: P1.5-G4 -- Matching (Faza 0.7 §14, Faza 1 v1.5 §19)
title: "MatchPerformanceImportBatch: uvezene redove matchovati na DistributionInstance (external_content_id + analytics_match_key)"
risk: MEDIUM
coordinator: claude
implementer: TBD
reviewers: [claude]
status: "OPEN -- contract written before code, čeka implementera"
created_at: 2026-09-06
dependencies: [ACS-F1-043]
allowed_paths:
  - src/ai_campaign_studio/domain/performance/entities.py
  - src/ai_campaign_studio/ports/repositories.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_performance_repository.py
  - src/ai_campaign_studio/application/performance/
  - tests/unit/domain/performance/
  - tests/unit/infrastructure/database/repositories/test_sqlite_performance_repository.py
  - tests/unit/application/performance/
  - tests/integration/application/performance/
forbidden_paths:
  - src/ai_campaign_studio/presentation/
  - src/ai_campaign_studio/presentation_webview/
  - src/ai_campaign_studio/application/campaigns/
  - src/ai_campaign_studio/application/posts/
  - src/ai_campaign_studio/application/visual/
  - src/ai_campaign_studio/application/rendering/
  - src/ai_campaign_studio/application/export/
  - resources/migrations/
gitnexus_required: true
adversarial_required: false
gitnexus:
  required: true
  note: >
    Dopunjuje `PerformanceRepositoryPort` (nov metod) i
    `domain/performance/entities.py` (`PerformanceImportRow` dobija
    novo polje). Provjeriti da nijedan postojeći pozivalac
    `PerformanceImportRow(...)` (ACS-F1-043's `ConfirmPerformanceImport`
    + testovi) nije pokvaren dodavanjem novog polja SA DEFAULT
    vrijednošću.
---

# Kontekst

Posljednji dio P1.5-G3/G4 lanca. `ConfirmPerformanceImport` (ACS-F1-043,
mergovano) VEĆ perzistuje `PerformanceImportRow` redove sa
`distribution_instance_id=None` za SVE -- ovaj task ih pokušava
matchovati na stvaran `DistributionInstance`, po prioritetu iz Faza 0.7
§14:

```text
1. external_content_id
2. exported analytics_match_key
3. stable content/distribution IDs
4. manual user confirmation
```

**Scope OVOG taska: SAMO prioritet 1 i 2.** Prioritet 3 (stable-ID
fallback) i 4 (manual confirmation UI) su NAMJERNO van scope-a --
prioritet 3 zahtijeva dizajn odluku koja nije jasna dok G4-dio-1 ne
pokaže STVARAN procenat redova koji ostanu nematchovani nakon 1+2, a
prioritet 4 je GUI task (ne postoji još ekran za "Pregled i izvoz"
performance importa). Redovi koji ne prođu 1+2 ostaju
`distribution_instance_id=None` i `match_status="UNMATCHED"` ili
`"AMBIGUOUS"` (Objective #1) -- čekaju budući task.

**Scope odluka o "kojoj kampanji tražiti"** (review MORA potvrditi):
`PerformanceImportBatch`/`PerformanceImportRow` NE ČUVAJU
`campaign_id` nigdje (ACS-F1-043 ga namjerno nije tražio -- CSV može
imati `platform_code` na batch nivou, ali ne campaign). Korisnik koji
importuje CSV export sa neke platforme ZNA za koju kampanju je
export napravljen -- zato ovaj task uzima `campaign_id` kao EKSPLICITAN
parametar use-case-a (ne iz batch-a), i traži SVE
`DistributionInstance` redove TE kampanje (jedan repo poziv,
`list_distribution_instances_by_campaign`), pa u Python-u provjerava
prioritet 1 i 2 za svaki uvezeni red naspram te liste. Ovo je
namjerno pragmatičan MVP pristup (O(n) po kampanji, ne po cijeloj
bazi) -- ako broj `DistributionInstance`-ova po kampanji ikad postane
veliki, indeksiranje/SQL-lookup je budući optimizacioni task, NE ovaj.

**`analytics_match_key` nije stored kolona na `distribution_instances`**
(potvrđeno -- tabela nema tu kolonu, ACS-F1-039/041). Prioritet 2 zato
RAČUNA match key za svaki `DistributionInstance` u listi preko VEĆ
POSTOJEĆE `compute_analytics_match_key(content_piece_id,
content_revision_id, platform_code, format_code)` (domain/analytics/
match_key.py, ACS-F1-036) i poredi sa redovim uvezenim
`analytics_match_key` vrijednosti. Nema SQL izmjene.

# Objective

## 1. `PerformanceImportRow` -- novo polje (aditivno)

```python
match_status: Literal["UNMATCHED", "AMBIGUOUS", "MATCHED"] | None = None
```

(`None` = još nije pokušan matching -- razlikuje "nikad pokušano" od
"pokušano, nije uspjelo"; postojeći redovi iz ACS-F1-043 imaju `None`
prije nego ovaj task nad njima pokrene matching).

## 2. `PerformanceRepositoryPort` + SQLite -- dopuna

- `list_distribution_instances_by_campaign(campaign_id: CampaignId) ->
  tuple[DistributionInstance, ...]` (nov metod, aditivan).
- Postojeći `save_performance_import_row` MORA i dalje raditi (koristi
  se za UPDATE ovdje -- red se ponovo snima sa popunjenim
  `distribution_instance_id`/`match_status` nakon matching pokušaja;
  implementer provjerava da li postojeći SQL koristi `INSERT OR
  REPLACE`/`ON CONFLICT DO UPDATE` ili treba dopuniti da podrži
  update-in-place bez duplog reda).

## 3. `MatchPerformanceImportBatch` (`application/performance/
match_performance_import_batch.py`)

```python
def execute(
    self, batch_id: PerformanceImportBatchId, campaign_id: CampaignId
) -> MatchResult:
```

- Učitava sve redove batch-a (`list_performance_import_rows`) sa
  `distribution_instance_id IS None` (ili `match_status is None` --
  implementer bira tačan filter, ALI redovi koji su VEĆ matchovani se
  NE diraju ponovo -- idempotentno).
- Učitava sve `DistributionInstance` za `campaign_id`
  (Objective #2, JEDAN poziv, ne po redu).
- Za SVAKI kandidat red (mora imati bar jednu od `external_content_id`/
  `analytics_match_key` u `mapped_values` -- ako nema NIJEDNU,
  `match_status="UNMATCHED"` odmah, bez pretrage):
  1. **Prioritet 1**: ako `mapped_values` ima `external_content_id`,
     filtrirati listu na `di.external_content_id == vrijednost`. 0
     rezultata -> pređi na prioritet 2. 1 rezultat ->
     `MATCHED`, popuni `distribution_instance_id`. 2+ rezultata ->
     `AMBIGUOUS`, STANI (ne probaj prioritet 2 -- ambiguous na
     prioritetu 1 je konačno ambiguous).
  2. **Prioritet 2** (samo ako prioritet 1 nije dao rezultat): ako
     `mapped_values` ima `analytics_match_key`, za SVAKI
     `DistributionInstance` u listi izračunati
     `compute_analytics_match_key(di.content_piece_id,
     di.content_revision_id, di.platform_code, di.format_code)` i
     uporediti sa redovom uvezenom vrijednošću. 0/1/2+ rezultata isto
     kao gore.
  3. Nijedan prioritet nije dao rezultat -> `UNMATCHED`.
- Snima SVAKI red preko `save_performance_import_row` (update-in-place)
  sa novim `match_status`/`distribution_instance_id`.
- Vraća `MatchResult` (dataclass): `matched_count`, `ambiguous_count`,
  `unmatched_count`, `skipped_count` (redovi koji nisu imali NIJEDAN
  matching-relevantan podatak).

# Implementation steps

1. `PerformanceImportRow.match_status` polje (Objective #1) + testovi
   round-trip (uključujući `None` -> eksplicitno postavljena
   vrijednost -> ponovo pročitano).
2. Repo dopuna (Objective #2) + test: `list_distribution_instances_by_
   campaign` vraća SAMO instance TE kampanje (seed 2 kampanje, provjeri
   izolaciju).
3. `MatchPerformanceImportBatch` (Objective #3) + testovi:
   - happy path: red sa TAČNIM `external_content_id` -> `MATCHED`,
     `distribution_instance_id` popunjen.
   - happy path prioritet 2: red BEZ `external_content_id` ali sa
     TAČNIM `analytics_match_key` (izračunatim iz stvarnog
     `DistributionInstance`-a u testu, NE izmišljenim stringom) ->
     `MATCHED`.
   - ambiguous prioritet 1: DVA `DistributionInstance`-a sa ISTIM
     `external_content_id` (data-integrity edge case, ali mora se
     testirati) -> `AMBIGUOUS`, `distribution_instance_id` OSTAJE
     `None`.
   - unmatched: red sa `external_content_id` koji NE POSTOJI nigdje ->
     `UNMATCHED`.
   - skipped: red BEZ ijedne matching-relevantne vrijednosti (ni
     external_content_id ni analytics_match_key mapirani) ->
     `UNMATCHED` odmah (ili zaseban `skipped_count`, implementer
     dokumentuje tačnu razliku od običnog UNMATCHED ako je pravi).
   - idempotentnost: već-matchovan red se NE dira drugim pozivom
     (test: pozovi dvaput, provjeri da se `distribution_instance_id`
     ne mijenja/ne prepisuje na drugom pozivu).
   - izolacija po kampanji: red čiji `external_content_id` postoji ALI
     u DRUGOJ kampanji -> `UNMATCHED` (ne smije lažno matchovati preko
     granice kampanje).
4. Integration test: pun lanac
   `ConfirmPerformanceImport`→`MatchPerformanceImportBatch` nad
   STVARNOM bazom sa stvarnim `DistributionInstance` (iz
   `ExportCampaign`-a) + stvarnim CSV redovima -- bar jedan MATCHED,
   bar jedan UNMATCHED u istom batch-u.

# Acceptance

- [ ] `PerformanceImportRow.match_status` postoji, aditivno.
- [ ] `list_distribution_instances_by_campaign` postoji, izolovan po
      kampanji (test dokaz).
- [ ] `MatchPerformanceImportBatch` implementira TAČNO prioritet 1
      pa 2, STAJE na ambiguous (ne prelazi na sljedeći prioritet).
- [ ] Ambiguous na prioritetu 1 NE pokušava prioritet 2 (test dokaz).
- [ ] Idempotentno -- već-matchovan red se ne dira ponovo.
- [ ] Izolacija po kampanji dokazana testom (cross-campaign
      external_content_id NE matchuje lažno).
- [ ] `python -m pytest tests/unit/domain/performance/
      tests/unit/infrastructure/database/repositories/test_sqlite_performance_repository.py
      tests/unit/application/performance/ tests/integration/application/performance/ -v` prolazi.
- [ ] `python -m pytest -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.
- [ ] **CI provjeren preko PR-a.**

# Verification

```bash
python -m pytest tests/unit/domain/performance/ tests/unit/infrastructure/database/repositories/test_sqlite_performance_repository.py tests/unit/application/performance/ tests/integration/application/performance/ -v
python -m pytest -q
python -m ruff check .
python -m mypy src

git push -u origin task/ACS-F1-044-performance-matching
gh pr create --base main --title "ACS-F1-044: P1.5-G4 -- match imported rows to DistributionInstance"
gh pr checks
```

# Review focus -- Claude

- Ambiguous-na-prioritetu-1 STVARNO staje (ne "pada kroz" na
  prioritet 2 slučajno) -- pažljivo pročitati kontrolni tok, ne samo
  test rezultat.
- Cross-campaign izolacija STVARNO testirana sa DVIJE stvarne
  kampanje u istoj bazi.
- `compute_analytics_match_key` poziv koristi TAČNA 4 argumenta u
  TAČNOM redoslijedu (isti kao `export_campaign.py`-ov poziv --
  uporediti direktno, ne po sjećanju).
- Idempotentnost STVARNO testirana (drugi poziv, provjeriti da
  MATCHED red ne postane nešto drugo).
- GitNexus impact na `PerformanceImportRow`/`PerformanceRepositoryPort`
  STVARNO pokrenut.

# Rollback

MEDIUM risk -- nov use-case + aditivno polje + aditivan repo metod,
izolovano od GUI/export/campaign slojeva. Nema izmjena postojećeg
ponašanja.

# Coordination

Zavisi od ACS-F1-043 (mergovano). Zatvara P1.5-G4 (dio 1+2, prioritet
3+4 ostaju budući task). Nakon ovog: P1.5-G5 Metric Calculation
(Faza 1 v1.5 §20 -- CTR/CPC/CPM/CPA/ROAS) postaje sljedeći prirodan
korak, ALI čeka eksplicitan signal korisnika kao i do sad.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-044-performance-matching
Branch:   task/ACS-F1-044-performance-matching
Base:     main @ c9af4fc
```
