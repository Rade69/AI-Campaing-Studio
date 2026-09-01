# ACS-P0-008 — Codex review request

- **Task:** ACS-P0-008 — Resource validators + CI quality gate + security/no-secret checks + P0 gate report (P0.24-P0.28)
- **Branch:** `task/ACS-P0-008-validators-ci-security-gate` @ `530c4ed`
- **Risk:** HIGH — security-critical (secret scan, authoritative P0 gate artifact), full Codex+Claude+Human Owner cycle per workflow §29.
- **Implementer:** MiniMax (first task in this role — new agent added 2026-09-01, same implementer/reviewer capability profile as you).

Read in this order:

```text
agent_reports/ACS-P0-008-task-contract.md          (contract — read fully)
agent_reports/2026-09-01-ACS-P0-008-minimax.md      (implementer evidence, corrected)
agent_reports/2026-09-01-ACS-P0-008-minimax-confirmed.md (coordinator confirmation + findings)
agent_reports/2026-09-01-ACS-P0-008-review-claude.md (Claude review, PASS)
```

Diff base: `main` @ `f329ab9` (contract-only commit, pre-implementation).

## IMPORTANT — read before you conclude anything about the gate report

`main` currently carries an **unfixed, separate regression**
(`ACS-HOTFIX-001`, its own contract/branch — `hotfix/ACS-HOTFIX-001-job-event-ordering`):
a `JobManager` `CREATED`/`STARTED` event-ordering race caught by GitHub
Actions CI on Linux, not reliably reproducible on Windows locally (0/300 in
one coordinator repro attempt). `ACS-P0-008`'s committed
`artifacts/phase0_foundation_gate.json` reports `"pytest": true` because the
suite genuinely passed on this Windows worktree at commit time — the
generator is not lying, it really re-executes `pytest -q`. But this file
cannot be treated as the *final* P0 gate artifact until `ACS-HOTFIX-001`
merges and the report is regenerated against post-hotfix `main`. This is a
**merge-sequencing note, not a code-quality finding** for this task — please
review `ACS-P0-008`'s tooling on its own merits, but flag it in your verdict
if you think the sequencing risk needs stronger handling than "regenerate
before Human Owner sign-off."

## Two findings already resolved before this request (both found by Claude review)

1. **Real blocker, fixed**: `.gitignore`'s `artifacts/*` rule silently
   excluded `phase0_foundation_gate.json` from ever being tracked — the
   contract's P0.28 "commit when PASS" requirement was physically
   impossible without an exception. MiniMax added
   `!artifacts/phase0_foundation_gate.json` (mirrors the existing
   `!artifacts/.gitkeep` pattern).
2. **Evidence-report accuracy, corrected**: the original report claimed an
   `if __name__ == "__main__":` block was missing and had to be "restored"
   in `validate_resources.py`. `git diff main -- scripts/validate_resources.py`
   shows that block existed unchanged before and after — the claim was
   factually wrong (the code itself was never broken). MiniMax corrected
   the report text on request; no code change was needed.

## Review focus (from the task contract)

- Realistic bypass forms for the secret scanner
  (`scripts/check_no_secrets.py`): multi-line concatenated secrets,
  base64-encoded secrets, a secret split across two string literals
  (`"sk-" + "abc..."`). The contract calls these "probably out of P0
  scope" — form your own judgment on whether the current 5-pattern set is
  proportional or needs one more form before merge.
- Does `scripts/generate_phase0_gate_report.py` genuinely execute every one
  of the 17 checks (subprocess/import+call), or does any key have a
  hardcoded/fake check? I verified this myself but a second pass is
  valuable given this is the authoritative P0 gate artifact.
- Does the CI health-check step (`.github/workflows/ci.yml`) genuinely
  isolate the temp/data path, or could it still touch the runner's real
  user profile / a real keyring under some condition?
- Does `validate_resources.py`'s new `validate_platforms`/
  `validate_ai_providers`/`validate_migrations` duplicate logic that
  already exists in `PlatformRegistry`/`AIProviderRegistry`/
  `discover_migrations`, or does it appropriately delegate?
- Edge case: what happens if `artifacts/` doesn't exist when the generator
  tries to write — confirmed it creates the directory
  (`artifacts_dir.mkdir(parents=True, exist_ok=True)`), please double-check.
- The anti-recursion guard (`ACS_GATE_REPORT_RUNNING=1`) for the `pytest`
  check inside the gate report generator — confirm it actually prevents
  infinite recursion and doesn't accidentally skip real test coverage.

## Verification commands (run yourself, don't trust the reports)

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

## Do not touch

`forbidden_paths` from the contract (all of `src/ai_campaign_studio/`
except this task's own tooling additions). If you find something wrong in
already-merged foundation code (other than the already-known
ACS-HOTFIX-001), flag it as a finding rather than fixing it directly
(implementer != reviewer).
