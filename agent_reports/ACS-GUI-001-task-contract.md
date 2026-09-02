---
task_id: ACS-GUI-001
phase: Faza-1 (post G9)
title: "GUI-BASE: pywebview shell + sidebar navigacija + Početna (fixture-wired)"
risk: MEDIUM
coordinator: claude
implementer: minimax
reviewers: [claude]
status: "OPEN — contract written before code"
created_at: 2026-09-02
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/presentation_webview/
  - tests/unit/presentation_webview/
  - tests/integration/presentation_webview/
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/infrastructure/
  - src/ai_campaign_studio/presentation/
  - src/ai_campaign_studio/ai_registry/
  - src/ai_campaign_studio/channels/
  - src/ai_campaign_studio/localization/
  - src/ai_campaign_studio/jobs/
  - src/ai_campaign_studio/bootstrap.py
  - src/ai_campaign_studio/main.py
  - pyproject.toml
  - docs/gui-v3/
gitnexus_required: true
adversarial_required: false
gitnexus:
  required: true
  repository: "H:\\AI Campaing Studio"
  worktree: main (pre-branch pre-impact)
  branch: main
  head: 70bfa3f
  index_status: fresh (analyze re-run 2026-09-02)
  targets:
    - symbol: "new package presentation_webview/"
      upstream_risk: NONE
      upstream_count: 0
      downstream_notes: "Brand-new package, zero existing importers. Does not touch bootstrap.py/main.py (HIGH-risk files) -- gets its own standalone entrypoint. Reads (does not modify) docs/gui-v3/ as the visual source to port from."
      affected_processes: []
  scope_fit: PASS
  unknowns: []
---

# Kontekst

**G9 (UI Framework Gate) je zatvoren 2026-09-02** — Human Owner je eksplicitno
odlučio zaključati pywebview kao UI framework BEZ formalnog PySide6
poređenja (obrazloženje: SPIKE-001 je uspješno dokazao pywebview + sada
postoji `docs/PYWEBVIEW_SECURITY.md` hardening politika; vidi
`.agent/CURRENT_STATE.md` sekciju "G9 — UI Framework Gate"). Ovo je PRVI
task koji smije praviti production `presentation_webview/` (AR5 je do sada
to zabranjivala). SPIKE-001 (`spike/pywebview-content-studio` grana) ostaje
throwaway prototip — ovaj task ne nastavlja na tom kodu, gradi novi
production paket od nule, ali smije se ugledati na dokazan SSR pattern iz
SPIKE-001 (`presentation_webview/spike_content_studio.py` — BeautifulSoup
injection u statični HTML) kao referencu za implementacionu tehniku.

`docs/gui-v3/` je zaključan kanonski GUI dizajn (vidi `V3_PLAN.md` i
`INTEGRATION.md` u tom direktorijumu — **pročitati oba u cjelosti prije
koda**). Ovaj task je faza "GUI-BASE" iz `V3_PLAN.md`: shell, sidebar,
breadcrumbs, tokens/komponente — plus PRVI stvarno fixture-wired ekran
(Početna) kao referentni pattern za sve buduće ekrane.

**Obavezno pročitati u cjelosti prije koda**: `docs/PYWEBVIEW_SECURITY.md`
(9 sekcija) — ovaj task mora zadovoljiti tačke 1–3 i 6 kao acceptance gate
(vidi ispod), ostatak prema obimu.

**Zašto ne bootstrap.py/main.py**: oba su na HIGH risk listi (registry/
bootstrap kontrakti). Ovaj task dobija SOPSTVENI, potpuno odvojen entrypoint
unutar `presentation_webview/` (npr. `presentation_webview/__main__.py`,
pokreće se sa `python -m ai_campaign_studio.presentation_webview`) — ne
dira postojeći `main.py` čiji docstring eksplicitno kaže "Does not start a
GUI in Phase 0" (ta rečenica ostaje tačna za `main.py` — GUI entry point
živi odvojeno, dok se eksplicitno ne odluči drugačije kroz novi kontrakt).
Smije IMPORTOVATI iz `ai_campaign_studio.bootstrap` (npr. `create_bootstrap`)
ako zatreba, ali ne smije MIJENJATI taj fajl.

**Risk**: MEDIUM. Nova, izolovana prezentaciona površina — nema postojećih
importera, ne dira domain/application/infrastructure/bootstrap. §29
politika: Claude-only review, PASS -> odmah commit/push/merge.

Prije koda pročitati:

```text
AGENTS.md
CLAUDE.md
docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md
.agent/CURRENT_STATE.md (cijela "G9" sekcija + "Sljedeći koraci za GUI")
docs/gui-v3/V3_PLAN.md
docs/gui-v3/INTEGRATION.md
docs/PYWEBVIEW_SECURITY.md (cijeli, 9 sekcija)
AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md
  sekcija 4 AR5, AR6 (presentation_webview granice)
```

