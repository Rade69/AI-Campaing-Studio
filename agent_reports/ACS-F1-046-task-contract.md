---
task_id: ACS-F1-046
phase: "Kritičan fix — GUI čitanje stvarnih podataka (web Claude review 2026-09-07, Nalaz 3, dio 1)"
title: "Kampanje lista čita stvarne kampanje iz baze (prvi read-path ekran, obrazac za ostale)"
risk: HIGH
coordinator: claude
implementer: TBD
reviewers: [claude, codex]
status: "OPEN -- contract written before code, čeka implementera"
created_at: 2026-09-07
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/presentation_webview/bridge/__init__.py
  - src/ai_campaign_studio/presentation_webview/screens/kampanje/__init__.py
  - src/ai_campaign_studio/presentation_webview/static/app.js
  - src/ai_campaign_studio/presentation/contracts.py
  - src/ai_campaign_studio/presentation/ui_models.py
  - tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py
  - tests/unit/presentation_webview/test_kampanje_ssr.py
  - tests/unit/presentation/test_contracts.py
  - tests/unit/presentation/test_ui_models.py
  # -- proširenje 2026-09-07, vidi ACS-F1-046-addendum-scope-decision.md --
  - src/ai_campaign_studio/ports/repositories.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_campaign_repository.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_brand_repository.py
  - tests/unit/ports/test_repositories.py
  - tests/unit/infrastructure/database/repositories/test_sqlite_campaign_repository.py
  - tests/unit/infrastructure/database/repositories/test_sqlite_brand_repository.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/
  - resources/migrations/
  - src/ai_campaign_studio/presentation_webview/screens/studio_sadrzaja/
  - src/ai_campaign_studio/presentation_webview/screens/pregled_izvoz/
  # NAPOMENA: ports/ i infrastructure/ su djelimično dozvoljeni -- SAMO
  # tačno ta tri fajla navedena gore u allowed_paths, tri NOVA aditivna
  # metoda (list_campaigns, get_latest_plan_for_campaign, get_brand).
  # Svi ostali ports/*.py i infrastructure/**/*.py fajlovi OSTAJU
  # forbidden bez izuzetka.
gitnexus_required: true
adversarial_required: true
gitnexus:
  required: true
  note: >
    Prvi READ js_api metod ikad dodat na bridge (do sad su sve tri
    postojeće metode WRITE-only). Provjeriti da li nešto POSTOJEĆE
    pretpostavlja da bridge nema read-metode (npr. neki test koji
    provjerava "bridge ima TAČNO N metoda").
---

# Kontekst

Nezavisna review "web Claude" (2026-09-07) je otkrila strukturnu
prepreku: `__main__.py` renderuje SVIH 9 ekrana preko `write_all_pages()`
JEDNOM, u build-time, u privremeni fajl, i navigacija ide preko
`file://` `<a href>` linkova. `write_all_pages(out_dir)` NE PRIMA
NIKAKVE stvarne podatke -- svi ekrani su `DEFAULT_FIXTURE`. Bridge ima
TRI js_api metode (`create_campaign_and_generate_plan`,
`generate_campaign_content`, `configure_provider`) -- SVE TRI su
write-only. Korisnik NE MOŽE vidjeti nijednu stvarno kreiranu
kampanju, plan, ili objavu kroz GUI.

**Ovo NIJE "još nije završeno"** -- to je arhitektonska rupa: SSR-at-
build-time fundamentalno ne može nositi runtime podatke bez
client-side čitanja. Codex je ovo već implicitno pogodio kroz BF-1
(ACS-GUI-008/009) -- rješenje tamo je bilo "app.js IIFE čita
`?campaign=`/`?plan=` iz URL-a i otkriva već-postojeći DOM element."
To rješava "ZNAM koji je ID", ali NE rješava "PRIKAŽI mi STVARNE
podatke za taj ID" -- svaki sljedeći ekran udara u isti zid.

**Scope ovog taska**: SAMO "Kampanje" lista (najjednostavniji ekran --
tabela od N redova, bez editovanja). Cilj je uspostaviti OBRAZAC
(bridge read-metod + JS DOM-punjenje) koji ostali ekrani (Brend,
Kalendar, Studio sadržaja detalj) mogu kasnije PONOVITI kao ZASEBNE,
manje taskove -- NE pokušavati sve ekrane odjednom u ovom task-u.

