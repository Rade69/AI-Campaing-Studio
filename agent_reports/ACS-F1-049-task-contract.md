---
task_id: ACS-F1-049
phase: "GUI read-path -- Brend ekran (drugi ekran u ACS-F1-046 obrascu)"
title: "Brend ekran čita stvaran brand/snapshot/approved facts iz baze"
risk: HIGH
coordinator: claude
implementer: TBD
reviewers: [claude, codex]
status: "OPEN -- contract written before code, čeka implementera"
created_at: 2026-09-07
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/presentation_webview/bridge/__init__.py
  - src/ai_campaign_studio/presentation_webview/screens/brend/__init__.py
  - src/ai_campaign_studio/presentation_webview/static/app.js
  - src/ai_campaign_studio/presentation/contracts.py
  - src/ai_campaign_studio/presentation/ui_models.py
  - tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py
  - tests/unit/presentation_webview/test_brend_ssr.py
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
  - src/ai_campaign_studio/presentation_webview/screens/plan_kampanje/
  - src/ai_campaign_studio/presentation_webview/screens/kalendar/
  - src/ai_campaign_studio/presentation_webview/screens/studio_sadrzaja/
  - src/ai_campaign_studio/presentation_webview/screens/pregled_izvoz/
gitnexus_required: true
adversarial_required: true
gitnexus:
  required: true
  note: >
    Drugi read-path ekran nakon ACS-F1-046 (Kampanje). Provjeriti da
    `get_brand`/`get_snapshot`/`list_snapshot_facts` (VEĆ POSTOJEĆE
    repo metode -- nema potrebe za novim) i dalje imaju iste potpise
    poslije bilo kakvih međuvremenih izmjena.
---

# Kontekst

ACS-F1-046 je uspostavio OBRAZAC za GUI read-path ekrane: novi READ
`js_api` bridge metod + `app.js` DOM hidratacija + SSR fixture kao
offline fallback. `Brend` je DRUGI ekran u tom nizu (najavljen kao
budući task u ACS-F1-046-ovoj Coordination sekciji).

**Ovaj task je NIŽEG rizika za repo sloj nego ACS-F1-046** --
`BrandRepositoryPort.get_brand(brand_id)`,
`BrandRepositoryPort.get_snapshot(snapshot_id)` i
`FactRepositoryPort.list_snapshot_facts(snapshot_id)` VEĆ POSTOJE (svi
korišteni od `create_campaign_and_generate_plan`/`_ensure_brand()`
danas). **Nema potrebe za NOVIM repo metodama.** Projekat je
single-brand MVP -- `_ensure_brand()` (već postoji u bridge-u) uvijek
vraća ISTI demo brand/snapshot par (seeduje ga ako ne postoji), pa
Brend ekranu ne treba "lista brendova", samo "trenutni brand".

**BF-1/BF-2 klase nalaza iz ACS-F1-046 (Codex-ov drugi review) MORAJU
biti unaprijed primijenjene ovdje, ne ponovo otkrivane:**

1. `loadX()` funkcija mora koristiti immediate fast path + jednokratni
   `window.addEventListener('pywebviewready', loadX, {once:true})`
   fallback -- NIKAD bezuslovan poziv pri parsiranju skripte.
2. Hidratacija mora ciljati JEDINSTVEN, ekran-specifičan marker
   (`data-brend-*` ili slično), NIKAD generički selector koji bi mogao
   pogoditi element na drugom ekranu.

# Objective

## 1. Nova READ js_api metoda: `get_brand_overview() -> dict`

Nema ulaznog payload-a (ili prazan `{}`, implementer bira, konzistentno
sa `list_campaigns`). Poziva `self._ensure_brand()` (POSTOJEĆI metod)
da dobije `(brand_id, snapshot_id)`, zatim `self._brand_repo.get_brand(brand_id)`
+ `self._brand_repo.get_snapshot(snapshot_id)` +
`self._fact_repo.list_snapshot_facts(snapshot_id)`.

Vraća: brand ime, snapshot polja relevantna za GUI (implementer bira
tačan podskup od `BrandVoice`/`Audience`/itd. koji STVARNO odgovara
postojećim SSR tab panelima -- brand-info, approved-facts, brand-voice,
brand-resources -- provjeriti STVARAN `BrendFixture`/`BrandInfo`/
`ApprovedFact`/`BrandResource` oblik u `screens/brend/__init__.py` PRIJE
pisanja koda, ne pretpostavljati), i listu `ApprovedFact` (samo
`is_fact_usable` fact-ove -- isti standard kao `select_allowed_facts`).

Nikad ne vraća SQL/Path/exception objekte. Nepostojeći brand (teorijski,
`_ensure_brand()` bi ovo trebao spriječiti) -> `ok=False` sa jasnim
`error_code`, ne izuzetak.

## 2. `brend/__init__.py` -- render sa STVARNIM podacima

