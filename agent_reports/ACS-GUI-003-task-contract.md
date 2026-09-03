---
task_id: ACS-GUI-003
phase: Faza-1 (post G9, post ACS-GUI-004)
title: "GUI-BASE: campaign workflow ekrani (Opis / Plan / Studio sadržaja / Pregled i izvoz) iz docs/gui-v3 u presentation_webview"
risk: MEDIUM
coordinator: claude
implementer: pi
reviewers: [claude]
status: "OPEN — contract written before code"
created_at: 2026-09-03
dependencies:
  - ACS-GUI-001 (merged, main @ cad003e) — shell + Početna
  - ACS-GUI-002 (merged, main @ 99f3502) — Brend/Kampanje/Kalendar/Podešavanja fixture-wired
  - ACS-GUI-004 (merged, main @ 7246dd6/e534d0f) — real tab-panel switching pattern (Brend/Podešavanja) — OVAJ task MORA koristiti isti pattern za Studio sadržaja tabove, NE mokapov stari cosmetic-only markup (vidi napomena ispod)
allowed_paths:
  - src/ai_campaign_studio/presentation_webview/screens/opis_kampanje/__init__.py
  - src/ai_campaign_studio/presentation_webview/screens/plan_kampanje/__init__.py
  - src/ai_campaign_studio/presentation_webview/screens/studio_sadrzaja/__init__.py
  - src/ai_campaign_studio/presentation_webview/screens/pregled_izvoz/__init__.py
  - src/ai_campaign_studio/presentation_webview/screens/kampanje/__init__.py
  - src/ai_campaign_studio/presentation_webview/screens/_static_pages.py
  - src/ai_campaign_studio/presentation_webview/shell/__init__.py
  - src/ai_campaign_studio/presentation_webview/static/app.css
  - tests/unit/presentation_webview/test_opis_kampanje_ssr.py
  - tests/unit/presentation_webview/test_plan_kampanje_ssr.py
  - tests/unit/presentation_webview/test_studio_sadrzaja_ssr.py
  - tests/unit/presentation_webview/test_pregled_izvoz_ssr.py
  - tests/unit/presentation_webview/test_kampanje_ssr.py
  - tests/unit/presentation_webview/test_static_pages_generator.py
  - tests/unit/presentation_webview/test_shell.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/infrastructure/
  - src/ai_campaign_studio/presentation/
  - src/ai_campaign_studio/presentation_webview/screens/pocetna/
  - src/ai_campaign_studio/presentation_webview/screens/brend/
  - src/ai_campaign_studio/presentation_webview/screens/kalendar/
  - src/ai_campaign_studio/presentation_webview/screens/podesavanja/
  - src/ai_campaign_studio/presentation_webview/__main__.py
  - src/ai_campaign_studio/presentation_webview/static/app.js
  - src/ai_campaign_studio/presentation_webview/static/brand-logo.png
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
  head: c416a58
  index_status: fresh (analyze re-run 2026-09-03 post window-state/logo/mockup-sync merge)
  targets:
    - symbol: "src/ai_campaign_studio/presentation_webview/screens/_static_pages.py:write_all_pages"
      upstream_risk: LOW
      upstream_count: "0 direct callers indexed besides __main__.main() and the test suite (both outside a code-symbol dependency edge). Currently iterates ONLY shell.SIDEBAR_ITEMS (5 sidebar screens) to build target_dir/screens/{key}/index.html. This task ADDS a second, parallel loop for the 4 new non-sidebar workflow screens (opis_kampanje/plan_kampanje/studio_sadrzaja/pregled_izvoz) — they must NOT be added to SIDEBAR_ITEMS (they are not top-level nav items; they're reached via Kampanje → 'Otvori' and the stepper, and via Kalendar's existing ?campaign= query-param link)."
      downstream_notes: "Consumed by __main__.py (pywebview entry point) and the static-pages generator tests."
      affected_processes: []
    - symbol: "src/ai_campaign_studio/presentation_webview/shell/__init__.py:render_shell"
      upstream_risk: LOW
      upstream_count: "Called by every screen's page-generation path via _static_pages.py. This task does NOT change render_shell's signature — it already accepts `crumbs: list[Breadcrumb]` for exactly this use case (dynamic breadcrumb text like 'Kampanje › Proljetna kolekcija › Opis kampanje'). SIDEBAR_ITEMS stays a 5-item tuple; active_key for all 4 new screens is \"kampanje\" (keeps the Kampanje sidebar link highlighted while inside the workflow, matching the mokap)."
      downstream_notes: "No other importers of render_shell besides _static_pages.py."
      affected_processes: []
    - symbol: "src/ai_campaign_studio/presentation_webview/screens/kampanje/__init__.py:render_body"
      upstream_risk: LOW
      upstream_count: "Currently every 'Otvori' button is data-action=\"toast\" with message 'Kampanja workflow ekran dolazi u ACS-GUI-003' — the module's own docstring says as much. This task turns 'Otvori' into a real <a href=\"../opis_kampanje/index.html\"> (mokap doesn't parametrize by campaign id at the GUI-BASE tier — same simplification already used by Kalendar's ?campaign=<name> query param elsewhere, follow that precedent if a campaign-scoping query param is wanted; otherwise a plain static link is acceptable for this tier)."
      downstream_notes: "Imported by _static_pages.py (importlib). No other importers."
      affected_processes: []
  scope_fit: PASS
  unknowns:
    - "Whether 'Otvori' should carry a ?campaign=<name> query param (like Kalendar already does) or link to a static path — implementer's call, document the choice in evidence."
