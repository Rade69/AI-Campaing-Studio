# ACS-P0-004 — Final decision packet

**Task:** ACS-P0-004 — Channel/Platform/Format registry (P0.13)
**Branch:** `task/ACS-P0-004-channel-registry`, HEAD `be3767a`
**Base:** `main@a712ce3`
**Contract:** `agent_reports/ACS-P0-004-task-contract.md`

## D1 — Readiness recommendation: **READY FOR HUMAN APPROVAL**

Requested scope (P0.13) is fully implemented, all reviewer-raised defects
are confirmed fixed with independent re-verification, no blocking finding
remains, and the one residual gap is the same structural GitNexus
limitation already accepted for every prior merge this session.

## Blocking findings

None open.

## Accepted/fixed findings

| ID | Reviewer | Defect | Round fixed | Evidence |
|---|---|---|---|---|
| BF-1 | Codex (round 1) | Blank `formats:` YAML key (`None`) fell through to a raw `TypeError` instead of `RegistryError` | round 1 (`6a2bd79`) | `agent_reports/2026-08-31-ACS-P0-004-fix-round-crush-confirmed.md` |
| BF-2 | Codex (round 1) | `frozen=True` Pydantic models still held mutable `list` fields — a caller could mutate a returned object and corrupt cached registry state for all future reads | round 1 (`6a2bd79`) | same, fixed via `tuple[str, ...]` (matches ACS-P0-003's existing convention) |
| BF-3 | Codex (round 1) | Case-variant duplicate `supported_formats` references (`[STORY, story]`) passed normalization unrejected | round 1 (`6a2bd79`) | same, closed via post-normalization duplicate check |
| BF-4 | Codex (round 2) | `raw.get("formats") or []` treated every falsy scalar (`False`, `""`, `0`) as `None`, bypassing the type check | round 2 (`be3767a`) | `agent_reports/2026-08-31-ACS-P0-004-fix-round2-crush-confirmed.md`; Codex round 3 (`PASS_WITH_NOTES`) confirmed closed with no regression on blank-key/null/empty-list behavior |

Each fix was independently re-verified by the coordinator — not just the
implementer's diff — including re-executing every one of Codex's original
live-probe reproduction scripts against the fixed code at every round.
Crush submitted no self-report at any point in this task (same pattern as
ACS-P0-001); all implementer evidence in the trail above was reconstructed
directly from the diff and by the coordinator independently running both
the required adversarial proofs and every regression probe.

Claude's architecture review (`agent_reports/2026-08-31-ACS-P0-004-review-claude.md`,
PASS, on the pre-fix commit `d379813`) covered data-driven design, absence
of platform-specific branching, and port/seam integration — none of which
were touched by either fix round (both stayed scoped to `channels/definitions.py`,
`channels/registry.py`, and the unit test file), so that verdict still holds.

## Residual risks (human should knowingly accept)

- **GitNexus impact analysis unavailable for this task** (same as every
  prior task this session) — both the CLI and `mcp__gitnexus__*` tools bind
  to the registered main checkout, not this linked worktree.
  `gitnexus_impact` is `UNKNOWN`, compensated at every round by full manual
  diff review, file-by-file reading, and live reproduction scripts.
- **`enabled: "true"` (string) Pydantic lax coercion** — Codex flagged this
  as non-blocking in round 1 and re-confirmed it's out of scope; strict
  YAML bool typing was never required by the task contract.

## Confirmed validation (final HEAD `be3767a`)

```text
python -m pytest -q      → 65 passed
python -m ruff check .   → All checks passed!
python -m mypy src       → Success (23 source files)
```

All 4 blocking findings' original reproduction scenarios re-run against the
final code by the coordinator: all now behave correctly, with explicit
regression checks confirming blank-key/`null`/empty-list `formats:` still
work as before.

## Scope status

All P0.13 implementation steps are complete (Channel enum, immutable
definitions, `PlatformRegistryPort`, data-driven `PlatformRegistry`, all 9
initial platforms with spec'd formats). No `OUT_OF_SCOPE_FINDING` was
raised. Three fix rounds were pure defect-correction on already-in-scope
files (2, then 3, then 2 files respectively) — no scope expansion.

## Human decision needed

Approve merge of `task/ACS-P0-004-channel-registry` (`be3767a`) into `main`,
accepting the GitNexus-gap risk noted above — or request further revision.

Note: ACS-P0-003 (localization, running in parallel) is still awaiting its
Codex review — this merge decision for ACS-P0-004 is independent of that
one and does not need to wait for it.
