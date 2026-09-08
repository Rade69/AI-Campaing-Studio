---
task_id: ACS-F1-053
phase: "P1.5-G7a — Campaign Performance summary (Minimal UI dio 1, Faza 1 v1.5 §22)"
title: "Pregled i izvoz ekran prikazuje stvaran Campaign Performance summary"
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
    Četvrti GUI read-path ekran nakon Kampanje/Brend/Početna
    (ACS-F1-046/049/051). Provjeriti da
    `build_campaign_performance_summary` (ACS-F1-050) i dalje ima isti
    potpis poslije bilo kakvih međuvremenih izmjena.
---

# Kontekst

P1.5-G6 (ACS-F1-050) je isporučio `build_campaign_performance_summary(repo,
campaign_id) -> CampaignPerformanceSummary` (`application/performance/
build_performance_summaries.py`) -- čista funkcija, agregira
`DerivedMetricSet`/`CanonicalMetricSet`/`distribution_instance_count` za
jednu kampanju. Ovaj task je PRVI GUI caller tog koda -- P1.5-G7 (Faza 1
v1.5 §22, "Minimal UI") traži "Campaign → Performance tab", podijeljen
ovdje na G7a (ovaj task, čisto čitanje) / G7b (ContentPiece sekcija,
budući task) / G7c (Import Performance + CSV mapping dialog, budući
task, genuinski nov UX obrazac -- file picker, višekoračni dialog).

**"Pregled i izvoz" ekran je odabran kao mjesto prikaza** (ne novi
ekran, ne novi tab-sistem): već je jedini ekran koji nosi stvaran
`campaign_id` kroz `?campaign=` query param (ACS-GUI-009 obrazac), već
je "završni pregled kampanje" ekran pojmovno, i NEMA postojeći tab-
sistem (za razliku od Studio sadržaja) pa se Performance prikazuje kao
NOVA kartica u postojećem `grid g2`/novom redu, ne novi tab.

**Trenutno NEMA test podataka u realnoj bazi** (P1.5-G3/G4/G5 nikad
nisu imali GUI write-path za CSV import -- to je G7c) -- ovaj ekran će
u praksi TRENUTNO prikazivati "Nema podataka o performansama" jer
`DistributionInstance`/`PerformanceSnapshot` tabele su prazne za
stvarne kampanje. To je OČEKIVANO i ISPRAVNO ponašanje, ne bug --
implementer MORA testirati i prazan i popunjen slučaj (popunjen preko
direktnog repo seed-a u testu, isto kao G6-ovi testovi).

**BF-1/BF-2/XSS klase nalaza (F1-046/049/051, F1-049 REJEKT presedan)
MORAJU biti primijenjene OD PRVE VERZIJE, uključujući OBAVEZAN izvršni
Node/VM test od početka (ne string-assertion):**

1. `loadX()` funkcija: immediate fast path + jednokratni
   `window.addEventListener('pywebviewready', loadX, {once:true})`
   fallback.
2. Ekran-specifičan marker (`data-perf-*` ili slično), NIKAD generički
   selector.
3. **Node/VM test mora modelirati `addEventListener`-ov `options`
   argument i dokazati exactly-once ponašanje preko DVOSTRUKOG emit-a**
   (F1-051 BF-1 presedan -- string-presence i "listener registrovan
   jednom" NISU dovoljni, mora se dokazati da se hidratacija/API poziv
   desio TAČNO jednom nakon dva `pywebviewready` eventa).

# Objective

## 1. Nova READ js_api metoda: `get_campaign_performance(raw_payload: dict) -> dict`

Isti obrazac kao `get_job_status` (payload nosi `campaign_id: str`, NE
prazan `{}` kao `list_campaigns`/`get_dashboard_overview` -- ovaj poziv
je specifičan za JEDNU kampanju):

```python
def get_campaign_performance(self, raw_payload: dict) -> dict:
    if not isinstance(raw_payload, dict): -> VALIDATION_ERROR
    campaign_id = raw_payload.get("campaign_id")
    if not isinstance(campaign_id, str) or not campaign_id.strip(): -> VALIDATION_ERROR
    ...
```

Poziva `build_campaign_performance_summary(self._performance_repo,
CampaignId(campaign_id))` (POSTOJI, G6). `self._performance_repo` VEĆ
POSTOJI kao `@property` na `CampaignBridgeApi` (već korišten od
`export_campaign_package`) -- reuse, ne dupliraj.

Vraća DTO sa: `derived` (6 polja iz `DerivedMetricSet` -- CTR/CPC/CPM/
CPA/ROAS/conversion_rate, sva opciona), `raw` (relevantan podskup iz
`CanonicalMetricSet` -- implementer bira koja polja SSR prikaz stvarno
treba, ne mora vraćati svih 9), `distribution_instance_count: int`.

Nepostojeći `campaign_id` (kampanja ne postoji u bazi) ->
`VALIDATION_ERROR`, ne `INTERNAL_ERROR` (isti obrazac kao ostale
per-id read metode). Nula `DistributionInstance`-a (postojeća
kampanja, nema performance podataka) -> `ok=True` sa svim
`derived`/`raw` poljima `None`/`0` -- NE greška, to je normalan
"nema još podataka" slučaj.

