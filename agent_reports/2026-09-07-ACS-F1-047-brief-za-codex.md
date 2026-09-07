# → ZA CODEX — ACS-F1-047 adversarial review

PR #12: https://github.com/Rade69/AI-Campaing-Studio/pull/12
Branch: `task/ACS-F1-047-job-manager-wiring` (rebase-ovan na main,
commit sadrži i fix rundu 2).
Implementer: MiniMax. Task contract:
`agent_reports/ACS-F1-047-task-contract.md`.

## Šta ovaj task radi

`generate_campaign_content` (Studio sadržaja) je radio sinhrono unutar
jednog `js_api` poziva -- plan sa 12 stavki × ~10s po AI pozivu = ~2
minuta zamrznuto dugme. Sad je job-backed preko `JobManager`: sync
boundary validation + approve + SUPERSEDED-reject ostaju sinhroni
(brz odgovor), per-piece AI petlja ide na `ThreadPoolExecutor` worker
thread preko closure-a koji otvara SOPSTVENI `_resource_scope`
(HOTFIX-002 obrazac primijenjen na job thread). Novi `get_job_status`/
`cancel_job` js_api metodi + `app.js` polling/cancel UI.

## Runda 1 -> BLOCKING nalaz -> fix runda 2 (VAŽNO za tvoj review)

Prva implementacija (`3253330`) je imala closure koji nije znao
sopstveni `job_id` -- koristio je `_find_current_job_id(job_manager)`,
heuristiku koja traži TAČNO JEDAN `RUNNING` job na CIJELOM, dijeljenom
`JobManager`-u (`max_workers=4`). Čim su postojala 2+ RUNNING joba
(bilo kog tipa, ne samo `generate_campaign_content`), lookup je vraćao
`""` -- progress i terminalni `generated_count`/`content_piece_ids`
su ostajali na 0/() IAKO JE sadržaj STVARNO generisan.

Ja sam ovo reprodukovao izolovano (5/5 pokušaja) I potvrdio da se VEĆ
dešava u implementer-ovom vlastitom BF-3 concurrent-lock testu (2/3
poziva `_find_current_job_id` ambiguous) -- test je prolazio jer je
provjeravao samo agregatni DB count, ne per-job outcome. Puna analiza:
`agent_reports/2026-09-07-ACS-F1-047-review-claude.md`.

**Fix (runda 2, `77a477b` sadržaj)**: `CancellationToken` sad nosi
svoj `job_id` kao aditivan atribut, postavljen u `JobManager.submit()`
GDJE JE `job_id` VEĆ POZNAT (prije registracije future-a) -- potpuno
deterministički, bez ambiguity-a ikad. `_find_current_job_id` u
potpunosti uklonjen. Novi test
`test_two_concurrent_jobs_each_know_their_own_job_id`: dva konkurentna
`generate_campaign_content` poziva za RAZLIČITE `(campaign_id,
plan_id)` parove (lock ih NE serijalizuje), svaki asertuje SOPSTVENI
`generated_count == 2`.

**Ja sam ovaj fix mutation-testirao**: privremeno vratio staru
`cancellation.py`/`manager.py` (bez `token.job_id`) dok closure i dalje
čita `token.job_id` -- novi test PUCA (job završava `FAILED` zbog
`AttributeError`), potvrđujući da test STVARNO hvata regresiju, ne
samo prolazi slučajno. Fajlovi vraćeni preko `git checkout --`
odmah nakon.

## Ostalo iz runde 1 (nezavisno potvrđeno PASS, nepromijenjeno rundom 2)

- Objective #1 (`JobManager.update_progress`) -- lock/emit obrazac
  identičan već-hardened `_run`/`_finish` iz ACS-HOTFIX-001.
- DTO shrink (`GenerateContentResultUiModel` 7->5 polja) -- nema
  preostalih referenci na stara polja van `JobState`.
- BF-4 (SUPERSEDED rejection) -- i dalje potpuno sinhrono, 0 AI poziva.
- Idempotentnost re-klika -- drugi poziv na već-generisanu kampanju
  ne duplira.
- `get_job_status`/`cancel_job` -- unknown `job_id` -> sync
  `VALIDATION_ERROR`, nema `JobError` leak-a.

## N1-N4 (manji nalazi, sve popravljeno u rundi 2)

- N1: dokstring je tvrdio "single executor thread" (činjenično
  netačno, `max_workers=4`) -- ispravljeno da jasno kaže zašto je lock
  potreban.
- N2: zastarjeli komentar u `_LIFECYCLE_ERROR_MAPPERS` bloku (stara
  DTO polja) -- ažuriran, generalizovan.
- N3: mrtav kod u `app.js` (`_pollOnce`+prvi `setInterval`,
  `_onTerminal` nikad pozvan) -- svedeno na jedan `_pollOnce` koji radi
  i progress i terminal granu.
- N4: `jobs/models.py` + `jobs/cancellation.py` izmijenjeni van
  originalnog `allowed_paths` -- retroaktivno prijavljeno kao
  `OUT_OF_SCOPE_FINDING` u fix-brief-3 evidence-u, oba benigna/aditivna,
  odobreno.

## Verifikacija (moja, nakon rebase-a na main)

```text
python -m pytest -q          -> 1071 passed
python -m ruff check .       -> All checks passed!
python -m mypy src           -> Success: no issues found in 175 source files
```

CI na PR #12: u toku, javiću ako padne.

## Tvoj fokus (review focus iz kontrakta + moja runda 1)

- Closure-ov resource lifecycle na job thread-u -- STVARNA
  worker-thread reprodukcija, ne pretpostavka (isti nivo kao
  HOTFIX-002).
- `token.job_id` kanal -- provjeri da NEMA drugog puta kroz koji bi se
  desila ista ambiguity-klasa greška (npr. da li BILO KOJI drugi
  budući job type koji dijeli `JobManager` mogao ponovo uvesti sličnu
  heuristiku).
- Otkazivanje -- STVARNO zaustavlja petlju (test već postoji,
  provjeri adversarial edge-case: cancel taman kad je job na granici
  RUNNING->terminal).
- Progress polling ne curi resurse (`setInterval` se čisti na SVAKOJ
  terminalnoj grani i grešci -- provjereno kod, ali probaj adversarial
  IPC-failure scenario).
- Da li postoji BILO KOJI drugi skriveni "ambiguity" ili "guess"
  obrazac u ovoj implementaciji sličan `_find_current_job_id`-u koji
  sam propustio.

Kad završiš, javi rezultat (PASS/PASS_WITH_NOTES/REJECT + blocking
findings ako ih ima) -- koordinator prenosi Human Owner-u za odobrenje
prije merge-a (HIGH risk, pun ciklus).
