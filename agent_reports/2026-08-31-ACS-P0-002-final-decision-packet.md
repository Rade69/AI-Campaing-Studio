# ACS-P0-002 — Final decision packet

**Task:** ACS-P0-002 — Config/logging/common + architecture boundaries (P0.06–P0.10)
**Branch:** `task/ACS-P0-002-config-boundaries`, HEAD `d6dc783`
**Base:** `main@1725aaa`
**Contract:** `agent_reports/ACS-P0-002-task-contract.md`

## D1 — Readiness recommendation: **READY FOR HUMAN APPROVAL**

Requested scope (P0.06–P0.10) is fully implemented, all reviewer-raised
defects are confirmed fixed with independent re-verification, no blocking
finding remains, and the residual gaps are structural/process items already
known and consistently compensated for, not code defects.

## Blocking findings

None open.

## Accepted/fixed findings

| ID | Reviewer | Defect | Round fixed | Evidence |
|---|---|---|---|---|
| F1 | Codex (round 1) | Boundary checker missed relative import, `importlib.import_module`/`__import__` literal calls, `Flask`/`flask` casing bug | round 1 (`cb58c14`) | `agent_reports/2026-08-31-ACS-P0-002-fix-round-pi.md`; Codex round 2 confirmed all 4 stay closed |
| F2 | Codex (round 2) | 5 more literal dynamic-import forms unhandled: `importlib.__import__`, `getattr(importlib,"import_module")`, 3 aliasing variants | round 2 (`3ab8eb7`) | `agent_reports/2026-08-31-ACS-P0-002-fix-round2-pi.md`; Codex round 3 confirmed closed |
| F3 | Codex (round 3) | Global alias dict wasn't lexical-scope aware — an unrelated function's local import could shadow a module-level alias, hiding a real forbidden import | round 3 (`f30c5b3`) | `agent_reports/2026-08-31-ACS-P0-002-fix-round3-pi.md`; Codex round 4 confirmed closed |
| F4 | Codex (round 4) | Class body incorrectly treated as an enclosing scope for its methods (violates Python LEGB semantics) | round 4 (`d6dc783`) | `agent_reports/2026-08-31-ACS-P0-002-fix-round4-pi.md`; Codex round 5 (`PASS_WITH_NOTES`) confirmed closed |

Each fix was independently re-verified by the coordinator (not just the
implementer's self-report): at every round the coordinator reproduced the
exact adversarial scenario plus a combined replay of every previously known
bypass in one pass against the fixed checker, confirming no regression. By
round 4 that combined replay covered 11 distinct bypass/scope forms, all
caught, clean tree still passing (15/15 architecture tests).

Claude's initial architecture review (`agent_reports/2026-08-31-ACS-P0-002-review-claude.md`,
PASS, on the pre-fix commit `c6fa0b8`) covered dependency direction, domain
purity, and bootstrap/composition-root discipline — none of which were
touched by any of the four fix rounds (all four stayed scoped to exactly
`tests/architecture/test_import_boundaries.py`), so that architectural
verdict still holds for the final state.

## Residual risks (human should knowingly accept)

- **R1 — GitNexus impact analysis unavailable for this task.** Both the CLI
  and the newly available `mcp__gitnexus__*` tools bind to the registered
  main checkout, not the linked task worktree — confirmed independently by
  the implementer, the coordinator, and Codex, at multiple rounds.
  `gitnexus_impact` is `UNKNOWN`, not "no impact." Compensated throughout by
  full manual diff review and file-by-file reading at every round. This is a
  process/tooling gap, not evidence of a code defect, but it means no
  automated blast-radius check backs this HIGH-risk merge.
- **R2 — Redaction key-name matching is substring-only**, not
  separator-normalized (flagged by Codex round 1 as non-blocking). Real
  fragment matches (`api_key`, `secret`, etc.) work; edge-case key spellings
  without a matching fragment could theoretically slip through. Not part of
  this task's acceptance criteria.
- **R3 — `AppPaths._default_resources_dir()`** assumes a source-tree/editable-install
  layout; will need a different resolver (e.g. `importlib.resources`) if/when
  the package is ever distributed as a wheel. Explicitly out of scope for P0.
- **R4 — `main.py`'s `except Exception: return 1`** is a broad catch with no
  structured error output. Acceptable for the P0 health-check entrypoint;
  future health-check/CLI work should use the `AppError`/`ErrorCode`
  taxonomy this same task introduced.
- **R5 (process, not this task's defect) — `.agent/GITNEXUS_PROTOCOL.md`**
  still references a `gitnexus check --cycles` subcommand that doesn't exist
  in the installed CLI (discovered during ACS-P0-001 post-merge, still
  unfixed). Doesn't block this merge; worth cleaning up before it's needed.
- **R6 (process) — uncommitted Performance/Analytics doc changes** sit in the
  main working tree (`AGENTS.md`, `CLAUDE.md`, `.agent/PROJECT_MAP.md`,
  `.agent/TASK_ROUTING.md`, two new plan docs), added from another session.
  Unrelated to ACS-P0-002, not touched by this task, but still uncommitted —
  worth a decision on whether/when to commit them.

## Confirmed validation (final HEAD `d6dc783`)

```text
python -m pytest -q        → 43 passed
python -m ruff check .     → All checks passed!
python -m mypy src         → Success (18 source files)
--health-check              → exit 0
pip list / pip check        → no forbidden dependencies, no broken requirements
```

Adversarial: 11 distinct bypass/lexical-scope forms, independently
reproduced by the coordinator in one combined pass against the final
checker — all caught; clean tree unaffected (15/15 architecture tests).

Diff from merge-base (`main@1725aaa`) to final HEAD (`d6dc783`) stays
entirely within the Task Contract's `allowed_paths`; no `forbidden_paths`
touched at any point across five rounds.

## Not verified

- Automated GitNexus blast-radius/impact analysis (see R1) — structurally
  unavailable for this worktree in the current tooling setup.

## Scope status

All P0.06–P0.10 implementation steps from the Task Contract are complete
(package bootstrap extension, `AppSettings`/`AppPaths`, logging + redaction,
domain error taxonomy, empty `application`/`ports`/`presentation` seams, and
the import-boundary meta-test suite). No `OUT_OF_SCOPE_FINDING` was raised
by either implementer. The four fix rounds were pure defect-correction on
one already-in-scope file, not scope expansion.

## Human decision needed

Approve merge of `task/ACS-P0-002-config-boundaries` (`d6dc783`) into
`main`, explicitly accepting R1–R6 above as known/carried risks — or request
further revision on any specific item.
