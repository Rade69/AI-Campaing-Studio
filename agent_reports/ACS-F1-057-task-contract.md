---
task_id: ACS-F1-057
phase: "P1.5-G8 prerequisite — PerformanceSnapshot materijalizacija iz matched CSV redova"
title: "Popuniti realan gap u G3/G4/G5/G6 lancu: matched PerformanceImportRow ne postaje PerformanceSnapshot"
risk: MEDIUM
coordinator: claude
implementer: TBD
reviewers: [claude]
status: "OPEN -- contract written before code, čeka implementera"
created_at: 2026-09-08
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/application/performance/materialize_performance_snapshots.py
  - src/ai_campaign_studio/presentation_webview/bridge/__init__.py
  - tests/unit/application/performance/test_materialize_performance_snapshots.py
  - tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py
  - tests/integration/application/performance/
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/infrastructure/
  - resources/migrations/
  - src/ai_campaign_studio/presentation_webview/screens/
  - src/ai_campaign_studio/presentation_webview/static/app.js
gitnexus_required: true
adversarial_required: false
gitnexus:
  required: true
  note: >
    OBAVEZNO `gitnexus_impact` na `MatchPerformanceImportBatch`,
    `ConfirmPerformanceImport`, `confirm_performance_import` (bridge)
    PRIJE izmjene -- ovaj task DODAJE poziv novom use-caseu unutar
    postojeće, već pregledane bridge metode (ACS-F1-055). Potvrditi da
    nijedan drugi caller/test ne pretpostavlja da
    `confirm_performance_import` NE kreira snapshotove (malo
    vjerovatno, ali provjeriti).
---

# Kontekst

**Nalaz implementera (Pi) prije bilo kakvog koda za ACS-F1-056 (P1.5-G8),
nezavisno potvrđen od koordinatora čitanjem izvornog koda:**

`MatchPerformanceImportBatch.execute()` (`application/performance/
match_performance_import_batch.py`) SAMO postavlja `match_status`/
`distribution_instance_id` na `PerformanceImportRow` (poziva
ISKLJUČIVO `self._repo.save_performance_import_row(...)`). NIKAD ne
poziva `save_performance_snapshot(...)`.

`build_campaign_performance_summary`/`build_content_performance_summary`
(G6, `application/performance/build_performance_summaries.py`) čitaju
ISKLJUČIVO preko `list_performance_snapshots_by_distribution_instance`
-- dakle `PerformanceSnapshot` entitete, NIKAD `PerformanceImportRow`.

**Posljedica**: CSV red koji se uspješno poklopi (`match_status=
"MATCHED"`) NIKAD ne postaje vidljiv G5/G6 kalkulator lancu. Cio
G7a/G7b GUI prikaz (Campaign/Content Performance kartice, ACS-F1-053/054)
će ZAUVIJEK prikazivati `None`/`0` za bilo koju kampanju čiji su podaci
stigli KROZ CSV import put -- iako je import "uspio" (matched_count >
0), derived metrike se nikad ne pojavljuju. Ovo NIJE UI bug -- G7a/b su
ispravno implementirani i pregledani, oni ispravno čitaju ono što
postoji (ništa).

**Ovo je taj gap.** Task ga popunjava PRIJE nego što se P1.5-G8
(integration acceptance) nastavi -- G8 bez ovoga ne bi mogao dokazati
NIŠTA o derived metrikama iz stvarno uvezenih podataka (D2 opcija
odbačena: proglašavanje Slice 1.5 gotovim bez ovog dokaza bi ostavilo
centralnu funkcionalnost neprovjerenu, isti obrazac grešaka koji je
G10/G7 disciplina cijeli dan izbjegavala).

# Objective

## 1. Novi use-case: `MaterializePerformanceSnapshots`

Novi fajl `application/performance/materialize_performance_snapshots.py`.
NE dira `match_performance_import_batch.py` (ostaje netaknut, već
pregledan/mergovan) -- čist, odvojen, uskog-odgovornosti use-case, isti
princip kao ostatak G3/G4/G5/G6 lanca.

```python
class MaterializePerformanceSnapshots:
    def __init__(self, performance_repo: PerformanceRepositoryPort) -> None: ...

    def execute(
        self, batch_id: PerformanceImportBatchId
    ) -> MaterializeResult:
        """Za SVAKI red u batch-u sa match_status == 'MATCHED' I
        errors == () (validan), kreirati i persistovati JEDAN
        PerformanceSnapshot. Redove koji su MATCHED ali imaju errors
        (moguće -- MatchPerformanceImportBatch ne provjerava row.errors
        prije matchovanja) PRESKOČITI, ne srušiti se, brojati odvojeno.
        Idempotentno: ako je red već materijalizovan (vidi Otvoreno
        pitanje #2), ne duplirati.
        """
```

