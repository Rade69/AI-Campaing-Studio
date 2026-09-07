# ACS-F1-047 — fix-brief za MiniMax (poslije Codex REJECT #2, PR #12)

Odnosi se na:
`H:\ai-campaign-studio-worktrees\ACS-F1-047-job-manager-wiring\agent_reports\2026-09-07-ACS-F1-047-rereview-codex.md`
(verdict REJECT, 1 blocking finding: BF-CODEX-3). BF-CODEX-1 i
BF-CODEX-2 su POTVRĐENO zatvoreni -- Codex to eksplicitno kaže, ovaj
finding je NOV, otkriven u tvom OWN fixu za BF-CODEX-1.

BF-CODEX-3 je zapravo TAČNO ona "ne-blokirajuća opservacija" koju sam
JA sam primijetio i prijavio Codex-u na procjenu u prošlom handoff-u
(`2026-09-07-ACS-F1-047-brief-za-codex-2.md`) -- Codex je otišao dalje
i STVARNO reprodukovao uživo (JS harness) koliko je loše: ne samo
duplirani submit, nego i preuranjeno brisanje markera koje otvara
TREĆI submit poslije prvog cancel-a. Ozbiljnije nego što sam
pretpostavio, opravdano blocking.

PR #12 se i dalje NE MERGE-uje. HIGH task, pun ciklus i dalje važi.

## Nezavisna verifikacija (coordinator, prije ovog briefa)

Repo nema JS test harness/CI za `app.js`, pa sam napravio SOPSTVENI
minimalan Node repro (izvučen TAČAN `generateContent()` tekst iz
trenutnog `app.js`-a, stub `document`/`window.pywebview.api` sa
odgođenim submit Promise-om, fake dugme sa `dataset`/`addEventListener`).
Dva "klika" prije nego prvi IPC poziv resolve-uje:

```text
submit_calls_before_first_response = 2
acsJobActive after both clicks (pre-resolve) = undefined
acsJobActive after both submits resolved = 1
click listeners attached to button = 2

BF-CODEX-3 CONFIRMED: double-click produced 2 backend submits.
```

Potvrđeno identično Codex-ovom nalazu: `button.dataset.acsJobActive`
se postavlja TEK POSLIJE `await api.generate_campaign_content(...)`
(linija ~401 u trenutnom kodu), pa oba klika prije prvog resolve-a
prolaze re-entrancy guard (koji provjerava marker na liniji ~300) i
oba pozivaju backend. Dva nezavisna `_onClickWhileRunning` listenera
se stackuju na ISTOM dugmetu (dijele istu `dataset`/`textContent`
labelu), pa prvi cancel klik/prvi terminalni tracker prerano čisti
zajednički marker dok je DRUGI job još RUNNING -- otvara VRATA za
TREĆI, spurious submit. Backend per-pair lock i dalje sprečava
duplikate u BAZI (potvrđeno prošlom rundom), ali UI ugovor je
nedeterminističan.

## Fix — marker se postavlja SINHRONO PRIJE prvog await-a

**Lokacija**: `generateContent(button)`, `app.js`.

**Šta promijeniti**:

1. Pomjeriti `button.dataset[JOB_ACTIVE_ATTR] = '1';` sa trenutne
   pozicije (poslije `await api.generate_campaign_content(...)`,
   unutar `if (!submitResult.ok)` provjere) NA MJESTO ODMAH POSLIJE
   `api`-availability provjere, PRIJE `button.textContent = 'Pokrećem…';`
   i prije `try { ... await ... }` bloka -- dakle prije BILO KAKVOG
   `await`-a, sinhrono u istom event-loop tick-u kao provjera guard-a
   na početku funkcije.
2. **Obavezno dodati čišćenje markera na sync-reject grani**
   (`if (!submitResult || !submitResult.ok) { ... }`) -- trenutno ta
   grana NE čisti marker jer ga do sad nije ni postavljala prije
   await-a; sad MORA (`delete button.dataset[JOB_ACTIVE_ATTR];`) prije
   `return`, inače neuspio submit (npr. SUPERSEDED plan) TRAJNO
   zaključava dugme (guard na početku funkcije bi ga zauvijek
   blokirao).
3. Grane koje VEĆ čiste marker (outer `catch (err)` na dnu funkcije,
   `_pollOnce`-ov IPC-blip catch, `_renderTerminal`) OSTAJU
   nepromijenjene -- one su već ispravne iz prošle runde.

Rezultat: prvi klik odmah postavlja marker (prije IPC round-trip-a),
pa DRUGI, brzi klik na ISTI event-loop tick vidi marker `'1'` i
`return`-uje na samom početku funkcije -- NEMA drugog submita, NEMA
drugog trackera/listenera na dugmetu.

## Test (Codex traži "JS runtime test sa deferred submit Promiseom")

Repo nema formalnu JS test infrastrukturu (nema `package.json`, nema
JS test runner-a u CI-ju) -- ovo NIJE nešto što ovaj task treba da
uvede kao novu trajnu infrastrukturu (van scope-a, veća odluka).
Prihvatljivo rješenje za OVU rundu: **standalone Node skripta**
(isti pristup kao moj repro gore -- izvuci `generateContent`-ov
trenutni tekst, stub `document`/`window.pywebview`, deferred-Promise
`generate_campaign_content`, dispatch dva "klika" prije resolve-a),
čiji se izlaz uključi DOSLOVNO u evidence (kao dokaz), analogno kako
je ACS-F1-046 string-assertion test za `escapeHtml` bio prihvaćen kao
alternativa headless DOM testu kad harness ne postoji. Ako želiš da
skriptu trajno uključiš u repo (npr. `scripts/js_smoke_tests/`), javi
mi prije nego je commituješ -- to je mala scope odluka koju mogu
odobriti brzo, ali nije obavezna za sam fix.

Minimalna asercija koju test/skripta mora dokazati:
- Dva brza poziva `generateContent(button)` PRIJE nego prvi
  `generate_campaign_content` resolve-uje -> TAČNO JEDAN backend
  submit poziv.
- Poslije resolve-a, TAČNO JEDAN `click` listener na dugmetu.

## Šta NE dirati (Codex-ovo ograničenje, i dalje važi)

- Ne dirati ispravan `try/finally` partial-outcome fix (BF-CODEX-2).
- Ne vraćati `button.disabled` kao RUNNING guard -- to bi ponovo
  slomilo cancel (BF-CODEX-1 bi se vratio).
- Ne vraćati `_find_current_job_id` -- `token.job_id` kanal ostaje.
- Ne širiti u `domain/`/`application/`/`ports/`/`infrastructure/database/`/
  export flow.
- Ne refaktorisati `JobManager` -- ovo je čisto JS state-timing fix.

## Verifikacija prije re-review-a

```bash
python -m pytest tests/unit/jobs/ tests/unit/presentation_webview/ tests/unit/presentation/ -v
python -m pytest -q
python -m ruff check .
python -m mypy src
```

Plus Node repro (gore) kao dokaz da je BF-CODEX-3 stvarno zatvoren.
Sve mora proći, 0 regresija. Poslije zelenog run-a, tražiti Codex
rereview PR #12-a treći put. HIGH task ne ide na Human Owner approval
dok Codex ne da PASS.
