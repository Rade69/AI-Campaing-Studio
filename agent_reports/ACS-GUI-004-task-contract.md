---
task_id: ACS-GUI-004
phase: Faza-1 (post G9, post ACS-GUI-002)
title: "GUI-BASE: port mokap tab design (button-style + real panel switching) iz docs/gui-v3 u presentation_webview"
risk: MEDIUM
coordinator: claude
implementer: crush
reviewers: [claude]
status: "DONE — merged"
created_at: 2026-09-03
dependencies:
  - ACS-GUI-001 (merged, main @ cad003e) — shell + Početna
  - ACS-GUI-002 (merged, main @ 99f3502) — Brend/Kampanje/Kalendar/Podešavanja fixture-wired
allowed_paths:
  - src/ai_campaign_studio/presentation_webview/static/app.css
  - src/ai_campaign_studio/presentation_webview/static/app.js
  - src/ai_campaign_studio/presentation_webview/screens/brend/__init__.py
  - src/ai_campaign_studio/presentation_webview/screens/podesavanja/__init__.py
  - tests/unit/presentation_webview/test_brend_ssr.py
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
  - src/ai_campaign_studio/presentation_webview/screens/kampanje/
  - src/ai_campaign_studio/presentation_webview/screens/kalendar/
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
  head: 7709ee3
  index_status: fresh (analyze re-run 2026-09-03 post FLOW-1001 merge)
  targets:
    - symbol: "src/ai_campaign_studio/presentation_webview/static/app.css"
      upstream_risk: LOW
      upstream_count: "Single shared stylesheet. Currently has OLD V3 underline-tab CSS (.tabs{border-bottom;...} .tab{border-bottom:2px solid transparent}). This task REPLACES that block with button-style tabs from mokap. Other CSS rules must stay byte-identical except for the targeted replacements listed in Implementation steps."
      downstream_notes: "Imported by all 5 screens via shell/__init__.py. No other importers."
      affected_processes: []
    - symbol: "src/ai_campaign_studio/presentation_webview/static/app.js"
      upstream_risk: LOW
      upstream_count: "Single shared script. Currently has only .active toggle for tabs (no panel switching). This task ADDS data-tab-target → data-tab-panel switching logic, keeping the existing toast + .active-toggle code intact."
      downstream_notes: "Imported by shell. No other importers."
      affected_processes: []
    - symbol: "src/ai_campaign_studio/presentation_webview/screens/brend/__init__.py"
      upstream_risk: LOW
      upstream_count: "Currently emits 1 grid with 2 cards (brand info + facts) plus 3-card resource row. This task WRAPS each logical section in a data-tab-panel div keyed to one of 4 tabs, so the new JS can show/hide. Fixture dataclass structure is unchanged; only render_body() output structure changes."
      downstream_notes: "Imported by screens/_static_pages.py (importlib). No other importers."
      affected_processes: []
    - symbol: "src/ai_campaign_studio/presentation_webview/screens/podesavanja/__init__.py"
      upstream_risk: LOW
      upstream_count: "Currently emits 2-col grid: left card with 3 tabs, right card with single AI-provajderi panel. This task WRAPS the right card in 3 data-tab-panel divs (Opšte placeholder, Jezik placeholder, AI provajderi real). Left card tabs get data-tab-target attrs."
      downstream_notes: "Imported by screens/_static_pages.py (importlib). No other importers."
      affected_processes: []
  scope_fit: PASS
  unknowns: []
---

# Kontekst

Treći GUI task nakon ACS-GUI-001 (shell + Početna, merged `cad003e`) i
ACS-GUI-002 (Brend/Kampanje/Kalendar/Podešavanja fixture-wired, merged
`99f3502`). GUI design brief `_2026-09-02-GUI-design-brief-za-minimax.md`
je u mokapu (`docs/gui-v3/`) iterirao na **pravom tab-panel switching**:
button-style tabovi sa `data-tab-target="<id>"` + `<div data-tab-panel
id="<id>">` panelima, klik mijenja `.active` klasu I
show/hide panel preko `p.hidden = (p.id !== target)`. Produkcioni
`presentation_webview/` **nikad nije primio taj update** — ACS-GUI-002
je kopirao markup iz mokapa ali sa starim underline-CSS-om i bez
`data-tab-panel` logike u `app.js`. Korisnik je 2026-09-03 potvrdio
problem screenshot-om: tabovi izgledaju kao underline tekst i klik ne
mijenja sadržaj.

**Obavezno pročitati prije koda**:

