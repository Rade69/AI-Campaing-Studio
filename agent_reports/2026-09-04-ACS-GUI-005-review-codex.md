# ACS-GUI-005 — Codex independent review

Date: 2026-09-04  
Reviewer: Codex  
Branch/worktree reviewed: `task/ACS-GUI-005-campaign-bridge` in `H:\ai-campaign-studio-worktrees\ACS-GUI-005-campaign-bridge`

## Verdict

**FAIL — 1 blocking verification finding.**

I did not find a proven new bridge security/data-integrity bug in the main
`CampaignBridgeApi` path. The bridge validates non-dict/Pydantic-invalid input
before brand/provider/use-case execution, maps internal failures to bounded
error codes/messages, and keeps the adapter factory free of SecretStore access.

However, the branch does not currently pass a fresh full test gate in this
environment because ACS-GUI-005 changed `_open_window()` to construct a real
`CampaignBridgeApi()` but did not update the existing pywebview unit test to
isolate that new side effect.

## Blocking findings

### BF-1 — `_open_window` unit test now constructs the real bridge/bootstrap and can fail before checking the WebView2 contract

Evidence:

- `src/ai_campaign_studio/presentation_webview/__main__.py:179` imports
  `CampaignBridgeApi`.
- `src/ai_campaign_studio/presentation_webview/__main__.py:181` constructs
  `bridge = CampaignBridgeApi()`.
- `src/ai_campaign_studio/presentation_webview/__main__.py:189` passes
  `js_api=bridge`.
- `tests/unit/presentation_webview/test_webview2_fail_loud.py:86` still patches
  only `webview` and `_probe_webview2`, then calls `_open_window()`.

Fresh full pytest result:

```text
3 failed, 712 passed, 1 warning in 52.67s
```

The relevant ACS-GUI-005-induced failure:

```text
FAILED tests/unit/presentation_webview/test_webview2_fail_loud.py::test_pywebview_start_uses_explicit_edgechromium_and_debug_false
PermissionError: [Errno 13] Permission denied:
'C:\\Users\\38765\\AppData\\Local\\AI Campaign Studio\\AI Campaign Studio\\logs\\ai_campaign_studio.log'
```

Root cause: the unit test is meant to verify only that `_open_window()` calls
`webview.start(gui="edgechromium", debug=False)`. After ACS-GUI-005,
`_open_window()` also constructs the real GUI bridge, which calls
`create_bootstrap()` and configures logging/paths/DB-facing composition. In a
restricted or clean test environment this can fail before the assertion being
tested is reached.

Why this is blocking:

- ACS-GUI-005 is HIGH risk and expected to keep the verification gate green.
- This is not a style issue: a pre-existing acceptance/security test is no
  longer hermetic and can fail due unrelated filesystem/logging side effects.
- The fix is narrow and inside allowed scope: patch `CampaignBridgeApi` in the
  unit test, or add a small injectable bridge factory/helper so `_open_window`
  can be tested without building the full backend composition root.

The two other full-suite failures observed in the same run were sandbox/worktree
harness artifacts, not branch-specific product findings:

- `test_main_against_clean_repo_passes`: `git ls-files` failed with exit 128
  when invoked from the sibling worktree under this restricted runner.
- `test_gate_report_against_current_repo_passes`: failed writing
  `artifacts/phase0_foundation_gate.json` in the sibling worktree due sandbox
  permissions.

## Non-blocking notes

### N1 — `CampaignBridgeApi` error mapping looks bounded; no internal secret/path leak found

Reviewed paths around:

- `CampaignBridgeApi.create_campaign_and_generate_plan()`
- `_ensure_brand()`
- `_resolve_provider()`
- `build_text_generation_adapter()`

Internal exception branches log full details server-side but return bounded
messages such as `type(exc).__name__`, not raw tracebacks, DB paths, credential
refs, or SecretStore values. Validation/domain exceptions may return
`str(exc)`, but those are user/payload-facing validation messages, not internal
secret-store or filesystem material in the reviewed call path.

### N2 — Provider factory can instantiate with an empty key if called directly, but the bridge guards it

`build_text_generation_adapter(provider_code, api_key)` deliberately does not
validate `api_key`; the unit test for the factory confirms this contract. In
the GUI bridge call path, `_resolve_provider()` returns `None` for missing/empty
secret values and `create_campaign_and_generate_plan()` stops at
`PROVIDER_KEY_MISSING` before calling the factory.

I do not consider this blocking for ACS-GUI-005 because the public GUI entry
point has the guard, and the factory is not a SecretStore-aware policy layer.

## Verification performed

Targeted review/test evidence:

```text
pytest tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py \
       tests/unit/infrastructure/ai/test_provider_adapter_factory.py \
       tests/architecture/test_import_boundaries.py -q -p no:cacheprovider

42 passed, 1 warning in 5.83s
```

Static checks on touched areas:

```text
ruff check <presentation_webview/presentation/provider_factory touched paths>
All checks passed!
```

```text
mypy <presentation_webview/presentation/provider_factory touched paths>
Success: no issues found in 20 source files
```

Full pytest:

```text
pytest tests -q -p no:cacheprovider
3 failed, 712 passed, 1 warning in 52.67s
```

Health check:

- `python -m ai_campaign_studio` is not a valid module entry in this repo
  (`ai_campaign_studio.__main__` does not exist).
- `python -m ai_campaign_studio.main --health-check` was inconclusive in this
  sandbox because it mixed the main workspace cwd with worktree source/resources
  and returned environment-level component errors. I did not count that as an
  ACS-GUI-005 product finding.

## Recommended fix

Patch only the pywebview unit-test seam:

- in `test_pywebview_start_uses_explicit_edgechromium_and_debug_false`, patch
  `ai_campaign_studio.presentation_webview.bridge.CampaignBridgeApi` or the
  imported symbol used by `_open_window()` so the test uses a sentinel fake
  bridge; or
- introduce a tiny `_build_bridge()` helper in `__main__.py` and patch that in
  the test.

Then rerun:

```text
pytest tests/unit/presentation_webview/test_webview2_fail_loud.py::test_pywebview_start_uses_explicit_edgechromium_and_debug_false -q
pytest tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py tests/unit/infrastructure/ai/test_provider_adapter_factory.py tests/architecture/test_import_boundaries.py -q
pytest tests -q
ruff check
mypy src tests
python -m ai_campaign_studio.main --health-check
scripts/health_check.py
```

