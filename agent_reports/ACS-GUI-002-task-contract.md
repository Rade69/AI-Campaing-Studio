---
task_id: ACS-GUI-002
phase: Faza-1 (post G9)
title: "GUI-BASE: preostala 4 sidebar ekrana (Brend/Kampanje/Kalendar/Podešavanja), fixture-wired"
risk: MEDIUM
coordinator: claude
implementer: minimax
reviewers: [claude]
status: "OPEN — contract written before code"
created_at: 2026-09-02
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/presentation_webview/screens/brend/
  - src/ai_campaign_studio/presentation_webview/screens/kampanje/
  - src/ai_campaign_studio/presentation_webview/screens/kalendar/
  - src/ai_campaign_studio/presentation_webview/screens/podesavanja/
  - tests/unit/presentation_webview/test_brend_ssr.py
  - tests/unit/presentation_webview/test_kampanje_ssr.py
  - tests/unit/presentation_webview/test_kalendar_ssr.py
  - tests/unit/presentation_webview/test_podesavanja_ssr.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/infrastructure/
  - src/ai_campaign_studio/presentation/
  - src/ai_campaign_studio/presentation_webview/shell/
  - src/ai_campaign_studio/presentation_webview/screens/__init__.py
  - src/ai_campaign_studio/presentation_webview/screens/_static_pages.py
  - src/ai_campaign_studio/presentation_webview/screens/pocetna/
  - src/ai_campaign_studio/presentation_webview/static/
  - src/ai_campaign_studio/presentation_webview/__main__.py
  - src/ai_campaign_studio/bootstrap.py
  - src/ai_campaign_studio/main.py
  - docs/gui-v3/
gitnexus_required: true
adversarial_required: false
gitnexus:
  required: true
  repository: "H:\\AI Campaing Studio"
  worktree: main (pre-branch pre-impact)
  branch: main
  head: b4b324f
  index_status: fresh (analyze re-run 2026-09-02 post ACS-GUI-001 merge)
  targets:
    - symbol: "src/ai_campaign_studio/presentation_webview/screens/{brend,kampanje,kalendar,podesavanja}/__init__.py"
      upstream_risk: LOW
      upstream_count: "These 4 modules already exist as ACS-GUI-001 placeholders, imported by screens/_static_pages.py (importlib.import_module by key, not a static import) and covered by tests/unit/presentation_webview/test_static_pages_generator.py's DRY/placeholder-content assertions. This task REPLACES their render_body() content -- the generator/tests outside allowed_paths must keep passing unmodified (see Acceptance)."
      downstream_notes: "No other importers."
      affected_processes: []
  scope_fit: PASS
  unknowns: []
---

# Kontekst

