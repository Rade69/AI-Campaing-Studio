# ACS-GUI-001 — Claude review, round 1

**Verdict: PASS WITH REQUIRED FIXES — not merged yet.** Nezavisno reprodukovao
pytest (281 passed)/ruff/mypy/import-boundaries u worktree-u (`H:\ai-campaign-studio-worktrees\ACS-GUI-001-gui-base-shell`,
`PYTHONPATH` override), pročitao sav kod (`__main__.py`, `shell/__init__.py`,
`screens/__init__.py`, `screens/pocetna/__init__.py`, `static/app.css`,
`static/app.js`, sva 4 "passthrough" ekrana, diff na
`tests/architecture/test_import_boundaries.py`, diff na `artifacts/phase0_foundation_gate.json`).

## Šta je odlično (bez primjedbi)

- **Sigurnost (`docs/PYWEBVIEW_SECURITY.md` §1–2) — rigorozno ispoštovano.**
  `webview.start(gui="edgechromium", debug=False)` doslovno u kodu.
  `_probe_webview2()` čita EdgeUpdate registry ključ, baca
  `WebView2MissingError` sa jasnom BHS porukom + link ka Evergreen
  Bootstrapper-u. Dodatni defense-in-depth: catch-all na
  `webview.start()` koji specifično detektuje "mshtml" u poruci greške
  kao drugu liniju odbrane. Testovi (`test_pywebview_start_uses_explicit_edgechromium_and_debug_false`,
  `test_probe_raises_when_webview2_is_missing`, `test_probe_is_noop_off_windows`)
  tačno pogađaju acceptance.
- Nema `js_api` bridge-a — ispravna odluka (Početna je čisto prikaz).
- Početna ekran je stvarno fixture-driven (`test_changing_fixture_changes_rendered_body`
  dokazuje), sve vrijednosti/tekstovi identični `docs/gui-v3/screens/01_pocetna/`.
  `html.escape()` dosljedno korišten za XSS higijenu.
- CSP header prisutan i testiran (`test_render_shell_sets_csp_header`,
  `test_render_shell_uses_local_static_assets`) — više nego što je
  acceptance strogo tražio (bonus).
- `tests/architecture/test_import_boundaries.py` proširenje je identično
  onome što sam ranije zatekao necommit-ovano direktno u `main` (i
  stash-ovao) — potvrđuje da je implementer ovaj put ispravno radio u
  dodijeljenom worktree-u, ne u glavnom checkout-u. Taj raniji proces-nalaz
  je riješen.
- Nema dirania `bootstrap.py`/`main.py`/domain/application/ports/infrastructure.

## Nalazi koji traže fix prije merge-a

### 1. `static/app.css`/`static/app.js` NISU kopija `docs/gui-v3/shared/` (kontrakt-kršenje)

Kontrakt eksplicitno: *"Portovati docs/gui-v3/shared/app.css i shared/app.js
u presentation_webview/static/ (**kopija**, ne symlink/live-read... production
paket nosi **svoju kopiju**)."* Stvarno stanje: oba fajla su nezavisno
prepisana — drugačije `.badge.info` boje, restrukturirane `.grid` klase,
dodano `.btn.ghost`/`.lang-toggle`/media query koji ne postoje u kanonskom
izvoru, i **potpuno nedostaju klase koje će trebati preostalih 8 ekrana**
(`.tabs`, `.stepper`, `.calendar`, `.studio`, `.provider`, `.fact`,
`.brand-status`, `.check`, `.callout`, `.table`, `.field`/`.input`/
`.textarea`/`.select`, itd.). `app.js` je isto potpuno prepisan (drugačiji
toast, event delegation umjesto direktnih listenera, nema campaign-context
toggle logike).

