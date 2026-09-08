---
task_id: ACS-F1-051
phase: "GUI read-path -- Početna (Dashboard) ekran (treći read-path ekran, ACS-F1-046 obrazac)"
title: "Početna ekran čita stvarne KPI/nedavne kampanje iz baze"
risk: HIGH
coordinator: claude
implementer: TBD
reviewers: [claude, codex]
status: "OPEN -- contract written before code, čeka implementera"
created_at: 2026-09-08
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/presentation_webview/bridge/__init__.py
  - src/ai_campaign_studio/presentation_webview/screens/pocetna/__init__.py
  - src/ai_campaign_studio/presentation_webview/static/app.js
  - src/ai_campaign_studio/presentation/contracts.py
  - src/ai_campaign_studio/presentation/ui_models.py
  - tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py
  - tests/unit/presentation_webview/test_pocetna_ssr.py
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
  - src/ai_campaign_studio/presentation_webview/screens/pregled_izvoz/
  - src/ai_campaign_studio/presentation_webview/screens/podesavanja/
gitnexus_required: true
adversarial_required: true
gitnexus:
  required: true
  note: >
    Treći read-path ekran nakon ACS-F1-046 (Kampanje) i ACS-F1-049
    (Brend). Provjeriti da `campaign_repo.list_campaigns()`,
    `content_repo.list_campaign_content()` (VEĆ POSTOJEĆE repo metode
    -- nema potrebe za novim) i dalje imaju iste potpise poslije bilo
    kakvih međuvremenih izmjena.
---

# Kontekst

ACS-F1-046 (Kampanje) i ACS-F1-049 (Brend) su uspostavili i DVA PUTA
dokazali obrazac za GUI read-path ekrane: novi READ `js_api` bridge
metod + `app.js` DOM hidratacija + SSR fixture kao offline fallback.
Početna (Dashboard) je TREĆI ekran u tom nizu -- prva stranica koju
korisnik vidi, trenutno potpuno fixture-driven (`PočetnaFixture`,
`screens/__init__.py`).

**Ovaj task NEMA arhitektonski domain gap kakav su imali G5
(currency) -- sve potrebne podatke već nose postojeći entiteti:**

- `kpi_posts_planned`/`kpi_drafts`/`kpi_approved` -> `ContentPiece.status`
  (`ContentStatus.PLANNED`/`DRAFT`/`APPROVED`, već postoje kao enum
  vrijednosti) preko postojeće `ContentRepositoryPort.list_campaign_content(campaign_id)`.
- `recent_campaigns` -> `CampaignSummaryUiModel` (već postoji iz
  ACS-F1-046) preko postojeće `CampaignRepositoryPort`-ove liste
  kampanja (ista logika kao `list_campaigns()` bridge metoda -- OVAJ
  task može interno reuse-ovati tu logiku, ne duplirati je).
- `kpi_active_campaigns` -> `Campaign.status` (`CampaignStatus` enum)
  postoji, ALI **nema eksplicitan ARCHIVED/CANCELLED status** -- šta
  tačno znači "aktivna" nije trivijalno. Implementer BIRA jednu
  razumnu definiciju (npr. "svaka kampanja koja NIJE `EXPORTED`", ili
  "ukupan broj kampanja" ako se ne može opravdati suptilnija podjela)
  i DOKUMENTUJE izbor u evidence-u -- nije potrebna duboka istraga kao
  G5-ova valuta, samo eksplicitna, ne prećutna odluka.
- `activity` (Zadnje aktivnosti) -> **NEMA domain koncept "activity
  log" nigdje u sistemu.** Ovaj panel OSTAJE fixture-only (isti
  presedan kao ACS-F1-049-ovo brand-voice/brand-resources) --
  implementer NE izmišlja aktivnosti niti pokušava rekonstruisati
  "aktivnost" iz `created_at` timestamp-ova ako to ne bi bilo
  smisleno; dokumentuje odluku, ne prećutno ostavlja prazno.

**BF-1/BF-2/XSS klase nalaza iz ACS-F1-046 (Codex round 2) i
ACS-F1-049 (Codex round 1, REJECT) MORAJU biti primijenjene OD PRVE
VERZIJE, uključujući test:**

