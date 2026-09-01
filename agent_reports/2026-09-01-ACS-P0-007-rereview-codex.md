---
verdict: REJECT
scope: PASS
acceptance: REJECT
architecture: PASS
security: PASS
tests: REJECT
gitnexus_impact: UNKNOWN
blocking_findings:
  - R2-BF-1: "JobManager.shutdown(cancel_futures=True) can cancel a queued future while leaving its JobState permanently PENDING."
---

CILJ: Re-review ACS-P0-007 fix round 2 na `task/ACS-P0-007-jobs-presentation-bootstrap` @ `4fa7774`, fokusirano na zatvaranje Codex BF-1/BF-2 i proporcionalnu regresiju oko `submit()`/`shutdown()` lifecycle-a i presentation import guarda.

URAĐENO: REJECT — originalni BF-1 i BF-2 su zatvoreni, ali svježa adversarial provjera našla je novi stvarni `JobManager` lifecycle bug za queued job tokom shutdowna.

NE DIRATI: Ne širiti UI framework odluku, ne dirati domain/application/channel/localization/AI registry, ne uvoditi container/service-locator u bootstrap.

SLJEDEĆE: Fix-runda treba usko zatvoriti queued-future shutdown ponašanje i dodati regression test koji dokazuje da nijedan prihvaćeni job ne ostaje trajno `PENDING` nakon `shutdown(cancel_futures=True)`.

# CILJ

Codex independent re-review za ACS-P0-007 round 2.

Pregledan je branch:

```text
task/ACS-P0-007-jobs-presentation-bootstrap @ 4fa777402d1da5abed10087b9a4550acb7720e74
```

Diff od prethodnog Codex review requesta:

```text
489207a..4fa7774
```

# PROVJERENO

Round-2 diff je usko ograničen na očekivani fix scope:

- `src/ai_campaign_studio/jobs/manager.py`
- `tests/unit/jobs/test_manager.py`
- `tests/unit/presentation/test_no_gui_imports.py`
- round-2 agent reports / Codex rereview request

Pročitano:

- `agent_reports/2026-09-01-ACS-P0-007-fix-round2-pi.md`
- `agent_reports/2026-09-01-ACS-P0-007-codex-review-request-round2.md`
- stvarni diff `489207a..4fa7774`
- izmijenjeni `JobManager`
- izmijenjeni JobManager regression testovi
- izmijenjeni presentation guard

# GITNEXUS / IMPACT

GitNexus u task worktree-ju i dalje nije pouzdan kao evidence izvor:

```text
npx gitnexus status
Repository not indexed.
Run: gitnexus analyze
```

```text
npx gitnexus detect-changes
Error: Multiple repositories indexed. Specify which one with the "repo" parameter.
Available: deklarant_pro, FieldFix-IT, Dentaland, FlowOS, AI-Campaing-Studio
```

Zato je `gitnexus_impact: UNKNOWN`. Kompenzacija je ručni diff/source review i live adversarial probe.

# BLOCKING FINDINGS

## R2-BF-1 — Queued job ostaje trajno `PENDING` ako ga `shutdown(cancel_futures=True)` otkaže prije starta

Status: BLOCKING

Lokacija:

- `src/ai_campaign_studio/jobs/manager.py`
- `JobManager.submit()`
- `JobManager.shutdown()`

Round-2 fix ispravno dodaje `_shutdown` flag i sprječava originalni slučaj `submit()` nakon već izvršenog `shutdown()`:

```text
## submit-after-shutdown
raised RuntimeError cannot submit new jobs: JobManager is shut down
jobs 0
tokens 0
events []
```

Međutim, ostaje drugi stvarni lifecycle slučaj:

1. `JobManager(max_workers=1)` pokrene dug `blocker` job.
2. Drugi job se uspješno prihvati i emituje `CREATED`, ali ostaje queued u `ThreadPoolExecutor`.
3. Pozove se `shutdown(wait=False)`.
4. `ThreadPoolExecutor.shutdown(cancel_futures=True)` otkaže queued future.
5. Pošto `JobManager` ne čuva future niti ima done-callback za executor-cancelled future, drugi job ostaje trajno `PENDING`.

Repro output:

```text
## queued-future-shutdown
first SUCCEEDED
second PENDING
events ['CREATED', 'STARTED', 'CREATED', 'SUCCEEDED']
```

Zašto je blocking:

Ovo nije teorijski race-only slučaj. Dovoljno je imati `max_workers=1`, jedan aktivan posao i jedan queued posao. JobManager već javno prihvati drugi posao (`submit()` vrati id i emituje `CREATED`), ali poslije shutdowna ne postoji terminalni event/state za taj job. To krši osnovnu lifecycle/state/event invarijantu koju ovaj P0 foundation task uvodi.