---

# Kontekst

Peti GUI-BASE task. ACS-GUI-001/002 dali su 5 sidebar ekrana (Početna/Brend/Kampanje/Kalendar/
Podešavanja), fixture-driven, SSR-style. ACS-GUI-004 je dodao STVARAN tab-panel switching pattern
(`data-tab-target` → `data-tab-panel`) i dokazao ga na Brend/Podešavanja. Application-layer pipeline
(LoadBrandFixture → CreateCampaign → GenerateCampaignPlan → EditCampaignPlan/ApproveCampaignPlan →
GenerateSocialPost → claim linter → ReviseContentPiece) je **potpuno gotov** (svi taskovi merged,
vidi `.agent/CURRENT_STATE.md`).

`docs/gui-v3/` ima 9 mokap ekrana; production `presentation_webview/` ima samo 5 (sidebar ekrani).
Nedostaju 4 **campaign workflow** ekrana koji čine 5-koračni stepper (Opis kampanje → Plan kampanje
→ Kalendar[postojeći] → Studio sadržaja → Pregled i izvoz):

```text
docs/gui-v3/screens/04_opis_kampanje/index.html
docs/gui-v3/screens/05_plan_kampanje/index.html
docs/gui-v3/screens/07_studio_sadrzaja/index.html
docs/gui-v3/screens/08_pregled_izvoz/index.html
```

`kampanje/__init__.py`-ov docstring i in-code komentar to eksplicitno najavljuju: *"the campaign
workflow screens (Opis / Plan / Studio sadržaja / Pregled) do not exist in presentation_webview yet
and land in ACS-GUI-003"*.

**Obavezno pročitati prije koda**:

```text
docs/gui-v3/screens/04_opis_kampanje/index.html
docs/gui-v3/screens/05_plan_kampanje/index.html
docs/gui-v3/screens/07_studio_sadrzaja/index.html
docs/gui-v3/screens/08_pregled_izvoz/index.html
docs/gui-v3/screens/03_kampanje/index.html            (Otvori link cilja opis_kampanje)
agent_reports/ACS-GUI-001-task-contract.md            (shell + write_all_pages pattern)
agent_reports/ACS-GUI-002-task-contract.md            (fixture-dataclass + render_body pattern)
agent_reports/ACS-GUI-004-task-contract.md            (STVARAN tab-panel switching pattern — koristiti za Studio sadržaja tabove)
```

Pogledati postojeći kod da razumiješ TAČAN pattern (ne izmišljati novi):

```text
src/ai_campaign_studio/presentation_webview/screens/kampanje/__init__.py
  (render_body() — 'Otvori' dugme je trenutno data-action="toast", TREBA postati <a href>)
src/ai_campaign_studio/presentation_webview/screens/brend/__init__.py
  (post-ACS-GUI-004 primjer STVARNOG tab-panel switching pattern -- panel_ids, data-tab-target,
   data-tab-panel, hidden na ne-default panelima -- Studio sadržaja MORA koristiti ISTI pattern)
src/ai_campaign_studio/presentation_webview/shell/__init__.py
  (render_shell(*, active_key, page_title, body_html, crumbs=None) -- crumbs parametar POSTOJI,
   koristiti ga za "Kampanje › Proljetna kolekcija › <Ekran>". NE DIRATI potpis, samo pozivati.)
src/ai_campaign_studio/presentation_webview/screens/_static_pages.py
  (write_all_pages() trenutno iterira SAMO shell.SIDEBAR_ITEMS -- 5 sidebar ekrana. Ova 4 nova
   ekrana NISU sidebar stavke -- trebaju DRUGU listu/loop u istoj funkciji, npr.
   WORKFLOW_ITEMS = (("opis_kampanje", "Opis kampanje", [breadcrumb chain]), ...) sa
   active_key="kampanje" za sva 4 i eksplicitnim crumbs. NE dodavati ih u SIDEBAR_ITEMS.)
```

