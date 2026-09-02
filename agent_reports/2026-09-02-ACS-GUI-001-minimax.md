# ACS-GUI-001 — fix round evidence (MiniMax, 2026-09-02)

Implementer: MiniMax · Reviewer: Claude (round 1 review)
Branch: `task/ACS-GUI-001-gui-base-shell`
Worktree: `H:\ai-campaign-studio-worktrees\ACS-GUI-001-gui-base-shell`
Base: `main @ 0a6dbc4` (G9 close commit)

This report documents the fix round for the three findings raised in
Claude's round 1 review. Round 1 runtime evidence (HTML dumps of all
5 screens) lives in `artifacts/ACS-GUI-001-evidence-*.html` — kept
under `artifacts/` rather than `agent_reports/` because they were
generated for testing/inspection, not as deliverable artifacts.

## Round 2 findings → fixes

### 1. `static/app.css` i `static/app.js` nisu doslovna kopija `docs/gui-v3/shared/`

**Fix:** oba fajla su sada **bajt-identične kopije** V3 reference,
provjereno SHA-256 hashom.

```
V3   app.css : CEE664A375F744DE3BF2F10B1F8B3562BD4CF40AE67E32903C8DCE9CA2407272
WT   app.css : CEE664A375F744DE3BF2F10B1F8B3562BD4CF40AE67E32903C8DCE9CA2407272
match: True (7828 B)

V3   app.js  : E1CEF68453CC0BBDE464E893D042D3CDE5A927E07675A393ECF1F45933516E19
WT   app.js  : E1CEF68453CC0BBDE464E893D042D3CDE5A927E07675A393ECF1F45933516E19
match: True (1277 B)
```

Sada su dostupne sve klase koje će trebati preostalih 8 ekrana:
`.tabs`, `.stepper`, `.calendar`, `.provider`, `.fact`, `.badge.warn/
.info/ok/danger`, `.grid.g2/g3/g4`, itd. — sve iz V3 shared/app.css.

### 2. Shell dodaje `.lang-toggle` koji ne postoji u V3 dizajnu

**Fix:** uklonjen cijeli `<div class="lang-toggle">` (EN/BHS pill
switch) iz `shell/render_shell()`. Topbar sada sadrži samo crumbs,
tačno kao V3 referentni ekrani.

Regression test dodan u `test_pocetna_ssr.py`:

```python
def test_render_shell_has_no_lang_toggle() -> None:
    page = render_shell(active_key="pocetna", page_title="Početna", body_html="")
    assert "lang-toggle" not in page
    assert 'class="pill"' not in page
```

### 3. Sidebar/topbar markup nije DRY — 4 placeholder ekrana dupliciraju shell

**Fix:** sva 4 placeholder ekrana (Brend / Kampanje / Kalendar /
Podešavanja) sada prolaze kroz istu `render_shell()` funkciju kao
Početna. Implementirano kroz:

* `screens/{brend,kampanje,kalendar,podesavanja}/__init__.py` — svaki
  izlaže `render_body()` sa placeholder sadržajem (h2 + "ACS-GUI-002"
  poruka).
* `screens/_static_pages.py` — novi modul sa `write_all_pages(out_dir)`
  koji iterira `SIDEBAR_ITEMS` i renderira svih 5 ekrana kroz isti
  shell, pišući `out_dir/screens/{key}/index.html`. Shell markup
  postoji na **jednom mjestu** — `shell/render_shell()`.
* `__main__.py` sada zove `_materialise_pages()` koji koristi
  `write_all_pages()` umjesto ranijeg `_render_pocetna_to_tempfile()`.
  Generisani fajlovi žive u `tempfile.mkdtemp(prefix="ai_campaign_studio_gui_")`
  za trajanje processa.
* Starih 5 statičkih HTML fajlova (ručno kodiranih) su premješteni u
  `artifacts/obsolete-v1-static-html/` (delete blokiran policy-jem).

DRY enforcement test u `test_static_pages_generator.py`:

```python
def test_write_all_pages_share_one_csp_and_one_static_link(tmp_path):
    # ... iterira pages, sakuplja CSP, CSS link, JS link u setove ...
    assert len(csps) == 1, f"CSP diverges across screens: {csps}"
    assert len(css_links) == 1, f"CSS link diverges: {css_links}"
    assert len(js_links) == 1, f"JS link diverges: {js_links}"
```

