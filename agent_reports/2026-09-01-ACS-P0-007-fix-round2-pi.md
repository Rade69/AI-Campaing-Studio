# ACS-P0-007 — Pi fix round 2 report

- **Task:** ACS-P0-007 — JobManager + Presentation contracts/state + Bootstrap wiring + Health-check
- **Implementer:** pi
- **Branch:** `task/ACS-P0-007-jobs-presentation-bootstrap`
- **Round:** fix round 2 (Codex REJECT — BF-1, BF-2)

---

## What was rejected (Codex review)

### BF-1 — `JobManager.submit()` after `shutdown()` left an orphan PENDING job

`submit()` recorded the PENDING state + token and emitted `CREATED` before
calling `ThreadPoolExecutor.submit()`. After `shutdown()`, the executor raises
`RuntimeError`, leaving a never-finishing `PENDING` job in `_jobs` and a
contradictory `CREATED` event in subscribers.

### BF-2 — presentation guard missed literal dynamic imports

`tests/unit/presentation/test_no_gui_imports.py` scanned only `Import` and
`ImportFrom` nodes, so `importlib.import_module("PySide6")` and
`__import__("PySide6")` bypassed the GUI/web/provider/infra boundary.

---

## What changed

### BF-1 fix — `src/ai_campaign_studio/jobs/manager.py`

- Added an explicit `self._shutdown` flag (set under the lock in `shutdown()`).
- `submit()` now checks the flag under the lock and raises `RuntimeError`
  **before** recording any state or emitting `CREATED`.
- Added a defensive rollback: if the executor still raises `RuntimeError`
  during scheduling, the just-recorded job/token are removed before re-raising,
  so no orphan state and no `CREATED` event can leak.
- `shutdown()` is idempotent.

### BF-2 fix — `tests/unit/presentation/test_no_gui_imports.py`

- Replaced the static-only scanner with an AST visitor that also detects
  literal dynamic imports: `importlib.import_module(...)`,
  `importlib.__import__(...)`, `builtins.__import__(...)`, `__import__(...)`,
  and the `getattr(importlib, "import_module")(...)` form, with alias
  resolution (`import importlib as loader`).
- Added `test_guard_detects_literal_dynamic_imports` covering
  `importlib.import_module("PySide6")`, `__import__("PySide6")`, and
  `importlib.import_module("ai_campaign_studio.infrastructure.database")`.

### New regression tests

- `tests/unit/jobs/test_manager.py::test_submit_after_shutdown_raises_and_leaves_no_orphan`
- `tests/unit/jobs/test_manager.py::test_shutdown_is_idempotent`
- `tests/unit/presentation/test_no_gui_imports.py::test_guard_detects_literal_dynamic_imports`

---

## Adversarial proof — BF-1

Temporarily removed both the `_shutdown` flag check and the rollback from
`submit()` (the pre-fix behaviour). The regression test FAILED:

```
$ python -m pytest tests/unit/jobs/test_manager.py::test_submit_after_shutdown_raises_and_leaves_no_orphan -q
...
E       AssertionError: assert {'055fd485-...': JobState(..., status=<JobStatus.PENDING: 'PENDING'>, ...)} == {}
1 failed in 0.07s
```

Restored the fix — PASS:

```
$ python -m pytest tests/unit/jobs/test_manager.py::test_submit_after_shutdown_raises_and_leaves_no_orphan -q
1 passed in 0.04s
```

## Adversarial proof — BF-2

Temporarily emptied `_DYNAMIC_IMPORT_CALLABLES` (disabled dynamic detection).
The self-test FAILED:

```
$ python -m pytest tests/unit/presentation/test_no_gui_imports.py::test_guard_detects_literal_dynamic_imports -q
...
E       AssertionError: assert 'PySide6' in []
1 failed in 0.07s
```

Restored the callable set — PASS:

```
$ python -m pytest tests/unit/presentation/test_no_gui_imports.py::test_guard_detects_literal_dynamic_imports -q
1 passed in 0.06s
```

---

## Full re-verification

```
$ python -m pytest -q
168 passed in 5.63s

$ python -m ruff check .
All checks passed!

$ python -m mypy src
Success: no issues found in 51 source files

$ python -m ai_campaign_studio.main --health-check
{"database": "ok", "migrations": "ok", "platform_registry": "ok", "provider_registry": "ok", "python": "3.14.1", "secret_store": "available", "status": "ok", "translations": "ok", "ui_framework": "not_selected"}
exit=0

$ python scripts/health_check.py
{"database": "ok", "migrations": "ok", "platform_registry": "ok", "provider_registry": "ok", "python": "3.14.1", "secret_store": "available", "status": "ok", "translations": "ok", "ui_framework": "not_selected"}
exit=0
```

---

## Files changed in this round

- `src/ai_campaign_studio/jobs/manager.py` (BF-1)
- `tests/unit/jobs/test_manager.py` (2 new regression tests)
- `tests/unit/presentation/test_no_gui_imports.py` (BF-2 + dynamic-import self-test)