**VAŽNA napomena o mokap zastarjelosti (Studio sadržaja)**: `07_studio_sadrzaja/index.html` mokap
JOŠ UVIJEK koristi stari kozmetički tab markup (`data-action="tab"` bez `data-tab-target`, sav
sadržaj sabijen u jedan `.studio` grid) — taj mokap ekran NIJE ažuriran tokom ACS-GUI-004 mockup
sync-a (samo je dobio logo swap, 2 linije diff-a). **Implementer NE SMIJE portovati tabove doslovno
kao kozmetičke** — mora primijeniti ISTI stvaran `data-tab-target`/`data-tab-panel` pattern koji je
ACS-GUI-004 već dokazao na Brend/Podešavanja (4 taba: Sadržaj / Korištene činjenice / Provjera
usklađenosti / Istorija verzija → 4 panela). Ovo je namjerno odstupanje od "portuj mokap doslovno" —
dokumentovati u evidence izvještaju, ne tražiti dodatno odobrenje (ovo IH je konzistentnost sa
već-odobrenim production pattern-om, ne scope creep).

**Risk**: MEDIUM — izolovana prezentaciona površina, ista klasa rizika kao ACS-GUI-001/002/004.
§29: Claude-only review, PASS → odmah merge.

# Objective

Portati 4 campaign workflow ekrana iz `docs/gui-v3/` u `presentation_webview/`, sve na GUI-BASE
(fixture-driven SSR, bez pravog use-case pozivanja — to je budući "bridge" task, ISTA
disciplina kao postojeći ekrani gdje su stvarne akcije `data-action="toast"`). Kampanje ekran
dobija stvaran link ka prvom koraku workflow-a.

## opis_kampanje (`screens/opis_kampanje/__init__.py`)

Stepper (korak 1 aktivan) + 2-kolonski grid formi: naziv kampanje, cilj (select), ponuda/proizvod
(textarea), ciljna publika (textarea) u lijevoj kartici; kanal/platforma/format/jezik
sadržaja/posebne instrukcije u desnoj kartici. Akcije: "Sačuvaj nacrt" (toast), "Sačuvaj i napravi
plan →" (**stvaran `<a href="../plan_kampanje/index.html">`**).

Fixture: `OpisKampanjeFixture` sa poljima za sve prikazane vrijednosti (naziv, cilj, ponuda,
publika, kanal, platforma, format, jezik, instrukcije, campaign_name za breadcrumb/badge).

## plan_kampanje (`screens/plan_kampanje/__init__.py`)

Stepper (korak 2 aktivan, korak 1 "done" → link nazad). Tabela plana: # / Uloga (badge) / Tema /
Cilj / Format / Status (6 redova u mokapu — Problem/Edukacija/Dokaz/Prigovor/Ponuda/Akcija).
Akcije: "← Opis" (stvaran link nazad), "Regeneriši plan" (toast), "Odobri plan i nastavi →"
(**stvaran link ka postojećem `../kalendar/index.html?campaign=<naziv>`** — koristi VEĆ POSTOJEĆI
`?campaign=` query-param handler u `kalendar/__init__.py`/`app.js`, ne izmišljati novi mehanizam).

Fixture: `PlanKampanjeFixture` sa listom `PlanItem(index, role_badge_variant, role_label, theme,
goal, format, status_label)`.

## studio_sadrzaja (`screens/studio_sadrzaja/__init__.py`)

Stepper (korak 4 aktivan, koraci 1-3 "done" → linkovi nazad, uključujući korak 3 "Kalendar" sa
`?campaign=` linkom). 4 STVARNA tab-panela (vidi napomena gore): Sadržaj (default-active — meta
kartica stavke + edit forma: naslov/hook, glavni tekst, CTA, 5 "brzih akcija" dugmadi svi
`data-action="toast"` sa porukama `"Bridge stub: <akcija>"`, plus preview placeholder karticu i
akcije "Sačuvaj nacrt"/"Pošalji na reviziju"), Korištene činjenice (fact liste), Provjera
usklađenosti (check liste), Istorija verzija (placeholder — "Dostupno u narednoj verziji" callout,
isti ton kao ostali prazni paneli u projektu).

Fixture: `StudioSadrzajaFixture` sa poljima za meta karticu (item_index, item_total, role, platform,
format, planned_date, status), edit forma (hook, hook_char_count, hook_char_limit, body_text, cta),
liste `facts: list[ApprovedFact]`, `compliance_checks: list[str]`.