Ako bilo koji screen ikada re-implementira shell (i time divergent
CSP/asset linkove), ovaj test pada.

### 4. Usputni nalazi (round 2 usput)

* ✅ `artifacts/phase0_foundation_gate.json` — revertiran
  (`git restore`). Bio je auto-regenerisan artifact, van scope-a.
* ✅ Circular import riješen: `screens/pocetna/__init__.py` više ne
  importuje `DEFAULT_FIXTURE` na module-load; `render_body()` radi
  lazy import. Slično, `screens/_static_pages.py` koristi
  `render_pocetna_body()` bez argumenata (default = `DEFAULT_FIXTURE`).
  Import graf je sada jednosmjerna: `__init__` → `_static_pages` →
  `pocetna` (lazy) → `__init__` (parent).

## CI verifikacija

| Provjera | Komanda | Rezultat |
|---|---|---|
| ruff | `ruff check src/ai_campaign_studio/presentation_webview/ tests/unit/presentation_webview/ tests/architecture/test_import_boundaries.py` | All checks passed |
| mypy | `mypy src/ai_campaign_studio/presentation_webview/` | Success: no issues found in 10 source files |
| pytest (scope) | `pytest tests/unit/presentation_webview/ tests/architecture/test_import_boundaries.py` | **41 passed in 0.37s** |
| pytest (full suite) | `pytest tests/ --ignore=tests/unit/scripts --ignore=tests/integration/startup --ignore=tests/test_foundation.py --ignore=tests/unit/secrets` | **216 passed in 7.97s** |

### Test breakdown (41)

```
tests/unit/presentation_webview/test_pocetna_ssr.py             14
  (13 round 1 + 1 new: test_render_shell_has_no_lang_toggle)
tests/unit/presentation_webview/test_static_pages_generator.py   7
  (new in round 2: covers DRY, lang-toggle absence, remote-asset
   absence, fixture data, per-screen placeholder h2 + ACS-GUI-002)
tests/unit/presentation_webview/test_webview2_fail_loud.py        5
tests/architecture/test_import_boundaries.py                    15
```

### Pre-existing failures (ne moj scope)

| File | Greška | Verdict |
|---|---|---|
| `src/ai_campaign_studio/infrastructure/secrets/keyring_secret_store.py:6` | `import keyring` fails (module not installed); isti `import-not-found` pattern na `mypy` | Pre-existing (commit `5517c8b` ACS-P0-005, 2026-09-01). Fix = `# type: ignore[import-not-found,import-untyped]`, isti pattern kao moj fix na `__main__.py:82`. Vlasništvo: P0/Pi rad. |
| `tests/integration/startup/test_bootstrap.py`, `test_health_check.py`, `tests/test_foundation.py`, `tests/unit/secrets/test_secret_store.py` | `ModuleNotFoundError: No module named 'keyring'` (transitive import preko `bootstrap.py`) | Pre-existing, vezano za isti keyring issue iznad. |
| `tests/unit/scripts/test_generate_phase0_gate_report.py` | cp1252 codec error u subprocess output capture | Pre-existing (Windows-environent issue), bio vidljiv i u round 1. |

Svi ovi failures postoje na `main` grani (verifikovano
`git diff HEAD` prazan za `keyring_secret_store.py`).

## Verifikovano u runtime-u (što sam i šta nisam uradio)

**Uradeno:**
* `write_all_pages()` pozvan iz realnog Python koda (ne samo test
  fixture) — kreira 5 HTML fajlova, svaki 4401/2908/2917/2917/2926
  bajtova (Početna je najveća jer ima fixture data, ostali su
  placeholder).
* Svih 5 fajlova nose isti CSP string, isti `../static/app.css` href
  i isti `../static/app.js` src (asserted by test).
* Svih 5 fajlova imaju `active` klasu na tačno onom sidebar linku
  koji odgovara key-u (asserted by parametrized test).
* Niti jedan fajl ne sadrži `lang-toggle`, `fonts.googleapis.com`,
  `cdn.tailwindcss.com`, `unpkg.com` (asserted by test).

