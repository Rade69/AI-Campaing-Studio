# ACS-P0-007 — Pi fix round 1 report

- **Task:** ACS-P0-007 — JobManager + Presentation contracts + Bootstrap + Health-check
- **Implementer:** pi
- **Branch:** `task/ACS-P0-007-jobs-presentation-bootstrap`
- **Round:** fix round 1 (guard test bug)

---

## What was broken

`tests/unit/presentation/test_no_gui_imports.py` had a real bug: the helper
returned only the **top-level** module segment of each import
(`alias.name.split(".")[0]` / `node.module.split(".")[0]`). The forbidden
prefix check then compared that top-level name against
`"ai_campaign_studio.infrastructure"`:

```python
for prefix in _FORBIDDEN_PREFIXES:          # ("ai_campaign_studio.infrastructure",)
    for name in tops:                        # e.g. "ai_campaign_studio"
        if name == prefix or name.startswith(prefix + "."):
            ...
```

`name` was always `"ai_campaign_studio"`, which is neither equal to nor a
prefix-extension of `"ai_campaign_studio.infrastructure"`, so the
infrastructure half of the guard could never fire. The guard was a no-op for
the very boundary it was added to protect.

## What changed

Rewrote `tests/unit/presentation/test_no_gui_imports.py`:

- `_imported_modules()` now returns **full** module names:
  - `import ai_campaign_studio.infrastructure` → `ai_campaign_studio.infrastructure`;
  - `from X import Y` → `X.Y` (so `from ai_campaign_studio import infrastructure`
    is caught);
  - relative imports are resolved against `ai_campaign_studio.presentation`.
- `_forbidden_names()` applies the top-level check (GUI/web/provider SDK) on the
  first segment and the prefix check on the full name.
- Added two self-tests so the guard can never silently become a no-op again:
  - `test_guard_detects_forbidden_imports` (PySide6 + infra via `from X import Y`
    and direct submodule import);
  - `test_guard_allows_clean_presentation_imports`.

## Adversarial proof — real forbidden import in `presentation/state.py`

To prove the fixed guard is not a no-op against the actual presentation tree
(not just a synthetic tmp file), a forbidden import was temporarily added to
`src/ai_campaign_studio/presentation/state.py`:

```python
from ai_campaign_studio.infrastructure.database.connection import create_connection
```

**FAIL (forbidden import present):**

```
$ python -m pytest tests/unit/presentation/test_no_gui_imports.py -v
...
tests/unit/presentation/test_no_gui_imports.py::test_presentation_has_no_gui_web_or_infra_imports FAILED [ 33%]
...
E       AssertionError: assert ['state.py: a...e_connection'] == []
E         Left contains one more item: 'state.py: ai_campaign_studio.infrastructure.database.connection.create_connection'
1 failed, 2 passed in 0.14s
```

The guard caught the exact dotted path. The temporary import was removed.

**PASS (import removed):**

```
$ python -m pytest tests/unit/presentation/test_no_gui_imports.py -v
tests/unit/presentation/test_no_gui_imports.py::test_presentation_has_no_gui_web_or_infra_imports PASSED [ 33%]
tests/unit/presentation/test_no_gui_imports.py::test_guard_detects_forbidden_imports PASSED [ 66%]
tests/unit/presentation/test_no_gui_imports.py::test_guard_allows_clean_presentation_imports PASSED [100%]
3 passed in 0.06s
```

`grep` confirms no leftover import in `presentation/state.py`.

## Evidence

```
$ python -m pytest tests/unit/presentation/test_no_gui_imports.py -v
tests/unit/presentation/test_no_gui_imports.py::test_presentation_has_no_gui_web_or_infra_imports PASSED [ 33%]
tests/unit/presentation/test_no_gui_imports.py::test_guard_detects_forbidden_imports PASSED [ 66%]
tests/unit/presentation/test_no_gui_imports.py::test_guard_allows_clean_presentation_imports PASSED [100%]
3 passed in 0.07s
```

Full re-verification:

```
$ python -m pytest -q
165 passed in 5.07s

$ python -m ruff check .
All checks passed!

$ python -m mypy src
Success: no issues found in 51 source files
```

## Files changed in this round

- `tests/unit/presentation/test_no_gui_imports.py` (rewrite + 2 new self-tests)
- `agent_reports/2026-09-01-ACS-P0-007-pi.md` (added "Fix round 1" section)
