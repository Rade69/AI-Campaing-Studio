# ACS-GUI-014 — vizuelna traka napretka za ingestion + kritičan bugfix

**Datum:** 2026-09-11
**Agent:** Claude
**Scope:** frontend-only (HTML/CSS/JS), bez izmjena backend-a — svi
`progress_current`/`progress_total`/`phase` podaci su već postojali u
`JobState` od ACS-GUI-011, samo se nisu prikazivali vizuelno.

## Šta je urađeno

1. Vizuelna traka napretka (`.ingest-progress`) ispod "Pokreni ingestion"/
   "Obriši sve" dugmadi — determinate (stvarni %) kad job javi
   `progress_total>0` (FETCH/EXTRACT/BUILD_FACTS faze), indeterminate
   (animirana klizeća traka) prije toga (DISCOVER faza, prije prvog
   izvještaja).
2. Status tekst sad prikazuje i brojeve: "U toku — FETCH (3/12)…".

## KRITIČAN nalaz tokom pisanja testa — postojeći bug u ACS-GUI-011

Dok sam pisao Node-VM test za traku napretka (koji prvi put stvarno
POKREĆE `startIngestion()` unutar izvršnog JS okruženja, ne samo poziva
bridge direktno iz Pythona kao svi moji raniji "live" testovi), test je
pukao sa `ReferenceError: POLL_INTERVAL_MS is not defined`.

**Uzrok:** `app.js` je niz odvojenih top-level IIFE-ova (`(function(){...})()`).
`POLL_INTERVAL_MS` je deklarisan unutar IIFE-a "Studio sadržaja"
(linija ~319), a `startIngestion()` (dodano u ACS-GUI-011) je unutar
POTPUNO ODVOJENOG, sibling IIFE-a (fact-review, linija ~1169+) — ta dva
IIFE-a NE DIJELE scope. Referenciranje `POLL_INTERVAL_MS` iz
fact-review IIFE-a je referenca na nepostojeću promjenljivu.

**Stvarna posljedica u pravoj aplikaciji:** klik na "Pokreni ingestion" bi:
1. Uspješno pozvao `start_brand_ingestion` (posao STVARNO kreće na
   backend-u — fetch/extract/build_facts sve rade normalno)
2. ODMAH nakon toga pukao na `setInterval(fn, POLL_INTERVAL_MS)` pozivu
   (ReferenceError, neuhvaćen)
3. Dugme ostaje zauvijek `disabled`, status tekst zaglavljen na
   "Pokrećem preuzimanje…", `loadFactReview()` se nikad ne pozove

Ovo se savršeno poklapa sa korisnikovim opisom ("sporo, ne vidim da li se
uopšte nešto učitava") — vjerovatno NIJE bila (samo) sporost mreže, nego
ovaj crash koji je zamrzavao UI dok je posao u pozadini tiho završavao.
`node --check` (syntax-only) ovo nije mogao uhvatiti jer nikad ne
IZVRŠAVA IIFE tijela — samo test koji stvarno pokreće JS u `vm` modulu je
ovo otkrio.

**Fix:** lokalna `const INGEST_POLL_INTERVAL_MS=1200` unutar fact-review
IIFE-a, umjesto posezanja u tuđi scope.

**Napomena o procesu:** ovo je bug u već mergovanom ACS-GUI-011 (i time
posredno u ACS-GUI-012/013 koji su nastavili na istom kodu) — popravljen
je ovdje jer je otkriven baš dok se radilo na direktno povezanoj funkciji,
ne kao nepovezan "refactor u istom commit-u".

## Verifikacija

```
Novi Node-VM test (test_ingestion_progress_bar_determinate_then_hidden_on_terminal):
  Tick 1 (RUNNING, total=0)     → indeterminate=True, hidden=False
  Tick 2 (RUNNING, current=1/4) → indeterminate=False, width="25%"
  Tick 3 (SUCCEEDED)            → hidden=True
  → PRIJE fix-a: test je pukao sa ReferenceError (potvrđuje bug postojao)
  → POSLIJE fix-a: 6/6 test_brend_review_ui.py PASS

Live bridge re-provjera (https://example.com/, nepromijenjeno od
ACS-GUI-011, backend path nije bio uzrok bug-a): fetched=2 extracted=6
candidates=6 — i dalje radi.

ruff/mypy: čisto
pytest (ciljano, presentation_webview): 340/340 PASS
pytest (puna regresija): 1546 passed, 0 failed, 427.95s
```

## Šta korisnik treba znati

Nakon ove izmjene, "Pokreni ingestion" bi TREBALO da stvarno prikazuje
živ napredak umjesto da izgleda zamrznuto — ovo je vjerovatno rješenje i
za osjećaj "sporo/ne vidim da li radi", ne samo dodatak trake napretka.

## Kako testirati

Zatvori postojeći prozor aplikacije (koristi STARI, pokvareni JS) i
pokreni ponovo:
```
cd "H:\AI Campaing Studio"
$env:PYTHONPATH = "H:\AI Campaing Studio\src"
.venv\Scripts\python.exe -m ai_campaign_studio.presentation_webview
```
Brend → Pregled činjenica → unesi URL → Pokreni ingestion — traka
napretka bi trebalo da se pojavi i pomjera, dugme se vraća u normalno
stanje po završetku.
