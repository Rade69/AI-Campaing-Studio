---
verdict: REJECT
scope: PASS
acceptance: REJECT
architecture: PASS
security: REJECT
tests: REJECT
gitnexus_impact: NOT_REQUIRED
blocking_findings:
  - "F2 CRITICAL: _redirect_unsafe_reason() fails OPEN on any requests.RequestException (incl. plain timeout) during the redirect-chain pre-check — live-reproduced full SSRF: a redirect target that simply delays its response past the 3s check timeout (_REDIRECT_CHECK_TIMEOUT) bypasses the ONLY control protecting top-level navigation redirects (context.route does not intercept those, per the module's own docstring), and the browser navigates straight through to a loopback/private target."
  - "Missing regression test for the fail-open path — the only existing redirect test (test_redirect_to_literal_ip_is_blocked) exercises the fast-redirect happy path only; nothing in the suite would catch a regression or confirm a fix of the fail-open bug."
  - "service_workers=\"block\" has ZERO test coverage — no test registers a Service Worker and verifies interception. This is an explicit Codex-review-required item in the task contract (§6) and was never actually checked in two review rounds (coordinator round1 marked it 'VERIFIED' based on code reading, not a reproducer)."
---

# ACS-S2-017 (S2-G8 Playwright fallback) — fresh adversarial re-review

CILJ: Nezavisna, reproducer-based adversarial provjera F2 (redirect SSRF
TOCTOU), F3 (body cap post-hoc DoS), F4 (stderr=DEVNULL diagnostics loss) +
mutation-test na ključne guard-ove, jer je Codex koji je ovo trebao raditi
stalno prekidan. Coordinator round1 već dao PASS sa 2 OUT_OF_SCOPE_FINDINGS
(F1 contract greška — irelevantno ovdje, F2 redirect-hop mitigacija
"prihvaćena" bez live fail-open testa).

URAĐENO: REJECT — pronađen live-reprodukovan kritičan SSRF bypass u F2 koji
ni implementer ni coordinator nisu testirali (testirali su samo happy-path
brz redirect). Bypass je trivijalan za napadača koji kontroliše redirect
cilj (samo usporiti odgovor >3s), ne zahtijeva DNS rebinding ni bilo šta
sofisticirano.

## Scope provjera

```
git diff --stat main...HEAD   → 15 fajlova, +2065/-0
```

15, ne 14 kao u coordinator izvještaju — razlika je tačno 188 linija, što je
`agent_reports/2026-09-11-ACS-S2-017-coordinator-round1.md` sam (coordinator
je brojao PRIJE pisanja svog izvještaja — 2065-188=1877, tačno se poklapa sa
coordinator brojkom). Nema stvarnog neslaganja.

`git diff --name-only` potvrđuje: SVI izmijenjeni fajlovi su u
`allowed_paths` (Task Contract §1) plus dva agent_report fajla. **ZERO
touches na `forbidden_paths`** — potvrđeno directno, ne preuzeto od
implementera. `scope: PASS`.

## PROVJERENO

### F2 — redirect SSRF TOCTOU prozor — **BYPASS POTVRĐEN LIVE**

Pročitan `_redirect_unsafe_reason()`
(`src/ai_campaign_studio/subprocess_runtime/playwright_worker.py:69-100`):
prati redirect lanac preko `requests.get(allow_redirects=False, timeout=(3.0,
3.0))`, validira svaki hop kroz `UrlSafetyPolicy` PRIJE nego browser
navigira. Docstring sam kaže: "best-effort: network failures/timeouts fall
through to the browser's own handling" — i kod to doslovno radi:

```python
except requests.RequestException:
    return None  # best-effort: let the browser surface the failure
```