**Zašto je ovo bitno, ne samo stil**: `docs/gui-v3/` je Human-Owner-
zaključan kanonski GUI izvor (vidi `V3_PLAN.md`: *"V3 je jedini kandidat za
finalni GUI dizajn"*), a njegov vlastiti acceptance kriterijum kaže *"jedan
shared design system"*. Sada već na prvom production wiring koraku postoje
DVA razdvojena design sistema. Kad ACS-GUI-002 bude portovao preostalih 8
ekrana, ili će morati vratiti sve izbačene klase (efektivno konvergirajući
nazad ka kanonskom CSS-u), ili će divergencija rasti.

**Traženi fix**: zamijeniti `static/app.css` i `static/app.js` doslovnom,
bajt-identičnom kopijom `docs/gui-v3/shared/app.css`/`app.js`. Provjeriti
da Početna i dalje renderuje ispravno (treba raditi bez izmjena — kanonski
CSS je superset, nema konfliktnih selektora sa trenutnim markup-om).

### 2. Shell dodaje UI element koji ne postoji u zaključanom dizajnu

`render_shell()` dodaje `<div class="lang-toggle">Jezik EN/BHS pill</div>`
u topbar. Ovo ne postoji NIGDJE u `docs/gui-v3`-ovih 9 ekrana — nova,
neatražena dizajn odluka umetnuta direktno u production port. Trenutno je
inertno (nema click handler-a u `app.js`), ali je dizajn dodatak van scope-a
ovog taska i van zaključanog V3 dizajna.

**Traženi fix**: ukloniti iz `render_shell()` za sada. Ako je ideja dobra
(jezički toggle u topbar-u), predložiti je kroz `docs/gui-v3` kanal prvo
(novi ekran/element tamo, Human Owner potvrdi), ne tiho ubaciti u
production kod mimo dizajn izvora.

### 3. Sidebar/topbar markup NIJE stvarno DRY (acceptance kriterijum promašen)

Acceptance: *"Shell markup (sidebar/topbar) je DRY-ovan u shared template,
nije kopiran po ekranu."* Stvarno: `render_shell()` se koristi SAMO za
dinamički renderovanu Početnu. Sva četiri "passthrough" ekrana (Brend/
Kampanje/Kalendar/Podešavanja) su statični HTML fajlovi sa CIJELIM
sidebar/topbar markup-om nezavisno zalijepljenim u svaki fajl — 4 kopije
istog markup-a, van `render_shell()`. Test suite ovo ne hvata jer testovi
(`test_render_shell_*`) provjeravaju samo `render_shell()` funkciju, nikad
stvarni sadržaj tih 4 statična fajla.

**Traženi fix**: generisati ta 4 placeholder ekrana kroz `render_shell()`
(npr. mali build/init korak koji piše static HTML fajlove pozivom te iste
funkcije sa "ACS-GUI-002" placeholder body-jem), umjesto ručno održavanog
duplikata. `render_shell()` već postoji i radi — ovo je mali dodatak, ne
redizajn.

## Sitno (spomenuti, ne blokira)

- Nema `agent_reports/<datum>-ACS-GUI-001-minimax.md` evidence izvještaja
  (samo task contract + `artifacts/*.html` screenshot dump-ovi). Workflow
  §11 traži implementer evidence — dodati kratak izvještaj uz fix round
  (šta je promijenjeno, verifikacija komande + output).
- `artifacts/phase0_foundation_gate.json` je modifikovan u worktree-u
  (stara `ruff: FAIL` snimka od ranije iteracije — trenutno ruff PRIOLAZI,
  potvrđeno nezavisno). Taj fajl nije u `allowed_paths` — revertovati ga
  (`git checkout -- artifacts/phase0_foundation_gate.json`) prije sljedeće
  provjere, ne dio ovog taska.

## Sljedeći korak

Fix round na istoj branch/worktree (`task/ACS-GUI-001-gui-base-shell`).
Nakon fixeva #1–#3 (i evidence izvještaja), javiti koordinatoru za round 2
review. Nema potrebe za Codex rundom niti Human Owner odobrenjem za sam
fix-round zahtjev (MEDIUM risk, §29) — ali merge čeka PASS na round 2.
