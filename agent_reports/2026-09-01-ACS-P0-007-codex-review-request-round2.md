# ACS-P0-007 — Codex re-review request (round 2)

- **Branch:** `task/ACS-P0-007-jobs-presentation-bootstrap` @ `ffa25ad`
- **Diff since your round 1 review:** `489207a..ffa25ad`

Closes both round 1 blocking findings:

```text
agent_reports/2026-09-01-ACS-P0-007-fix-round2-pi.md   (implementer fix + adversarial proof)
```

- **BF-1** (`JobManager.submit()` after `shutdown()` orphan job): fixed in
  `src/ai_campaign_studio/jobs/manager.py` — explicit `_shutdown` flag
  checked before any side effect, rollback around `executor.submit()` for
  the race window, `CREATED` emitted only after successful scheduling. New
  regression tests: `test_submit_after_shutdown_raises_and_leaves_no_orphan`,
  `test_shutdown_is_idempotent`.
- **BF-2** (dynamic-import bypass in the presentation guard): fixed in
  `tests/unit/presentation/test_no_gui_imports.py` — scanner now resolves
  `importlib.import_module(...)`, `__import__(...)`, `importlib.__import__(...)`,
  `builtins.__import__(...)`, `getattr(importlib, "import_module")(...)`, with
  alias resolution. New self-test: `test_guard_detects_literal_dynamic_imports`.

Coordinator (Claude) independently reproduced both: ran `submit()` after
`shutdown()` directly (confirmed empty `_jobs`), and broke each fix in turn
(removed the shutdown check/rollback; injected a real
`importlib.import_module("PySide6")` into `presentation/state.py`) to
confirm FAIL, then restored to confirm PASS — not just re-read the
implementer's own proof.

## What I'd like you to specifically re-check

- Any remaining race in `submit()`/`shutdown()` beyond what BF-1 covered —
  e.g. two threads calling `submit()` concurrently right as `shutdown()`
  flips the flag; is the lock scope sufficient?
- Whether the dynamic-import scanner has a bypass form your round-1 probe
  didn't try — e.g. `import importlib; m = importlib; m.import_module(...)`
  (double indirection), f-string/format-built module names,
  `sys.modules`/`exec`-based loading.
- Full re-run of pytest/ruff/mypy/health-check on `ffa25ad`.

## Verification (independently re-run by coordinator on `ffa25ad`)

```
python -m pytest -q                → 168 passed
python -m ruff check .             → All checks passed!
python -m mypy src                 → Success: no issues found in 51 source files
python -m ai_campaign_studio.main --health-check → exit 0
python scripts/health_check.py     → exit 0
```

Everything else from the round 1 request stands (scope, "do not touch" list,
context). No other changes were made outside BF-1/BF-2.
