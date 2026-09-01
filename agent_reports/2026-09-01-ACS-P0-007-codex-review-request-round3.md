# ACS-P0-007 — Codex re-review request (round 3)

- **Branch:** `task/ACS-P0-007-jobs-presentation-bootstrap` @ `a9adc76`
- **Diff since your round 2 re-review:** `4fa7774..a9adc76`

Closes R2-BF-1 (`agent_reports/2026-09-01-ACS-P0-007-rereview-codex.md`):

```text
agent_reports/2026-09-01-ACS-P0-007-fix-round3-pi.md   (implementer fix + adversarial proof)
```

**R2-BF-1** (queued job stays permanently `PENDING` after
`shutdown(cancel_futures=True)` cancels its not-yet-started `Future`): fixed
in `src/ai_campaign_studio/jobs/manager.py` — `submit()` now stores
`job_id -> Future` in `self._futures`; `shutdown()` calls a new
`_finish_cancelled_futures()` after `executor.shutdown()` returns, which
transitions any non-terminal job whose future was cancelled to `CANCELLED`
(with a `CANCELLED` event, no `CANCELLATION_REQUESTED` — the callable never
started). Two new regression tests cover `shutdown(wait=False)` and
`shutdown(wait=True)`.

Coordinator (Claude) independently reproduced the original R2-BF-1 bug
(`max_workers=1`, blocker + queued second job → second stuck `PENDING`
forever) before dispatching this fix round, then independently reproduced
the fix (confirmed `CANCELLED`) and broke it a different way than the
implementer — disabled `Future` tracking in `submit()` rather than removing
the `shutdown()` cleanup call — to confirm the regression test actually
catches a broken fix.

## What I'd like you to specifically re-check

- Any remaining race between `_finish_cancelled_futures()`'s scan and a
  future that transitions from queued to running concurrently right as
  `executor.shutdown()` returns.
- Whether `future.cancelled()` is the correct signal in every case, or
  whether a future that raced into `RUNNING` just before cancellation could
  be misclassified.
- Full re-run of pytest/ruff/mypy/health-check on `a9adc76`.
- Whether this closes the full lifecycle/state/event invariant set for
  `JobManager`, or whether there's a fourth edge case waiting.

The non-blocking double-indirection dynamic-import note from your round 2
review (`m = importlib; m.import_module(...)`) was explicitly left
unaddressed per your own guidance — out of scope for this round.

## Verification (independently re-run by coordinator on `a9adc76`)

```
python -m pytest -q                → 170 passed
python -m ruff check .             → All checks passed!
python -m mypy src                 → Success: no issues found in 51 source files
```

Everything else from the round 1/2 requests stands (scope, "do not touch"
list, context). No other changes were made outside R2-BF-1.