1. `loadX()` funkcija mora koristiti immediate fast path + jednokratni
   `window.addEventListener('pywebviewready', loadX, {once:true})`
   fallback -- NIKAD bezuslovan poziv pri parsiranju skripte.
2. Hidratacija mora ciljati JEDINSTVEN, ekran-specifičan marker
   (`data-pocetna-*` ili slično), NIKAD generički selector koji bi
   mogao pogoditi element na drugom ekranu.
3. **OBAVEZAN izvršni Node/VM DOM test od PRVE verzije** (ne
   string-presence test) -- ACS-F1-049 je dobio REJECT ISKLJUČIVO zbog
   ovoga (kod je bio ispravan, test nije to dokazivao). Ne ponavljati
   tu grešku: test mora IZVRŠITI stvaran commitovan `app.js` u Node
   `vm` kontekstu (isti obrazac kao
   `test_app_js_campaign_hydration_lifecycle_and_screen_isolation` iz
   F1-046 i `test_app_js_brand_hydration_lifecycle_isolation_and_xss`
   iz F1-049) i dokazati: kasnu API injekciju -> `pywebviewready`
   poziva hydrate funkciju TAČNO jednom; immediate fast path; nula API
   poziva/netaknut DOM na ekranu BEZ `data-pocetna-*` markera; svaki
   interpolirani string (recent campaign name/status, kpi hint/value
   ako su string) ide kroz `textContent` ili `escapeHtml`, NIKAD
   sirov `innerHTML`.

# Objective

## 1. Nova READ js_api metoda: `get_dashboard_overview() -> dict`

Nema ulaznog payload-a (ili prazan `{}`, konzistentno sa
`list_campaigns`/`get_brand_overview`). Reuse-uje postojeću
`campaign_repo`/`content_repo` logiku (implementer odlučuje da li
poziva internu helper funkciju koju `list_campaigns` već koristi, ili
piše paralelnu petlju -- ALI ne duplira poslovnu logiku bez razloga).

Za svaku kampanju: status, broj `ContentPiece` po statusu
(PLANNED/DRAFT/APPROVED), ime (isti `offer`-as-name obrazac kao
`CampaignSummaryUiModel`). Vraća agregirane brojače (4 KPI) + listu
"nedavnih kampanja" (razumna gornja granica, npr. 5 -- MVP nema
paginaciju, isti presedan kao `list_campaigns`).

`activity` NIJE dio ovog DTO-a -- SSR fixture panel za "Zadnje
aktivnosti" ostaje netaknut/fixture-only.

Nikad ne vraća SQL/Path/exception objekte. Prazna baza (nula kampanja)
-> `ok=True` sa svim brojačima `0` i praznom listom, NE greška.

## 2. `pocetna/__init__.py` -- render sa STVARNIM podacima

`render_body()` OSTAJE fixture-driven za offline/build-time SSR
(netaknuto). `app.js` dobija `loadDashboardOverview()` (ili slično)
koji se poziva na `pywebviewready` (+ immediate fast path), zamjenjuje
SSR fixture sadržaj u 4 KPI kartice i "Nedavne kampanje" listi
STVARNIM podacima. "Zadnje aktivnosti" panel se NE dira.

XSS-escape OBAVEZAN na svaku interpoliranu vrijednost (kampanja ime
dolazi iz korisničkog unosa preko `CampaignBriefInput.offer`, isti
rizik kao Kampanje lista).

## 3. `presentation/contracts.py` + `ui_models.py`

`PresentationFacade` dobija `get_dashboard_overview` potpis. Nov
`DashboardOverviewResultUiModel`/odgovarajući row model (implementer
bira imena, prati `*ResultUiModel` obrazac iz `list_campaigns`/
`get_brand_overview`).

# Implementation steps

1. Pročitati STVARAN `PočetnaFixture`/`Kpi`/`RecentCampaign` oblik u
   `screens/__init__.py` PRIJE pisanja koda -- mapirati tačno koja SSR
   polja imaju realan domain izvor (4 KPI + recent_campaigns) i koje
   ostaje fixture-only (activity).
