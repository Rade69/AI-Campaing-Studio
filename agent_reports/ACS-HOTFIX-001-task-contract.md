---
task_id: ACS-HOTFIX-001
phase: P0-hotfix
title: "JobManager: CREATED/STARTED event ordering race (regression from ACS-P0-007 fix round 2)"
risk: HIGH
coordinator: claude
implementer: pi
reviewers: [codex, claude]
status: "OPEN — contract written before code"
created_at: 2026-09-01
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/jobs/manager.py
  - tests/unit/jobs/test_manager.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/channels/
  - src/ai_campaign_studio/localization/
  - src/ai_campaign_studio/ai_registry/
  - src/ai_campaign_studio/infrastructure/
  - src/ai_campaign_studio/presentation/
  - src/ai_campaign_studio/bootstrap.py
  - src/ai_campaign_studio/main.py
  - src/ai_campaign_studio/jobs/models.py
  - src/ai_campaign_studio/jobs/events.py
  - src/ai_campaign_studio/jobs/cancellation.py
gitnexus_required: false
adversarial_required: true
---

# Kontekst

**Regresija otkrivena na već merge-ovanom `main`-u** (GitHub Actions CI run
`33502313009`, push commit `f329ab9`, pytest job crven — 3 testa u
`tests/unit/jobs/test_manager.py` FAILED sa event-order swap: `STARTED`
prije `CREATED`).

