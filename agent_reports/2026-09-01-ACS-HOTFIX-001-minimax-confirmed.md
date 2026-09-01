# ACS-HOTFIX-001 — Coordinator confirmation (Claude)

- **Task:** ACS-HOTFIX-001 — JobManager CREATED/STARTED event-ordering race
- **Branch:** `hotfix/ACS-HOTFIX-001-job-event-ordering` (base `main@638a479`)
- **Implementer:** MiniMax
- **Coordinator:** Claude — independently re-verified, does not take implementer's report at face value

---

## Process note — a coordinator error during verification, now resolved

While reproducing the fix, an attempted `git stash`/`checkout stash@{0} --
<path>` maneuver on my part accidentally reverted
`tests/unit/jobs/test_manager.py` to its last-committed (pre-hotfix) state,
destroying MiniMax's uncommitted new test in the working tree. This was my
mistake, not the implementer's. MiniMax re-added the test; I independently
confirmed its presence and content before proceeding with the rest of this
review. `src/ai_campaign_studio/jobs/manager.py` was never affected by this
incident (confirmed via diff throughout). All further adversarial work below
used only the `Edit`/`Read` tools against known-good content, not further
git history manipulation, to avoid repeating the mistake.

## Scope check

`git status --short`: exactly `src/ai_campaign_studio/jobs/manager.py`
(modified) and `tests/unit/jobs/test_manager.py` (modified) — both in
`allowed_paths`. No `forbidden_paths` touched.

## Environment gotcha — confirmed real, handled correctly

MiniMax's report flags that the shared `.venv`'s editable-install `.pth`
file can point at a different checkout than the one being verified,
silently testing stale code. Verified this is a real risk: confirmed the
`.pth` currently points at this hotfix worktree's `src/`, and additionally
used an explicit `PYTHONPATH` override for every verification command
below as a second, independent safeguard — regardless of what the shared
`.pth` says. Confirmed via `python -c "import ai_campaign_studio.jobs.manager
as m; print(m.__file__)"` that the correct file is loaded.

## Independent verification run

```
python -m pytest -q                → 171 passed
python -m pytest tests/unit/jobs/test_manager.py -v → 17 passed
python -m ruff check .             → All checks passed!
python -m mypy src                 → Success: no issues found in 51 source files
20x loop, -k "event_sequence or event_ordering_under_slow" → 20/20 clean (4 passed each)
```

## Adversarial reproduction — extensive, went beyond the implementer's own proof

Independently reproduced the fix, and in doing so found something the
implementer's own adversarial proof did not surface:

1. **Partial revert #1** (`_emit` reverted to snapshot-then-release,
   `RLock` + emit-inside-`submit()`'s-lock left intact): test still PASSED,
   10/10. This means `RLock` plus calling `_emit` from inside `submit()`'s
   own `with self._lock:` block is, by itself, already sufficient — because
   `RLock`'s recursion counter keeps the true lock held for the full
   duration of `submit()`'s outer block regardless of what `_emit`'s own
   nested block does.
2. **Partial revert #2** (plain `Lock` instead of `RLock`, `CREATED` emit
   moved back outside `submit()`'s lock block, `_emit`'s lock-holding-
   through-callbacks left intact): test still PASSED, 5/5, even with the
   sleep window extended to 2 seconds. This means `_emit` holding the lock
   through callback dispatch is, by itself, ALSO already sufficient —
   because the worker thread needs that same lock for its own RUNNING
   transition and blocks on it for the full callback duration, regardless
   of where `submit()` calls `_emit` from.
3. **Full revert** (all three elements broken simultaneously — plain
   `Lock`, emit outside `submit()`'s lock, `_emit` snapshot-then-release):
   test FAILED reliably, 5/5, with the exact original symptom
   (`STARTED`/`SUCCEEDED` observed before `CREATED`).
4. Restored the exact original (fixed) file content via `Edit` (verified
   zero diff against MiniMax's commit-pending state, no leftover probe
   markers), confirmed PASS again (171 passed, 20/20 targeted loop clean).

**Conclusion**: the shipped fix contains genuine redundancy — either
(`RLock` + emit-inside-`submit()`'s-lock) or (`_emit` holding the lock
through callback dispatch) alone closes this specific race; MiniMax shipped
both. This is not a defect — redundant protection in a concurrency fix is
reasonable defense-in-depth, and the combination also has independent value
for other emit call sites (`cancel`, `_finish`, `_finish_cancelled_futures`)
that don't share `submit()`'s specific lock-nesting shape. But it does mean
the evidence report's claim that "the fix is complete only with all three
changes" is not quite accurate as a minimality claim — any two of the three
elements already suffice for this specific test. Not blocking; noted for
the record since evidence-report accuracy matters for this project (see
also the ACS-P0-008 `__main__`-block correction earlier today).

## BF-1 / R2-BF-1 regression check (from ACS-P0-007)

`test_submit_after_shutdown_raises_and_leaves_no_orphan`,
`test_shutdown_is_idempotent`,
`test_shutdown_cancels_queued_job_without_leaving_pending_state`,
`test_shutdown_wait_true_cancels_queued_job_without_leaving_pending_state`
all pass unchanged — the `RLock` promotion and `_emit` change do not
regress either prior fix.

## Verdict

PASS. Ready for Codex review request (HIGH risk — regression on
already-merged foundation code, full cycle per workflow §29).
