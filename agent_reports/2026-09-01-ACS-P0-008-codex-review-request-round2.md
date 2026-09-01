# ACS-P0-008 — Codex review request (round 2)

- **Branch:** `task/ACS-P0-008-validators-ci-security-gate`, HEAD is a merge commit combining fix round 1 (`8f43b28`) with current `main` (`4b22137`, includes `ACS-HOTFIX-001`).
- **Diff since your round 1 review:** `6b257b8..8f43b28` for the actual fix content (the merge commit on top brings in `main`'s independent `ACS-HOTFIX-001` work, already reviewed separately — see below).

## What changed since round 1

Round 1 (`agent_reports/2026-09-01-ACS-P0-008-review-codex.md`, on
`6b257b8`) returned `REJECT` with two blocking findings:

- **BF-1**: secret-shaped literals in the tracked test scope triggered the
  scanner on the clean baseline, making the gate report genuinely emit
  `status: "FAIL"` while the previously committed
  `artifacts/phase0_foundation_gate.json` claimed `PASS`.
- **BF-2**: the scanner and the gate report both echoed the matched
  secret-shaped value back into stderr / the tracked JSON `notes[]`.

Fix round 1 (`agent_reports/2026-09-01-ACS-P0-008-minimax-fixround1.md`)
closes both — 5 files changed, all within `allowed_paths`.

## Important — this branch now includes `ACS-HOTFIX-001`

This branch originally forked from `main` **before** `ACS-HOTFIX-001` (the
JobManager `CREATED`/`STARTED` event-ordering race fix, already reviewed
and merged separately by you in
`agent_reports/2026-09-01-ACS-HOTFIX-001-review-codex.md`) merged. Since
the gate report's `pytest`/`job_manager` checks need to genuinely cover the
fixed `jobs/manager.py`, the coordinator merged current `main` into this
branch before finalizing fix round 1. **Please do not re-review
`src/ai_campaign_studio/jobs/manager.py` or `tests/unit/jobs/test_manager.py`
here** — that work already went through its own full HIGH-risk cycle and is
merged. Your round 2 review here should focus exclusively on the
`ACS-P0-008` fix round 1 diff listed above.

## Read set

1. `agent_reports/ACS-P0-008-task-contract.md` — original contract.
2. `agent_reports/2026-09-01-ACS-P0-008-review-codex.md` — your round 1
   review (BF-1, BF-2).
3. `agent_reports/2026-09-01-ACS-P0-008-minimax-fixround1.md` — this
   round's implementer evidence.
4. `agent_reports/2026-09-01-ACS-P0-008-minimax-fixround1-confirmed.md` —
   coordinator confirmation, including an independent adversarial
   reproduction using a different probe than the implementer's own
   (an Anthropic-shaped key rather than OpenAI/Bearer).
5. The 5 changed files (`scripts/check_no_secrets.py`,
   `scripts/generate_phase0_gate_report.py`, and three
   `tests/unit/scripts/*` files) — diff range `6b257b8..8f43b28`.
6. The regenerated `artifacts/phase0_foundation_gate.json` — `status:
   "PASS"`, all 17 checks `true`, `notes: []`.

## Known environment constraint (same as ACS-HOTFIX-001)

The shared `.venv`'s editable-install `.pth` file can point at a different
checkout than the one you're verifying. Check it first:

```bash
cat "H:/AI Campaing Studio/.venv/Lib/site-packages/__editable__.ai_campaign_studio-0.1.0.pth"
```

It should point at this worktree's `src/`
(`H:\ai-campaign-studio-worktrees\ACS-P0-008-validators-ci-security-gate\src`)
for your verification. If not, either fix the `.pth` or set `PYTHONPATH`
explicitly for every command — the coordinator used the latter as a
belt-and-suspenders safeguard.

## What to focus on for this round

1. **BF-1 still closed.** Re-run `python scripts/check_no_secrets.py` on
   the worktree — must be `NO CONFIRMED SECRET IN TRACKED FILES`, exit 0.
   Confirm the only `sk-[A-Za-z0-9]{16,}`-shaped text anywhere in tracked
   source is the scanner's own regex pattern definition (which doesn't
   self-match — `test_scan_file_does_not_self_match` covers this).
2. **BF-2 still closed.** Inject a real secret-shaped value into a tracked
   file yourself (try a form neither the implementer nor the coordinator
   used, if you'd like independent coverage) and confirm: (a) the
   scanner's stderr shows `<redacted>`, never the raw value; (b) the
   regenerated gate report's `notes[]` for `no_secrets_detected` contains
   only the exit code, never the raw value.
3. **No new findings** — same checklist as round 1: no test regrew a
   key-shaped literal, no new `Finding.render()` path reintroduces the raw
   snippet, no new gate-report check could echo a secret without its own
   redaction.
4. **`artifacts/phase0_foundation_gate.json` is a real PASS, not
   hand-edited.** `notes: []` is the tell — a real PASS run writes an empty
   array.
5. **Scope discipline** — confirm the fix round 1 diff (`6b257b8..8f43b28`)
   touches only the 5 files above; the merge commit on top should show only
   `ACS-HOTFIX-001` content, nothing else.

## Non-blocking observations from the implementer (worth a look, not blocking)

- `_FILLER = "abcdefghijklmnop"` test constant is duplicated across three
  test files — a possible future refactor, not a fix-round item.
- `Finding.snippet` still carries the raw value for in-process callers;
  only the human-facing `render()` redacts. Intentional (human-output
  invariant, not a data-model invariant) — flag if you'd prefer stricter.

## Verification commands

```bash
python -m pytest -q
python -m ruff check .
python -m mypy src
python scripts/validate_resources.py
python scripts/check_no_secrets.py
python -m ai_campaign_studio.main --health-check
python scripts/generate_phase0_gate_report.py
cat artifacts/phase0_foundation_gate.json
python tests/unit/scripts/_adv_runner.py
```

## Verdict format

```yaml
verdict: PASS | PASS_WITH_NOTES | REJECT
scope: PASS | REJECT
acceptance: PASS | REJECT
architecture: PASS | REJECT
security: PASS | REJECT
tests: PASS | REJECT
gitnexus_impact: PASS | UNKNOWN | REJECT
blocking_findings: [...]
```