Uzrok: `JobManager.submit()` fix round 2 (ACS-P0-007, BF-1: "submit after
shutdown ostavlja orphan PENDING job") je pomjerio
`self._executor.submit(self._run, job_id, func, token)` UNUTAR
`with self._lock:` blok, ali `self._emit(JobEvent(CREATED, ...))` je ostao
NAKON što se lock oslobodi:

```python
with self._lock:
    if self._shutdown: raise RuntimeError(...)
    self._jobs[job_id] = state
    self._tokens[job_id] = token
    try:
        future = self._executor.submit(self._run, job_id, func, token)
    except RuntimeError:
        ...
        raise
    self._futures[job_id] = future
self._emit(JobEvent(job_id, JobEventType.CREATED, ...))  # <-- OUTSIDE lock
return job_id
```

`JobManager._run()` (izvršava se na worker thread-u koji executor odmah
može dodijeliti) svoju prvu radnju radi POD ISTIM `self._lock`-om (state →
RUNNING), pa čim submitting thread oslobodi lock, worker thread se takmiči
da ga zauzme PRIJE nego što submitting thread stigne da pozove
`self._emit(CREATED)`. Ako worker pobijedi tu trku, `STARTED` event stiže
subscriberima prije `CREATED`-a za isti job — kontradiktoran event stream.

Ovo NIJE uhvaćeno kroz tri Codex runde niti kroz koordinatorovu nezavisnu
adversarial reprodukciju na ACS-P0-007, jer je race probabilistička i
Windows lokalno okruženje (gdje su svi dosadašnji testovi rađeni) je
očigledno mnogo manje sklono da je izloži nego Linux GitHub Actions runner.
Ovo je važna lekcija: postojeći testovi provjeravaju TAČAN redoslijed
(`assert events == [CREATED, STARTED, ...]`), što je ispravno, ali
verifikacija samo na jednoj platformi/jednom pokretanju nije dovoljna za
race-condition regresije — potrebna je deterministička adversarial provjera
(vidi ispod), ne samo "test je prošao lokalno".

**Ovo je HIGH prioritet i blokira ACS-P0-008** — `pytest -q` mora biti
zeleno (deterministički, ne "obično prolazi") prije nego što
`generate_phase0_gate_report.py` može ikad legitimno upisati
`"pytest": true`.

# Objective

Ukloniti race tako da `CREATED` event UVIJEK stigne subscriberima prije
`STARTED`-a za isti job, deterministički (ne probabilistički), bez ponovnog
otvaranja BF-1 (orphan PENDING job nakon `submit()` posle `shutdown()`) niti
R2-BF-1 (queued job trajno PENDING nakon `shutdown(cancel_futures=True)`).

# Implementation steps

1. Analiziraj tačno zašto do race-a dolazi (opisano gore) — potvrdi
   razumijevanje prije izmjene.
2. Fix mora garantovati da worker thread (`_run()`) ne može ni pokušati da
   zauzme `self._lock` (potrebno mu za RUNNING tranziciju) prije nego što je
   `CREATED` emit u potpunosti završen na submitting thread-u. Praktično to
   znači: `self._emit(CREATED)` mora biti pozvan PRIJE nego što se
   `self._lock` oslobodi u `submit()`.
3. `self._emit()` sam po sebi kratko zauzima `self._lock` (da snapshot-uje
   `self._callbacks`) — ako `submit()` već drži taj isti `Lock` i pozove
   `self._emit()` iznutra, obični `threading.Lock` će deadlock-ovati (nije
   reentrant). Rješenje: promijeni `self._lock` iz `threading.Lock()` u
   `threading.RLock()` (reentrant), što bezbjedno dozvoljava ugniježđeno
   zauzimanje od strane ISTOG thread-a, a i dalje ispravno blokira DRUGE
   threadove (kao i do sada svuda gdje se `self._lock` koristi — `cancel`,
   `get_state`, `subscribe`, `shutdown`, `_run`, `_finish`, `_emit`, novi
   `_finish_cancelled_futures`).
4. U `submit()`: pozovi `self._emit(JobEvent(CREATED, ...))` UNUTAR
   `with self._lock:` bloka (poslije uspješnog `self._futures[job_id] =
   future`), ne poslije njega. Ukloni postojeći emit poziv koji je trenutno
   izvan bloka.
5. Provjeri da BF-1 i R2-BF-1 ponašanje ostaje netaknuto:
   - `submit()` poslije `shutdown()` i dalje ne smije upisati state niti
     emitovati CREATED (provjera `self._shutdown` ostaje prva u bloku).
   - rollback na `RuntimeError` iz `executor.submit()` i dalje mora raditi
     BEZ emitovanog CREATED-a (rollback se dešava PRIJE emit poziva u novom
     redoslijedu — provjeri da je tako).
   - `shutdown()`/`_finish_cancelled_futures()` logika iz R2-BF-1 ostaje
     nepromijenjena (koristi isti, sada `RLock`, lock — provjeri da nema
     nove interakcije).
6. Razmisli i eksplicitno navedi u evidence reportu: da li promjena na
   `RLock` otvara bilo kakav novi rizik (npr. callback koji sam pokuša da
   pozove `submit()`/`cancel()` na istom manageru iz istog thread-a dok se
   nalazi unutar `_emit()` pozvanog iz `submit()`'s lock-a — sa `RLock`
   bi to sada "uspjelo" umjesto deadlock-a, što može sakriti loš
   caller-pattern. Ovo NIJE P0 blocking (nema takvog callback-a u projektu
   trenutno), samo dokumentuj kao poznatu karakteristiku.

# Acceptance

- [ ] `test_event_sequence_success`, `test_event_sequence_failure`,
      `test_event_sequence_cancellation` (postojeći testovi) prolaze
      DETERMINISTIČKI, ne samo "obično".
- [ ] Novi deterministički adversarial test (vidi ispod) prolazi.
- [ ] Svi postojeći BF-1/R2-BF-1 regression testovi
      (`test_submit_after_shutdown_raises_and_leaves_no_orphan`,
      `test_shutdown_is_idempotent`,
      `test_shutdown_cancels_queued_job_without_leaving_pending_state`,
      `test_shutdown_wait_true_cancels_queued_job_without_leaving_pending_state`)
      i dalje prolaze bez izmjene ponašanja.
- [ ] Pun `pytest -q`, `ruff check .`, `mypy src` prolaze.
- [ ] Fix ograničen na `jobs/manager.py` + njegove testove — ništa drugo
      dirano.

# Adversarial test (obavezno — adversarial_required: true)

Probabilistička race provjera NIJE dovoljna (upravo je to propustilo bug na
Windows-u tri runde zaredom). Potreban je DETERMINISTIČKI dokaz:

1. Registruj callback na `subscribe()` koji, SAMO kad primi `CREATED`
   event, namjerno spava (npr. `time.sleep(0.2)`) prije nego što vrati
   kontrolu — simulira spor subscriber i forsira maksimalan race prozor.
2. Sa STARIM (buggy) kodom, ovaj test mora pouzdano FAILOVATI (worker
   thread ima 200ms da zauzme lock i emituje STARTED dok submitting thread
   još čeka u sporom callback-u) — potvrdi ovo PRIVREMENIM vraćanjem stare
   `submit()` strukture (ili commentovanjem fix-a), pokreni test, potvrdi
   FAIL, vrati fix.
3. Sa NOVIM (fiksovanim) kodom, worker thread NE MOŽE zauzeti lock dok
   submitting thread (uključujući spori callback) ne završi CIJELI
   `with self._lock:` blok — test mora pouzdano PASSovati bez obzira na
   sporost callback-a.
4. Dokumentuj oba output-a (FAIL sa starim kodom, PASS sa novim) doslovno.

Dodatno: pokreni postojeće event-sequence testove u petlji (npr. 50-100x
zaredom) kao dodatni (ne-deterministički, ali korisan) statistički dokaz da
race više ne nestaje/pojavljuje se povremeno.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest -q
python -m pytest tests/unit/jobs/test_manager.py -v
for i in $(seq 1 50); do python -m pytest tests/unit/jobs/test_manager.py -q -k event_sequence || break; done
python -m ruff check .
python -m mypy src
```

# Review focus — Codex

- da li `RLock` uvodi bilo kakav suptilan bug u POSTOJEĆOJ logici koja se
  oslanjala na `Lock`-ovo nereentrantno ponašanje (provjeri sve postojeće
  `with self._lock:` blokove — nijedan trenutno ne poziva nešto što bi samo
  sebe rekurzivno zaključavalo, ali potvrdi eksplicitno);
- da li deterministički adversarial test STVARNO forsira race (ne samo
  "obično prolazi") — probaj i sam smanjiti/ukloniti `sleep` da vidiš da li
  test i dalje pouzdano hvata regresiju bez njega, ili je `sleep` neophodan
  za pouzdanost;
- da li fix slučajno ponovo otvara BF-1 ili R2-BF-1 (re-pokreni njihove
  originalne repro scenarije eksplicitno, ne samo regression testove);
- generalno: da li ima drugih mjesta u fajlu gdje se emit dešava izvan
  lock-a na način koji bi mogao imati sličan (još neotkriven) race sa nekim
  drugim eventom.

# Rollback

HIGH — regresija na već merge-ovanom foundation kodu koji `bootstrap.py`
koristi. Ako adversarial dokaz ne pokaže pouzdan FAIL→PASS, ili Codex nađe
da fix otvara novi problem — ne mergovati, dodatna fix runda.

# Coordination

Nema drugog paralelnog taska trenutno aktivnog na ovom fajlu. ACS-P0-008
(MiniMax, drugi worktree) ne dira `jobs/manager.py` — disjoint sa ovim
hotfixom, ali ACS-P0-008 zavisi FUNKCIONALNO od ovog fixa (njegov
`generate_phase0_gate_report.py` mora vidjeti zeleno `pytest`).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-HOTFIX-001-job-event-ordering
Branch:   hotfix/ACS-HOTFIX-001-job-event-ordering
Base:     main @ 638a479
```