`None` znači "nijedan nebezbjedan hop nađen" (SAFE) u pozivaocu
(`_process_one`, linija 131-138). Problem: `context.route()` **ne presreće
redirect hop-ove top-level navigacije** (potvrđeno u samom kodu/docstringu,
"verified live" od strane implementera) — što znači da je
`_redirect_unsafe_reason` JEDINA odbrana za top-level redirect ka
privatnom/loopback cilju. Fail-open na bilo koji `requests.RequestException`
znači: ako se provjera ne uspije završiti iz BILO KOJEG razloga (timeout,
konekcija odbijena, TLS greška...), odbrane NEMA — browser ide dalje bez
ikakve provjere redirect lanca.

**Live reproducer** (server koji na `/redirect-slow` spava 3.5s pa vrati 302
ka `http://127.0.0.1:{port}/leak`, dovoljno sporo da probije `requests`-ov
3s timeout ali dovoljno brzo za browser-ov ~20s navigation timeout):

```
=== Step 1: direktan _redirect_unsafe_reason() poziv ===
elapsed=5.05s  reason=None
!!! FAIL-OPEN CONFIRMED: pre-check timed out and returned None (treated as SAFE)

=== Step 2: pun PlaywrightFetcher.fetch() end-to-end ===
elapsed=12.15s
result.error=None status_code=200
hits['leak']=1
!!! SSRF CONFIRMED LIVE: browser reached the loopback target via the slow redirect
```