2. Odlučiti i dokumentovati definiciju "aktivna kampanja" (Kontekst
   sekcija).
3. Bridge metoda (Objective #1) + testovi: prazna baza, normalan
   slučaj sa više kampanja/statusa, no secret/path/exception leak.
4. `contracts.py`/`ui_models.py` dopuna + testovi.
5. `app.js`/`pocetna/__init__.py` povezivanje -- PRIMIJENITI
   `pywebviewready` + ekran-specifičan-marker obrazac OD POČETKA +
   **OBAVEZAN izvršni Node/VM test** (vidi Kontekst tačka 3) + test da
   SSR offline fallback i dalje radi.
6. Integration test: STVARNA baza sa >=2 kampanje različitih statusa,
   `get_dashboard_overview()` vraća TAČNE brojače.

# Acceptance

- [ ] `get_dashboard_overview` postoji, vraća TAČNE podatke iz baze
      (ne izmišljene), nula na praznoj bazi (ne greška).
- [ ] Nijedan secret/path/exception tekst ne curi.
- [ ] `app.js` koristi `pywebviewready` + immediate fast path (NIKAD
      bezuslovan poziv), i ekran-specifičan marker (NIKAD generički
      selector) -- OD PRVE VERZIJE.
- [ ] **Izvršni Node/VM DOM test postoji OD PRVE VERZIJE** i dokazuje
      lifecycle + cross-screen izolaciju + XSS-safe interpolaciju
      (string-presence test NIJE dovoljan -- vidi Kontekst tačka 3).
      Implementer nezavisno reprodukuje bar 2 mutacije (bezuslovan
      poziv, generički selector) prije predaje evidence-a, isti
      obrazac kao F1-049 fix runda.
- [ ] "Aktivna kampanja" definicija eksplicitno dokumentovana u
      evidence-u.
- [ ] "Zadnje aktivnosti" panel ostaje fixture-only, dokumentovano
      zašto (nema domain koncept), ne izmišljeno.
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

git push -u origin task/ACS-F1-051-pocetna-read-path
gh pr create --base main --title "ACS-F1-051: Pocetna dashboard citanje iz baze"
gh pr checks
```

# Review focus — Claude + Codex (adversarial)

- **Izvršni test stvarno dokazuje lifecycle/izolaciju/XSS** (ne
  string-presence) -- ovo je PRVI provjereni item, prije bilo čega
  drugog, s obzirom na F1-049 presedan.
- Pywebview lifecycle race (immediate fast path + `pywebviewready`
  fallback, exactly-once listener).
- Cross-screen izolacija (nula DOM izmjena/API poziva na ekranu bez
  `data-pocetna-*` markera).
- XSS escape stvarno testiran (payload u kampanja imenu).
- Prazna baza -> nula/prazna lista, ne greška.
- "Aktivna kampanja" definicija je razumna i dokumentovana (ne
  proizvoljna bez obrazloženja).

# Rollback

HIGH risk -- treći read-path presedan, ali NIŽI proceduralni rizik od
prethodna dva (obrazac je sada dva puta dokazan, BF-1/BF-2/XSS lekcije
su eksplicitno ugrađene u OVAJ kontrakt umjesto da se otkrivaju tokom
review-a). Pun review ciklus i dalje obavezan (HIGH/GUI lifecycle
klasa).

# Coordination

Paralelno sa ACS-F1-050 (P1.5-G6 Analytics Read Models) --
`allowed_paths` potpuno disjoint (`presentation_webview/screens/pocetna/`
+ `bridge/__init__.py` + `app.js` vs `domain/performance/` +
`ports/` + `infrastructure/` + `application/performance/`), sigurno
za paralelan rad. NE paralelizovati sa BILO KOJIM drugim taskom koji
dira `presentation_webview/static/app.js`/`bridge/__init__.py`.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-051-pocetna-read-path
Branch:   task/ACS-F1-051-pocetna-read-path
Base:     main @ fb1d79e
```