```text
docs/gui-v3/V3_PLAN.md
docs/gui-v3/INTEGRATION.md
docs/gui-v3/shared/app.css                        (.tabs / .tab / .tabs-vertical CSS — SOURCE OF TRUTH)
docs/gui-v3/shared/app.js                         (tab handler + data-tab-panel logika — SOURCE OF TRUTH)
docs/gui-v3/screens/02_brend/index.html           (4 taba → 4 panela, tačan markup)
docs/gui-v3/screens/09_podesavanja/index.html     (3 vertikalna taba → 3 panela, tačan markup)
agent_reports/ACS-GUI-001-task-contract.md        (shell + write_all_pages pattern)
agent_reports/ACS-GUI-002-task-contract.md        (fixture-dataclass + render_body pattern)
agent_reports/2026-09-02-GUI-design-brief-za-minimax.md (zašto tab switching uopšte)
```

Pogledati postojeći kod da razumiješ TAČAN pattern (ne izmišljati novi):

```text
src/ai_campaign_studio/presentation_webview/shell/__init__.py
  (render_shell, NE DIRATI — sidro koje drži sidebar/topbar/content)
src/ai_campaign_studio/presentation_webview/static/app.js
  (trenutni tab handler je samo .active toggle, TREBA proširiti)
src/ai_campaign_studio/presentation_webview/screens/brend/__init__.py
  (trenutni render_body() emitira 1 grid + 3-card resursi — WRAPPATI u 4 panela)
src/ai_campaign_studio/presentation_webview/screens/podesavanja/__init__.py
  (trenutni render_body() emitira 2-col grid sa 1 panelom — WRAPPATI u 3 panela)
tests/unit/presentation_webview/test_brend_ssr.py
  (NE DIRAJ test_changing_fixture_changes_rendered_body i ostale fixture testove —
   oni testiraju renderiranu HTML, koja se mijenja. Ako tvoje strukturne promjene
   razbiju njihov output assertion, UPDATE-UJ te testove tako da očekuju NOVU
   strukturu sa data-tab-panel atributima. NE MIJENJAJ smisao testa.)
tests/unit/presentation_webview/test_podesavanja_ssr.py
  (isto kao gore)
```

**Risk**: MEDIUM — izolovana prezentaciona površina, ista klasa rizika
kao ACS-GUI-001/002. §29: Claude-only review, PASS → odmah merge.

# Objective

Portati dizajn taba iz `docs/gui-v3/` (button-style + real panel
switching) u `src/ai_campaign_studio/presentation_webview/`. Rezultat:
klik na bilo koji tab (Brend: 4 taba, Podešavanja: 3 vertikalna taba)
mijenja prikazani panel sa stvarnim sadržajem, ne samo `.active` klasu.

## CSS port (`static/app.css`)

Zamijeni **CIJELI** postojeći `.tabs{...}` i `.tab{...}` + `.tab.active{...}`
blok sa mokap verzijom (izvor: `docs/gui-v3/shared/app.css`). Konkretno:

```text
PRIJE (stari V3 underline):
  .tabs{display:flex;gap:4px;border-bottom:1px solid var(--line);margin-bottom:18px}
  .tab{padding:10px 12px;font-size:13px;font-weight:700;color:#64748b;border-bottom:2px solid transparent}
  .tab.active{color:#4338ca;border-color:#4f46e5}

POSLIJE (mokap button-style, kopiraj verbatim):
  .tabs{display:flex;gap:6px;margin-bottom:18px;flex-wrap:wrap}
  .tabs.tabs-vertical{flex-direction:column;align-items:stretch;gap:8px}
  .tabs.tabs-vertical .tab{justify-content:flex-start;width:100%}
  .tab{display:inline-flex;align-items:center;justify-content:center;padding:10px 16px;font-size:13px;font-weight:700;color:var(--muted);background:#fff;border:1px solid var(--line);border-radius:9px;cursor:pointer;transition:all .15s;font-family:inherit;line-height:1.1}
  .tab:hover{background:#f8fafc;color:var(--text);border-color:var(--primary)}
  .tab.active{background:var(--primary);border-color:var(--primary);color:#fff;box-shadow:0 1px 2px rgba(79,70,229,.25)}
  .tab.active:hover{background:var(--primary2);border-color:var(--primary2);color:#fff}
```

**VAŽNO** — boja aktivnog taba koristi `var(--primary)`. Produkcioni
`--primary` je trenutno **indigo `#4f46e5`**. NE MIJENJAJ `--primary`
u produkciji (to je scope creep — emerald paleta pripada zasebnom
tasku, ne ovom). Ako korisnik želi emerald, to je budući ACS-GUI-005
ili slično. U ovom tasku prihvatiti indigo.

