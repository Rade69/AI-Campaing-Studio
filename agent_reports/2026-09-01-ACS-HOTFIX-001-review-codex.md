---
task_id: ACS-HOTFIX-001
reviewer: codex
date: 2026-09-01
branch: hotfix/ACS-HOTFIX-001-job-event-ordering
commit: 11d5b48abcaf1bf52f69227bd39e3458f788d3e7
base: 638a479470f785db2b56bc26208061a18dc07cd7
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
tests: PASS
gitnexus_impact: UNKNOWN
blocking_findings: []
---

# CILJ

Nezavisno pregledati HIGH-risk hotfix za `JobManager` event-ordering regresiju
sa `main`-a: subscriber ne smije nikad vidjeti `STARTED` prije `CREATED` za isti
job, bez ponovnog otvaranja ACS-P0-007 BF-1/R2-BF-1 lifecycle bugova.

# URAĐENO

PASS_WITH_NOTES. Nema blocking findings u pregledanom scope-u. Fix zatvara
`CREATED`/`STARTED` race kroz `RLock`, emitovanje `CREATED` dok `submit()` još
drži manager lock, i `_emit()` dispatch pod lock-om. Standardni i adversarial
dokazi prolaze.

# SCOPE

Pregledan diff `638a479..11d5b48`.

Produkcijski/test scope je u skladu sa contractom:

- `src/ai_campaign_studio/jobs/manager.py`
- `tests/unit/jobs/test_manager.py`

Dodatno su dodani samo hotfix/review reporti u `agent_reports/`. Nema izmjena u
zabranjenim slojevima (`domain`, `application`, `ports`, registries,
`presentation`, `bootstrap.py`, `main.py`, `jobs/models.py`,
`jobs/events.py`, `jobs/cancellation.py`).

# PROVJERENO

- `JobManager.__init__`: `Lock` je promijenjen u `RLock`, što dozvoljava
  `submit()` → `_emit()` reentrant path iz istog thread-a, dok worker thread i
  dalje blokira na istom lock-u.
- `JobManager.submit`: `_shutdown` check ostaje prije state/future upisa;
  `executor.submit()` rollback se dešava prije `CREATED`; `CREATED` se emituje
  tek nakon uspješnog future registration-a i prije izlaska iz lock-a.
- `_run`, `_finish`, `cancel`, `shutdown`, `_finish_cancelled_futures`: nisu
  promijenjeni sem kroz novi `RLock`/`_emit` dispatch trade-off; prethodni
  terminal-state i queued-cancellation putevi ostaju konzistentni.
- Novi test `test_event_ordering_under_slow_created_callback_deterministic`
  stvarno forsira spor `CREATED` callback i assertuje tačan event stream.

# GITNEXUS / IMPACT

GitNexus nije dao pouzdan worktree rezultat:

```text
npx gitnexus status
→ Repository not indexed. Run: gitnexus analyze

npx gitnexus detect-changes --scope compare --base-ref main --repo .
→ Repository "." not found. Available: ... AI-Campaing-Studio
```

Zato je `gitnexus_impact: UNKNOWN`, ne “clean”. Kompenzacija: ručno pročitan
pun diff, okolni `JobManager` lifecycle kod, `JobEvent`/`JobState` modeli i
svi postojeći job tests. Pošto javni API nije proširen i diff je ograničen na
jedan lifecycle primitive + test, ovo nije blocking za hotfix verdict.

# BLOCKING FINDINGS

Nema potvrđenih blocking nalaza.

# STANDARDNA VERIFIKACIJA

Svi commandi su pokrenuti sa eksplicitnim:

```text
PYTHONPATH=H:\ai-campaign-studio-worktrees\ACS-HOTFIX-001-job-event-ordering\src
```

Import identity:

```text
H:\ai-campaign-studio-worktrees\ACS-HOTFIX-001-job-event-ordering\src\ai_campaign_studio\jobs\manager.py
```

Rezultati:

```text
pytest -q <hotfix-worktree>\tests --basetemp=.codex_tmp_hotfix\pytest
→ 171 passed, 1 warning in 5.44s

pytest -q <hotfix-worktree>\tests\unit\jobs\test_manager.py
→ 17 passed in 3.80s

ruff check <hotfix-worktree>\src <hotfix-worktree>\tests <hotfix-worktree>\scripts --no-cache
→ All checks passed!

mypy <hotfix-worktree>\src
→ Success: no issues found in 51 source files

50x loop: pytest -q tests/unit/jobs/test_manager.py -k event
→ 50/50 clean; svaki run: 4 passed, 13 deselected
```

Napomena: prvi pytest pokušaji su pali prije test-body-ja zbog sandbox tempdir
ograničenja (`C:\Users\...\Temp\pytest-of-radovan` i top-level `H:\...`
basetemp nisu writable). Rerun sa basetemp-om unutar glavnog checkouta prolazi.

# ADVERSARIALNA PROVJERA

Pokrenut dodatni scratch adversarial script bez izmjene hotfix branch-a. Pokrio
je:

1. slow `CREATED` callback + brzi job: očekivani stream
   `[CREATED, STARTED, SUCCEEDED]`;
2. `submit()` nakon `shutdown()`: `RuntimeError`, bez eventa i bez orphan
   `_jobs`/`_tokens`;
3. queued job cancellation na `shutdown(wait=False)`: queued job završava kao
   `CANCELLED`;
4. queued job cancellation na `shutdown(wait=True)`: queued job završava kao
   `CANCELLED`;
5. callback koji pokrene drugi thread koji zove `get_state()` na istom
   manageru: drugi thread korektno blokira dok callback drži lock, pa se
   odblokira nakon callback-a; nema deadlock-a ako callback ne čeka taj drugi
   thread da završi dok sam drži lock.

Rezultat:

```text
adversarial_hotfix001: PASS
```

CLI health-check bez override-a vraća build-failed JSON u ovom sandboxu jer
default `AppPaths` pokušava korisnički data dir van writable scope-a. Sa
eksplicitnim `AppSettings(data_dir_override=...)` u writable scratch dir-u:

```text
{'status': 'ok', 'python': '3.14.1', 'database': 'ok', 'migrations': 'ok',
 'translations': 'ok', 'platform_registry': 'ok', 'provider_registry': 'ok',
 'secret_store': 'available', 'ui_framework': 'not_selected'}
```

# NOTES / RESIDUAL RISK

- Shipped fix je redundantan: `RLock + CREATED inside submit lock` i `_emit`
  dispatch-under-lock se preklapaju za ovaj konkretni race. To nije defekt;
  za concurrency hotfix je prihvatljiva defense-in-depth odluka.
- `_emit()` sada drži manager lock dok callbackovi rade. To namjerno
  serializuje `get_state`, `cancel`, `submit`, `_run` i `_finish` tokom sporog
  callback-a. Testirao sam da cross-thread callback call-in blokira pa se
  odblokira. Jedini deadlock oblik koji ostaje teorijski moguć je loš subscriber
  obrazac: callback drži manager lock, pokrene drugi thread koji treba isti
  manager lock, pa sinhrono čeka taj drugi thread. Takvog subscriber-a nema u
  projektu danas; ne prijavljujem kao blocking.

# NE DIRATI U FIX RUNDI

Ne dirati `presentation` contract/state model, bootstrap composition root,
health-check schema, registries, domain/application/ports/infrastructure, niti
prethodne ACS-P0-007 BF-1/R2-BF-1 mehanizme. Ovaj hotfix je već dovoljno usko
zatvoren.

# SLJEDEĆE

Human Owner / koordinator može tretirati Codex review kao PASS_WITH_NOTES bez
blocking findings. Za merge i dalje važi HIGH-risk puni ciklus: eksplicitno
Human Owner odobrenje prije merge-a.
