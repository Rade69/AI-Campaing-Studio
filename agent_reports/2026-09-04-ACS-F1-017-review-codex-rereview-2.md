---
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
tests: PASS_WITH_NOTES
gitnexus_impact: NOT_AVAILABLE
blocking_findings: []
resolved_findings: [BF-1, R2-BF-1]
---

CILJ: Re-review 2 za ACS-F1-017 nakon R2-BF-1 fix-a u OpenAI-compatible `json_object` exact-count detektoru.
URAĐENO: PASS_WITH_NOTES — R2-BF-1 je zatvoren; `discount`/`account_id` više ne proizvode lažni exact-count prompt blok, dok stvarni `*_count` i standalone `count` slučajevi ostaju pokriveni.
NE DIRATI: Ne širiti ovu rundu na dynamic-import guard, live OpenRouter provjeru, application/ports/registry/bootstrap ili druge provider adaptere.
SLJEDEĆE: Ako Claude review ostaje PASS, ovo je spremno za Human Owner odluku/odobrenje; live OpenRouter može ostati zaseban smoke-test kasnije.

# ACS-F1-017 — Codex re-review 2

Pregledano prema:

- `agent_reports/2026-09-04-ACS-F1-017-rereview-2-za-codex.md`
- `agent_reports/ACS-F1-017-task-contract.md`
- `agent_reports/2026-09-04-ACS-F1-017-pi.md`
- `agent_reports/2026-09-04-ACS-F1-017-review-claude.md`
- `agent_reports/2026-09-04-ACS-F1-017-review-codex-rereview.md`
- `src/ai_campaign_studio/infrastructure/ai/openai_adapter.py`
- `src/ai_campaign_studio/infrastructure/ai/openai_compatible_providers.py`
- `tests/unit/infrastructure/ai/test_openai_adapter.py`
- `tests/unit/infrastructure/ai/test_openai_compatible_providers.py`

## Worktree / branch sanity check

The review was run against the correct worktree and branch:

```text
Worktree: H:\ai-campaign-studio-worktrees\ACS-F1-017-openai-compatible-providers
Branch: task/ACS-F1-017-openai-compatible-providers
HEAD: 73f52b1 CURRENT_STATE: ACS-F1-018 merged (Anthropic adapter, A8 part 4)
```

The requested brief exists in this worktree and is tracked:

```text
agent_reports/2026-09-04-ACS-F1-017-rereview-2-za-codex.md
```

## Verdict

PASS_WITH_NOTES.

No confirmed code defect found in the reviewed scope.

R2-BF-1 is closed. The previous false-positive path:

```text
discount: 20
account_id: 123
```

no longer causes the adapter to add an `Exact count requirements` block to the system prompt. The positive cases still work:

```text
content_piece_count: 3
count: 3
item_count: 5
```

## Resolved findings

### BF-1 — remains closed

Previously verified: DeepSeek/OpenRouter/generic OpenAI-compatible providers use `JSON_OBJECT_MODE`, while the default OpenAI path still uses `json_schema`. This was not reopened in this narrow rereview.

Relevant evidence:

- `build_deepseek_adapter(...)` passes `structured_output_mode=JSON_OBJECT_MODE`.
- `build_openrouter_adapter(...)` passes `structured_output_mode=JSON_OBJECT_MODE`.
- `build_openai_compatible_adapter(...)` defaults to `JSON_OBJECT_MODE`.
- Default `OpenAIAdapter(...)` still defaults to `JSON_SCHEMA_MODE`.

### R2-BF-1 — closed

Previous issue:

```python
r"(?P<name>[A-Za-z][A-Za-z0-9_]*count[A-Za-z0-9_]*)\s*:\s*(?P<value>\d+)"
```

matched any identifier containing the substring `count`, so `discount: 20` and `account_id: 123` were treated as exact output collection counts.

Current implementation:

```python
r"(?P<name>(?:[A-Za-z][A-Za-z0-9_]*_count|\bcount\b))\s*:\s*(?P<value>\d+)"
```

Evidence:

- `src/ai_campaign_studio/infrastructure/ai/openai_adapter.py:47`
- `tests/unit/infrastructure/ai/test_openai_adapter.py` includes:
  - positive `content_piece_count`, `count`, `item_count`;
  - negative `discount`, `account_id`;
  - `json_object` no-count path omits the count block.

Independent probe against the current code:

```text
content_piece_count [('content_piece_count', 3)]
has_count_block True
- `content_piece_count` = 3: the corresponding output collection must contain exactly 3 item(s)

count [('count', 3)]
has_count_block True
- `count` = 3: the corresponding output collection must contain exactly 3 item(s)

item_count [('item_count', 5)]
has_count_block True
- `item_count` = 5: the corresponding output collection must contain exactly 5 item(s)

discount []
has_count_block False

account_id []
has_count_block False

no_count []
has_count_block False
```

Conclusion: the exact bug from the prior Codex rejection is fixed.

## Blocking findings

None.

## Notes

No new proportional notes from this narrow round.

One existing residual from earlier P0 review cycles remains intentionally out of scope here: double-indirection dynamic import bypass in presentation guard. This task did not touch that guard.

## Coverage reviewed

- Correct worktree/branch and tracked rereview-2 brief.
- `OpenAIAdapter` structured mode branching.
- `_COUNT_LINE_RE` and `_count_constraints_from_text(...)`.
- `json_object` prompt construction and count-block insertion/omission.
- DeepSeek/OpenRouter/generic factory defaults.
- Default OpenAI `json_schema` preservation.
- Targeted tests for adapter/factory behavior.
- Scope status.

## Verification evidence

`git status --short --branch`:

```text
## task/ACS-F1-017-openai-compatible-providers
 M src/ai_campaign_studio/infrastructure/ai/openai_adapter.py
 M tests/unit/infrastructure/ai/test_openai_adapter.py
?? agent_reports/2026-09-04-ACS-F1-017-pi.md
?? agent_reports/2026-09-04-ACS-F1-017-review-claude.md
?? agent_reports/2026-09-04-ACS-F1-017-review-codex-rereview.md
?? src/ai_campaign_studio/infrastructure/ai/openai_compatible_providers.py
?? tests/unit/infrastructure/ai/test_openai_compatible_providers.py
```

Targeted adapter/factory tests:

```text
python -m pytest tests/unit/infrastructure/ai/test_openai_adapter.py tests/unit/infrastructure/ai/test_openai_compatible_providers.py -q -p no:cacheprovider
25 passed in 1.23s
```

Ruff:

```text
python -m ruff check src tests scripts
All checks passed!
```

Architecture boundaries:

```text
python -m pytest tests/architecture/test_import_boundaries.py -q -p no:cacheprovider
18 passed in 0.26s
```

Mypy:

```text
python -m mypy src --cache-dir .tmp_f1017_r2_mypy --config-file pyproject.toml
Success: no issues found in 137 source files
```

Secret scan:

```text
python scripts/check_no_secrets.py
NO CONFIRMED SECRET IN TRACKED FILES
```

Full test suite from this sandbox with explicit `PYTHONPATH` and workspace `--basetemp`:

```text
python -m pytest tests -q -p no:cacheprovider --basetemp .tmp_f1017_r2_pytest
2 failed, 696 passed, 1 warning in 99.13s
```

Both failures are the known linked-worktree/sandbox artifacts, not ACS-F1-017 defects:

1. `test_main_against_clean_repo_passes` — subprocess `git ls-files` exits 128 from the linked worktree path in this sandbox.
2. `test_gate_report_against_current_repo_passes` — `PermissionError` writing `artifacts/phase0_foundation_gate.json` in the sibling worktree.

## GitNexus / impact

NOT_AVAILABLE.

Attempt from the main checkout:

```text
npx gitnexus detect-changes --scope compare --base-ref main --repo AI-Campaing-Studio
No changes detected.
```

This is not credible for this linked worktree because the worktree visibly has adapter/test changes and untracked task files. I treated GitNexus as unavailable and compensated with direct source/diff/test review.

## Not verified

- No live DeepSeek/OpenRouter/API call in this Codex rereview-2 run.
- I did not re-review unrelated provider adapters or presentation guard internals.

