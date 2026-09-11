# ACS-S2-017 — fix round 1 (F2 SSRF fail-open + missing SW test coverage)

**Datum:** 2026-09-11
**Agent:** Claude (isti agent koji je uradio i `2026-09-11-ACS-S2-017-review-claude.md`, REJECT verdikt)
**Scope:** popravka BLOCKING FINDINGS iz review-a, bez širenja van `allowed_paths` iz Task Contract-a

## Šta je popravljeno

### F2 (CRITICAL) — redirect pre-check fail-open → fail-closed

`src/ai_campaign_studio/subprocess_runtime/playwright_worker.py`:
- `_redirect_unsafe_reason()`: `except requests.RequestException` više NE vraća
  `None` (tretirano kao bezbjedno) — vraća `f"redirect_check_failed:{type(exc).__name__}"`
  (tretirano kao nebezbjedno, fail closed). Ovo je jedina odbrana za
  top-level navigation redirect hop-ove (`context.route` ih ne presreće —
  dokumentovano u kodu), pa je fail-open ovdje bio direktan SSRF bypass.
- Read timeout za pre-check više nije fiksnih 3.0s niti 1:1 vezan za puni
  `request.timeout` (probao sam obje krajnosti) — `min(request.timeout, 5.0)`
  po hop-u: dovoljno da izbjegne lažne "unsafe" odluke za redirect koji je
  tek malo spor (potvrđeno: redirect sa 3.5s kašnjenjem sad se ispravno
  ODOBRAVA/ODBIJA na osnovu stvarnog sadržaja, ne na osnovu timeout-a), a
  ograničeno da worst-case (5 hopova × 5s = 25s) ne postane neproporcionalan
  navigacionom budžetu.

### Nedostajući regression test za F2

`tests/integration/infrastructure/web_ingestion/test_browser_ssrf.py`:
novi `test_redirect_check_failure_fails_closed` — redirect endpoint koji
kasni 2.0s (probija skraćeni `timeout=1` fetcher-a u testu), potvrđuje
`result.error` počinje sa `unsafe:` i `hits['leak']==0`.

### Service Worker — netestirana tvrdnja zamijenjena stvarnim testom

Isti fajl: `test_service_worker_never_becomes_active_when_blocked` +
control `test_service_worker_activates_control_without_block`.

**Važna korekcija tokom rada**: prva verzija testa je pretpostavila da
`navigator.serviceWorker.register()` baca grešku kad je blokiran — POGREŠNO.
Playwright dokumentacija (potvrđeno web search-om) kaže da `service_workers=
"block"` PREPISUJE `register()` da i dalje RESOLVE-uje (uz console warning
"Service Worker registration blocked by Playwright"), bez stvarne
registracije. Prvi test je zato lažno prijavio "registered" kao bug. Ispravljen
test provjerava stvarno bezbjednosno relevantno svojstvo: da worker NIKAD ne
postane `active`/`controlling` (ograničeno čekanje, ne beskonačno) + da se
tačna Playwright warning poruka pojavi u konzoli. **Rezultat: `service_workers=
"block"` RADI ispravno** — ovo NIJE bio stvaran bug, bio je nedostatak testa
koji je prikrivao da se ovo nikad nije provjerilo.

## Verifikacija

```
Live reproducer (F2, prije popravke): hits['leak']=1, result.error=None → SSRF PROŠAO
Live reproducer (F2, poslije popravke): hits['leak']=0, result.error='unsafe:ip_not_global:127.0.0.1' → BLOKIRANO
python -m ruff check <izmijenjeni fajlovi>: All checks passed
python -m mypy src/ai_campaign_studio/subprocess_runtime: Success, 0 errors
python -m pytest -q <6 target G8 test fajlova>: 36/36 PASS (72-85s, uključuje 3 nova testa)
python -m pytest -q (puna regresija): 1534 passed, 0 failed, 429s
```

## Šta nije dirano

`url_safety_policy.py` (G3, forbidden), `http_fetcher.py` (G3, forbidden),
`ingest_brand_sources.py` (G6, forbidden) — sve ostalo van `allowed_paths` iz
Task Contract-a. F3 (body cap post-hoc) i F4 (stderr=DEVNULL) ostaju
dokumentovani, prihvaćeni rizici (arhitektonski ograničeni, non-blocking),
nisu dirani ovom rundom po review preporuci.

## Napomena o procesu

Ovaj fix je urađen i verifikovan od strane ISTOG agenta koji je pisao
originalni review (REJECT verdikt) — normalno bi ovo tražilo SVJEŽU
nezavisnu adversarial rundu prije Human Owner odobrenja (Task Contract §6,
workflow puni ciklus za HIGH risk). Preskočeno na eksplicitan zahtjev Human
Ownera (2026-09-11, "da se ne mučimo, popravi pa merdžuj/komituj/pušuj") —
zabilježeno ovdje transparentno, ne prećutno. Nezavisna live-reprodukcija
prije/poslije popravke (gore) je urađena kao minimalna zamjena, ne kao puna
zamjena za drugu review rundu.

## Sljedeće

Nakon merge-a: `npx gitnexus analyze` (GitNexus index osvježavanje, per
Korak 5). F3/F4 ostaju kao poznata ograničenja za eventualni follow-up kad
se G8 stvarno ožiči u `ingest_brand_sources.py`.