`MaterializeResult` (novi frozen dataclass): `materialized_count`,
`skipped_invalid_count` (matched ali sa errors), implementer dodaje
druga polja ako opravdano.

**Mapiranje `mapped_values` (string) → `PerformanceSnapshot`:**

```text
period = MetricPeriod(
    start=datetime.fromisoformat(mapped_values["period_start"]),
    end=datetime.fromisoformat(mapped_values["period_end"]),
)
metrics = CanonicalMetricSet(
    reach=int(mapped_values["reach"]) if "reach" in mapped_values and
        mapped_values["reach"].strip() else None,
    ... (isto za svih 9 polja, int za 6, float za 3 -- ISTA
        _INT_METRIC_FIELDS podjela kao row_parsing.py, PROVJERITI
        vrijednosti tamo, ne pretpostaviti)
)
snapshot = PerformanceSnapshot(
    id=PerformanceSnapshotId(new_id()),
    distribution_instance_id=row.distribution_instance_id,
    period=period,
    observed_at=<implementer bira: period.end ili batch.imported_at
        -- dokumentovati izbor>,
    source=PerformanceSource.CSV_IMPORT,
    metrics=metrics,
    source_batch_id=batch_id,
    raw_metrics=row.raw_values,  # audit trail, isti princip kao
        PerformanceImportRow.raw_values
)
```

**Re-parsing je bezbjedan bez pune re-validacije** jer
`ConfirmPerformanceImport`/`row_parsing.py` VEĆ validira svaku
vrijednost prije persistovanja `PerformanceImportRow` -- `row.errors`
je prazan tuple TAČNO kad su svi `mapped_values` parseable. Ipak,
implementer NE smije pretpostaviti -- `datetime.fromisoformat`/`int`/
`float` pozivi i dalje treba da imaju eksplicitan `try/except` sa
jasnom greškom (fail-soft: preskoči red, ne sruši cijeli batch) kao
odbrambeni sloj, ne oslanjati se slijepo na "errors je prazan pa mora
proći".

## 2. Otvoreno pitanje — idempotencija (istražiti/odlučiti PRIJE koda)

`MatchPerformanceImportBatch` je eksplicitno idempotentan (preskače
redove sa već postavljenim `match_status`). Ovaj novi use-case MORA
imati istu garanciju -- ako se pozove dvaput nad istim batch-om (npr.
korisnik ponovo klikne "Potvrdi uvoz" ili bridge metoda se pozove
dvaput), NE smije kreirati DUPLIRANE snapshotove za isti red.

`PerformanceImportRow` NEMA polje koje bi zabilježilo "ovaj red je već
materijalizovan" (za razliku od `match_status` koji postoji baš za tu
svrhu na match nivou). Implementer MORA istražiti i odlučiti jedan od
pristupa, DOKUMENTOVATI izbor:

