# ACS-P0-007 — Final decision packet

**Task:** ACS-P0-007 — JobManager + Presentation contracts/state + Bootstrap wiring + Health-check (P0.20–P0.23)
**Branch:** `task/ACS-P0-007-jobs-presentation-bootstrap`, HEAD `3a5a5c0`
**Base:** `main@c456515`
**Contract:** `agent_reports/ACS-P0-007-task-contract.md`

## D1 — Readiness recommendation: **READY FOR HUMAN APPROVAL**

Requested scope (P0.20–P0.23) is fully implemented, all three reviewer-raised
defects across three Codex rounds are confirmed fixed with independent
coordinator re-verification (including deliberately reproducing each bug and
each fix myself, not just re-reading the implementer's or Codex's own proof),
no blocking finding remains, and residual items are either the same
structural GitNexus gap accepted on every prior merge, or an explicitly
non-blocking item Codex itself scoped out.

## Blocking findings

None open.

## Accepted/fixed findings

| ID | Reviewer | Defect | Round fixed | Evidence |
|---|---|---|---|---|
| (pre-Codex) | Claude | Presentation boundary guard (`test_no_gui_imports.py`) derived only the top-level segment of each import (`split(".")[0]`), so the `_FORBIDDEN_PREFIXES` check against `ai_campaign_studio.infrastructure` could never match — dead code, same bypass class as ACS-P0-002 | fix round 1 (`b687187`) | `agent_reports/2026-09-01-ACS-P0-007-fix-round1-pi.md`; coordinator independently injected a real forbidden import into `presentation/state.py`, confirmed FAIL, restored, confirmed PASS |
| BF-1 | Codex (round 1) | `JobManager.submit()` after `shutdown()` recorded a `PENDING` job and emitted `CREATED` before the executor raised `RuntimeError`, leaking an orphan job/event | fix round 2 (`ffa25ad`) | `agent_reports/2026-09-01-ACS-P0-007-fix-round2-pi.md`; coordinator independently re-ran `submit()` after `shutdown()`, confirmed no orphan state |
| BF-2 | Codex (round 1) | Presentation guard missed literal dynamic imports (`importlib.import_module(...)`, `__import__(...)`) | fix round 2 (`ffa25ad`) | same; coordinator independently injected a real `importlib.import_module("PySide6")` call into `presentation/state.py`, confirmed FAIL, restored, confirmed PASS |
| R2-BF-1 | Codex (round 2 re-review) | An accepted-but-still-queued job (worker busy) stayed permanently `PENDING` when `shutdown(cancel_futures=True)` cancelled its not-yet-started `Future` — `CREATED` emitted, no terminal state/event ever followed | fix round 3 (`a9adc76`) | `agent_reports/2026-09-01-ACS-P0-007-fix-round3-pi.md`; coordinator independently reproduced the original bug (`max_workers=1`, blocker + queued job → stuck `PENDING`) before dispatching the fix, then independently reproduced the fix and broke it a *different* way than the implementer (disabled `Future` tracking in `submit()` rather than removing the shutdown-cleanup call) to confirm the regression test actually catches a broken fix |

Codex round 3 re-review (`agent_reports/2026-09-01-ACS-P0-007-review-codex-round3.md`,
main checkout): **PASS_WITH_NOTES**, no blocking findings — confirmed R2-BF-1
closed via its own live probes (`wait=False`, `wait=True`, and a 100-job
concurrent submit/shutdown stress probe: 0 pending after shutdown).
Coordinator independently reproduced the same concurrent stress scenario
(100 concurrent `submit()` calls racing a `shutdown(wait=True)`): 100
accepted, 0 rejected, 0 left `PENDING`.

Claude's original architecture review (`agent_reports/2026-09-01-ACS-P0-007-review-claude.md`,
PASS, pre-Codex) covered build-sequence order, the `model_registry` alias
pattern, resource-lifecycle shutdown pairs, and the `PresentationFacade`
Protocol shape — none of which were touched by any of the three fix rounds
(all scoped to `jobs/manager.py`, its tests, and the presentation guard test),
so that verdict still holds.

## Residual risks (human should knowingly accept)

- **GitNexus impact analysis unavailable for this task** (same structural
  worktree-binding limitation as every prior task this session; pre-impact
  from the task contract was used instead — 1 known upstream caller for
  `create_bootstrap`, 0 for `from_bundled_resources` on both registries,
  confirmed accurate).
- **Presentation guard double-indirection dynamic-import bypass** — Codex
  round 2 found that `m = importlib; m.import_module("PySide6")` (assign-then-call
  indirection) still bypasses `test_no_gui_imports.py`. Codex explicitly
  scored this non-blocking, in the same class as `exec`/`sys.modules`/f-string
  obfuscated bypasses, and recommended against mixing it into the R2-BF-1
  lifecycle fix. Left unaddressed by design across rounds 2 and 3. Worth a
  future hardening pass if the presentation boundary becomes security-critical
  (e.g. once a concrete PySide6/pywebview adapter lands), but not blocking for
  P0 foundation.
- **`tests/test_foundation.py` was edited outside `allowed_paths`** — 2 tests
  updated to the new `bootstrap.py`/`main.py` surface, a necessary ripple
  from in-scope semantic changes (documented `OUT_OF_SCOPE_FINDING` in the
  original Pi evidence report, accepted by coordinator after line-by-line
  diff review — minimal, correct, no coverage weakened).

## Confirmed validation (final HEAD `3a5a5c0`)

```text
python -m pytest -q               → 170 passed
python -m ruff check .            → All checks passed!
python -m mypy src                → Success (51 source files)
python -m ai_campaign_studio.main --health-check → exit 0
python scripts/health_check.py    → exit 0
```

All three fix rounds' original reproduction scenarios re-run by both the
coordinator and Codex against the final code: all now behave correctly.
Coordinator additionally re-ran every adversarial invariant independently at
least once with its own break/restore cycle (network isolation, cooperative
cancellation, boundary guard × 2 forms, submit-after-shutdown, queued-job
shutdown-cancellation) — never relied solely on the implementer's or Codex's
own reported proof.

## Scope status

All P0.20–P0.23 implementation steps are complete: framework-neutral
`JobManager` (submit/get_state/cancel/subscribe/shutdown, cooperative
cancellation, now-correct lifecycle on every shutdown path), framework-neutral
`presentation/` (state/DTOs/`PresentationFacade` protocol, verified free of
GUI/web/infra imports including literal dynamic-import forms), `Bootstrap`
extended (not replaced) with the full P0.22 build sequence, `--health-check`
JSON entrypoint + `scripts/health_check.py` wrapper. One `OUT_OF_SCOPE_FINDING`
(`tests/test_foundation.py`) accepted as unavoidable ripple; no other scope
expansion across three fix rounds.

## Human decision needed

Approve merge of `task/ACS-P0-007-jobs-presentation-bootstrap` (`3a5a5c0`)
into `main`, accepting the residual items noted above — or request further
revision.
