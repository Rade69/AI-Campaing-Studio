---
verdict: REJECT
scope: PASS
acceptance: REJECT
architecture: PASS
security: REJECT
tests: REJECT
gitnexus_impact: PASS
blocking_findings:
  - BF-1: "_resolve_ai_adapter logs the full adapter-factory exception and can persist an API key in application logs."
  - BF-2: "Concurrent exports for the same campaign are not serialized and can corrupt the fixed <campaign_id>.zip output."
  - BF-3: "GUI-009 has no regression tests for cross-campaign plan rejection or the export-specific lifecycle-failure DTO shape."
---

# CILJ

Nezavisno, adversarialno provjeriti ACS-GUI-009 v2 na commitu
`ebfb50e864f1be6e17899f0d08bfc4cf05ad6035`: prvi GUI poziv stvarnog
`GenerateVisualSystem -> PlanPostLayout -> ExportCampaign` lanca, uključujući
SQLite write-ove, render, ZIP, pywebview lifecycle/error granicu i konkurentnost.

# URAĐENO

- Pročitan je stvarni diff svih 10 implementacijskih/test fajlova plus evidence.
- Provjeren je originalni Task Contract i post-HOTFIX-002/GUI-008 addendum.
- Provjeren je PR #9; head odgovara briefu (`ebfb50e`) i CI `test` je `SUCCESS`.
- Pokrenut je svježi targetirani i puni verification set.
- Ručno/adversarialno su izvršene putanje koje novi testovi ne pokrivaju:
  lifecycle failure, cross-campaign plan i secret-in-exception logging.
- Pokrenut je kontrolisani concurrent-write test nad istim ZIP outputom.

# PROVJERENO

- `export_campaign_package` ima `@_with_call_resources` i vraća
  `ExportCampaignResultUiModel` oblik.
- `_CallResources` sadrži `visual_repo` i `performance_repo`; oba su vezana za
  per-call connection graph.
- `ExportCampaign` se konstruiše sa svih 7 trenutnih zavisnosti, uključujući
  `performance_repo`.
- Happy path stvarno piše ZIP, a postojeći integration-style test otvara arhiv,
  provjerava `manifest.json`, PNG magic bytes i 2 `DistributionInstance` reda.
- Plan mora pripadati kampanji i biti `APPROVED` prije AI poziva.
- Produkcijski static HTML uvijek sadrži hidden/disabled export dugme, a runtime
  IIFE ga puni tek kada postoje oba query ID-a.
- `approve-gate` je UI-only; ne poziva nepostojeći approval backend.
- Izmjene su u ugovorenom scopeu. Dodatni
  `tests/unit/presentation_webview/test_static_pages_generator.py` eksplicitno
  je zahtijevan addendumom. Forbidden slojevi nisu dirani.

# GITNEXUS / IMPACT

Glavni checkout indeks je bio svjež na `70c9efa`.

- `GenerateVisualSystem`: upstream LOW, 0.
- `PlanPostLayout`: upstream LOW, 0.
- `ExportCampaign`: upstream LOW, 1 (package `__init__.py` import).

Worktree-binding ograničenje znači da `detect-changes --base-ref main` iz glavnog
checkouta nije opisao task branch (prikazao je samo lokalne router dokumente).
To nije tretirano kao dokaz čistog task diffa; scope i caller-i su zato provjereni
direktnim `git diff main...HEAD` pregledom.

# BLOCKING FINDINGS

## BF-1 — API ključ može završiti u application logu

Lokacija:
`src/ai_campaign_studio/presentation_webview/bridge/__init__.py:1219-1227`.

Novi `_resolve_ai_adapter` prosljeđuje `api_key` adapter factoryju, a njegovu
grešku hvata sa `logger.exception(...)`. `logger.exception` zapisuje i poruku
izuzetka/traceback. Ako adapter ili SDK uključi predani credential u poruku,
ključ se trajno zapisuje u log.

Adversarial dokaz: factory je namjerno podigao
`RuntimeError("adapter rejected credential=" + api_key)` sa sentinelom
`sk-SECRET-SENTINEL-GUI009`.

```text
secret_in_result=False
secret_in_logs=True
RuntimeError: adapter rejected credential=sk-SECRET-SENTINEL-GUI009
```

DTO nije procurio ključ, ali log jeste. Ovo krši isti secret-safety standard koji
je već primijenjen na `configure_provider` i lifecycle mapper. Fix mora logovati
samo sigurni provider code i `type(exc).__name__`, bez exception objekta i bez
tracebacka. Potreban je regresijski `caplog` test sa sentinel ključem.

## BF-2 — concurrent export može korumpirati ZIP

Lokacije:

- `bridge/__init__.py:897-973` — compound cache/generate/layout/export sekvenca
  nema per-campaign/per-plan lock;
- `bridge/__init__.py:957-972` — svi pozivi za kampanju pišu na istu
  `exports/<campaign_id>.zip` putanju;
- `infrastructure/export/zip_exporter.py:46-48` — `ZipFile(..., mode="w")`
  direktno otvara cilj, bez atomic temp+replace zaštite.