## pregled_izvoz (`screens/pregled_izvoz/__init__.py`)

Stepper (korak 5 aktivan, koraci 1-4 "done" → linkovi nazad). 3-kolonski grid content kartica
(vizual placeholder + naslov + tema + status badge, 3 stavke u mokapu), 2-kolonski grid ispod:
kvalitet provjere (check lista), izvoz paketa (row lista sa statusima + "Izvezi ZIP paket" dugme).
Header dugme "Odobri kampanju" (`btn success`). Sve akcije `data-action="toast"` (real export/
approve pipeline nije dio ovog taska — G10+ Performance/ZIP export scope).

Fixture: `PregledIzvozFixture` sa `content_items: list[ContentPreviewItem]`, `quality_checks:
list[str]`, `export_rows: list[ExportRow(label, status_variant, status_label)]`.

## Zajednički stepper helper

Kreirati dijeljeni helper (npr. u `shell/__init__.py` kao `stepper_html(active_step: int,
campaign_name: str) -> str`, ili lokalno duplirati po ekranu ako se implementer odluči da je to
čistije — obrazložiti izbor u evidence-u) koji generiše 5 koraka: koraci prije `active_step` su
`<a class="step done" href="...">`, `active_step` je `<div class="step active">` (bez linka), koraci
poslije su `<div class="step">` (bez linka). Korak 3 uvijek cilja
`../kalendar/index.html?campaign=<url-encoded naziv>` kad je "done" ili "active" link (u mokapu
Kalendar korak nikad nije "active" jer ekran postoji zasebno — ali MOŽE biti "done" link kad se
gleda iz koraka 4/5).

## Kampanje screen (`screens/kampanje/__init__.py`)

Zamijeniti `data-action="toast"` na "Otvori" dugmetu sa stvarnim `<a class="btn" href="../
opis_kampanje/index.html">` (odluka o `?campaign=` query param-u ostaje na implementeru — vidi
`unknowns` u gitnexus bloku, dokumentovati izbor).

# Implementation steps

1. Kreirati 4 nova screen modula (`opis_kampanje/`, `plan_kampanje/`, `studio_sadrzaja/`,
   `pregled_izvoz/`, svaki sa `__init__.py`) prateći TAČAN postojeći pattern: `@dataclass(frozen=True)`
   fixture klase, `DEFAULT_FIXTURE` sa vrijednostima iz mokapa, `render_body(fixture=None) -> str`,
   `__all__` export lista.
2. `studio_sadrzaja`: implementirati STVARAN tab-panel switching (4 `data-tab-target` tabova → 4
   `data-tab-panel` diva), NE kozmetički mokap markup (vidi napomena gore).
3. Dodati stepper helper (dijeljen ili po-ekranu, implementer-ova odluka).
4. `shell/__init__.py`: BEZ promjene potpisa `render_shell` — samo provjeriti da `crumbs` parametar
   ispravno radi za dinamičke breadcrumb-ove ("Kampanje › <naziv> › <ekran>"). Ako nešto fali,
   dokumentovati minimalan fix.
5. `_static_pages.py`: proširiti `write_all_pages()` sa DRUGIM loop-om (ne dirati SIDEBAR_ITEMS
   loop) koji generiše 4 nova ekrana u `target_dir/screens/{key}/index.html`, sa `active_key=
   "kampanje"` i eksplicitnim `crumbs` po ekranu. `_copy_static_assets()` ostaje netaknut (isti
   app.css/app.js/brand-logo.png, nema novih static asset-a u ovom tasku).
6. `kampanje/__init__.py`: "Otvori" dugme → stvaran link.
7. Testovi: novi `test_<screen>_ssr.py` po ekranu (fixture render, tab-panel struktura za studio,
   stepper struktura, real-link provjere), update `test_kampanje_ssr.py` (Otvori link umjesto
   toast), update `test_static_pages_generator.py` (svih 9 ekrana sad materijalizovano, ne samo 5),
   provjeriti/dodati `test_shell.py` slučaj za `crumbs` parametar ako fali pokrivenost.

# Acceptance

- [ ] Sva 4 nova ekrana renderuju kompletan fixture sadržaj (nema izostavljenih polja iz mokapa).
- [ ] Studio sadržaja: STVARAN tab-panel switching (data-tab-target/data-tab-panel), NE kozmetički.
- [ ] Stepper na sva 4 ekrana ispravno pokazuje done/active/upcoming stanja i tačne linkove.
- [ ] Kampanje → Opis kampanje → Plan kampanje → Kalendar (`?campaign=`) lanac linkova stvarno radi
      (provjeriti relativne putanje, ne samo tekst href-a).
