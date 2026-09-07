---
verdict: REJECT
scope: PASS
acceptance: REJECT
architecture: PASS
security: PASS
tests: REJECT
gitnexus_impact: PASS
blocking_findings:
  - BF-1: "loadCampaigns runs before pywebview.api is guaranteed ready and never retries on pywebviewready, so production can remain on fixture data."
  - BF-2: "The global table.table selector also matches Plan kampanje and replaces that unrelated table with campaign rows."
  - BF-3: "PR #11 is currently CONFLICTING/DIRTY against main; merge-tree shows unresolved shared presentation/bridge/app.js/test conflicts."
---

# CILJ

Nezavisno i adversarialno provjeriti ACS-F1-046 na PR #11 / commitu
`a9592024d783b7798c3d475e0f1b9ad5d2b1d6c0`: prvi READ `js_api` metod
`list_campaigns`, tri aditivna repository read metoda i client-side hidrataciju
Kampanje tabele, uz očuvan SSR fallback, XSS zaštitu i HOTFIX-002 lifecycle
obrazac.

# URAĐENO

- Pročitani su Task Contract, coordinator-approved scope addendum, implementer
  evidence, PR metadata i stvarni diff svih 15 fajlova.
- Rekonstruisan je tok SQLite -> repository ports/adapters ->
  `CampaignBridgeApi.list_campaigns` -> DTO -> `app.js` -> DOM.
- Pokrenute su adversarial DOM simulacije nad stvarnim `app.js` fajlom za:
  kasnu pywebview API injekciju, cross-screen selector i XSS payload.
- Headless je renderovan stvarni generisani HTML/CSS/JS sa izolovanim lažnim
  podacima radi vizuelnog poređenja SSR 7-kolonske i dinamičke 6-kolonske
  tabele.
- Ručno je izvršen SQLite lifecycle-failure put `list_campaigns` metode.
- Pokrenut je svježi targetirani/full test, ruff i mypy gate.
- Provjeren je GitNexus blast radius shared repository portova i bridge klase.

# PROVJERENO

- `CampaignRepositoryPort.list_campaigns()` i
  `get_latest_plan_for_campaign()` su aditivni i SQLite implementacije slijede
  ugovoreni `created_at DESC` / `version DESC LIMIT 1` obrazac.
- `BrandRepositoryPort.get_brand()` je aditivan, pravilno mapira `Brand` i vraća
  `None` za nepoznat ID.
- `list_campaigns` ima `@_with_call_resources`; fresh-worker-thread test prolazi.
- Prazna baza vraća `ok=True` i prazan `campaigns` tuple (JSON granica ga
  serializira kao listu).
- DTO sadrži ugovorena polja, a `created_at` je ISO string.
- Latest-plan repository test stvarno bira plan najviše verzije i učitava
  njegove iteme; bridge računa `plan_item_count` iz vraćenog plana.
- Lifecycle failure je ručno vratio tačan list DTO oblik i nije izložio
  sentinel SQL/path/exception detalje:

```text
{'ok': False, 'campaigns': (), 'error_code': 'INTERNAL_ERROR',
 'error_message': 'Učitavanje kampanja nije uspjelo (interna greška).'}
exact_keys=True
detail_leaked=False
```

- Adversarialni `<script>`, `<img onerror>`, `<svg onload>`, quote-attribute i
  markup payloadi u svim dinamičkim poljima su escapeovani. Stvarni izvršni
  rezultat:

```text
rawScript=false rawImg=false rawSvg=false rawCount=false escapedAll=true
```

- Nije pronađeno curenje secret/path/exception sadržaja u JS rezultat.
- Scope odgovara odobrenom addendumu; domain, application, migrations i drugi
  zabranjeni adapteri nisu dirani.

# GITNEXUS / IMPACT

GitNexus je pokazao:

- `CampaignRepositoryPort`: HIGH, 20 upstream dependanata / 16 direktnih
  importera;
- `BrandRepositoryPort`: HIGH, 20 upstream dependanata / 16 direktnih
  importera;
- `CampaignBridgeApi`: LOW, jedan direktni importer (`presentation_webview/__main__.py`).