Očekivana fix-runda:

- `JobManager` mora znati šta se desilo sa queued futures tokom shutdowna.
- Pri `shutdown(cancel_futures=True)` prihvaćeni queued jobovi ne smiju ostati `PENDING`.
- Prihvatljivi modeli:
  - čuvati mapping `job_id -> Future` i terminalizovati cancelled queued futures kao `CANCELLED`;
  - ili druga jasna strategija gdje svaki prihvaćen job nakon shutdowna završi u terminalnom stanju.
- Dodati regression test za queued job:
  - zauzeti worker blockerom,
  - submitovati drugi job,
  - pozvati `shutdown(wait=False)` ili `shutdown(wait=True)`,
  - dokazati da drugi job nije `PENDING` i da event stream nije kontradiktoran.

# ROUND-1 FINDINGS STATUS

## Original BF-1 — `submit()` nakon već izvršenog `shutdown()`

Status: CLOSED

Svježi repro pokazuje:

```text
raised RuntimeError cannot submit new jobs: JobManager is shut down
jobs 0
tokens 0
events []
```

To zatvara originalni orphan-state/CREATED-event slučaj.

## Original BF-2 — presentation guard dynamic `importlib` / `__import__`

Status: CLOSED for direct literal dynamic imports

Svježi repro:

```text
## presentation-dynamic-guard
direct ['PySide6', 'ai_campaign_studio.infrastructure.database']
```

`importlib.import_module("PySide6")`, `__import__("ai_campaign_studio.infrastructure.database")` i direktni literalni dynamic imports sada se hvataju.

Proporcionalna napomena, non-blocking:

```text
alias []
```

Varijanta:

```python
import importlib
m = importlib
m.import_module("PySide6")
```

i dalje prolazi kroz presentation guard. Ne rangiram ovo kao blocking u ovoj rundi jer ulazi u namjerno obfuscated/double-indirection klasu, zajedno sa `exec`, `sys.modules`, f-string/format-built module names itd. Direktni literal dynamic bypass iz round-1 je zatvoren. Ako Human Owner želi “paranoid guard” nivo, najbolje je centralizovati scanner i dodati assignment-alias tracking, ali to ne treba miješati sa runtime lifecycle bugom iz R2-BF-1.

# STANDARDNA VERIFIKACIJA

Pokrenuto na `4fa7774` koristeći branch `src` preko `PYTHONPATH`:

```text
python -m pytest -q H:\ai-campaign-studio-worktrees\ACS-P0-007-jobs-presentation-bootstrap\tests
```

Rezultat:

```text
168 passed, 1 warning in 5.29s
```

Warning je pytest cache warning u linked worktree-ju, nije test failure.

```text
python -m ruff check H:\ai-campaign-studio-worktrees\ACS-P0-007-jobs-presentation-bootstrap --no-cache
```

Rezultat:

```text
All checks passed!
```

```text
python -m mypy H:\ai-campaign-studio-worktrees\ACS-P0-007-jobs-presentation-bootstrap\src
```

Rezultat:

```text
Success: no issues found in 51 source files
```

Health-check sa eksplicitnim temp data/resources paths:

```text
{"database": "ok", "migrations": "ok", "platform_registry": "ok", "provider_registry": "ok", "python": "3.14.1", "secret_store": "available", "status": "ok", "translations": "ok", "ui_framework": "not_selected"}
```

# ADVERSARIALNA PROVJERA

Urađeno svježe:

- originalni `submit after shutdown` repro → PASS / closed;
- queued job + `shutdown(wait=False)` → FAIL / novi blocking R2-BF-1;
- direct literal dynamic imports in presentation guard → PASS / closed;
- double-indirection `m = importlib; m.import_module("PySide6")` → nije uhvaćeno, zabilježeno kao non-blocking proporcionalna napomena.

# NE DIRATI U FIX RUNDI

Fix-runda treba ostati uska:

- samo `JobManager` lifecycle/state/event handling i pripadajući regression testovi;
- bez promjene presentation contract/state modela osim ako se eksplicitno odluči dodatno ojačati guard;
- bez promjene bootstrap composition root-a;
- bez promjene health-check JSON schema;
- bez širenja u domain/application/channel/provider registry.

# SLJEDEĆE

REJECT dok R2-BF-1 ne bude zatvoren.

Nakon fix-runde očekujem:

1. regression test za queued accepted job tokom `shutdown(cancel_futures=True)`;
2. dokaz da prihvaćeni queued job terminalizuje (`CANCELLED` ili druga jasno definisana terminalna politika), ne ostaje `PENDING`;
3. ponovljeno:
   - full pytest,
   - ruff,
   - mypy,
   - health-check evidence.