`render_body()` OSTAJE fixture-driven za offline/build-time SSR
(netaknuto). `app.js` dobija `loadBrandOverview()` (ili slično) koji se
poziva na `pywebviewready` (+ immediate fast path), zamjenjuje SSR
fixture sadržaj STVARNIM podacima u brand-info i approved-facts
panelima (brand-voice/brand-resources mogu ostati fixture-only ako
domain model nema odgovarajuća polja -- implementer dokumentuje tu
odluku, ne izmišlja podatke).

XSS-escape OBAVEZAN na svaku interpoliranu vrijednost (brand ime i
fact tekst dolaze iz korisnički/AI-učitanih podataka preko fixture-a,
isti rizik kao Kampanje lista).

## 3. `presentation/contracts.py` + `ui_models.py`

`PresentationFacade` dobija `get_brand_overview` potpis. Nov
`BrandOverviewResultUiModel`/odgovarajući row model (implementer bira
imena, prati `*ResultUiModel` obrazac).

# Implementation steps

1. Pročitati STVARAN `BrendFixture`/`BrandInfo`/`ApprovedFact`/
   `BrandResource` u `screens/brend/__init__.py` I stvaran
   `Brand`/`BrandSnapshot`/`BrandVoice`/`Audience` domain oblik PRIJE
   pisanja koda -- mapirati tačno koja SSR polja imaju realan domain
   izvor i koja ostaju fixture-only.
2. Bridge metoda (Objective #1) + testovi: prazan/normalan slučaj,
   fact filtriranje (`is_fact_usable`), no secret/path/exception leak.
3. `contracts.py`/`ui_models.py` dopuna + testovi.
4. `app.js`/`brend/__init__.py` povezivanje -- PRIMIJENITI
   `pywebviewready` + ekran-specifičan-marker obrazac OD POČETKA (vidi
   Kontekst) + testovi: SSR offline fallback i dalje radi, XSS-escape
   dokazan (isti stil kao `test_app_js_campaign_hydration_lifecycle_and_screen_isolation`
   -- izvršan Node/VM test, ne samo string-assertion, ako je izvodljivo
   u razumnom vremenu; string-assertion prihvatljiv kao minimum).
5. Integration test: STVARNA baza, `LoadBrandFixture` demo brend →
   `get_brand_overview()` vraća TAČNE podatke.

# Acceptance

- [ ] `get_brand_overview` postoji, vraća TAČNE podatke iz baze (ne
      izmišljene).
- [ ] Nijedan secret/path/exception tekst ne curi.
- [ ] `app.js` koristi `pywebviewready` + immediate fast path (NIKAD
      bezuslovan poziv), i ekran-specifičan marker (NIKAD generički
      selector) -- OD PRVE VERZIJE, ne kao fix runda.
- [ ] SSR (`render_body()`) i dalje radi OFFLINE sa fixture prikazom.
- [ ] `domain/`, `application/`, `ports/`, `infrastructure/`, i sva
      ostala 5 screens/ foldera (kampanje, plan_kampanje, kalendar,
      studio_sadrzaja, pregled_izvoz) NISU DIRANI.
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

git push -u origin task/ACS-F1-049-brend-read-path
gh pr create --base main --title "ACS-F1-049: Brend citanje iz baze"
gh pr checks
```

# Review focus — Claude + Codex (adversarial)

- **Pywebview lifecycle** (Codex-ov ACS-F1-046 BF-1 presedan):
  adversarial DOM simulacija kasne API injekcije -- da li podaci
  STVARNO stignu poslije `pywebviewready`, ne samo teoretski.
- **Cross-screen izolacija** (BF-2 presedan): potvrditi da hidratacija
  NE dira nijedan element na drugim ekranima (pokrenuti isti stil testa
  kao `test_app_js_campaign_hydration_lifecycle_and_screen_isolation`).
- XSS escape stvarno testiran (payload u brand imenu/fact tekstu).
- `is_fact_usable` filtriranje stvarno primijenjeno (fact sa
  REJECTED/DEPRECATED statusom ne smije se pojaviti).

# Rollback

HIGH risk -- drugi read-path presedan, ali NIŽI stvaran rizik od
ACS-F1-046 (nema novih repo metoda, nema migracija). Pun review ciklus
i dalje obavezan zbog GUI lifecycle/cross-screen klase grešaka koje su
pogodile ACS-F1-046.

# Coordination

Paralelno sa ACS-F1-048 (Metric Calculation) -- `allowed_paths`
potpuno disjoint. NE paralelizovati sa BILO KOJIM drugim taskom koji
dira `presentation_webview/static/app.js`/`bridge/__init__.py` (lekcija
iz GUI-009/F1-046/F1-047 3-way merge sudara ranije danas -- ako se
treći read-path ekran (Kalendar/Studio sadržaja detalj/Podešavanja)
želi pokrenuti, čekati da OVAJ task prvo merge-uje).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-049-brend-read-path
Branch:   task/ACS-F1-049-brend-read-path
Base:     main @ cc84778
```