- [ ] Kampanje "Otvori" dugme je `<a href>`, ne više `data-action="toast"`.
- [ ] `write_all_pages()` generiše svih 9 ekrana (5 sidebar + 4 workflow); `SIDEBAR_ITEMS` ostaje
      5-elementni tuple (workflow ekrani NISU dodati u sidebar nav).
- [ ] `shell/__init__.py`, `screens/pocetna/`, `screens/brend/`, `screens/kalendar/`,
      `screens/podesavanja/`, `__main__.py`, `static/app.js`, `static/brand-logo.png` NISU DIRANI
      (osim eventualnog minimalnog `render_shell` internog fix-a ako je dokumentovan).
- [ ] `docs/gui-v3/` NIJE DIRAN.
- [ ] Nema izmjena u `domain/`, `application/`, `ports/`, `infrastructure/`, `presentation/`.
- [ ] `--primary` (indigo `#4f46e5`) netaknuto; sve akcije koje NISU eksplicitno navedene kao
      "stvaran link" ostaju `data-action="toast"` (nema tihog wiring-a ka pravim use-case-ima —
      to je budući bridge task).
- [ ] `python -m pytest -q` prolaze svi testovi.
- [ ] `python -m ruff check src tests scripts` i `python -m mypy src` prolaze.
- [ ] `python -m pytest tests/architecture/test_import_boundaries.py -v` prolazi.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest tests/ -q
python -m pytest tests/architecture/test_import_boundaries.py -v
python -m pytest tests/unit/presentation_webview/ -v
python -m ruff check .
python -m mypy src
```

# Vizuelna provjera (obavezna, NE samo testovi)

Implementer MORA pokrenuti aplikaciju (`python -m ai_campaign_studio.presentation_webview`), otići
na Kampanje ekran, kliknuti "Otvori", proći kroz sav 5 koraka stepper-a (Opis → Plan → Kalendar →
Studio → Pregled, koristeći stvarne linkove, ne ručno kucanje URL-a), i na Studio sadržaja ekranu
kliknuti sva 4 taba i potvrditi da se sadržaj mijenja. Screenshot svakog od 4 nova ekrana (4 komada,
Studio sadržaja sa aktivnim jednim od ne-default tabova) priložiti uz evidence izvještaj. **Ako
pywebview nije dostupan u implementer-ovom environment-u (display/WebView2), to eksplicitno
navesti u evidence-u** (koordinator će uraditi live provjeru na Human Owner-ovom ekranu, kao što je
rađeno za ACS-GUI-004) — ali pokušaj MORA biti dokumentovan, ne prećutan.

# Review focus — Claude

- Stepper linkovi tačni na svih 5 stanja (done/active/upcoming) i sva 4 nova ekrana;
- Studio sadržaja koristi STVARAN tab-panel pattern, ne kopiju kozmetičkog mokap markup-a;
- `write_all_pages()` loop za workflow ekrane ne dira postojeći `SIDEBAR_ITEMS` loop niti mijenja
  ponašanje za 5 postojećih ekrana (regresija provjera: postojeći testovi za tih 5 i dalje prolaze
  nepromijenjeni);
- `render_shell(crumbs=...)` pozivi ispravno formatiraju "Kampanje › <naziv> › <ekran>";
- Kampanje "Otvori" real link, ne toast;
- Nema `<a href>` ka nepostojećim putanjama (svaki href mora imati odgovarajući generisan fajl);
- Sve namjerno-toast akcije (Bridge stub dugmad, izvoz, odobri kampanju, sačuvaj nacrt, regeneriši
  plan) ostaju toast — nema tihog wiring-a ka `application/` use-case-ima;
- shell/pocetna/brend/kalendar/podesavanja/`__main__.py`/`static/app.js`/`brand-logo.png`
  netaknuti (git diff scope provjera);
- Screenshot-ovi (4 nova ekrana, uključujući aktivan ne-default Studio tab) priloženi, ili
  eksplicitno navedeno zašto nisu (pywebview environment ograničenje).

# Rollback

MEDIUM risk, izolovana prezentaciona površina. Fix na istoj branch bez proširenja scope-a.

# Coordination

Nezavisno od **ACS-F1-016** (OpenAI adapter, HIGH, u fix rundi) — nema dijeljenih fajlova, može
ići paralelno.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-GUI-003-campaign-workflow-screens
Branch:   task/ACS-GUI-003-campaign-workflow-screens
Base:     main @ c416a58
```