## JS port (`static/app.js`)

Proširi postojeći `if(action==='tab')` blok (trenutno samo .active
toggle, linija 6) sa `data-tab-target` → `data-tab-panel` logikom
iz mokapa. Konkretno, zamijeni CIJELI handler sa mokap verzijom:

```js
if(action==='tab') {
  const group=el.closest('[data-tabs]');
  group.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));
  el.classList.add('active');
  const target=el.dataset.tabTarget;
  if(target){
    const panels=document.querySelectorAll('[data-tab-panel]');
    panels.forEach(p=>{p.hidden=(p.id!==target);});
  }
}
```

Toast handler (`showToast` i `data-action="toast"`) i
`?campaign=` query handler (linije 10-17) ostaju **netaknuti**.

## Brend screen (`screens/brend/__init__.py`)

Trenutni `render_body()` emituje:
- page-head sa statuslinijom
- 4 `<div class="tab">` labela (još nema `data-tab-target`)
- 1 `<div class="grid g2">` sa 2 kartice (brand info + facts)
- 1 `<div class="section-title">` sa "Brend resursi" + dugme
- 1 `<div class="grid g3">` sa 3 resursa

**Potrebna promjena**: zamotati 4 logičke cjeline u `<div data-tab-panel
id="panel-X">` kontejnere, sa `data-tab-target="panel-X"` na
odgovarajućem tab labelu.

Konkretna podjela sadržaja (prema mokapu):

| Tab | Panel id | Sadržaj |
|---|---|---|
| Osnovni podaci | `panel-osnovni` | brand info kartica (ime, opis, publika, glas) — DIO STAROG GRIDA |
| Odobrene činjenice | `panel-cinjenice` | facts kartica — DIO STAROG GRIDA |
| Glas brenda | `panel-glas` | (placeholder za budući voice workspace — "Dostupno u narednoj verziji" callout, ISTI ton kao prazni paneli u mokapu) |
| Brend resursi | `panel-resursi` | 3 resurs kartice + section-title |

Prva dva (osnovni, cinjenice) su **dijelovi istog starog grida** —
zato taj grid MORA biti podijeljen na 2 panela (svaki sadrži jednu
karticu), a ne 1 grid sa 2 kartice. NEMA više jednog grida sa 2
kolone. Također, `<div class="grid g2">` → svaki panel koristi svoj
wrapper.

Ostali paneli (cinjenice, glas, resursi) NE SMIJU imati `hidden`
atribut — `data-tab-panel` + `id` je dovoljno. Samo oni koji NISU
default-active imaju `hidden`. Default-active je prvi (`panel-osnovni`),
pa on nema `hidden`, ostali imaju.

**Fixture struktura se NE MIJENJA** — `BrendFixture`, `BrandInfo`,
`VoiceBadge`, `ApprovedFact`, `BrandResource`, `DEFAULT_FIXTURE` ostaju
identični. Mijenja se samo `render_body()` output struktura.

## Podešavanja screen (`screens/podesavanja/__init__.py`)

Trenutni `render_body()` emituje:
- page-head
- 2-col grid: lijevi card sa 3 tab labela, desni card sa 1 panelom
  (samo AI provajderi)

**Potrebna promjena**: desni card postaje wrapper sa 3
`data-tab-panel` divovima. Svaki tab label dobija `data-tab-target`.

Konkretna podjela:

| Tab | Panel id | Sadržaj |
|---|---|---|
| Opšte | `panel-opste` | placeholder: "Opšte postavke — dostupno u narednoj verziji" (callout, isti ton kao pjesnici u mokapu) |
| Jezik | `panel-jezik` | placeholder: "Jezik sadržaja — dostupno u narednoj verziji" |
| AI provajderi | `panel-provajderi` | REALAN sadržaj: 6 provider-a + production callout (kao dosad) |

Trenutni `.tab` divovi imaju inline `style="display:block;border:0;margin:0"`
da bi se ponašali kao vertikalna lista. To treba UKLONITI — sada koriste
`tabs-vertical` klasu sa `display:flex; flex-direction:column;` (CSS
pravilo iz mokapa). Inline `style` se mijenja u `class="tabs tabs-vertical"`.

Provider lista (`_provider_row` helper) i `Provider`/`PodesavanjaFixture`
fixture struktura ostaju identični.

# Implementation steps

