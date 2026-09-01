# ACS-HOTFIX-001 — Final decision packet

**Task:** ACS-HOTFIX-001 — JobManager CREATED/STARTED event-ordering race (regression from ACS-P0-007 fix round 2)
**Branch:** `hotfix/ACS-HOTFIX-001-job-event-ordering`, HEAD `1df57ce`
**Base:** `main@638a479`
**Contract:** `agent_reports/ACS-HOTFIX-001-task-contract.md`

## D1 — Readiness recommendation: **READY FOR HUMAN APPROVAL**

Root cause fully understood, fix is minimal and scoped to one file plus its
tests, both Codex and the coordinator independently confirmed the fix
closes the exact race observed on GitHub Actions CI, and neither reviewer
found a blocking defect.

## Blocking findings

None.

## Notes (non-blocking, both reviewers converged independently)

| Note | Source | Detail |
|---|---|---|
| Redundant protection | Coordinator + Codex (independently) | Either (RLock + `CREATED` emit inside `submit()`'s lock) or (`_emit` holding the lock through callback dispatch) alone closes this race; the shipped fix ships both. Not a defect — reasonable defense-in-depth, and the second mechanism also protects other emit call sites (`cancel`, `_finish`, `_finish_cancelled_futures`) that don't share `submit()`'s lock-nesting shape. Corrects the evidence report's "all three changes are necessary" claim, which was not quite accurate as a minimality statement. |
| Theoretical deadlock shape | Codex | A callback that holds the manager lock (via `_emit`) and synchronously waits on a second thread that itself needs the same lock could deadlock. No such callback exists anywhere in the project today. Not blocking; worth remembering if a future `JobManager` subscriber is added. |
| Shared `.venv` `.pth` environment gotcha | MiniMax, confirmed by coordinator and Codex | The editable-install `.pth` file can silently point at a different checkout than the one being verified. Both reviewers worked around this with explicit `PYTHONPATH` overrides. Not a code defect — a verification-environment hazard specific to this session's multi-worktree setup. |

## Confirmed validation (final HEAD `1df57ce`)

```text
python -m pytest -q                                → 171 passed (coordinator, Codex)
python -m pytest tests/unit/jobs/test_manager.py -v → 17 passed
python -m ruff check .                              → All checks passed!
python -m mypy src                                  → Success (51 source files)
20-50x targeted loop (event_sequence/event_ordering) → clean every run, both reviewers
```

Both reviewers independently reproduced the original bug (FAIL) and the fix
(PASS) via adversarial breaks — the coordinator via three separate partial/
full reverts (discovering the redundancy noted above), Codex via a
scratch adversarial script covering the slow-CREATED-callback race,
submit-after-shutdown, and both queued-job-cancellation scenarios from
ACS-P0-007 (BF-1/R2-BF-1) directly, not just via the regression test suite.

## Scope status

Exactly two files touched: `src/ai_campaign_studio/jobs/manager.py` and
`tests/unit/jobs/test_manager.py`. No `forbidden_paths` touched, confirmed
by both reviewers independently. No `OUT_OF_SCOPE_FINDING`.

## Process note (transparency, not a code finding)

During coordinator verification, an attempted `git stash`/`checkout
stash@{0} -- <path>` maneuver briefly and accidentally reverted
`tests/unit/jobs/test_manager.py` to its pre-hotfix state, destroying
MiniMax's then-uncommitted new test in the working tree. This was a
coordinator process error, not an implementer or code defect.
`src/ai_campaign_studio/jobs/manager.py` was unaffected throughout. MiniMax
re-added the test; the coordinator independently confirmed its presence and
correctness before continuing review, and used only `Edit`/`Read` (no
further git-history manipulation) for the remainder of adversarial testing.

## Human decision needed

Approve merge of `hotfix/ACS-HOTFIX-001-job-event-ordering` (`1df57ce`)
into `main`, accepting the notes above — or request further revision.

After this merges, per the existing sequencing dependency recorded in
`.agent/CURRENT_STATE.md`: `artifacts/phase0_foundation_gate.json` (from
the separate, still-open ACS-P0-008 fix round) must be regenerated against
post-hotfix `main` before it can be treated as the final authoritative P0
gate artifact.
