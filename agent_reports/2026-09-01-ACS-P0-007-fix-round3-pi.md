# ACS-P0-007 — Fix round 3 report

- **Task:** ACS-P0-007 — JobManager + Presentation contracts/state + Bootstrap wiring + Health-check
- **Branch:** `task/ACS-P0-007-jobs-presentation-bootstrap`
- **Base commit for this round:** `4fa7774`
- **Scope:** R2-BF-1 only — JobManager lifecycle/state/event handling + `tests/unit/jobs/test_manager.py`

---

## What was rejected in Codex round 2

Codex found that an already accepted queued job could remain permanently
`PENDING` when `JobManager.shutdown(cancel_futures=True)` cancelled its
underlying `ThreadPoolExecutor` future before the worker ever started it.

Repro shape:

1. `JobManager(max_workers=1)`
2. submit long-running blocker
3. submit second queued job
4. call `shutdown(wait=False)`
5. second job remains `PENDING` with a `CREATED` event and no terminal event

---

## What changed

### `src/ai_campaign_studio/jobs/manager.py`

- Added `self._futures: dict[str, Future[None]]`.
- `submit()` now stores the `Future` immediately after successful
  `self._executor.submit(...)`, in the same critical section that records
  `_jobs` / `_tokens`.
- Existing rollback behavior for `RuntimeError` during scheduling remains:
  failed scheduling removes `_jobs` / `_tokens` and emits no `CREATED`.
- `shutdown()` still flips `_shutdown` first, then calls
  `self._executor.shutdown(wait=wait, cancel_futures=True)`.
- Only after `executor.shutdown(...)` returns, `_finish_cancelled_futures()`
  scans tracked futures.
- For every `future.cancelled() is True` whose job is not already terminal,
  the job transitions to `CANCELLED`, receives `finished_at=utc_now()`, and
  emits a `CANCELLED` event.
- No `CANCELLATION_REQUESTED` event is emitted for executor-cancelled queued
  jobs, because the callable never started and there is no cooperative cancel
  flow.

### `tests/unit/jobs/test_manager.py`

Added regression coverage:

- `test_shutdown_cancels_queued_job_without_leaving_pending_state`
  - covers `shutdown(wait=False)`;
  - proves queued accepted job becomes terminal `CANCELLED`;
  - proves event stream contains a terminal `CANCELLED` event and does not end
    at `CREATED`.
- `test_shutdown_wait_true_cancels_queued_job_without_leaving_pending_state`
  - covers `shutdown(wait=True)`;
  - runs shutdown in a separate thread while the first worker remains blocked;
  - waits until executor has actually cancelled the queued future, then releases
    the running blocker;
  - proves the queued job ends as `CANCELLED`.

No presentation guard, presentation contracts/state, bootstrap, health-check
schema, domain/application/channel/provider registry files were changed.

---

## Adversarial proof

### Regression test before fix — FAIL

After adding the `wait=False` queued-job regression test but before changing
`JobManager`, the test failed exactly on the stale `PENDING` state:

```text
FAILED tests/unit/jobs/test_manager.py::test_shutdown_cancels_queued_job_without_leaving_pending_state
E           AssertionError: assert <JobStatus.PENDING: 'PENDING'> is <JobStatus.CANCELLED: 'CANCELLED'>
1 failed
```

### Temporary removal of new shutdown cleanup — FAIL

After implementing the fix, I temporarily removed the new
`self._finish_cancelled_futures()` call from `shutdown()` and re-ran the same
test. It failed again with the original symptom:

```text
FAILED tests/unit/jobs/test_manager.py::test_shutdown_cancels_queued_job_without_leaving_pending_state
E           AssertionError: assert <JobStatus.PENDING: 'PENDING'> is <JobStatus.CANCELLED: 'CANCELLED'>
1 failed
```

### Restored fix — PASS

With futures tracking + shutdown cleanup restored:

```text
tests/unit/jobs/test_manager.py::test_shutdown_cancels_queued_job_without_leaving_pending_state
tests/unit/jobs/test_manager.py::test_shutdown_wait_true_cancels_queued_job_without_leaving_pending_state

2 passed, 1 warning in 0.05s
```

Full `test_manager.py`:

```text
16 passed, 1 warning in 3.68s
```

---

## Full verification

All commands were run after the final code change.

```text
python -c "import ai_campaign_studio"
```

Equivalent import-smoke script result:

```text
0.1.0
```

```text
python -m pytest -q H:\ai-campaign-studio-worktrees\ACS-P0-007-jobs-presentation-bootstrap\tests --basetemp=.codex_tmp\pytest-basetemp
```

Result:

```text
170 passed, 1 warning in 5.92s
```

The warning is the existing pytest cache warning in the linked worktree, not a
test failure. Earlier attempts without a sandbox-writable `--basetemp` failed
with `PermissionError` against `C:\Users\...\Temp` / non-writable worktree temp
paths; rerun with root `.codex_tmp` basetemp passed.

```text
python -m ruff check H:\ai-campaign-studio-worktrees\ACS-P0-007-jobs-presentation-bootstrap --no-cache
```

Result:

```text
All checks passed!
```

```text
python -m mypy H:\ai-campaign-studio-worktrees\ACS-P0-007-jobs-presentation-bootstrap\src
```

Result:

```text
Success: no issues found in 51 source files
```

Health-check entrypoints were run outside the sandbox because the app writes
logs under user AppData on default startup and the sandbox blocked that path.

```text
python -m ai_campaign_studio.main --health-check
```

Result:

```text
{"database": "ok", "migrations": "ok", "platform_registry": "ok", "provider_registry": "ok", "python": "3.14.1", "secret_store": "available", "status": "ok", "translations": "ok", "ui_framework": "not_selected"}
```

```text
python scripts/health_check.py
```

Result:

```text
{"database": "ok", "migrations": "ok", "platform_registry": "ok", "provider_registry": "ok", "python": "3.14.1", "secret_store": "available", "status": "ok", "translations": "ok", "ui_framework": "not_selected"}
```

---

## GitNexus

Pre-change GitNexus was attempted from the task worktree, but the known linked
worktree binding limitation remains:

```text
npx gitnexus context JobManager --repo .
Error: Repository "." not found. Available: deklarant_pro, FieldFix-IT, Dentaland, FlowOS, AI-Campaing-Studio
```

```text
npx gitnexus impact JobManager --direction upstream --depth 3 --include-tests --repo .
{
  "error": "Repository \".\" not found. Available: deklarant_pro, FieldFix-IT, Dentaland, FlowOS, AI-Campaing-Studio"
}
```

`gitnexus_impact` remains `UNKNOWN`, compensated by narrow diff/source review
and live regression/adversarial verification.

---

## Reviewer focus

Please re-check:

- whether executor-cancelled queued futures now always terminalize as
  `CANCELLED`;
- whether `CANCELLED` event emission after shutdown is acceptable for the
  framework-neutral event contract;
- whether the `_futures` mapping introduces any unintended lifecycle retention
  concerns for P0 (current `_jobs` / `_tokens` are already retained for state
  lookup, so this follows the existing retention model);
- whether there is any remaining `submit()` / `shutdown()` race not covered by
  the two queued-job regression tests.
