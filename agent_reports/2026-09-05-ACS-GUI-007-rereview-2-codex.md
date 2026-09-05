---
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
tests: PASS_WITH_NOTES
live_verification: NOT_AVAILABLE_BY_CODEX
gitnexus_impact: NOT_AVAILABLE
closed_findings: [BF-1, BF-2, BF-3]
blocking_findings: []
non_blocking_notes: [N1]
---

# ACS-GUI-007 — Codex re-review 2 after BF-3 fix

Reviewer: Codex  
Date: 2026-09-05  
Worktree: `H:\ai-campaign-studio-worktrees\ACS-GUI-007-provider-config`  
Branch: `task/ACS-GUI-007-provider-config`

```text
CILJ: Re-review za BF-3 — `configure_provider` generic exception log path nije smio logovati secret-bearing exception message.
URAĐENO: PASS_WITH_NOTES — BF-1/BF-2/BF-3 su zatvoreni; nema novih blocking nalaza u pregledanom opsegu.
NE DIRATI: application/domain/infrastructure/bootstrap/app.css i ostale ekrane; ovaj review je ostao na provider-secret bridge površini.
SLJEDEĆE: Može na Human Owner odluku/odobrenje, uz poznatu napomenu o Codex sibling-worktree full-suite harness failovima.
```

## Verdict

**PASS_WITH_NOTES.** Previous Codex findings are closed. No confirmed new
blocking defect found in the rereview scope.

## Closed findings

### BF-1 — closed: `configure_provider` error shape is now provider-specific

`configure_provider()` no longer routes its error paths through the campaign
flow `_err()` helper. It now uses `_provider_err(...)`, which returns exactly
`ProviderConfigResultUiModel` shape:

```text
{ok, provider_code, error_code, error_message}
```

The new regression test covers non-dict, missing fields, wrong types, unknown
provider, and generic backend error paths and checks that no `campaign_id` /
`plan_item_count` keys leak from the campaign flow.

### BF-2 — closed: bridge-unavailable JS path clears the password input

The provider-save handler now places the bridge availability branch inside the
same `try/finally` block as the async bridge call. Once a non-empty `apiKey` is
read, `finally` always runs:

```text
input.value=''
el.disabled=false
```

That covers success, returned-error, thrown exception, and the previous missed
`window.pywebview.api.configure_provider` unavailable path.

### BF-3 — closed: poisoned exception message no longer leaks to logs

Fix evidence:

- `src/ai_campaign_studio/presentation_webview/bridge/__init__.py:367-390`
  now catches `Exception as exc` and logs with `logger.error(...)`, not
  `logger.exception(...)`.
- The logged fields are bounded:
  provider code + `type(exc).__name__`.
- The exception object, traceback, and `str(exc)` are not passed to logging.

I repeated my previous adversarial scenario by patching
`secret_store.set_secret` to raise an exception whose message contains a
sentinel API-key-like string:

```text
RuntimeError("backend echoed sk-SENTINEL-R2-secret-99999")
```

Observed output:

```json
{
  "records": [
    {
      "exc_info": false,
      "message": "configure_provider failed for provider OPENAI (err=RuntimeError)"
    }
  ],
  "result": {
    "error_code": "INTERNAL_ERROR",
    "error_message": "Konfiguracija provajdera nije uspjela (interna greška).",
    "ok": false,
    "provider_code": null
  }
}
```

The sentinel does not appear in the returned dict or the captured formatted log
record, and `exc_info` is false.

## Verification performed

Targeted ACS-GUI-007 / bridge / presentation / boundary regression set:

```text
pytest tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py \
       tests/unit/presentation_webview/test_podesavanja_ssr.py \
       tests/unit/presentation \
       tests/architecture/test_import_boundaries.py -q -p no:cacheprovider

93 passed in 7.70s
```

Static checks on touched areas:

```text
ruff check <presentation_webview/presentation touched paths>
All checks passed!
```

```text
mypy <presentation_webview/presentation touched paths>
Success: no issues found in 19 source files
```

Full pytest from my restricted sibling-worktree runner:

```text
pytest tests -q -p no:cacheprovider
2 failed, 799 passed, 1 warning in 66.74s
```

The remaining two failures are the same runner/worktree permission artifacts
seen in prior GUI reviews, not ACS-GUI-007 product regressions:

- `tests/unit/scripts/test_check_no_secrets.py::test_main_against_clean_repo_passes`
  fails because subprocess `git ls-files -z --` exits 128 in this restricted
  sibling-worktree arrangement.
- `tests/unit/scripts/test_generate_phase0_gate_report.py::test_gate_report_against_current_repo_passes`
  fails because the subprocess cannot write
  `H:\ai-campaign-studio-worktrees\ACS-GUI-007-provider-config\artifacts\phase0_foundation_gate.json`
  under this sandbox permission profile.

## Non-blocking notes

### N1 — Live keyring verification still belongs to the coordinator/human environment

I did not repeat the real OS keyring + real provider key verification because I
do not have access to the real provider key in this review context. Claude's
previous report says the real keyring write and fresh-bridge Gemini call were
live-verified. This rereview independently verifies the code-level BF-3 closure
and regression tests, but treats that live provider proof as external evidence.

## Scope reviewed

- `src/ai_campaign_studio/presentation_webview/bridge/__init__.py`
- `src/ai_campaign_studio/presentation_webview/static/app.js`
- `tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py`
- Supporting targeted tests/static checks listed above.