# Objective

## 1. Nova READ js_api metoda: `list_campaigns() -> dict`

- Nema ulaznog payload-a (ili prazan `{}` -- implementer bira, ALI
  mora biti konzistentno sa ostalim metodama koje UVIJEK primaju
  dict).
- Koristi `self._campaign_repo` (VEĆ postoji preko `_with_call_resources`
  obrasca -- primijeniti dekorator i na ovu metodu, isti stil kao
  ostale tri).
- Vraća SVE kampanje (nema paginacije u ovoj verziji -- broj kampanja
  je danas mali; implementer NE gradi paginaciju "za svaki slučaj").
- Svaki red: `id`, `name` (ili offer/topic -- implementer provjerava
  STVARAN `Campaign`/`CampaignBrief` model za dostupna polja PRIJE
  pisanja koda), `status`, `plan_item_count` (broj stavki plana ako
  plan postoji, inače 0 ili null -- implementer dokumentuje), `brand`
  (ime brenda preko `brand_repo.get_brand()`, novi aditivni metod --
  vidi `ACS-F1-046-addendum-scope-decision.md`), `created_at` (ISO
  8601 string, NE Python `datetime` objekat -- json-serializable
  contract). **`updated_at` je ISKLJUČEN iz scope-a** (polje ne
  postoji nigdje u domain modelu -- vidi addendum za obrazloženje).
- NIKAD ne vraća SQL/Path/exception objekte -- isti standard kao
  postojeće tri metode (PYWEBVIEW_SECURITY §3).
- Prazna baza (nema kampanja) -> `{"ok": true, "campaigns": []}`, NE
  greška.

## 2. `kampanje/__init__.py` -- render sa STVARNIM podacima

- `render_body()` OSTAJE fixture-driven za OFFLINE/build-time SSR
  (isti obrazac kao BF-1: tabela se UVIJEK renderuje sa DEFAULT_FIXTURE
  ili praznim placeholder-om u build-time HTML-u).
- `app.js` dobija novu funkciju (npr. `loadCampaigns()`) koja se
  poziva PRI UČITAVANJU stranice (ne na klik) preko
  `window.pywebview.api.list_campaigns()`, i ZAMJENJUJE/PUNI tabelu
  STVARNIM redovima preko DOM manipulacije (implementer bira: potpuno
  zamijeniti `<tbody>` sadržaj preko `innerHTML`+`html.escape`-ekvivalent
  u JS-u -- **OBAVEZNO escape-ovati svaku vrijednost prije umetanja u
  DOM** da se izbjegne XSS, isti standard kao Python `html.escape`
  strana).
- Ako `window.pywebview.api.list_campaigns` ne postoji (npr. debug/
  offline pregled bez pywebview-a) -- tabela OSTAJE na fixture prikazu,
  NE baca grešku u konzoli koja blokira stranicu.
