---
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
tests: PASS_WITH_NOTES
gitnexus_impact: NOT_AVAILABLE
blocking_findings: []
resolved_findings: [BF-1]
notes: [N1, N2]
---

CILJ: Nezavisno/adversarial pregledati ACS-F1-018 — Anthropic live adapter nakon BF-1 fix runde.
URAĐENO: PASS_WITH_NOTES — native `output_config` put je stvarno implementiran i testiran; nema blocking findings. Dva mala note-a su dokumentovana bez zahtjeva za fix rundu.
NE DIRATI: Ne dirati `application/`, `ports/`, `ai_registry/`, `bootstrap.py`, OpenAI/DeepSeek/OpenRouter/Google adaptere, GUI ili provider resources.
SLJEDEĆE: Human Owner može čitati ovaj + Claude review za odluku; live Anthropic smoke-test ostaje vrijedan ako se obezbijedi pravi ključ.

# ACS-F1-018 — Codex adversarial review

Pregledano prema:

- `agent_reports/2026-09-04-ACS-F1-018-brief-za-codex.md`
- `agent_reports/ACS-F1-018-task-contract.md`
- `agent_reports/2026-09-04-ACS-F1-018-minimax.md`
- `agent_reports/2026-09-04-ACS-F1-018-review-claude.md`
- `src/ai_campaign_studio/infrastructure/ai/anthropic_adapter.py`
- `tests/unit/infrastructure/ai/test_anthropic_adapter.py`
- `pyproject.toml` diff
- `ports/ai.py` and current `TextGenerationPort` call sites

## Verdict

PASS_WITH_NOTES.

BF-1 is closed. The adapter no longer injects a JSON-schema directive into `system_text`; it sends:

```python
output_config={
    "format": {
        "type": "json_schema",
        "schema": request.json_schema,
    }
}
```

directly to `client.messages.create(...)`, while passing `system=request.system_text` unchanged.

I did not confirm a blocking defect in the reviewed scope.

## Resolved previous finding

### BF-1 — ZATVOREN

Evidence:

- `src/ai_campaign_studio/infrastructure/ai/anthropic_adapter.py:122` passes `system=request.system_text`.
- `src/ai_campaign_studio/infrastructure/ai/anthropic_adapter.py:124` passes `output_config`.
- `tests/unit/infrastructure/ai/test_anthropic_adapter.py:167` asserts the exact `output_config` payload.
- `tests/unit/infrastructure/ai/test_anthropic_adapter.py:194` asserts the old system-text schema injection is gone.
- Local SDK introspection against project `.venv` confirms `anthropic 1.3.0` and `messages.create(..., output_config: OutputConfigParam | Omit, system: ... )`.

My independent spy probe produced:

```text
payload_ok True
system_exact SYSTEM_SENTINEL -- do not mutate
messages [{'role': 'user', 'content': 'USER_SENTINEL'}]
output_config {'format': {'type': 'json_schema', 'schema': {'type': 'object', 'properties': {'items': {'type': 'array', 'minItems': 3, 'maxItems': 3, 'items': {'type': 'string'}}}, 'required': ['items']}}}
temperature 0.2
max_tokens 321
auth_calls 1
auth_error INVALID_API_KEY False
rate_calls 2
rate_error RATE_LIMIT False
```

This confirms the exact high-risk behavior from the brief:

- schema is sent to the SDK argument, not merely mentioned in prompt text;
- `system_text` is not modified;
- auth is not retried;
- rate-limit retry is bounded at 2 attempts;
- mapped errors do not include the `sk-ant` sentinel.

## Blocking findings

None.

No confirmed code defect found in the reviewed scope.

## Notes

### N1 — [low] Timeout-specific error message branch is currently unreachable

Evidence:

- `src/ai_campaign_studio/infrastructure/ai/anthropic_adapter.py:272`
- `src/ai_campaign_studio/infrastructure/ai/anthropic_adapter.py:276`
- SDK introspection: `APITimeoutError` MRO is `APITimeoutError -> APIConnectionError -> APIError -> AnthropicError`.

Failure path:

`_map_error()` checks `isinstance(exc, APIConnectionError)` before `isinstance(exc, APITimeoutError)`. Because `APITimeoutError` is a subclass of `APIConnectionError`, timeout errors map to `"Anthropic connection error"` instead of the more precise `"Anthropic request timed out"`.

Impact:

Bounded and non-blocking. The `ErrorCode` remains `NETWORK_ERROR`, retry behavior is correct, and user-visible secret safety is preserved. This is diagnostic precision only.

Recommended correction:

If touched later, check `APITimeoutError` before `APIConnectionError`, or remove the dead timeout-specific branch.

### N2 — [low] Future Anthropic model compatibility: avoid non-default `temperature` unless deliberately supported

Evidence:

- `src/ai_campaign_studio/infrastructure/ai/anthropic_adapter.py:219` forwards `temperature` when present.
- `tests/unit/infrastructure/ai/test_anthropic_adapter.py:257` asserts forwarding.
- Current project call sites reviewed (`GenerateCampaignPlan`, `GenerateSocialPost`, `ReviseContentPiece`) do not set `temperature`, so the common path omits it.
- Anthropic model-deprecation docs say non-default sampling parameters are deprecated for newer models and can return 400 on affected models.

Failure path:

If a future caller sets `AIRequest.temperature` against newer Anthropic models that reject non-default sampling params, the adapter will send it and map the resulting `BadRequestError` to `PROVIDER_ERROR`.

Impact:

Non-blocking today. Current production use-case path does not set temperature, the installed SDK signature still accepts it, and errors are safely mapped if a future caller does use it.

Recommended correction:

When model selection/runtime policy is added, either omit sampling params for Anthropic by default or gate them by model capability/provider policy.

## Coverage reviewed

- Complete new `AnthropicAdapter` implementation.
- Complete `test_anthropic_adapter.py`.
- `pyproject.toml` dependency diff.
- `TextGenerationPort` request/response contract.
- Existing application call sites that construct `AIRequest`.
- Error/retry behavior for `RateLimitError`, `APIConnectionError`, `APITimeoutError`, `AuthenticationError`, and `BadRequestError`.
- Fake response shape: tests construct real `anthropic.types.Message`, `TextBlock`, `Usage`, and `ModelInfo`, not broad `SimpleNamespace` response objects.
- Scope boundaries: `domain/`, `application/`, `ports/`, `ai_registry/`, `bootstrap.py`, OpenAI/OpenAI-compatible adapter files, and GUI are not modified by this task.

## Verification evidence

Repository/worktree identity:

```text
Worktree: H:\ai-campaign-studio-worktrees\ACS-F1-018-anthropic-adapter
Branch: task/ACS-F1-018-anthropic-adapter
```

`git status --short --branch`:

```text
## task/ACS-F1-018-anthropic-adapter
 M pyproject.toml
?? agent_reports/2026-09-04-ACS-F1-018-minimax.md
?? agent_reports/2026-09-04-ACS-F1-018-review-claude.md
?? src/ai_campaign_studio/infrastructure/ai/anthropic_adapter.py
?? tests/unit/infrastructure/ai/test_anthropic_adapter.py
```

`git diff --stat` only shows tracked changes:

```text
pyproject.toml | 22 +++++++++++++++++++---
```

The new adapter/test files are untracked, so I read them directly; I did not rely on `git diff --stat` alone.

Targeted Anthropic tests:

```text
python -m pytest tests/unit/infrastructure/ai/test_anthropic_adapter.py -q -p no:cacheprovider
29 passed in 1.88s
```

Full test suite from this sandbox with explicit `PYTHONPATH` and workspace `--basetemp`:

```text
python -m pytest tests -q -p no:cacheprovider --basetemp .tmp_f1018_pytest
2 failed, 671 passed in 94.46s
```

Both failures are environment/worktree artifacts, not Anthropic adapter defects:

1. `test_main_against_clean_repo_passes` — subprocess `git ls-files` exits 128 from the linked worktree path in this sandbox.
2. `test_gate_report_against_current_repo_passes` — `PermissionError` writing `artifacts/phase0_foundation_gate.json` in the sibling worktree.

Direct secret scan:

```text
python scripts/check_no_secrets.py
NO CONFIRMED SECRET IN TRACKED FILES
```

Ruff:

```text
python -m ruff check src tests scripts
All checks passed!
```

Architecture boundaries:

```text
python -m pytest tests/architecture/test_import_boundaries.py -q -p no:cacheprovider --basetemp .tmp_f1018_arch
18 passed in 0.27s
```

Mypy:

```text
python -m mypy src --cache-dir .tmp_f1018_mypy --config-file pyproject.toml
Success: no issues found in 135 source files
```

SDK introspection:

```text
anthropic 1.3.0
messages.create(... output_config: 'OutputConfigParam | Omit' ..., system: 'Union[str, Iterable[TextBlockParam]] | Omit' ...)
has OutputConfigParam True
has JSONOutputFormatParam True
Message ['container', 'content', 'id', 'model', 'role', 'stop_details', 'stop_reason', 'stop_sequence', 'type', 'usage']
TextBlock ['citations', 'text', 'type']
Usage ['cache_creation', 'cache_creation_input_tokens', 'cache_read_input_tokens', 'inference_geo', 'input_tokens', 'output_tokens', 'output_tokens_details', 'server_tool_use', 'service_tier']
ModelInfo ['capabilities', 'created_at', 'display_name', 'id', 'max_input_tokens', 'max_tokens', 'type']
```

## GitNexus / impact

NOT_AVAILABLE for this linked worktree.

Attempt:

```text
npx gitnexus detect-changes --scope compare --base-ref main --repo AI-Campaing-Studio
No changes detected.
```

That is not credible because the worktree visibly has `pyproject.toml` plus new untracked adapter/test files. I treated GitNexus as unavailable for this review and compensated with direct diff/source/call-site review.

## External documentation checked

- Anthropic docs show `system` as a top-level `messages.create(...)` parameter in Messages API examples.
- Anthropic docs show `output_config` as the current output control mechanism in newer examples/migration guidance.
- Anthropic model-deprecation docs note sampling parameter deprecations for newer models; this informed N2 only, not a blocking finding.

Sources:

- https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/prompt-templates-and-variables
- https://docs.anthropic.com/en/docs/about-claude/model-deprecations

## Not verified

- No live Anthropic API call. I did not have an Anthropic API key in scope.
- Server-side schema enforcement was verified by SDK argument shape + spy tests, not by a real network call.
- Fresh dependency install was not rerun by Codex in this review; I verified the installed project `.venv` is `anthropic 1.3.0` and that the SDK exposes the required types/parameters.