1. Deterministički `PerformanceSnapshotId` izveden iz `row.id` (npr.
   `new_id()` zamijeniti sa nečim izvedenim iz `str(row.id)` -- ALI
   provjeriti da li `save_performance_snapshot` radi UPSERT na `id`
   (postojeći SQLite adapter koristi `ON CONFLICT(id) DO UPDATE` --
   provjeriti u `sqlite_performance_repository.py` prije pretpostavke)
   -- ako da, drugi poziv sa istim izvedenim ID-jem samo prepiše isti
   red, bezopasno.
2. Provjeriti da li već postoji snapshot za taj `distribution_instance_id`
   + `source_batch_id` PRIJE kreiranja (novi query, PROVJERITI da li
   `list_performance_snapshots_by_distribution_instance` dovoljna --
   filtrirati po `source_batch_id` u memoriji, ne treba nova repo
   metoda).

Implementer bira, dokumentuje obrazloženje, testira sa dva uzastopna
poziva iste `execute()` metode nad istim batch-om.

## 3. Bridge wiring — `confirm_performance_import` (mala, aditivna izmjena)

Poslije postojećeg `MatchPerformanceImportBatch(...).execute(...)`
poziva (ACS-F1-055, NETAKNUT), dodati JEDAN novi poziv:

```python
materialize_result = MaterializePerformanceSnapshots(
    self._performance_repo
).execute(batch.id)
```

`ConfirmPerformanceImportResultUiModel` (postojeći DTO, ACS-F1-055)
dobija DVA nova polja: `materialized_count`, `skipped_invalid_count`
(implementer bira tačna imena ako ima jak razlog). GUI prikaz teksta u
`app.js` (POSTOJI, `writeImportResult`/summary poruka) MOŽE se
proširiti da uključi ova dva broja -- implementer procjenjuje da li je
to unutar `allowed_paths` (bridge je unutra, `static/app.js` je
EKSPLICITNO forbidden ovim kontraktom -- ako GUI tekst treba izmjenu,
prijaviti kao OUT_OF_SCOPE_FINDING za budući mali task, ne širiti
scope ovdje).

# Implementation steps

1. Istražiti i odlučiti idempotencija pristup (Objective #2) PRIJE
   koda.
2. `MaterializePerformanceSnapshots` + testovi: prazan batch, batch sa
   MATCHED+validnim redovima (tačan `PerformanceSnapshot` kreiran,
   ručno provjerene vrijednosti), MATCHED+invalid red (preskočen, ne
   sruši se), UNMATCHED/AMBIGUOUS redovi (ignorisani, nikad
   materijalizovani), idempotencija (dva uzastopna poziva, isti
   rezultat, nema duplikata).
3. Bridge wiring (Objective #3) + testovi: `confirm_performance_import`
   sada VRAĆA I `materialized_count` I stvarno kreira snapshotove
   (integration test preko real SQLite, isti seed-stil kao
   G6/G7a/b/c testovi).
4. Integration test: pun tok `ConfirmPerformanceImport` →
   `MatchPerformanceImportBatch` → `MaterializePerformanceSnapshots` →
   `build_campaign_performance_summary` VRAĆA STVARNE derived
   vrijednosti (ovo je KLJUČNI dokaz da je gap zatvoren -- prije ovog
   taska, ovaj isti test bi vratio sve `None`).

# Acceptance

- [ ] `MaterializePerformanceSnapshots` postoji, kreira TAČAN
      `PerformanceSnapshot` za svaki MATCHED+validan red.
- [ ] MATCHED+nevalidan red preskočen, ne sruši batch, brojan odvojeno.
- [ ] UNMATCHED/AMBIGUOUS redovi nikad ne postaju snapshot.
- [ ] Idempotencija dokazana testom (dva uzastopna poziva, nema
      duplikata) -- pristup dokumentovan i obrazložen.
- [ ] `confirm_performance_import` (bridge) sada poziva novi use-case,
      `MatchPerformanceImportBatch` NETAKNUT.
- [ ] **Integration test dokazuje da `build_campaign_performance_summary`
      VRAĆA STVARNE (ne None) derived vrijednosti nakon punog
      import→match→materialize toka** -- ovo je task-definišuća
      acceptance stavka.
- [ ] `domain/`, `ports/`, `infrastructure/`,
      `presentation_webview/screens/`,
      `presentation_webview/static/app.js` NISU DIRANI.
- [ ] `python -m pytest tests/unit/application/performance/
      tests/unit/presentation_webview/bridge/
      tests/integration/application/performance/ -v` prolazi.
- [ ] `python -m pytest -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.
- [ ] **CI provjeren preko PR-a.**

# Verification

```bash
python -m pytest tests/unit/application/performance/ tests/unit/presentation_webview/bridge/ tests/integration/application/performance/ -v
python -m pytest -q
python -m ruff check .
python -m mypy src

git push -u origin task/ACS-F1-057-materialize-performance-snapshots
gh pr create --base main --title "ACS-F1-057: Materialize PerformanceSnapshot from matched CSV rows"
gh pr checks
```

# Review focus — Claude (MEDIUM, §29)

- **Task-definišući dokaz**: integration test STVARNO pokazuje da
  derived metrike prestaju biti `None` nakon import→match→materialize
  toka (ne samo da `materialized_count > 0`).
- Idempotencija stvarno testirana, ne pretpostavljena.
- MATCHED+invalid red edge case stvarno pokriven (ovo je latentan bug
  koji `MatchPerformanceImportBatch` uvodi -- matchuje bez provjere
  `row.errors` -- ovaj task ga MORA ispravno rukovati na svom sloju,
  ne popraviti u `match_performance_import_batch.py`, koji je van
  `allowed_paths`).
- `raw_metrics=row.raw_values` čuva audit trail (isti princip kao
  `PerformanceImportRow`).

# Rollback

MEDIUM risk -- nova, izolovana application-layer logika + mala
aditivna bridge izmjena unutar VEĆ pregledane metode. Nula
domain/ports/infrastructure izmjena, nula GUI/lifecycle rizika (ne
dira `static/app.js`/`screens/`). Claude-only review → odmah merge po
§29 ako PASS.

# Coordination

**Blokira ACS-F1-056 (P1.5-G8)** -- G8-ov derived-metrički dio
acceptance kriterijuma je NEIZVODLJIV bez ovog taska. Preporučeni
redoslijed: ACS-F1-057 prvo (ovaj task), zatim ACS-F1-056 nastavlja
KAKO JE originalno kontraktovan (nema potrebe za D2 redefinicijom).
ACS-F1-056 kontrakt OSTAJE NEPROMIJENJEN -- njegove pretpostavke
postaju TAČNE tek nakon ovog taska.

Ne paralelizovati sa bilo kojim drugim taskom koji dira
`presentation_webview/bridge/__init__.py`.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-057-materialize-performance-snapshots
Branch:   task/ACS-F1-057-materialize-performance-snapshots
Base:     main @ 2c1a0e4
```
