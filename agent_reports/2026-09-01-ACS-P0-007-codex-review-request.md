# ACS-P0-007 — Codex review request

- **Task:** ACS-P0-007 — JobManager + Presentation contracts/state + Bootstrap wiring + Health-check (P0.20-P0.23)
- **Branch:** `task/ACS-P0-007-jobs-presentation-bootstrap` @ `b687187`
- **Risk:** HIGH — bootstrap/composition root, stays on full Codex+Claude+Human Owner cycle per workflow §29 regardless of the LOW/MEDIUM review-cost reduction.

Read in this order:

```text
agent_reports/ACS-P0-007-task-contract.md          (contract — read fully)
agent_reports/2026-09-01-ACS-P0-007-pi.md          (implementer evidence)
agent_reports/2026-09-01-ACS-P0-007-fix-round1-pi.md (fix round 1 evidence)
agent_reports/2026-09-01-ACS-P0-007-pi-confirmed.md (coordinator confirmation)
agent_reports/2026-09-01-ACS-P0-007-review-claude.md (Claude review, PASS)
```

Diff base: `main` @ `c456515` (contract-only commit, pre-implementation).

## Context you need

This is the first task that actually wires translator, both registries,
secret store, database+migrations, and a new JobManager into
`bootstrap.py`'s composition root — everything before this task only
built Settings→Paths→logging. `Bootstrap` was deliberately extended rather
than replaced with a parallel `FoundationContainer` class.

## Known finding already resolved (fix round 1)

Claude review (before this request) found that
`tests/unit/presentation/test_no_gui_imports.py` had a real bug: the
infrastructure-prefix check compared only the top-level import segment
(`split(".")[0]`) against a dotted prefix, so it could never fire — the
same bypass class Codex caught on ACS-P0-002. Fixed to track full dotted
import paths; two new self-tests guard against regression. Both the Claude
review and the fix-round evidence document independent FAIL→PASS
reproduction of this specific fix. Please still sanity-check the fixed
version — don't assume it's airtight just because a prior bypass class
inspired the fix.

## Review focus (from the task contract)

- Does the network-isolation adversarial proof (`test_bootstrap.py::
  test_bootstrap_builds_offline`) actually catch every network path, or only
  the three `socket.*` functions it monkeypatches? Is there another way
  `create_bootstrap` (or anything it calls — Translator, PlatformRegistry,
  AIProviderRegistry, `create_connection`, `run_migrations`, `JobManager`)
  could reach the network that the monkeypatch wouldn't catch?
- Does the cancellation test use a genuine concurrent scenario (it does —
  `ThreadPoolExecutor` + `time.sleep(0.001)` over 5000 steps), or is there a
  race between `cancel()`'s CANCELLING transition and the worker's final
  state write that could flake or mask a bug?
- `--health-check` JSON — try it with a real provider API key set in the
  environment (`AI_CAMPAIGN_STUDIO_OPENAI_API_KEY` or similar) and confirm
  no leak, not just the empty-environment case already tested.
- `JobManager` edge cases: `shutdown()` while a job is actively running,
  `cancel()`/`get_state()` on an unknown `job_id`, cancelling an already
  terminal job (no-op expected), `submit()` after `shutdown()`.
- Does `run_health_check` calling `bootstrap.migration_runner(...)` again
  (re-running migrations as part of every health check) have any downside
  beyond the idempotency already relied upon — e.g. under concurrent health
  checks, or on a corrupted/partially-applied migrations state?
- Is `Bootstrap` still not a service-locator antipattern — every wired
  field has a clear, explicit purpose, no generic `get(name)` access?
- `presentation/` boundary: re-check the fixed guard yourself with a fresh
  bypass attempt of your own (dynamic import, `importlib`, relative import,
  case-sensitivity variant) — the ACS-P0-002 lesson was that Claude's first
  pass missed exactly these forms.

## Verification commands (run yourself, don't trust the reports)

```bash
python -m pytest -q
python -m ruff check .
python -m mypy src
python -m ai_campaign_studio.main --health-check
python scripts/health_check.py
```

## Do not touch

Build sequence order, `model_registry` alias-to-`provider_registry` pattern,
resource-lifecycle shutdown pairs in `main.py`, `PresentationFacade`
Protocol shape — all deliberate per contract. If you find something wrong
in these, flag it as a finding rather than fixing it directly (implementer
!= reviewer).