Pogledati (ne kopirati slijepo, razumjeti pattern):

```text
H:\ai-campaign-studio-worktrees\SPIKE-001-pywebview-content-studio\
  presentation_webview\spike_content_studio.py  (SSR fixture-injection pattern)
```

# Objective

1. `presentation_webview/shell/` — sidebar/topbar/nav shell koji tačno
   replicira `docs/gui-v3/shared/` dizajn sistem (CSS/JS), portovan u
   package (ne live-referenciran iz `docs/`).
2. Sopstveni entrypoint (`python -m ai_campaign_studio.presentation_webview`)
   koji otvara pravi pywebview prozor, security-hardened po
   `docs/PYWEBVIEW_SECURITY.md` tačkama 1–3, 6.
3. Sidebar navigacija radi za svih 5 destinacija (Početna/Brend/Kampanje/
   Kalendar/Podešavanja) — Brend/Kampanje/Kalendar/Podešavanja mogu biti
   statični passthrough render `docs/gui-v3` ekrana (bez fixture
   injection, samo dokaz da je navigacija ožičena) u OVOM tasku; Početna
   MORA biti puno fixture-wired (vidi tačku 4).
4. `presentation_webview/screens/pocetna/` — Početna ekran, fixture/
   read-model driven (Python fixture data, SSR injection u HTML —
   isti pattern kao `docs/gui-v3` "AKTIVNE KAMPANJE"/"NACRTI"/"Nedavne
   kampanje"/"Zadnje aktivnosti" sekcije, ali sa Python-side podacima, ne
   statičnim brojevima hardkodiranim u HTML-u). Ovo je REFERENTNI pattern
   za sve buduće ekrane (ACS-GUI-002+ ih repliciraju za preostalih 8).

# Implementation steps

## Sigurnost (obavezno, `docs/PYWEBVIEW_SECURITY.md` tačke 1–3, 6)

- Entrypoint eksplicitno poziva `webview.start(gui='edgechromium', debug=False, ...)`.
  Ako WebView2 Runtime nije prisutan, `edgechromium` bira da GLASNO padne
  (exception/jasna poruka), NE da tiho pređe na `mshtml`. Napisati malu
  provjeru prije `webview.start()` (npr. detekcija WebView2 registry ključa
  ili hvatanje specifičnog pywebview exception-a) koja korisniku ispiše
  jasnu poruku + uputstvo da instalira WebView2 Runtime, umjesto sirovog
  Python traceback-a.
- `js_api` — u OVOM tasku vjerovatno NIJE potreban nikakav bridge (Početna
  je čisto prikaz, nema interaktivnih AI/write akcija). Ako implementer
  ipak doda `js_api` klasu (npr. za buduću ekstenziju), ona MORA biti uska,
  imenovana, i svaka metoda mora imati docstring — bez izuzetka, čak i ako
  je prazna/placeholder. Ako nije potrebna, NE dodavati "za svaki slučaj".
- Nema `target="_blank"` eksternih linkova u `docs/gui-v3` trenutno — ako
  se ijedan doda pri portovanju, mora imati `target="_blank"`.

## `presentation_webview/shell/`

