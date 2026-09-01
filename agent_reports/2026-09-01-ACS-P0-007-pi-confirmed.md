# ACS-P0-007 — Coordinator confirmation (Claude)

- **Task:** ACS-P0-007 — JobManager + Presentation contracts/state + Bootstrap wiring + Health-check
- **Branch:** `task/ACS-P0-007-jobs-presentation-bootstrap` @ `de88720`
- **Implementer:** Pi
- **Coordinator:** Claude — independently re-verified, does not take implementer's report at face value

---

## Scope check

`git diff main --stat` confirms all changed/new files are inside `allowed_paths`
except `tests/test_foundation.py`, which is the accepted OUT_OF_SCOPE_FINDING
(2 tests updated to the new bootstrap/main surface, ripple from in-scope
`bootstrap.py`/`main.py` semantic changes — reviewed diff line-by-line,
minimal and correct, no coverage weakened). No `forbidden_paths` touched.

## Source read in full (not diagonally)

`bootstrap.py`, `main.py`, `presentation/__init__.py`,
`jobs/{models,events,cancellation,manager}.py`,
`presentation/{contracts,state,ui_models}.py`, `scripts/health_check.py`,
`tests/unit/presentation/test_no_gui_imports.py` (both pre- and post-fix),
`tests/integration/startup/test_bootstrap.py`. Cross-checked
`AppSettings.environment`, `AppPaths.ensure_directories`/`resources_dir`/
`database_path`, `create_connection`, `run_migrations` signatures against
their actual P0-002/006 implementations — all match what `bootstrap.py`
calls.

## Independent verification run (own `.venv`, PYTHONPATH override to this worktree)

```
python -m pytest -q                → 165 passed
python -m ruff check .             → All checks passed!
python -m mypy src                 → Success: no issues found in 51 source files
python -m ai_campaign_studio.main --health-check → exit 0, JSON matches contract schema
python scripts/health_check.py     → exit 0, identical JSON
```

## Adversarial reproduction — done independently, not just re-read

1. **Bootstrap network isolation** — injected a real
   `socket.create_connection(("example.com", 80))` at the top of
   `create_bootstrap`, confirmed `test_bootstrap_builds_offline` FAILS with
   `AssertionError: network access attempted during bootstrap`, removed the
   probe, confirmed PASS, confirmed `git diff` shows no leftover.
2. **JobManager cooperative cancellation** — chose a different break than Pi's
   own proof (Pi removed the token-check from the test's callable; I instead
   removed the `self._tokens[job_id].request_cancel()` call inside
   `JobManager.cancel` itself, exercising the production cancel path
   directly). Confirmed `test_cooperative_cancellation_stops_work` FAILS
   (`did not reach {CANCELLED}; last state=... CANCELLING ...`), restored,
   confirmed PASS, confirmed no leftover.
3. **Boundary guard fix (fix round 1)** — added a real
   `from ai_campaign_studio.infrastructure.database.connection import create_connection`
   to `presentation/state.py`, confirmed
   `test_presentation_has_no_gui_web_or_infra_imports` FAILS and reports the
   exact dotted path, removed the import, confirmed PASS (3/3), confirmed no
   leftover.

## Fix round 1 — real finding, resolved

Found during Claude review (before Codex was engaged): the original
`test_no_gui_imports.py` derived only the top-level segment of each import
(`split(".")[0]`), so the `_FORBIDDEN_PREFIXES` check against
`"ai_campaign_studio.infrastructure"` could never match — the infrastructure
half of the guard was dead code (same bypass class as the Codex findings on
ACS-P0-002). No live violation existed, but the safety net was non-functional.
Sent back to Pi as a scoped fix-round brief rather than patched directly, to
preserve implementer/reviewer separation. Pi's fix tracks full dotted import
paths and adds two self-tests
(`test_guard_detects_forbidden_imports`/`test_guard_allows_clean_presentation_imports`)
against regression. Independently reproduced above (item 3).

## Verdict

PASS. Ready for Codex review request (HIGH risk — bootstrap/composition root
stays on the full cycle per workflow §29, unaffected by the LOW/MEDIUM
review-cost reduction).
