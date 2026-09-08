---
task_id: ACS-F1-055
phase: "P1.5-G7c — Import Performance dugme + CSV mapping dialog (Faza 1 v1.5 §22)"
title: "Pregled i izvoz ekran omogućava stvaran CSV performance import"
risk: HIGH
coordinator: claude
implementer: TBD
reviewers: [claude, codex]
status: "OPEN -- contract written before code, čeka implementera"
created_at: 2026-09-08
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/presentation_webview/bridge/__init__.py
  - src/ai_campaign_studio/presentation_webview/screens/pregled_izvoz/__init__.py
  - src/ai_campaign_studio/presentation_webview/static/app.js
  - src/ai_campaign_studio/presentation/contracts.py
  - src/ai_campaign_studio/presentation/ui_models.py
  - tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py
  - tests/unit/presentation_webview/test_pregled_izvoz_ssr.py
  - tests/unit/presentation_webview/test_static_pages_generator.py
  - tests/unit/presentation/test_contracts.py
  - tests/unit/presentation/test_ui_models.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/infrastructure/
  - resources/migrations/
  - src/ai_campaign_studio/presentation_webview/screens/kampanje/
  - src/ai_campaign_studio/presentation_webview/screens/brend/
  - src/ai_campaign_studio/presentation_webview/screens/plan_kampanje/
  - src/ai_campaign_studio/presentation_webview/screens/kalendar/
  - src/ai_campaign_studio/presentation_webview/screens/studio_sadrzaja/
  - src/ai_campaign_studio/presentation_webview/screens/pocetna/
  - src/ai_campaign_studio/presentation_webview/screens/podesavanja/
gitnexus_required: true
adversarial_required: true
gitnexus:
  required: true
  note: >
    Šesti/sedmi GUI presedan, ALI prvi WRITE-path performance task
    (G7a/b su bili read-only). Provjeriti da
    `PreviewPerformanceMapping`/`ConfirmPerformanceImport`/
    `MatchPerformanceImportBatch` (svi ACS-F1-042/043/044) i dalje
    imaju iste potpise. OBAVEZNO `gitnexus_impact` na sva tri PRIJE
    izmjene (čak i ako su read-only iz bridge perspektive, cross-check
    da niko drugi ne zavisi od njihovog trenutnog ponašanja na
    neočekivan način).
---

# Kontekst

Faza 1 v1.5 §22 traži "Import Performance button" + "CSV mapping
dialog" kao posljednji dio P1.5-G7 Minimal UI. Za razliku od G7a/G7b
(čisto čitanje), ovo je PRVI write-path performance task — korisnik
bira CSV fajl, sistem ga parsira/mapira/persistuje/matchuje.

**Postojeći backend lanac (sve VEĆ POSTOJI, G3/G4, ACS-F1-042/043/044)
-- ovaj task SAMO ožičava bridge/GUI, ne dira aplikacioni sloj:**

```python
PreviewPerformanceMapping().execute(file_path) -> PreviewResult
# columns: tuple[ColumnMappingSummary, ...] (canonical_field/header/
#   status "matched"|"ambiguous"|"unmatched"/candidates)
# total_rows, valid_rows, invalid_rows, invalid_samples

ConfirmPerformanceImport(performance_repo).execute(
    file_path, column_overrides=None, platform_code=None
) -> PerformanceImportBatch
# Persistuje batch + SVE redove (validne i nevalidne -- ništa se ne
# gubi). Nema blokiranja na invalid_rows > 0 -- to je već postojeća
# semantika, ne izmišljati novu.

MatchPerformanceImportBatch(performance_repo).execute(
    batch.id, campaign_id
) -> MatchResult
# matched_count, ambiguous_count, unmatched_count, skipped_count
```