1. **CSS port**: u `static/app.css`, zamijeni 3 stara CSS pravila
   (`.tabs{...}`, `.tab{...}`, `.tab.active{...}`) sa 7 novih pravila
   iz mokapa (verbatim, uključujući `.tabs.tabs-vertical` i
   `.tabs.tabs-vertical .tab` varijante).

2. **JS port**: u `static/app.js`, zamijeni `if(action==='tab') { ... }`
   blok (linija 6) sa proširenom verzijom koja radi i `.active` toggle
   I `data-tab-target` panel switching.

3. **Brend screen**:
   - U `render_body()`, dodaj `data-tab-target="panel-X"` na svaki
     `<div class="tab">` (label 0..3)
   - Zamijeni trenutni `<div class="grid g2">...</div>` (koji ima 2
     kartice) sa **2 odvojena** `<div data-tab-panel id="..." hidden>`
     kontejnera (jedan sa brand info karticom, drugi sa facts
     karticom)
   - Dodaj 2 nova panel kontejnera: `panel-glas` (placeholder
     callout) i `panel-resursi` (section-title + 3 resurs kartice —
     premjestiti IZ starog layouta)
   - `panel-osnovni` je default-active (nema `hidden`), ostali imaju
     `hidden`

4. **Podešavanja screen**:
   - U `_settings_tabs()`, dodaj `data-tab-target="panel-X"` na svaki
     tab div, i PROMIJENI inline `style="display:block;border:0;margin:0"`
     u `class="tabs tabs-vertical"`
   - U `render_body()`, zamijeni jedan panel (desni card) sa 3
     `data-tab-panel` divovima (panel-opste placeholder, panel-jezik
     placeholder, panel-provajderi real)
   - `panel-provajderi` je default-active (nema `hidden`), ostali imaju
     `hidden`

5. **Test update** (u `test_brend_ssr.py` i `test_podesavanja_ssr.py`):
   - Ako postojeći testovi provjeravaju output render_body() sa
     starom strukturom (npr. "ima 1 grid g2 sa 2 kartice"), update-uj
     te provjere da odgovaraju NOVOJ strukturi (4 data-tab-panel
     kontejnera za Brend, 3 za Podešavanja). Fixture testovi MORAJU
     i dalje prolaziti.
   - DODAJ nove testove:
     - "Brend: 4 taba imaju data-tab-target atribute"
     - "Brend: 4 panela sa data-tab-panel atributima postoje"
     - "Brend: samo panel-osnovni nema hidden atribut (default-active)"
     - "Podešavanja: 3 taba imaju data-tab-target atribute"
     - "Podešavanja: 3 panela sa data-tab-panel atributima"
     - "Podešavanja: samo panel-provajderi nema hidden (default-active)"

# Acceptance

- [ ] Klik na bilo koji Brend tab (4 komada) mijenja vidljivi panel
      (vizuelno provjeriti u pywebview prozoru, NE samo test assertion).
- [ ] Klik na bilo koji Podešavanja tab (3 komada, vertikalna lista)
      mijenja vidljivi panel.
- [ ] Brend tab-ovi izgledaju kao button-i (border, background, hover,
      active stanje) — NE underline.
- [ ] Podešavanja tab-ovi izgledaju kao button-i, vertikalno poravnati,
      cijelom širinom lijevog carda.
- [ ] Sva 4 Brend panela imaju SVE fixture podatke (brand info, facts,
      glas, resursi) i renderiraju se u DOM-u (samo `hidden` atribut
      se mijenja).
- [ ] Sva 3 Podešavanja panela prisutna u DOM-u (placeholder-i za
      Opšte/Jezik sa "Dostupno u narednoj verziji" callout-om, AI
      provajderi pun).
- [ ] `app.js` `data-action="tab"` handler sada radi I .active toggle
      I `data-tab-target` panel switching.
- [ ] `app.js` toast + `?campaign=` logika netaknuta (nema regresije).
- [ ] `shell/__init__.py`, `screens/__init__.py`,
      `screens/_static_pages.py`, `screens/pocetna/`,
      `screens/kampanje/`, `screens/kalendar/`, `__main__.py` NISU
      DIRANI (git diff provjera).
- [ ] `docs/gui-v3/` NIJE DIRAN (mokap referenca, source of truth za
      dizajn — ne modificirati).
- [ ] Nema izmjena u `domain/`, `application/`, `ports/`,
      `infrastructure/`, `presentation/` (van presentation_webview/).
- [ ] `--primary` u `:root` OSTAJE indigo `#4f46e5` — ne miješati
      emerald promjenu u ovaj task.
- [ ] `.brand-logo` pravilo (kanonski sidebar logo block na dnu
      `app.css`) NETAKNUTO.