- Prazna lista kampanja -> tabela prikazuje jasnu poruku ("Nema
  kreiranih kampanja. Napravi prvu preko 'Opis kampanje'.") umjesto
  prazne tabele BEZ objašnjenja.

## 3. `presentation/contracts.py` + `ui_models.py`

- `PresentationFacade` dobija `list_campaigns` potpis.
- Nov `CampaignSummaryUiModel`/`ListCampaignsResultUiModel` (implementer
  bira tačna imena, prati postojeći `*ResultUiModel` obrazac).

# Implementation steps

1. Istražiti STVARAN `Campaign`/`CampaignBrief`/`CampaignPlan` model
   (koja polja postoje, kako se plan_item_count računa, gdje se
   status prikazuje) PRIJE pisanja koda -- ne pretpostavljati.
2. Bridge metoda (Objective #1) + testovi: prazna baza, 1 kampanja
   bez plana, 1 kampanja SA planom (plan_item_count tačan), VIŠE
   kampanja (redoslijed -- implementer bira i dokumentuje, npr.
   `created_at DESC`), nema secret/path/exception leak-a.
3. `contracts.py`/`ui_models.py` dopuna + testovi.
4. `app.js`/`kampanje/__init__.py` povezivanje + test: SSR i dalje
   prikazuje fixture (offline/build-time dokaz), `loadCampaigns()`
   XSS-escape dokazan (ime kampanje sa `<script>` payload-om ne
   izvršava se u DOM-u -- test preko headless DOM parsing-a ili
   string-assertion na `escapeHtml`-ekvivalentnoj JS funkciji).
5. Integration test: STVARNA baza sa STVARNO kreiranom kampanjom
   (preko `CreateCampaign` use-case-a, ne ručni SQL insert) ->
   `list_campaigns()` je vraća sa TAČNIM podacima.

# Acceptance

- [ ] `list_campaigns` postoji, vraća SVE kampanje sa TAČNIM poljima.
- [ ] Prazna baza -> `{"ok": true, "campaigns": []}`, ne greška.
- [ ] Nijedan secret/path/exception tekst ne curi.
- [ ] `app.js` STVARNO puni DOM sa pravim podacima pri učitavanju
      stranice, XSS-escape dokazan.
- [ ] SSR (`render_body()`) i dalje radi OFFLINE (bez pywebview-a) sa
      fixture prikazom -- ne pokvaren postojeći test.
- [ ] `domain/`, `application/`, `ports/`, `infrastructure/`,
      `studio_sadrzaja/`, `pregled_izvoz/` NISU DIRANI. Van tri
      eksplicitno navedena `ports/`/`infrastructure/` fajla (addendum
      2026-09-07), nijedan drugi `ports/`/`infrastructure/` fajl NIJE
      DIRAN.
- [ ] `python -m pytest tests/unit/presentation_webview/
      tests/unit/presentation/ -v` prolazi.
- [ ] `python -m pytest -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.
- [ ] **CI provjeren preko PR-a.**

# Verification

```bash
python -m pytest tests/unit/presentation_webview/ tests/unit/presentation/ -v
python -m pytest -q
python -m ruff check .
python -m mypy src

git push -u origin task/ACS-F1-046-kampanje-read-path
gh pr create --base main --title "ACS-F1-046: Kampanje lista -- stvarno citanje iz baze"
gh pr checks
```

# Review focus -- Claude + Codex (adversarial)

- Ovo je PRVI read-path metod na bridge-u -- provjeriti da NIJEDNA
  postojeća pretpostavka ("bridge je write-only") nije negdje
  hardkodirana (grep za broj js_api metoda u testovima/dokumentaciji).
- XSS escape STVARNO testiran, ne pretpostavljen (payload sa
  `<script>`/`<img onerror=...>` u imenu kampanje).
- `plan_item_count` STVARNO tačan za kampanju SA planom (integration
  test, ne izmišljena vrijednost).
- SSR offline fallback STVARNO radi (test koji NE mock-uje
  `window.pywebview` i potvrđuje da se fixture prikazuje, ne prazna
  stranica ili JS greška).
- Thread-safety: `list_campaigns` mora imati `@_with_call_resources`
  isti kao ostale tri metode (per-call konekcija, ne stara
  instance-atribut greška iz HOTFIX-002).

# Rollback

HIGH risk -- prvi read-path presedan na bridge-u, mijenja kako se
GUI-BASE tier ekrani ponašaju (SSR fixture + client-side hydration
umjesto čisto statičan SSR). Izolovano na jedan ekran. Pun review
ciklus prije merge-a.

# Coordination

Nema zavisnosti. Uspostavlja OBRAZAC za ostale ekrane (Brend, Kalendar,
Studio sadržaja detalj-view, Pregled i izvoz content-cards) -- SVAKI
od njih postaje ZASEBAN budući task koji PONAVLJA ISTI obrazac
(`list_X`/`get_X_detail` read metod + `app.js` DOM-punjenje pri load-u),
ne novi task koji ponovo izmišlja pristup. Prioritet #2 po Human Owner
odluci (2026-09-07, poslije ACS-F1-045).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-046-kampanje-read-path
Branch:   task/ACS-F1-046-kampanje-read-path
Base:     main @ 70c9efa
```
