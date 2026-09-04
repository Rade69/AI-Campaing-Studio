# → ZA MINIMAX — ACS-GUI-005 (prvi GUI→backend bridge)

**Od:** koordinator (Claude) · **Za:** MiniMax · **Datum:** 2026-09-04

## Zašto ovaj task postoji

Human Owner je danas tražio krajnje iskrenu procjenu: arhitektura i
fact-grounding rade (live dokazano protiv DeepSeek i Google Gemini API-ja
u A8), ali GUI (`presentation_webview/`, port `docs/gui-v3` mokapa) i
backend (domain/application/infrastructure) su **potpuno nepovezani** —
svako dugme je ili `data-action="toast"` stub ili statičan `<a href>`.
Odobrio je promjenu prioriteta: ovaj task je prvi stvaran korak da se to
promijeni, i eksplicitno te je zadužio kao implementera.

## Šta je ovo, u jednoj rečenici

Klik na "Sačuvaj i napravi plan →" (Opis kampanje ekran) treba da prvi put
stvarno pozove `CreateCampaign` + `GenerateCampaignPlan` kroz nov
pywebview `js_api` bridge — pravi upis u SQLite, pravi poziv
konfigurisanom AI provideru — umjesto da samo navigira na sljedeću
statičnu stranicu.

## Prvi korak: pročitaj kontrakt u cijelosti

[agent_reports/ACS-GUI-005-task-contract.md](agent_reports/ACS-GUI-005-task-contract.md)
(`main @ cdbef5e`). Ovo NIJE opciono štivo — kontrakt zaključava
nekoliko poslovnih odluka koje bi inače morao sam da nagađaš:

- **Brand seeding** preko lokalnog `brand-seed.json` fajla (isti idiom
  kao postojeći window-state fajl u `__main__.py`) — `BrandRepositoryPort`
  nema "da li brend već postoji" upit i `LoadBrandFixture` generiše nov
  ID svaki put, pa se NE poziva na svaki app start bez ovog cache-a.
- **Hardkodovana provider→model tabela** (`resolve_default_text_model`
  ne pomaže ovdje — registry nema unaprijed registrovane modele).
  DeepSeek/OpenAI/Google model ID-jevi su preuzeti iz već live-
  verifikovanih A8 izvještaja (referencirani u kontraktu) — **Anthropic
  MORA biti nezavisno provjeren** prije nego što ga hardkodiraš, nije
  live-testiran nigdje u projektu. Ako nisi siguran u tačan model_id
  string, napiši to eksplicitno kao otvoreno pitanje u evidence
  izvještaju — ne nagađaj.
- **Zaključana forma→brief mapa** (channel/platform_code/format_code
  tabela, uključujući LinkedIn edge-case — nema Story/Feed format u
  registryju, pa uvijek dobija `PROFESSIONAL_POST` bez obzira na izabrani
  format).
- **Šta NIJE u scope-u** — posebno pročitaj tu sekciju: ne graditi cijeli
  `PresentationFacade`, ne dirati `ports/repositories.py`, ne graditi
  Podešavanja provider-config GUI flow, Plan kampanje ekran OSTAJE
  fixture u ovom tasku (pravi render generisanog plana je budući task).

## Risk i review put

**HIGH**, ne §29 skraćeni put. Ovo je prvi `js_api` bridge u projektu,
prva prava DB akcija iz GUI klika, prvi pravi AI poziv iz GUI klika.
`docs/PYWEBVIEW_SECURITY.md` §3 (js_api pravila izlaganja) je direktno
normativan — kontrakt ga citira, ali pročitaj cijeli fajl, ne samo
citat. Ide na pun ciklus: tvoj rad → Claude review → Codex adversarial
review → eksplicitno "odobravam" od Human Owner-a.

## Gdje raditi

```text
Worktree: H:\ai-campaign-studio-worktrees\ACS-GUI-005-campaign-bridge
Branch:   task/ACS-GUI-005-campaign-bridge
Base:     main @ 73f52b1
```

Worktree je već kreiran. Prije bilo kakvog testa, provjeri da editable
install pokazuje na OVAJ worktree (`.pth` trap — poznat problem):

```bash
python -m pip install -e . --no-deps -q
```

**Radi u projektnom `.venv`-u** (`.venv\Scripts\python.exe` ili
aktiviran venv), ne u sistemskom Python-u — ovo je bila lekcija iz
ACS-F1-018 (istraživao si SDK verziju protiv sistemskog Python-a, a
projektni `.venv` je imao drugu major verziju sa drugačijim API-jem).

## Funkcionalni test — treba ti podešen provider

Kontrakt traži da stvarno pokreneš aplikaciju i klikneš dugme (ne samo
unit testovi). Za to treba bar jedan provider sa API ključem u
keyring-u (`provider/<CODE>/api_key`, preko `ConfigureProvider`
use-case-a — NE ručno u bazu). Ako nemaš način da to sam podesiš, javi
mi PRIJE nego što dođeš do tog koraka — ja mogu podesiti DeepSeek ili
Google ključ u projektnom keyring-u (već ih imam od A8 live validacije,
samo trebam ih upisati pod pravi `provider/<CODE>/api_key` naziv umjesto
mog ad-hoc validacionog naziva).

## Kad završiš

Evidence izvještaj: `agent_reports/2026-09-04-ACS-GUI-005-minimax.md`
(ne commit-uj — ostavi u worktree-u, javi mi putanju). U izvještaju
eksplicitno:

- svi acceptance checkboxovi iz kontrakta, jedan po jedan;
- kako si provjerio Anthropic model_id (ili da ga NISI uključio ako
  nisi mogao verifikovati);
- screenshot toast poruke (uspjeh) + dokaz da su `campaigns`/
  `campaign_plans` redovi stvarno nastali u SQLite bazi;
- dokaz da drugi klik ne duplira brend (broj redova u `brands` tabeli
  prije/poslije);
- koji testovi prolaze (`pytest -q`, `ruff check .`, `mypy src`,
  `test_import_boundaries.py`).

Ako naiđeš na nešto što kontrakt nije predvidio (npr.
`test_import_boundaries.py` ne dozvoljava import koji ti treba iz
`presentation_webview/`), STANI i javi mi — ne zaobilaziti test ili
mijenjati fajl van `allowed_paths`.