**Namjerno MINIMALAN v1 scope (u duhu §22 "Ne praviti veliki Analytics
centar"):**

1. **NEMA interaktivnog column-remapping UI-ja.** `column_overrides`
   ostaje `None` u ovom tasku. Preview prikazuje status po polju
   (matched/ambiguous/unmatched + candidate headeri) READ-ONLY -- ako
   korisnik vidi `ambiguous`/`unmatched`, poruka ga upućuje da ispravi
   CSV header i ponovo izabere fajl. Interaktivna remapping forma je
   BUDUĆI task, ne ovaj (implementer NE gradi je, čak ni kao stub).
2. **Nema blokiranja na invalid rows.** `ConfirmPerformanceImport` već
   persistuje sve redove (validne i nevalidne) -- preview samo
   INFORMIŠE (X validno / Y nevalidno + par uzoraka), potvrda uvijek
   radi ako je fajl uopšte parsiran.
3. **Fajl picker je NATIVE OS dialog** (`window.create_file_dialog`,
   pywebview 6.2.1, `webview.OPEN_DIALOG`), NE HTML `<input type=file>`
   -- desktop-first app, konzistentno sa ostatkom aplikacije.

# Objective

## 1. Bridge pristup `window` objektu (NOVO -- ne postoji trenutno)

`CampaignBridgeApi` TRENUTNO nema referencu na svoj `webview.Window`
(kreiran POSLIJE bridge instance u `__main__.py`, `js_api=bridge`).
Pristup preko `webview.windows[0]` (single-window app, potvrđeno u
`_open_window` -- tačno jedan `create_window` poziv u cijeloj
aplikaciji). Implementer dodaje `import webview` (lokalni import unutar
metode, isti obrazac kao `__main__.py`-ov `_open_window` -- ne globalni
import, da testni okvir bez pywebview instaliranog i dalje radi;
provjeriti `architecture_boundaries` test koji ovo štiti).

## 2. Nova WRITE js_api metoda: `pick_and_preview_performance_csv(raw_payload: dict | None = None) -> dict`

```python
if not webview.windows: -> INTERNAL_ERROR (nema aktivnog prozora,
    teorijski nemoguće u produkciji, ali test-safe)
paths = webview.windows[0].create_file_dialog(
    webview.OPEN_DIALOG,
    file_types=('CSV Files (*.csv)', 'All files (*.*)'),
)
if not paths: -> ok=True, cancelled=True (korisnik otkazao dialog --
    NIJE greška)
file_path = paths[0]
preview = PreviewPerformanceMapping().execute(file_path)
-> ok=True, cancelled=False, file_path=file_path, mapiran PreviewResult
```

Greške pri parsiranju (npr. fajl nije validan CSV, `ImportPerformanceCsv`
baca izuzetak) -> `VALIDATION_ERROR` sa razumljivom porukom, NE
`file_path`/stacktrace leak.

## 3. Nova WRITE js_api metoda: `confirm_performance_import(raw_payload: dict) -> dict`

Payload: `{file_path: str, campaign_id: str, platform_code: str | None}`.
Validacija: dict + `file_path`/`campaign_id` str non-empty. Nepostojeća
kampanja -> `VALIDATION_ERROR`.

```python
batch = ConfirmPerformanceImport(self._performance_repo).execute(
    file_path, column_overrides=None, platform_code=platform_code
)
match_result = MatchPerformanceImportBatch(
    self._performance_repo
).execute(batch.id, CampaignId(campaign_id))
-> ok=True, batch_id=str(batch.id), row_count, valid_count, invalid_count
   (iz batch), matched_count/ambiguous_count/unmatched_count/skipped_count
   (iz match_result)
```

## 4. `pregled_izvoz/__init__.py` -- render + hidratacija

Novi "Uvezi CSV" dugme (`data-action="import-performance-csv"`) u
postojećoj Performance oblasti ekrana. Klik pokreće JS tok: poziv
`pick_and_preview_performance_csv` → ako `cancelled`, ništa (korisnik
je otkazao) → ako preview stigne, prikazati READ-ONLY summary (status
po polju + counts + par invalid uzoraka) sa dugmetom "Potvrdi uvoz" →
klik poziva `confirm_performance_import` sa `file_path` iz prethodnog
koraka (JS ga drži u lokalnoj varijabli, NE šalje ponovo file dialog)
→ rezultat prikazan kao summary (uvezeno/poklopljeno/nepoklopljeno).

SSR fixture: dugme uvijek prisutno, `data-perf-import-result` callout
prazan/hidden po defaultu (isti obrazac kao `data-export-result`/
`data-generate-result`).

**BF-1/BF-2/XSS klase nalaza MORAJU biti primijenjene, uključujući
OBAVEZAN izvršni Node/VM test:** ekran-specifičan marker, XSS-escape na
SVAKI tekst koji dolazi iz CSV fajla (header imena, invalid sample
poruke -- CSV je KORISNIČKI fajl, tretirati identično kao AI-generisan
tekst). Ovaj task NEMA `pywebviewready` lifecycle komponentu (dugme se
klikne, ne hidratuje se automatski na load) -- Node/VM test ovdje
dokazuje XSS-escape i cross-screen izolaciju (dugme/rezultat postoje
SAMO na ovom ekranu), ne exactly-once emit (nije primjenjivo za
click-triggered tok, za razliku od G7a/b).

## 5. `presentation/contracts.py` + `ui_models.py`

`PresentationFacade` dobija oba nova potpisa. Novi UiModel-i za
preview (`PerformanceCsvPreviewResultUiModel` ili slično -- implementer
bira imena) i confirm (`ConfirmPerformanceImportResultUiModel` ili
slično).

# Implementation steps

1. Bridge `window` pristup (Objective #1) -- provjeriti da
   `architecture_boundaries` test i dalje prolazi (lokalni import).
2. `pick_and_preview_performance_csv` + testovi: cancelled dialog
   (mock `create_file_dialog` -> `None`/prazna lista), stvaran CSV
   fixture -> tačan preview (matched/ambiguous/unmatched status),
   neparsibilan fajl -> VALIDATION_ERROR, no secret/path leak (fajl
   putanja JESTE dio legit odgovora ovdje -- to nije secret, ali
   PROVJERITI da se ne curi ništa DRUGO poput internal DB path-a).
3. `confirm_performance_import` + testovi: nepostojeća kampanja,
   stvaran fixture CSV -> tačan batch + match rezultat (real SQLite,
   isti seed-stil kao G6/G7a/b testovi), non-dict payload.
4. `contracts.py`/`ui_models.py` dopuna + testovi.
5. `pregled_izvoz/__init__.py` render + `app.js` povezivanje --
   ekran-specifičan marker + XSS-escape na CSV-porijeklo tekst +
   **OBAVEZAN izvršni Node/VM test** (cross-screen izolacija + XSS,
   ne exactly-once lifecycle -- objašnjeno u Objective #4) + test da
   SSR offline fallback i dalje radi.
6. Integration test: stvaran CSV sadržaj preko `tmp_path` (POSTOJEĆI
   obrazac -- `_write_csv(tmp_path, content)` helper već postoji u
   `tests/unit/application/performance/test_preview_performance_mapping.py`,
   isti stil koristiti ovdje, ne izmišljati novi fixture mehanizam),
   pun tok preview→confirm→match, tačni rezultati.

# Acceptance

- [ ] `pick_and_preview_performance_csv` postoji, ispravno rukuje
      cancelled dialog (ok=True, cancelled=True, NE greška).
- [ ] `confirm_performance_import` postoji, vraća tačan batch +
      match rezultat preko POSTOJEĆIH use-caseova (nula duplirane
      logike).
- [ ] `column_overrides` ostaje `None` (nema remapping UI-ja u v1,
      eksplicitna odluka, ne propust).
- [ ] Nijedan secret/path/exception tekst (osim samog izabranog
      file_path-a, koji je legit dio odgovora) ne curi.
- [ ] XSS-escape na CSV-porijeklo tekst (header imena, invalid sample
      poruke) stvarno testiran.
- [ ] **Izvršni Node/VM DOM test postoji OD PRVE VERZIJE** -- dokazuje
      cross-screen izolaciju + XSS, ne exactly-once (nije primjenjivo).
- [ ] SSR (`render_body()`) i dalje radi OFFLINE sa fixture prikazom.
- [ ] `domain/`, `application/`, `ports/`, `infrastructure/`, svi
      ostali screens/ folderi NISU DIRANI.
- [ ] `python -m pytest tests/unit/presentation_webview/
      tests/unit/presentation/ -v` prolazi.
- [ ] `python -m pytest -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] `node --check src/ai_campaign_studio/presentation_webview/static/app.js`
      prolazi.
- [ ] Nema izmjena van `allowed_paths`.
- [ ] **CI provjeren preko PR-a.**

# Verification

```bash
python -m pytest tests/unit/presentation_webview/ tests/unit/presentation/ -v
python -m pytest -q
python -m ruff check .
python -m mypy src
node --check src/ai_campaign_studio/presentation_webview/static/app.js

git push -u origin task/ACS-F1-055-import-performance-csv
gh pr create --base main --title "ACS-F1-055: Import Performance CSV dugme + preview"
gh pr checks
```

# Review focus — Claude + Codex (adversarial)

- **`window.create_file_dialog` mock-ovanje u testovima ispravno**
  (bez stvarnog OS dialog-a u CI-ju -- provjeriti da testovi ne
  pokušavaju otvoriti pravi native dialog na headless CI runneru).
- Cross-screen izolacija (dugme/rezultat postoje SAMO na ovom ekranu).
- XSS escape na CSV-porijeklo tekst stvarno testiran (payload u CSV
  header imenu).
- `column_overrides=None` potvrđeno -- implementer NIJE dodao
  remapping UI van scope-a.
- `ConfirmPerformanceImport`/`MatchPerformanceImportBatch` pozvani sa
  TAČNIM argumentima, nula duplirane parsing/matching logike u bridge
  sloju.
- Cancelled-dialog putanja stvarno testirana kao normalan slučaj, ne
  greška.

# Rollback

HIGH risk -- prvi write-path performance task, prva `window` pristup
integracija u bridge sloju (nov obrazac, ne postoji presedan). Pun
review ciklus obavezan.

# Coordination

**NE paralelizovati** sa bilo kojim drugim taskom koji dira
`presentation_webview/static/app.js`/`bridge/__init__.py`. Ovo je
posljednji dio G7 (G7a/b su zatvoreni). Nakon ovog taska: P1.5-G8
(Integration acceptance, čist backend/integration test scenario, VJEROVATNO
ne treba `presentation_webview/` uopšte -- provjeriti Faza 1 v1.5 §23
scenario prije pisanja tog kontrakta).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-055-import-performance-csv
Branch:   task/ACS-F1-055-import-performance-csv
Base:     main @ b5bb0e0
```
