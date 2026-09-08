---
verdict: REJECT
scope: PASS
acceptance: REJECT
architecture: PASS
security: PASS
tests: REJECT
gitnexus_impact: PASS
blocking_findings:
  - "BF-1: Brend app.js test je string-presence test koji ne razlikuje ispravnu implementaciju od poznatih BF-1/BF-2 i XSS regresija; potreban je izvršni Node/VM DOM test."
---

# ACS-F1-049 — Codex adversarial review PR #14

## CILJ

Nezavisno pregledati PR #14 (`task/ACS-F1-049-brend-read-path`, HEAD
`7ca63aa`) protiv `agent_reports/ACS-F1-049-task-contract.md`, sa fokusom na
pywebview lifecycle race, cross-screen izolaciju, XSS i stvarnu primjenu
`is_fact_usable` filtriranja.

## PROVJERENO

- Pročitan je stvarni diff `main...HEAD`, ne samo implementer evidence.
- Produkcijski/test diff je ograničen na ugovorene fajlove. Dodatni
  `agent_reports/2026-09-07-ACS-F1-049-brend-read-path-evidence.md` je obavezni
  workflow artefakt, ne scope creep produkcijskog koda.
- `get_brand_overview()` koristi postojeće `_ensure_brand()`, `get_brand()`,
  `get_snapshot()` i `list_snapshot_facts()` metode; repo/domain/application/
  infrastructure kod nije mijenjan.
- DTO mapiranje odgovara stvarnom domain obliku: prvi `Audience` daje
  `name — description`, a voice je `(formality, *tone)`.
- Svi vraćeni facts prolaze kroz autoritativni
  `domain.facts.policies.is_fact_usable`; politika vraća `True` samo za
  `FactStatus.APPROVED`. SQLite test sa snapshot-linkovanim `SUPERSEDED` factom
  potvrđuje da se ne vraća.
- Bridge lifecycle failure vraća tačan BrandOverview DTO i ne vraća/loguje
  sentinel exception/path tekst. Uobičajeni read failure prati već prihvaćeni
  `logger.exception` obrazac; ova putanja ne prima niti dohvaća credentiale.
- SSR ostaje fixture-driven i offline upotrebljiv; nova hidratacija dira samo
  brand-info/approved-facts polja za koja postoji realan domain izvor.
- PR je na GitHubu `MERGEABLE/CLEAN`; CI `test` je zelen na istom HEAD-u.

## GITNEXUS / IMPACT

- Main indeks je svjež na `bd402d5`.
- `CampaignBridgeApi` upstream: LOW, jedan direktni import
  (`presentation_webview/__main__.py`).
- `PresentationFacade` upstream: LOW, 0 dependanata u grafu.
- `is_fact_usable` ima HIGH postojeći upstream blast radius (16 simbola, dva
  procesa), ali ovaj PR ne mijenja politiku; samo dodaje još jednog callera.
- `detect-changes --scope compare` iz glavnog checkouta pokazuje samo lokalne
  AGENTS/CLAUDE izmjene, što je poznata linked-worktree binding limitacija i
  nije validan task-branch diff. Kompenzacija: ručni `git diff main...HEAD`,
  server-side `gh pr diff --name-only` i `rg` caller sweep. Nije pronađen skriven
  caller ni širi runtime proces izvan ugovorenog bridge/UI toka.

## BLOCKING FINDINGS

### BF-1 — trenutni test ne dokazuje lifecycle, izolaciju ni puni XSS invariant

Lokacija: `tests/unit/presentation_webview/test_brend_ssr.py`,
`test_app_js_has_brand_hydration_with_escape_and_lifecycle` (oko linija
268–300).

Test provjerava samo da se pojedini stringovi pojavljuju bilo gdje u zajedničkom
`app.js`. Nije vezano dokazano da:

1. `pywebviewready` zaista poziva `loadBrandOverview` nakon kasne API injekcije;
2. Brend kod ne poziva API i ne dira DOM na drugom ekranu;
3. `brand_name` i `primary_audience` ostaju na XSS-safe `textContent` putu.

Adversarial in-memory mutacije (bez izmjene fajlova) dale su:

```text
unconditional loadBrandOverview() (BF-1)            -> sve postojeće test-provjere PASS
generic .card guard uz prisutan data-brend marker   -> sve postojeće test-provjere PASS
name/audience textContent -> unsafe innerHTML       -> sve postojeće test-provjere PASS
```

Zbog toga test ne pada na poznatoj lošoj varijanti i nije trajni regression
dokaz za HIGH-risk presedan. Kontrakt dopušta string assertions kao minimum,
ali eksplicitno daje prednost izvršnom Node/VM testu ako je izvodljiv. Ovdje je
izvodljiv (postojeći Campaign test već daje harness, a reviewerska proba je
izvršila cijeli stvarni `app.js` za nekoliko sekundi).

Required fix: dodati izvršni Node/VM test po uzoru na
`test_app_js_campaign_hydration_lifecycle_and_screen_isolation` koji najmanje
dokazuje kasnu injekciju + exactly-once listener, immediate put, nula Brend API
poziva/nula DOM izmjena na non-Brend ekranu te XSS payload za ime, publiku,
voice, fact code i fact text. Test mora pasti na gore navedenim lošim
varijantama.

## STANDARDNA VERIFIKACIJA

```text
pytest tests/unit/presentation_webview tests/unit/presentation -q
-> 314 passed in 30.89s

pytest -q
-> 1146 passed, 1 skipped, 1 warning in 132.20s

ruff check .
-> All checks passed!

mypy src
-> Success: no issues found in 176 source files

node --check src/ai_campaign_studio/presentation_webview/static/app.js
-> PASS (exit 0)

git diff --check main...HEAD
-> PASS (bez outputa)
```

## ADVERSARIALNA PROVJERA

Nezavisni Node/VM DOM harness izvršio je stvarni commitovani `app.js`:

```text
lateReadyListeners=1
lateOnce=true
lateUnchangedBeforeEvent=true
lateHydrated=true
lateApiCalls=1
otherUntouched=true
otherApiCalls=0
otherReadyListeners=0
immediateApiCalls=1
textContentCarriesLiteral=true
htmlEscaped=true
rawPayloadTag=false
```

Dakle, trenutni produkcijski kod za BF-1/BF-2/XSS ponaša se ispravno. REJECT
je isključivo zato što PR nema test koji će to ponašanje zaštititi od povratka
poznate greške. `is_fact_usable` je i kodom i SQLite testom potvrđen kao stvarno
primijenjen, ne samo importovan/spomenut.

## NE DIRATI U FIX RUNDI

- Ne mijenjati bridge/DTO/domain/repository implementaciju; za njih nije nađen
  funkcionalni blocker.
- Ne širiti scope na brand-voice editor, resources ili description polje.
- Ne mijenjati `is_fact_usable` politiku niti repo metode.
- Fix treba biti test-only u postojećem dozvoljenom Brend test fajlu (ili
  drugom već dozvoljenom presentation_webview test fajlu).

## SLJEDEĆE

Crush dodaje izvršni Node/VM regresijski test i pushuje isti PR. Nakon toga
Codex radi kratki re-review fokusiran na: test prolazi na ispravnom kodu, pada
na BF-1/BF-2/XSS mutacijama, puni relevantni gate ostaje zelen. Human Owner
odobrenje tek nakon PASS re-reviewa; ovaj report nije merge odobrenje.