Ovo NIJE teoretski DNS-rebinding scenario (koji bi zahtijevao kontrolu DNS-a
sa niskim TTL-om — coordinator je residual risk okarakterisao kao "isti nivo
kao G3" upravo u tom smislu). Ovo je mnogo jednostavniji, direktno
eksploatabilan bypass: napadač koji kontroliše redirect cilj (realan model
prijetnje za ovaj feature — G8 obrađuje URL-ove koje korisnik/kampanja
unosi) samo treba da uspori odgovor. Coordinator-ov F2 verifikacioni test
(`test_redirect_to_literal_ip_is_blocked`) testira SAMO brz redirect —
zeleno svjetlo tog testa NE dokazuje da je mitigacija efektivna protiv
realnog napadača.

**Kontradikcija sa Acceptance §5.2**: "Redirect chain ka literal IP-u →
blocked" nije tačno u opštem slučaju — tačno je samo kad server odgovori
brže od 3s.

### F3 — body cap post-hoc (DoS) — potvrđeno čitanjem koda, konzistentno sa coordinator nalazom

```python
body_html = page.content()          # cijeli renderirani DOM u memoriji PRVO
body_bytes = body_html.encode("utf-8")
if len(body_bytes) > request.max_bytes:   # provjera TEK POSLIJE
```

`page.content()` nema streaming/veličinski limit u Playwright API-ju — cijeli
DOM mora biti materijalizovan prije nego što se dužina uopšte može izmjeriti.
Za razliku od G3 (`http_fetcher.py`) koji provjerava `Content-Length` PRIJE
buferovanja i dodatno stream-uje chunk-po-chunk sa ranim prekidom — G8
strukturno NE MOŽE to isto, jer JS-renderirani sadržaj ne postoji dok
Chromium ne završi izvršavanje. Coordinator-ova karakterizacija
"legitimna trade-off" je ispravna kao arhitektonska ocjena, ALI izvještaj
to tretira gotovo kao zatvoreno pitanje bez i jednog DoS reproducera (npr.
stranica koja JS-om generiše ogroman DOM) koji bi pokazao STVARNU cijenu
(koliko memorije/vremena prođe prije nego cap uhvati). Nisam radio taj live
test (van budžeta ove runde) — ovo ostaje **NOT VERIFIED (magnitude)**,
mehanizam sam je potvrđen čitanjem koda. Ne blokira merge, ali ne treba
tretirati kao potpuno zatvoreno.

### F4 — stderr=DEVNULL diagnostics loss — potvrđeno čitanjem koda

`playwright_fetcher.py:105`: `stderr=subprocess.DEVNULL`. Svaki Python
traceback, Chromium crash log ili Playwright interna greška iz worker
subprocess-a se bespovratno gubi. Parent samo zna DA je worker umro
(`proc.poll()`), nikad ZAŠTO. Coordinator-ovo obrazloženje (PIPE bez čitača
= deadlock rizik) je tehnički tačno i legitiman razlog za DEVNULL umjesto
PIPE — ALTERNATIVA (ring-buffer reader thread koji čita i odbacuje/čuva
zadnjih N linija, coordinator sam to pominje kao mogući follow-up) nije
implementirana niti je testirana odsutnost. Ne blokira merge (nije
korektnosni ni bezbjednosni bug, samo operativna slijepa tačka) — ali na
Windows-u (§9 posebna ograničenja, poznata krhkost oko Chromium instalacije)
ovo će vjerovatno prvi put zasmetati baš kod prve produkcijske instalacije
kad worker ne uspije da se pokrene.

### Mutation test — `_redirect_unsafe_reason` guard je stvaran regression-guard

Privremeno onemogućen redirect-check (`if False and redirect_reason is not
None:`) → `test_redirect_to_literal_ip_is_blocked` FAILED (`hits['leak']==1`,
`result.error is None` umjesto `unsafe:...`) → vraćeno → `git diff --stat`
čist (mutacija potpuno reverzovana, nema ostatka u working tree-u). Test
JESTE prava odbrana za ono što pokriva — problem je što ne pokriva fail-open
slučaj (vidi F2 gore).

### Service Worker block — NETESTIRANO

`grep -rn "service_worker" tests/` → nula pogodaka. Nijedan test ne
registruje Service Worker i provjerava da li je njegov fetch presretnut.
Task Contract §6 eksplicitno traži ovu provjeru kao Codex fokus tačku —
nikad nije urađena, u dvije review runde. Ne mogu potvrditi ni oboriti da li
`service_workers="block"` stvarno radi (Playwright API opcija postoji i po
dokumentaciji bi trebala spriječiti REGISTRACIJU Service Worker-a u cijelom
context-u, što je jača garancija od "blokiraj SW fetch-eve" — ali "trebala
bi" nije isto što i dokazano ovdje).

### Wiring / blast radius (zamjena za formalni GitNexus alat)

```
grep -rln "PlaywrightFetcher|PlaywrightWorker" src/ tests/  → samo unutar G8 test fajlova
grep -rln "detect_js_heavy" src/                            → nula pogodaka van js_render_detector.py
grep classify_target/PageClassifier u ingest_brand_sources.py → nula pogodaka
```

G8 je trenutno potpuno neožičen u produkcijski pipeline (G6
`ingest_brand_sources.py` ga ne poziva) — konzistentno sa "opcioni,
SAMO SPIKE+gate" statusom iz contract-a i sa `forbidden_paths` koji
eksplicitno isključuje taj fajl. Blast radius je efektivno nula DOK se ne
ožiči u budućem tasku — što F2 čini HITNIJIM da se popravi PRIJE tog
ožičavanja (kad će G8 stvarno primati URL-ove iz nepouzdanog izvora), ne
manje hitnim.

## GITNEXUS / IMPACT

`gitnexus_impact: NOT_REQUIRED` — nisam pokrenuo formalni GitNexus MCP alat
u ovoj sesiji (nije potvrđeno indeksiran/dostupan za ovaj worktree u ovom
kontekstu). Zamijenjeno ručnom grep-baziranom provjerom pozivalaca (vidi
"Wiring / blast radius" gore), koja potvrđuje isti zaključak kao contract-ova
sopstvena tvrdnja ("SubprocessWorker = new module, isolated"). Ovo je
**Not verified** stavka po ACS evidence formatu — formalni GitNexus impact
report nije priložen.

## BLOCKING FINDINGS

1. **F2 (CRITICAL)** — fail-open na `requests.RequestException` u
   `_redirect_unsafe_reason` dozvoljava potpun SSRF bypass kroz spor
   redirect odgovor. Live reprodukovano, izvan svake sumnje.
2. Nedostaje regression test za fail-open putanju.
3. `service_workers="block"` efektivnost nikad nije testirana ni
   reprodukovana, uprkos eksplicitnom contract zahtjevu.

## STANDARDNA VERIFIKACIJA (ponovo pokrenuto nezavisno)

```
python -m ruff check <G8 fajlovi>: All checks passed
python -m mypy <subprocess_runtime + playwright_fetcher>: Success, 0 errors
python -m pytest -q <6 target test fajlova>: 33 passed in 72.18s
  (poklapa se sa prijavljenih "33/33 PASS in 73.17s")
git diff --stat main...HEAD: 15 fajlova (razlika od "14" objašnjena gore,
  bez stvarnog neslaganja)
```

Nisam pokrenuo pun `pytest -q` (1488+ regresioni set) — van budžeta ove
runde, targeted G8 set je dovoljan za scope ovog review-a.

## ADVERSARIALNA PROVJERA

- F2 live reproducer (slow-redirect fail-open) — **BYPASS POTVRĐEN**, vidi
  gore.
- Mutation test na `_redirect_unsafe_reason` guard — test je real regression
  guard za ono što pokriva (potvrđeno FAIL na mutaciji, potvrđeno PASS i čist
  `git diff` poslije revert-a).
- F3 mehanizam potvrđen čitanjem koda; magnituda DoS-a nije live testirana
  (Not verified).
- F4 potvrđeno čitanjem koda (stderr=DEVNULL, nema alternative).
- Service Worker block efektivnost — Not verified (nema testa, nisam gradio
  novi zbog vremenskog budžeta; prioritet je bio F2 koji se pokazao kritičan).

## NE DIRATI U FIX RUNDI

Sve van `allowed_paths` iz Task Contract-a (G3 SSRF policy, G4/G5/G6/G7b,
domain/). Fix za F2 treba ostati unutar `_redirect_unsafe_reason` i njenog
poziva u `_process_one` (ili u `route_handler`/subprocess strani) — NE u
`url_safety_policy.py` (forbidden).

## SLJEDEĆE

1. Implementer: popraviti fail-open na F2 — minimalno, `except
   requests.RequestException` ne smije vratiti `None` (safe); treba vratiti
   unsafe reason (fail CLOSED) ili barem eksplicitno ograničen
   retry/fallback koji ne pušta browser dalje bez provjere. Dodati
   regression test analogan `repro_f2_redirect_toctou.py` (slow-redirect
   scenario) u `test_browser_ssrf.py`.
2. Implementer/QA: dodati barem jedan Service Worker registration +
   interception test prije nego se F2 ponovo šalje na review.
3. Coordinator: NE prihvatati "VERIFIED" oznaku za sigurnosnu mitigaciju bez
   live reproducer-a koji pokriva i failure/edge-case putanju, ne samo happy
   path — ovo je isti obrazac kao F2 ovdje (test postoji, zelen je, ali ne
   dokazuje ono što izvještaj tvrdi).
4. F3/F4 mogu ostati kao dokumentovan, prihvaćen rizik za MERGE ove runde
   (arhitektonski ograničeni / operativni, ne regresija) — ali treba ih
   eksplicitno upisati kao poznata ograničenja u finalni merge log, ne samo
   u coordinator draft.
5. Nakon fix-a za F2: nova adversarial runda (mutation + live reproducer na
   popravljenoj verziji) prije Human Owner odobrenja — ovo je HIGH risk
   task, puni ciklus (§6) i dalje važi.

---

```text
CILJ: Fresh adversarial re-review F2/F3/F4 + mutation test na S2-G8 Playwright fallback, jer je Codex stalno prekidan.
URAĐENO: REJECT — live-reprodukovan kritičan SSRF bypass u F2 (redirect pre-check fail-open na timeout/network error); ostali nalazi (F3, F4, netestiran service_workers) su non-blocking napomene.
NE DIRATI: G3 url_safety_policy.py i sve forbidden_paths iz Task Contract-a; fix ostaje unutar subprocess_runtime/playwright_worker.py.
SLJEDEĆE: implementer popravlja F2 fail-open (fail closed umjesto fail open) + dodaje regression test za taj scenario i barem jedan Service Worker test, pa nova adversarial runda prije Human Owner odobrenja.
```