Drugi GUI task nakon ACS-GUI-001 (shell + Početna, merged, `main @ cad003e`
-> `9259792`). `V3_PLAN.md`-ova faza "Screen integration redom 01→09" —
ovaj task pokriva preostala 4 ekrana koja su trenutno ACS-GUI-002
placeholder-i ("Ovaj ekran dobija punu implementaciju u narednom GUI
task-u") unutar top-level sidebar-a: **Brend, Kampanje, Kalendar,
Podešavanja**. Peti sidebar ekran (Početna) je već gotov. Preostalih 5
ekrana iz `docs/gui-v3` (Opis kampanje, Plan kampanje, Studio sadržaja,
Pregled i izvoz — cijeli campaign workflow stepper) NISU dio ovog taska
(budući ACS-GUI-003).

**Obavezno pročitati prije koda**:

```text
docs/gui-v3/V3_PLAN.md
docs/gui-v3/INTEGRATION.md
docs/gui-v3/screens/02_brend/index.html
docs/gui-v3/screens/03_kampanje/index.html
docs/gui-v3/screens/06_kalendar/index.html
docs/gui-v3/screens/09_podesavanja/index.html
docs/PYWEBVIEW_SECURITY.md (već primijenjeno u shell/__main__.py — ovaj
  task ne dira sigurnosni kod, ali mora ostati u skladu s njim, npr. nema
  eksternih linkova bez target="_blank", nema remote asset referenci)
agent_reports/2026-09-02-ACS-GUI-001-minimax.md (round 2 evidence — da
  vidiš tačno kako je shell/write_all_pages/fixture pattern postavljen)
```

Pogledati postojeći kod da razumiješ TAČAN pattern koji se replicira (ne
izmišljati novi):

```text
src/ai_campaign_studio/presentation_webview/shell/__init__.py (render_shell — NE DIRATI)
src/ai_campaign_studio/presentation_webview/screens/__init__.py (write_all_pages — NE DIRATI)
src/ai_campaign_studio/presentation_webview/screens/pocetna/__init__.py (fixture dataclass + render_body() PATTERN)
src/ai_campaign_studio/presentation_webview/screens/brend/__init__.py (trenutni placeholder — ZAMIJENITI sadržaj)
tests/unit/presentation_webview/test_static_pages_generator.py (NE DIRATI — ali provjeriti da tvoje izmjene
  ne kvare `test_write_all_pages_placeholder_screens_carry_only_their_label`, koji trenutno očekuje
  "ACS-GUI-002" placeholder tekst za ova 4 ekrana; taj test MORA biti update-ovan da odgovara REALNOM
  sadržaju — ali taj fajl je van tvog allowed_paths, javi koordinatoru šta treba promijeniti u njemu,
  ne diraj ga sam)
```

**Risk**: MEDIUM — izolovana prezentaciona površina, ista klasa rizika
kao ACS-GUI-001. §29: Claude-only review, PASS -> odmah merge.

# Objective

Za svaki od 4 ekrana: zamijeniti placeholder `render_body()` sa realnim,
fixture-driven sadržajem koji vizuelno odgovara `docs/gui-v3` referenci,
portovanim kroz Python (fixture dataclass + `html.escape()` disciplina,
isti pattern kao `screens/pocetna/`).

## Brend (`docs/gui-v3/screens/02_brend/index.html`)

- Tabs red (Osnovni podaci / Odobrene činjenice / Glas brenda / Brend
  resursi) — vizuelni markup, tab-switching JS već postoji u
  `static/app.js` (`data-action="tab"`), ne pisati novi JS.
- Brand-status red ("Provjereno i ažurno" + datum) — datum može biti
  fixture string, ne treba biti live `datetime.now()` (ovo je i dalje
  fixture-tier ekran).
- 2-kolonski grid: brand info kartica (ime, opis, primarna publika, glas
  brenda badge-ovi) + odobrenih činjenica kartica (fixture lista facts —
  koristiti isti demo brend "BrightSmile" kao svuda drugo u projektu).
- Brend resursi (3 kartice: Logo, Paleta boja, Izvori).

## Kampanje (`docs/gui-v3/screens/03_kampanje/index.html`)

- Tabela kampanja: fixture lista `Campaign(name, brand, status_variant,
  status_label, planned_count, last_modified)`, 3 reda kao u referenci.
- **"Otvori" dugme/link**: docs/gui-v3 linkuje ka `04_opis_kampanje` —
  taj ekran NE POSTOJI u `presentation_webview` (ACS-GUI-003, van scope-a).
  Zato "Otvori" MORA biti `data-action="toast"` stub (isti pattern kao
  Početna "+ Nova kampanja" dugme), NE `<a href>` ka nepostojećoj stranici
  (to bi bio mrtav/404 link u pravom pywebview prozoru).
- "+ Nova kampanja" dugme — isto, `data-action="toast"` stub.

## Kalendar (`docs/gui-v3/screens/06_kalendar/index.html`)

- 28-dnevni calendar grid, fixture lista `CalendarEvent(day, label,
  variant)` (3 eventa kao u referenci — variant utiče na `.event`/
  `.event.green`/`.event.amber` CSS klasu).
- Callout napomena o tome da kalendar nije publishing — statičan tekst.
- **Campaign-context banner mehanizam**: `docs/gui-v3`-ova verzija ovog
  ekrana (nakon mojih ranijih fixeva u toj branch-i) ima uslovni
  `?campaign=...` query-param banner (breadcrumb + stepper + "Nastavi →
  Studio sadržaja" dugme) koji se pojavljuje samo kad se ekran otvori sa
  tim parametrom. Taj mehanizam cilja ka ekranima (Plan kampanje, Studio
  sadržaja) koji NE POSTOJE u `presentation_webview` još — **ne portovati
  taj banner mehanizam u ovom tasku**. Portovati SAMO globalni Kalendar
  pogled (bez query-param logike) — banner dolazi sa ACS-GUI-003 kad i
  ostatak campaign workflow-a postoji da ga primi.

## Podešavanja (`docs/gui-v3/screens/09_podesavanja/index.html`)

- Lijeva kolona: tabs (Opšte / Jezik / **AI provajderi** aktivan) —
  vizuelni markup, samo "AI provajderi" panel ima stvaran sadržaj u ovoj
  fazi (isto kao referenca — "trenutno vizuelno razrađen AI provider dio").
- Desna kolona: fixture lista `Provider(code, display_name, logo_initials,
  status_label)` — svih 6 (OpenAI, Anthropic, Google, DeepSeek,
  OpenRouter, OpenAI kompatibilan), svaki "Nije povezano" + "Podesi"
  `data-action="toast"` stub (NE pozivati stvarni `PresentationFacade` —
  to je budući task, ne ovaj).
- Callout o production toku (API ključ → Testiraj vezu → Učitaj modele →
  Izaberi model) — statičan tekst, već tačan iz reference.

# Implementation steps

Za svaki ekran, isti obrazac kao `screens/pocetna/__init__.py`:

1. Fixture dataclass(-e) u istom `__init__.py` (frozen `@dataclass`, ne
   Pydantic — ovo nije boundary, isto pravilo kao Početna).
2. `DEFAULT_FIXTURE` konstanta sa podacima identičnim `docs/gui-v3`
   referenci (isti brojevi/imena/statusi — vizuelna koherentnost sa
   dizajn izvorom).
3. `render_body(fixture: XFixture | None = None) -> str` — `html.escape()`
   dosljedno za sav tekst izveden iz fixture podataka.
4. Svaki eksterni/stub link ide kroz `data-action="toast"` (postojeći
   `app.js` handler), NE kroz `<a href>` ka nepostojećoj stranici.

# Acceptance

- [ ] Sva 4 ekrana vizuelno odgovaraju svojoj `docs/gui-v3` referenci
      (isti brojevi, imena, statusi, redoslijed sekcija).
- [ ] Svaki ekran je fixture-driven — test dokazuje da promjena fixture
      vrijednosti mijenja renderovani output (isti obrazac kao
      `test_changing_fixture_changes_rendered_body` za Početnu).
- [ ] `html.escape()` korišten dosljedno za sav fixture-izvedeni tekst.
- [ ] Nijedan link ka ne-postojećem ekranu (Opis kampanje, Plan kampanje,
      Studio sadržaja, Pregled i izvoz) — samo `data-action="toast"`
      stub-ovi.
- [ ] Kalendar NE sadrži `?campaign=` banner/stepper mehanizam u ovom
      tasku (van scope-a, dolazi sa ACS-GUI-003).
- [ ] `shell/__init__.py`, `screens/__init__.py`, `screens/_static_pages.py`,
      `screens/pocetna/`, `static/`, `__main__.py` nisu dirani.
- [ ] Nema novih remote asset referenci (fonts.googleapis.com,
      cdn.tailwindcss.com, itd.) — CSP iz `render_shell()` ostaje
      `default-src 'self'`, provjeri da tvoj markup ne krši to.
- [ ] `python -m pytest -q`, `ruff check .`, `mypy src` prolaze —
      **OSIM** `tests/unit/presentation_webview/test_static_pages_generator.py`,
      za koji se očekuje da će `test_write_all_pages_placeholder_screens_carry_only_their_label`
      pasti (jer sadržaj više nije placeholder) — to je OČEKIVANO i
      koordinator će update-ovati taj test pri merge-u (fajl je van tvog
      `allowed_paths`). U evidence izvještaju eksplicitno navesti koji
      testovi padaju i zašto, ne sakriti to.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest tests/ --ignore=tests/unit/presentation_webview/test_static_pages_generator.py -q
python -m pytest tests/architecture/test_import_boundaries.py -v
python -m pytest tests/unit/presentation_webview/test_brend_ssr.py tests/unit/presentation_webview/test_kampanje_ssr.py tests/unit/presentation_webview/test_kalendar_ssr.py tests/unit/presentation_webview/test_podesavanja_ssr.py -v
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- vizuelna vjernost `docs/gui-v3` referenci (koordinator uporediti
  string-po-string ključne vrijednosti);
- nema `<a href>` ka nepostojećim ekranima;
- Kalendar ne curi campaign-context banner prije vremena;
- fixture-driven disciplina (isti nivo kao Početna round 1/2 review);
- `shell/`/`screens/__init__.py`/`_static_pages.py`/`pocetna/`/`static/`
  netaknuti (git diff dokazuje).

# Rollback

MEDIUM risk, izolovana prezentaciona površina. Fix na istoj branch bez
proširenja scope-a.

# Coordination

Nezavisno od **ACS-F1-007** (Pi, A6) i **ACS-F1-008** (Crush, A7) —
potpuno disjoint, sva tri mogu ići paralelno odmah. Koordinator će nakon
merge-a update-ovati `test_static_pages_generator.py`-jev placeholder
test da odgovara novom sadržaju (van tvog scope-a, ne čekaj na to da
predaš svoj rad).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-GUI-002-remaining-sidebar-screens
Branch:   task/ACS-GUI-002-remaining-sidebar-screens
Base:     main @ b4b324f
```