- [ ] `python -m pytest -q` prolaze svi testovi uključujući
      `test_brend_ssr.py` i `test_podesavanja_ssr.py` (sa update-ima
      iz Implementation step 5).
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] `python -m pytest tests/architecture/test_import_boundaries.py
      -v` prolazi.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest tests/ -q
python -m pytest tests/architecture/test_import_boundaries.py -v
python -m pytest tests/unit/presentation_webview/test_brend_ssr.py tests/unit/presentation_webview/test_podesavanja_ssr.py -v
python -m ruff check .
python -m mypy src
```

# Vizuelna provjera (obavezna, NE samo testovi)

Implementer MORA pokrenuti aplikaciju (`python -m
ai_campaign_studio.presentation_webview --width 1440 --height 860`,
sa `PYTHONPATH=src`), otići na Brend ekran, kliknuti SVA 4 taba i
potvrditi da se sadržaj mijenja. Isto za Podešavanja (3 vertikalna
taba). Screenshot jednog aktivnog stanja za svaki ekran (4+3=7
screenshot-ova) priložiti uz evidence izvještaj. Bez vizuelne
potvrde task se NE SMIJE proglasiti PASS-om.

# Review focus — Claude

- `data-tab-target` ↔ `data-tab-panel` ID matching je potpuno
  konzistentan (svaki target ima odgovarajući panel, nema
  dangling ID-ova, nema duplikata);
- `.tabs-vertical` klasa pravilno primijenjena u Podešavanja
  (zamijenio inline `style` iz starog koda);
- Brend: 2-kartica grid podijeljen na 2 panela, NE dupliciran
  sadržaj;
- placeholder-i za prazne panele (Glas brenda, Opšte, Jezik) imaju
  isti ton kao mokap referenca (callout stil, ne prazan div);
- nema `<a href>` ka nepostojećim ekranima;
- `app.js` toast + `?campaign=` netaknuto (diff samo u `tab` handler
  bloku);
- shell/pattern/početna/kampanje/kalendar statički netaknuti (git
  diff scope provjera);
- 7 screenshot-ova (4 Brend + 3 Podešavanja) priloženi.

# Rollback

MEDIUM risk, izolovana prezentaciona površina. Fix na istoj branch
bez proširenja scope-a.

# Coordination

Disjoint od **FLOW-1002** (provider config persistence) i
**FLOW-1003** (OpenAI adapter) koji su u toku — nema dijeljenih
fajlova. Može ići paralelno s njima.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-GUI-004-tab-panel-switching
Branch:   task/ACS-GUI-004-tab-panel-switching
Base:     main @ 7709ee3
```

**NAPOMENA** — Implementer NE SMIJE miješati emerald paletu
(`--primary: #10b981`) u ovaj task. Ako korisnik naknadno zatraži
emerald, to ide u zaseban ACS-GUI-005 ili sličan task. Ovaj task
prenosi DIZAJN (button-style + switching) a NE PALETU.

# Post-hoc scope napomena (2026-09-03, Human Owner odobrio u review-u)

Implementacija je odstupila od kontrakta na dva mjesta, oba naknadno
odobrena od strane Human Owner-a tokom koordinator review-a (ne
tiho — eksplicitno pitano i potvrđeno):

1. **CSS nije bio uska zamjena** — kontrakt je tražio zamjenu tačno 3
   `.tabs`/`.tab`/`.tab.active` pravila, "ostatak byte-identical".
   Implementacija je uradila širi density/spacing rewrite
   (`.nav`, `.topbar`, `.content`, `.page-head`, `.card`, `.metric`,
   `.section-title`, `.row`, `.field`, `.callout`, `.provider`,
   kalendar `.day`) koji utiče na sve ekrane (dijeljeni `app.css`).
   Human Owner je ovo tražio ranije u sesiji ("previše skrola,
   paneli nekonzistentni") — koordinator retroaktivno potvrdio scope.
   `--primary` (indigo `#4f46e5`) OSTAO netaknut kako je i traženo.
2. **Language picker (SR/HR/BS/EN) u Podešavanja → Jezik** nije bio u
   originalnom kontraktu (Jezik je trebao biti prazan placeholder).
   Human Owner potvrdio da je ovo njegov zahtjev; implementacija
   ostaje čisto UI (toast + active state), ne vezuje se na
   `PresentationFacade.set_app_locale()`.

Implementer u evidence izvještaju potpisan kao "Crush" (kontrakt je
originalno pisao "minimax" kao planirani implementer) — koordinator
je uskladio `implementer:` polje sa stvarnim stanjem.