## 2. `pregled_izvoz/__init__.py` -- render + hidratacija

`render_body()` OSTAJE fixture-driven (dodati SSR fixture polja za
Performance karticu -- implementer bira razuman default, npr. "Nema
podataka o performansama još" placeholder). Nova kartica u postojećem
`grid g2` red (ili novi red ispod, implementer procjenjuje layout) sa
ekran-specifičnim `data-perf-*` markerima za svako izvedeno polje koje
se prikazuje.

`app.js` dobija `loadCampaignPerformance()` -- poziva
`get_campaign_performance({campaign_id})` gdje `campaign_id` dolazi iz
POSTOJEĆEG `?campaign=` URL param čitanja (već postoji u boot IIFE za
export dugme -- reuse tu logiku, ne duplirati parsing). Prazan/`None`
derived polja -> prikazati "N/A" ili slično, NIKAD prazan string koji
izgleda kao bug.

XSS-escape nije kritičan za brojeve (`CTR: 0.034` itd. su formatirani
brojevi, ne slobodan tekst), ALI `distribution_instance_count`/
formatirane vrijednosti I DALJE idu kroz `textContent`, ne `innerHTML`
sa string-konkatenacijom (isti standard kao ostali ekrani, ne praviti
izuzetak "jer su ovo samo brojevi").

## 3. `presentation/contracts.py` + `ui_models.py`

`PresentationFacade` dobija `get_campaign_performance` potpis. Nov
`CampaignPerformanceResultUiModel` (implementer bira tačna polja,
prati `*ResultUiModel` obrazac -- vidi `DashboardOverviewResultUiModel`
kao najbliži presedan za "agregat sa opcionim brojevima").

# Implementation steps

1. Bridge metoda (Objective #1) + testovi: nepostojeća kampanja
   (VALIDATION_ERROR), postojeća kampanja bez performance podataka
   (ok=True, sve None/0), postojeća kampanja SA seed-ovanim
   `DistributionInstance`+`PerformanceSnapshot` podacima (tačne
   vrijednosti -- isti seed-stil kao G6-ovi testovi), no secret/path/
   exception leak.
2. `contracts.py`/`ui_models.py` dopuna + testovi.
3. `pregled_izvoz/__init__.py` render + `app.js` povezivanje --
   `pywebviewready` + ekran-specifičan marker OD POČETKA + **OBAVEZAN
   izvršni Node/VM test sa dvostrukim emit-om** (Kontekst tačka 3) +
   test da SSR offline fallback i dalje radi.
4. Integration test: STVARNA baza, seed kampanja + distribution
   instance + snapshot, `get_campaign_performance()` vraća TAČNE
   agregate (isti stil kao F1-050-ovi testovi).

# Acceptance

- [ ] `get_campaign_performance` postoji, vraća TAČNE agregate za
      kampanju SA podacima, `None`/`0` za kampanju BEZ podataka
      (ok=True u oba slučaja), `VALIDATION_ERROR` za nepostojeću
      kampanju.
- [ ] Nijedan secret/path/exception tekst ne curi.
- [ ] `app.js` koristi `pywebviewready` + immediate fast path +
      ekran-specifičan marker OD PRVE VERZIJE.
- [ ] **Izvršni Node/VM DOM test postoji OD PRVE VERZIJE**, modelira
      `addEventListener` options, emituje `pywebviewready` DVAPUT,
      dokazuje exactly-once API poziv (F1-051 BF-1 standard, ne
      slabiji).
- [ ] SSR (`render_body()`) i dalje radi OFFLINE sa fixture prikazom.
- [ ] `domain/`, `application/`, `ports/`, `infrastructure/`, i svi
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

git push -u origin task/ACS-F1-053-campaign-performance
gh pr create --base main --title "ACS-F1-053: Campaign Performance summary u Pregled i izvoz"
gh pr checks
```

# Review focus — Claude + Codex (adversarial)

- **Izvršni test dokazuje exactly-once lifecycle** (dvostruki emit,
  F1-051 standard) -- OVO je prvi provjereni item, ne string-presence.
- Cross-screen izolacija (nula DOM izmjena/API poziva na ekranu bez
  `data-perf-*` markera).
- Prazna performance putanja (kampanja bez podataka) stvarno testirana
  kao NORMALAN slučaj, ne kao greška.
- `derived` dolazi iz `build_campaign_performance_summary` (G5/G6
  lanac), nema ručne formule u bridge/frontend sloju.

# Rollback

HIGH risk -- četvrti read-path presedan, GUI lifecycle klasa grešaka.
Pun review ciklus obavezan.

# Coordination

**NE paralelizovati** sa G7b (ContentPiece Performance, Studio
sadržaja) ni G7c (Import Performance UI) -- sva tri dijele
`presentation_webview/static/app.js` i `bridge/__init__.py` (ista
lekcija kao GUI-009/F1-046/F1-047 3-way sudar). Sekvencijalno: G7a
(ovaj task) → G7b → G7c → P1.5-G8 (Integration acceptance).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-053-campaign-performance
Branch:   task/ACS-F1-053-campaign-performance
Base:     main @ 5cb5a96
```