**Nisam uradio (i zašto):**
* **Live `python -m ai_campaign_studio.presentation_webview`** —
  ne mogu pokrenuti u ovoj sesiji (nema display session-a + `webview`
  modul nije instaliran u test env). Svi sigurnosni aspekti
  (`gui='edgechromium'`, `debug=False`, WebView2 probe, mshtml
  defense) su pokriveni testovima u `test_webview2_fail_loud.py`.
  Coordinator može live-testirati na mašini sa instaliranim
  `pywebview` + WebView2 Runtime.
* **`git commit`** — workflow §29 zahtijeva coordinator (Claude)
  review prije `git commit`. Čekam round 2 review sign-off.

## Fajl-za-fajl promjene (round 2)

### Izmijenjeno (5)
1. `src/ai_campaign_studio/presentation_webview/static/app.css` —
   byte-identical V3 kopija.
2. `src/ai_campaign_studio/presentation_webview/static/app.js` —
   byte-identical V3 kopija.
3. `src/ai_campaign_studio/presentation_webview/shell/__init__.py` —
   `.lang-toggle` uklonjen.
4. `src/ai_campaign_studio/presentation_webview/screens/__init__.py` —
   re-export `write_all_pages`.
5. `src/ai_campaign_studio/presentation_webview/screens/pocetna/__init__.py` —
   lazy import `DEFAULT_FIXTURE` (cycle break).

### Dodano (6)
1. `src/ai_campaign_studio/presentation_webview/screens/_static_pages.py` —
   `write_all_pages()` generator.
2. `src/ai_campaign_studio/presentation_webview/screens/brend/__init__.py` —
   placeholder `render_body()`.
3. `src/ai_campaign_studio/presentation_webview/screens/kampanje/__init__.py`
4. `src/ai_campaign_studio/presentation_webview/screens/kalendar/__init__.py`
5. `src/ai_campaign_studio/presentation_webview/screens/podesavanja/__init__.py`
6. `tests/unit/presentation_webview/test_static_pages_generator.py` —
   7 novih testova (DRY enforcement, lang-toggle absence, fixture
   data, remote-asset absence, per-screen h2).

### Premješteno (5)
* `screens/{pocetna,brend,kampanje,kalendar,podesavanja}/index.html` →
  `artifacts/obsolete-v1-static-html/` (delete blokiran policy-jem).

### Revert (1)
* `artifacts/phase0_foundation_gate.json` (auto-regenerisan,
  van scope-a).

### Test proširen (1)
* `tests/unit/presentation_webview/test_pocetna_ssr.py` — dodan
  `test_render_shell_has_no_lang_toggle` regression test.

## Worktree status

```
$ git status --porcelain
 M tests/architecture/test_import_boundaries.py
?? src/ai_campaign_studio/presentation_webview/
?? tests/unit/presentation_webview/
?? artifacts/obsolete-v1-static-html/        # (backup ručno kodiranog HTML-a)
```

Main repo (`H:\AI Campaing Studio`) je clean — prethodni round 1 leak
je bio fiksiran prije round 2 fix-a.

## Šta coordinator dobija nakon odobrenja

Predlažem sljedeći commit (koordinator radi `git add` + `git commit`):

* `src/ai_campaign_studio/presentation_webview/...` (12 fajlova, od
  čega 5 novih, 1 modificiran, 5 mjesta gdje su index.html fajlovi
  uklonjeni).
* `tests/unit/presentation_webview/...` (4 fajla, od čega 2 nova
  modificirana, 1 novi test fajl).
* `tests/architecture/test_import_boundaries.py` (boundary extension).
* `agent_reports/2026-09-02-ACS-GUI-001-minimax.md` (round 1) +
  `agent_reports/2026-09-02-ACS-GUI-001-r2-minimax.md` (round 2, ovaj
  fajl) — opciono; neki workflow-evi drže evidence van source tree.
* `artifacts/obsolete-v1-static-html/` — ne commitovati; backup je
  samo za referencu, dok se round 1 fajlovi definitivno ne potvrde
  da nisu potrebni.

---

**Spreman za round 2 review.** Čekam Claude-ovu odluku o merge-u.