Shared-port izmjene su čisto aditivne; svi postojeći potpisi ostaju isti, a puni
suite/type gate je zelen. GitNexus indeks glavnog checkouta bio je svjež na
`eb24247`, ali je `main` tokom reviewa napredovao dalje do `b2ac2ff`.
`detect-changes` iz task worktreea ponovo je prijavio poznato sibling-worktree
ograničenje i mapirao glavni checkout umjesto pouzdanog task diffa; rezultat je
zato tretiran kao nepouzdan, ne kao zero-impact dokaz. Kompenzacija: puni
`main...HEAD` diff, svi caller-i, port/adapter implementacije, merge-tree i puni
test/type gate pregledani su ručno. GitNexus stale/worktree ograničenje samo po
sebi nije uzrok REJECT verdikta.

# BLOCKING FINDINGS

## BF-1 — production hydration može trajno ostati na fixture podacima

Lokacija: `src/ai_campaign_studio/presentation_webview/static/app.js:380-423`.

`loadCampaigns()` se poziva odmah pri evaluaciji shared `app.js`, provjeri
`window.pywebview.api`, i ako API još ne postoji samo uradi `return`. Nema
listenera za `pywebviewready` i nema retryja.

To je stvaran lifecycle kvar, ne teorijska preferencija: pywebview dokumentacija
eksplicitno kaže da `pywebview.api` nije garantovan ni na `window.onload` i da se
za dostupnost mora koristiti `window.pywebviewready`. Ovdje se poziv događa još
ranije, iz script taga na kraju body-ja.

Adversarial DOM dokaz nad stvarnim `app.js`:

```text
1. app.js evaluiran dok window.pywebview ne postoji
2. pywebview.api ubrizgan naknadno
3. simuliran pywebviewready event

registered_pywebviewready=false
table_after_ready=SSR FIXTURE
```

Posljedica: prvi READ path na stvarnom desktop startu može potpuno preskočiti
bazu i korisniku nastaviti prikazivati tri demo kampanje, bez greške i bez nove
prilike za učitavanje.

Minimalni fix: ako je API već dostupan, pozvati `loadCampaigns()` odmah; inače
registrirati one-shot `window.addEventListener('pywebviewready', loadCampaigns)`.
Offline preview ostaje fixture jer se event tamo nikada neće desiti.

## BF-2 — hidratacija prepisuje tabelu na ekranu Plan kampanje

Lokacije:

- `static/app.js:381` — `document.querySelector('table.table')`;
- `screens/kampanje/__init__.py:111` — ciljna tabela koristi `.table`;
- `screens/plan_kampanje/__init__.py:151` — nepovezana plan tabela koristi istu
  `.table` klasu;
- shared shell učitava isti `app.js` na svakom ekranu.

Hydration IIFE nema screen/page guard i bira prvi generički `table.table` u
cijelom dokumentu. Kada se otvori Plan kampanje uz aktivan bridge,
`list_campaigns` uspije i kod zamijeni plan item tabelu sa šest kolona Kampanje
liste.

Izvršni dokaz nad stvarnim `app.js`, sa DOM-om koji predstavlja postojeću Plan
tabelu:

```text
plan_table_replaced=true
contains_campaign_row=true
```

Dobiveni HTML počinje sa kolonama `Kampanja / Brend / Status / Planirano /
Kreirano`, umjesto `# / Uloga / Tema / Cilj / Format / Status`.

Minimalni fix: ciljnoj Kampanje tabeli dati jedinstven marker, npr.
`data-campaigns-table`, i u JS koristiti isključivo taj selector (ili jednako
strogo ograničiti IIFE na Kampanje page root). Ne koristiti globalni `.table`.

## BF-3 — PR je trenutno konfliktan sa aktuelnim mainom

GitHub je tokom reviewa vratio (kasniji poll se vratio na privremeni
`UNKNOWN` dok ponovo računa mergeability):

```text
headRefOid: a9592024d783b7798c3d475e0f1b9ad5d2b1d6c0
mergeable: CONFLICTING
mergeStateStatus: DIRTY
CI test: SUCCESS
```

Read-only `git merge-tree` protiv aktuelnog `main`-a potvrđuje stvarne konflikte
u shared fajlovima, uključujući `presentation/contracts.py`,
`presentation/ui_models.py`, `presentation_webview/bridge/__init__.py`,
`presentation_webview/static/app.js` i njihove presentation/bridge testove.
Main je nakon briefa dobio GUI-009/F1-047 promjene u istim površinama; zeleni CI
je izvršen na starom PR head/base stanju i ne dokazuje integrirani rezultat.