Guard oko `_record_campaign_visual_system` štiti samo jednu dict mutaciju; ne
serializira `get -> GenerateVisualSystem -> PlanPostLayout -> write_zip`. Dva
pywebview worker poziva mogu zato istovremeno otvoriti isti ZIP u `w` modu.

Kontrolisani test je 50 puta pokrenuo dva stvarna `ZipExportWriter` poziva prema
istoj putanji, sa barrierom prije upisa. Rezultat:

```text
iterations=50 failures=9
examples: testzip() reported A/file-005.bin or B/file-000.bin as corrupt
```

UI trenutno sinhrono postavlja `button.disabled=true` prije prvog `await`, pa
običan brzi dvoklik u jednom prozoru smanjuje vjerovatnoću. To ipak nije backend
garancija: bridge je namjerno thread-dispatched, a fiksna output putanja čini
posljedicu stvarnom korupcijom artefakta. Isti lock treba obuhvatiti cijelu
export sekvencu za isti `(campaign_id, plan_id)` i imati barrier-based regression
test sa dva worker threada. Time se ujedno uklanja compound race visual-system
cachea.

Samo nezaštićeno dict čitanje nije zaseban blocker pod trenutnim CPythonom;
problem je neatomarna višekoračna operacija i isti filesystem cilj.

## BF-3 — dvije kritične negativne putanje nisu zaključane testom

GUI-009 export testovi nemaju:

1. `campaign_id` + plan koji stvarno pripada drugoj kampanji;
2. `create_connection` lifecycle failure koji mora vratiti tačno export DTO
   polje-set.

Ručno izvršenje pokazalo je da trenutni kod obje putanje sada obrađuje ispravno:

```text
cross-campaign -> VALIDATION_ERROR / "Plan ... ne pripada kampanji ..."
lifecycle -> INTERNAL_ERROR, exact keys:
campaign_id,error_code,error_message,exported_count,ok,skipped_count,zip_path
```

Međutim, to nije regresijska zaštita. Posebno, postojeći lifecycle test poziva
samo configure/create/generate-content metode, ne export. Helper
`_seed_brand_and_campaign` hardkoduje `plan-1` i `item-1...`, pa njegovo prosto
dvostruko pozivanje ne pravi dva nezavisna plana; drugi seed prepisuje/reveže
isti ID. Mismatch test mora koristiti dva stvarno različita campaign/plan ID-a.

# STANDARDNA VERIFIKACIJA

Svježe pokrenuto u v2 worktreeu uz eksplicitan `PYTHONPATH=<worktree>/src`:

```text
python -m pytest tests/unit/presentation_webview/ tests/unit/presentation/ -q
275 passed in 15.51s

python -m pytest -q
1065 passed, 1 warning in 102.68s

python -m ruff check .
All checks passed!

python -m mypy src
Success: no issues found in 175 source files
```

Green suite ne detektuje BF-1/BF-2/BF-3.

# ADVERSARIALNA PROVJERA

- Secret sentinel: rezultat čist, log kompromitovan — FAIL (BF-1).
- Dva istovremena writer-a na istoj campaign ZIP putanji: 9/50 korumpiranih
  arhiva — FAIL (BF-2).
- Export lifecycle error DTO: runtime shape is trenutno tačan — PASS ručno,
  ali bez testa (BF-3).
- Cross-campaign ownership: runtime guard trenutno odbija — PASS ručno, ali bez
  stvarno nezavisnog two-campaign/two-plan testa (BF-3).
- Uzastopni, završeni re-export stvara nove `DistributionInstance` redove. To je
  prihvaćena semantika "svaki export je novi distribution event", ne zaseban
  blocker. Brzi accidental double-click je na UI strani zaustavljen dok promise
  traje; BF-2 se odnosi na backend concurrent-call sigurnost.
- LayoutSpec nema `visual_system_id` vezu, pa race ne može ostaviti dangling FK
  prema obrisanom sistemu. Ipak, bez serializationa dva poziva mogu planirati
  layout prema različitim sistemima i zatim čitati globalni latest-by-piece
  layout; predloženi export lock zatvara i taj semantic race.

# NE DIRATI U FIX RUNDI

- Ne mijenjati `domain/`, `application/`, `ports/`, `infrastructure/` ili
  migracije radi ovog fixa.
- Ne mijenjati namjernu semantiku uzastopnog re-exporta kao novog
  `DistributionInstance` događaja.
- Ne uvoditi DB-backed visual-system lookup/schema promjenu; per-plan in-process
  serialization je dovoljna za ovaj task.
- Ne mijenjati UI-only ulogu `approve-gate` dugmeta.

# SLJEDEĆE

1. Zamijeniti `logger.exception` sigurnim type-only logovanjem i dodati sentinel
   `caplog` regresijski test.
2. Serializirati cijeli export za isti `(campaign_id, plan_id)` i dodati
   deterministički concurrent worker-thread test koji potvrđuje jedan validan
   ZIP i nedupliran visual system.
3. Dodati stvarni two-campaign/two-plan ownership test i export lifecycle exact
   DTO test.
4. Ponoviti targetirani/full gate i zatražiti Codex rereview. HIGH task ne ide
   na Human Owner approval dok se ova tri nalaza ne zatvore.
