# ACS-HOTFIX-001 — Codex review request

- **Task:** ACS-HOTFIX-001 — JobManager CREATED/STARTED event-ordering race (regression from ACS-P0-007 fix round 2)
- **Branch:** `hotfix/ACS-HOTFIX-001-job-event-ordering` @ `57b28a7`
- **Risk:** HIGH — regression on already-merged foundation code that `bootstrap.py` wires in. Full Codex+Claude+Human Owner cycle per workflow §29.

Read in this order:

```text
agent_reports/ACS-HOTFIX-001-task-contract.md
agent_reports/2026-09-01-ACS-HOTFIX-001-minimax.md          (implementer evidence)
agent_reports/2026-09-01-ACS-HOTFIX-001-minimax-confirmed.md (coordinator confirmation + findings)
agent_reports/2026-09-01-ACS-HOTFIX-001-review-claude.md     (Claude review, PASS)
```

Diff base: `main` @ `638a479`.

## Context

Original bug caught by GitHub Actions CI on Linux (run `33502313009`), not
reproducible reliably on Windows — a probabilistic race where
`JobManager.submit()`'s worker thread could emit `STARTED` before the
submitting thread finished emitting `CREATED`, because `executor.submit()`
was moved inside `submit()`'s lock (ACS-P0-007 fix round 2, BF-1) but the
`CREATED` emit stayed outside it.

## Important environment note before you run anything

The shared `.venv`'s editable-install `.pth` file can point at a different
checkout than the one you're verifying, silently testing stale code. Check
it first:

```bash
cat "H:/AI Campaing Studio/.venv/Lib/site-packages/__editable__.ai_campaign_studio-0.1.0.pth"
```

It must point at this worktree's `src/`. If not, either fix the `.pth` or
set `PYTHONPATH` explicitly to this worktree's `src` for every command —
the coordinator used the latter as a belt-and-suspenders safeguard
regardless of the `.pth` state.

## A finding from coordinator review — not blocking, but worth your own check

Independent adversarial reproduction found the shipped fix has genuine
redundancy: either (a) `RLock` + emitting `CREATED` from inside `submit()`'s
own `with self._lock:` block, OR (b) `_emit()` holding the lock through the
entire callback-dispatch loop, is **independently sufficient** to close this
specific race — confirmed via two different partial reverts, each of which
still passed the new deterministic test, and only a full revert of all
three elements reliably reproduced the original failure (5/5 FAIL) with the
exact original symptom (`STARTED`/`SUCCEEDED` before `CREATED`). This isn't
a defect (redundant protection is a reasonable trade-off, and part (b) also
matters for the other emit call sites — `cancel`, `_finish`,
`_finish_cancelled_futures` — that don't share `submit()`'s specific lock-
nesting shape), but it does mean the evidence report's "the fix is complete
only with all three changes" claim is not a strict minimality claim. Please
form your own judgment on whether this redundancy is worth trimming or
should stay as defense-in-depth — not a blocking item either way.

## Review focus (from the task contract)

- Does the deterministic adversarial test (`test_event_ordering_under_slow_created_callback_deterministic`)
  genuinely force the race, or could it have its own blind spot (e.g., does
  it depend on `ThreadPoolExecutor` having spare capacity, or would it
  behave differently under `max_workers=1` with a busy pool)?
- Does `RLock` introduce any subtle bug in the *existing* logic that relied
  on `Lock`'s non-reentrant behavior? (Coordinator checked all `with
  self._lock:` sites — none currently self-nest — but a second pass is
  valuable given this touches the core lifecycle primitive.)
- Does the fix re-open BF-1 (`submit()` after `shutdown()` leaves an orphan
  job) or R2-BF-1 (queued job stuck `PENDING` after
  `shutdown(cancel_futures=True)`) from ACS-P0-007? Both regression tests
  pass, but please re-run their original repro scenarios directly, not just
  the regression tests.
- `_emit()` now holds the lock through callback dispatch — confirm this
  doesn't introduce a deadlock risk if a future callback ever calls back
  into the same `JobManager` instance from a different thread (should
  block correctly, not deadlock, given `RLock` — but only for the *same*
  thread; a different thread calling in would legitimately block until the
  slow callback finishes, which is the documented trade-off).

## Verification commands (run yourself, don't trust the reports)

```bash
python -m pytest -q
python -m pytest tests/unit/jobs/test_manager.py -v
python -m ruff check .
python -m mypy src
for i in $(seq 1 50); do python -m pytest tests/unit/jobs/test_manager.py -q -k "event_sequence or event_ordering_under_slow" || break; done
```

## Do not touch

Everything outside `src/ai_campaign_studio/jobs/manager.py` and
`tests/unit/jobs/test_manager.py`. If you find something wrong elsewhere
(other than this already-known race), flag it as a finding rather than
fixing it directly (implementer != reviewer).
