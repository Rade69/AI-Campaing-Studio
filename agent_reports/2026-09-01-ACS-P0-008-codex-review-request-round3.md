# ACS-P0-008 — Codex review request (round 3, lean/focused)

- **Branch:** `task/ACS-P0-008-validators-ci-security-gate` @ `cf3cd1f`
- **Diff since your round 2 PASS_WITH_NOTES:** `8b256bb..cf3cd1f`

## Why this round is narrow

Your round 2 review (`agent_reports/2026-09-01-ACS-P0-008-review-codex-round2.md`)
already confirmed BF-1 and BF-2 closed with no blocking findings, including
your own independent Anthropic-shaped probe. Nothing about BF-1/BF-2
changed since then. **Please do not re-review BF-1/BF-2** — this round is
scoped to two new items only, both already independently reproduced by the
coordinator (see `agent_reports/2026-09-01-ACS-P0-008-minimax-bf3-confirmed.md`).

## What's new

### BF-3 — secret scanner provider-coverage gap

Flagged via an external product/security review pass, empirically
confirmed by the coordinator before being sent to the implementer:
`EnvironmentSecretStore.secret_to_env_var` (already-merged foundation code)
generates `AI_CAMPAIGN_STUDIO_<PROVIDER_CODE>_API_KEY` for *every*
registered provider (OpenAI, Anthropic, Google, DeepSeek, OpenRouter,
OpenAI-compatible), but `check_no_secrets.py`'s patterns only hardcoded
`OPENAI_API_KEY`/`ANTHROPIC_API_KEY`. Google- and OpenRouter-shaped leaks
in that env-var form were not caught; DeepSeek was only accidentally
caught because its key format happens to share OpenAI's `sk-` prefix.

Fix: one new `ai_campaign_studio_env` pattern
(`scripts/check_no_secrets.py`) that follows the naming convention
structurally, covering all current and future providers with no
per-provider hardcoding. New test:
`test_scan_file_detects_ai_campaign_studio_env_per_provider` (all 6
current providers + one hypothetical future one, quoted and unquoted).

### `_KEY_VALUE` character-class bug (found by the implementer while fixing BF-3)

`_KEY_VALUE`'s regex character class was `r"[A-Za-z0-9._\-]{16,}"` — a
stray `_` was included between the escaped `.` and `\-`, so the class
silently matched underscore too. This meant any 16+ character Python
identifier (e.g. a variable named `leak_probe_value`) could false-positive
match as a "key-shaped value" once the BF-3 pattern (whose value-capture
group has no `\b` boundary around the value, unlike the legacy patterns)
was added. Fixed to `r"[A-Za-z0-9.-]{16,}"`.

## Read set

1. `agent_reports/2026-09-01-ACS-P0-008-minimax-fixround1.md` — full
   evidence, including the BF-3 reproduction (7-provider probe set,
   before/after) and the `_KEY_VALUE` bug discovery narrative.
2. `agent_reports/2026-09-01-ACS-P0-008-minimax-bf3-confirmed.md` —
   coordinator confirmation with independent adversarial probes (a
   Google-shaped key different from the implementer's own test values;
   direct regex-behavior confirmation for the `_KEY_VALUE` fix).
3. Diff `8b256bb..cf3cd1f`: `scripts/check_no_secrets.py`,
   `tests/integration/startup/test_health_check.py`,
   `tests/unit/scripts/test_check_no_secrets.py`.

## What to focus on

1. Does `ai_campaign_studio_env` genuinely cover every provider without
   per-provider hardcoding — try a provider code not in the current test
   list (something other than `MISTRAL`).
2. Does the `_KEY_VALUE` fix reintroduce any false-negative — a real key
   containing `.` or `-` should still match; only the stray `_` inclusion
   is removed. Try a real-shaped key with underscores in a *different*
   position than the value (e.g. as part of a longer surrounding context)
   to make sure nothing legitimate is now missed.
3. Self-scan (`test_scan_file_does_not_self_match` or equivalent) —
   confirm the new pattern's own definition text still doesn't self-match.
4. Scope discipline — confirm the diff touches only the 3 files above (plus
   report files), nothing in `forbidden_paths`.

## Verification commands

```bash
python -m pytest -q
python -m ruff check .
python -m mypy src
python scripts/check_no_secrets.py
python scripts/generate_phase0_gate_report.py
cat artifacts/phase0_foundation_gate.json
```

## Verdict format

```yaml
verdict: PASS | PASS_WITH_NOTES | REJECT
scope: PASS | REJECT
security: PASS | REJECT
tests: PASS | REJECT
blocking_findings: [...]
```