Portovati `docs/gui-v3/shared/app.css` i `shared/app.js` u
`presentation_webview/static/` (kopija, ne symlink/live-read iz `docs/`
— `docs/gui-v3/` je dizajn referenca, production paket nosi svoju kopiju).
Shell HTML template (sidebar + topbar + content slot) izveden iz
zajedničkog markup obrasca koji se ponavlja u svih 9 `docs/gui-v3/screens/*/
index.html` fajlova (isti sidebar/topbar u svakom) — DRY-ovati u shell
template umjesto kopiranja tog bloka po ekranu (V3_PLAN već kaže "ekrani
ne dupliraju production business logiku" — ovo je analogno za markup).

## Entrypoint

`presentation_webview/__main__.py` (ili `app.py` + tanak `__main__.py`) —
parsira minimalne CLI opcije po uzoru na `main.py` obrazac (npr.
`--width`/`--height`, konzistentno sa postojećim stilom), gradi prozor,
poziva `webview.start(...)`.

## `presentation_webview/screens/pocetna/`

Python fixture data (npr. `fixture_data.py` — plain dict/dataclass, NE
Pydantic ovdje, ovo nije domain granica, samo lokalni prezentacioni
placeholder dok pravi `PresentationFacade`/use-case ne postoji) sa istim
poljima koje `docs/gui-v3/screens/01_pocetna/index.html` već prikazuje:
broj aktivnih kampanja, objava u planu, nacrta, odobrenih; lista nedavnih
kampanja (naziv + status badge); lista zadnjih aktivnosti (tekst + vrijeme).
SSR injection u HTML template (BeautifulSoup ili ekvivalent — pattern iz
SPIKE-001) prije nego se prosljedi `webview.create_window(url=...)`.

# Acceptance

- [ ] `webview.start(gui='edgechromium', debug=False, ...)` eksplicitno u
      kodu (ne oslanjanje na default) — test/code-review provjerava
      doslovno prisustvo oba argumenta.
- [ ] WebView2 Runtime odsustvo rezultira jasnom, korisniku čitljivom
      greškom (ne sirov traceback, ne tihi fallback na `mshtml`) — dokazano
      test-om koji simulira/mock-uje odsustvo (ne zahtijeva stvarno
      deinstaliranje Runtime-a na CI mašini).
- [ ] Ako `js_api` postoji: svaka metoda ima docstring, klasa je uska i
      imenovana (ne generic "Api"/"Bridge" grab-bag). Ako ne postoji —
      eksplicitno navesti u evidence izvještaju da nije bio potreban.
- [ ] Sidebar navigacija: klik na svih 5 stavki (Početna/Brend/Kampanje/
      Kalendar/Podešavanja) mijenja prikazani sadržaj (dokazano ručnim
      testiranjem u pokrenutom prozoru — evidence izvještaj mora sadržati
      screenshot ili jasan opis šta je isprobano, ne samo tvrdnju).
- [ ] Početna ekran prikazuje Python fixture podatke (ne hardkodirani
      HTML) — promjena vrijednosti u `fixture_data.py` mora se odraziti u
      prikazu (test dokazuje kroz SSR output, ne kroz stvarni prozor).
- [ ] `presentation_webview/static/` je kopija `docs/gui-v3/shared/`
      sadržaja, ne referenca — `docs/gui-v3/` ostaje netaknut
      (`forbidden_paths`).
- [ ] Shell markup (sidebar/topbar) je DRY-ovan u shared template, nije
      kopiran po ekranu.
- [ ] `main.py`, `bootstrap.py`, `pyproject.toml` nisu dirani.
- [ ] `python -c "import ai_campaign_studio"` i dalje radi (novi paket ne
      kvari postojeći import graf).
- [ ] `python -m pytest -q`, `ruff check .`, `mypy src` prolaze (novi
      paket uključen u provjere).
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest -q
python -m pytest tests/unit/presentation_webview tests/integration/presentation_webview -v
python -m ruff check .
python -m mypy src
python -m ai_campaign_studio.presentation_webview   # ručna provjera: prozor se otvara, edgechromium, nav radi
```

# Review focus — Claude

- `gui='edgechromium'` + `debug=False` doslovno u kodu, WebView2-odsustvo
  je glasna greška, ne tihi fallback (ovo je JEDINI najvažniji nalaz iz
  `docs/PYWEBVIEW_SECURITY.md` — provjeriti pažljivo);
- nema `js_api` metoda koje vraćaju sekrete ili primaju neprovjerene
  putanje/komande (ako bridge uopšte postoji u ovom tasku);
- `presentation_webview/` ne importuje ništa iz `domain/`, `application/`,
  `ports/`, `infrastructure/` (fixture-only u ovoj fazi — provjeriti kroz
  `tests/architecture/test_import_boundaries.py`, proširiti taj test ako
  ne već pokriva novi paket);
- `docs/gui-v3/` zaista netaknut (git diff dokazuje);
- shell markup DRY, ne copy-paste po ekranu;
- evidence izvještaj sadrži stvaran dokaz da je prozor otvoren i
  navigacija isprobana (screenshot ili detaljan opis), ne samo "radi".

# Rollback

MEDIUM risk, izolovan novi paket bez postojećih importera. Fix na istoj
branch bez proširenja scope-a. STOP i vrati na puni ciklus ako task pokaže
potrebu da dira `bootstrap.py`/`main.py`/`pyproject.toml` — to zahtijeva
redefinisan kontrakt.

# Coordination

Nezavisno od **ACS-F1-003** (Pi) i **ACS-F1-004** (Crush) — potpuno
disjoint `allowed_paths`, nema zavisnosti, sva tri taska mogu ići paralelno
odmah. Slijedeći GUI task (ACS-GUI-002, preostalih 8 ekrana) čeka da se
ovaj task merge-uje i review-uje — service kao referentni pattern.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-GUI-001-gui-base-shell
Branch:   task/ACS-GUI-001-gui-base-shell
Base:     main @ 70bfa3f
```