Minimalni fix: nakon BF-1/BF-2 izmjena rebaseovati branch na tadašnji aktuelni
`main`, ručno sačuvati sve postojeće lifecycle mappere/metode i oba UI flowa,
zatim ponoviti puni gate i pushati novi head prije re-reviewa.

# STANDARDNA VERIFIKACIJA

Svježe pokrenuto u task worktreeu sa eksplicitnim
`PYTHONPATH=<worktree>/src`:

```text
12 fokusiranih list_campaigns/repository/SSR testova
12 passed in 2.27s

python -m pytest -q
1077 passed, 1 warning in 99.31s

python -m ruff check .
All checks passed!

python -m mypy src
Success: no issues found in 175 source files
```

PR #11 CI `test` check je `SUCCESS` na tačnom headu `a9592024`. Green suite
ne izvršava stvarni on-load DOM lifecycle niti provjerava izolaciju od druge
`.table` instance, pa ne detektuje BF-1/BF-2; PR je trenutno konfliktan s mainom
pa taj check nije dokaz integriranog stanja.

# ADVERSARIALNA PROVJERA

- Kasna pywebview API injekcija: FAIL — event listener ne postoji (BF-1).
- Plan kampanje DOM sa aktivnim bridgeom: FAIL — tabela je zamijenjena campaign
  redovima (BF-2).
- XSS payload kroz sva dinamička polja: PASS — raw markup nije završio u DOM-u.
- SQLite open/lifecycle failure: PASS ručno — tačan `_list_err` DTO, bez detalja.
- Fresh worker thread: PASS kroz postojeći test.
- Empty DB i repository ordering/latest-plan: PASS kroz postojeće testove.
- Vlastiti real-SQLite scenario sa planom verzije 1 (3 stavke) i verzije 2
  (1 stavka) vratio je `latest_plan_item_count=1`.
- Lifecycle `create_connection` failure vratio je tačan četveropoljni list DTO,
  a SQL/path/sentinel exception detalji nisu završili u JS rezultatu.
- Vizuelni sanity-check na 1280x820: dinamičkih 6 kolona i dva realistična reda
  stanu bez preklapanja ili horizontalnog overflowa; duži naziv kampanje i ISO
  datum ostaju čitljivi. Razlika prema 7-kolonskom SSR fixtureu sama po sebi nije
  nalaz.
- U repou postoje zastarjele dokumentacijske tvrdnje `exactly one public method`
  (`presentation_webview/__main__.py:181`) i `Single public method`
  (`bridge/__init__.py:257`). Nije pronađen runtime allowlist/broj-metoda koji
  blokira read metod; ovo je dokumentacijski dug, ne blocker ovog diffa.

# NE DIRATI U FIX RUNDI

- Ne mijenjati repository portove/adapters, DTO oblik, ordering ili latest-plan
  SQL; ti dijelovi su ispravni.
- Ne mijenjati SSR fixture fallback niti prazno-state poruku.
- Ne širiti task na dinamički detail/open flow, druge read metode ili
  `updated_at`.
- Ne dirati domain/application/migrations niti GUI-009/ACS-F1-047 worktreeove.

# SLJEDEĆE

1. Vezati početno učitavanje za `pywebviewready`, uz immediate fast path kada je
   API već prisutan.
2. Dodati jedinstven Kampanje-table marker i ukloniti globalni `table.table`
   selector.
3. Rebaseovati na aktuelni `main` i pažljivo razriješiti shared bridge/app.js/
   presentation-contract konflikte bez gubitka GUI-009/F1-047 metoda.
4. Dodati izvršne JS/DOM regresijske testove: (a) API se pojavi nakon script
   evaluacije pa event hidratizira tabelu; (b) Plan kampanje tabela ostaje
   netaknuta uz aktivan bridge. Postojeći source-string XSS test može ostati,
   ali nije dovoljan za ove lifecycle/scope invariants.
5. Kao jeftinu zaštitu proširiti postojeći connection-failure test da asertuje
   tačan `list_campaigns` lifecycle DTO oblik.
6. Ponoviti puni gate i zatražiti Codex rereview. HIGH task nije spreman za
   Human Owner approval/merge.
