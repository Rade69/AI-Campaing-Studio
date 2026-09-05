---
verdict: FAIL
scope: PASS
acceptance: FAIL
architecture: PASS
security: FAIL
tests: PASS_WITH_NOTES
live_verification: NOT_AVAILABLE_BY_CODEX
gitnexus_impact: NOT_AVAILABLE
blocking_findings: [BF-1, BF-2]
non_blocking_notes: [N1]
---

# ACS-GUI-007 — Codex adversarial review

Reviewer: Codex  
Date: 2026-09-04  
Worktree: `H:\ai-campaign-studio-worktrees\ACS-GUI-007-provider-config`  
Branch: `task/ACS-GUI-007-provider-config`

```text
CILJ: Pregledati HIGH-risk JS→bridge provider-secret konfiguraciju.
URAĐENO: FAIL — pronađena su 2 blocking nalaza u secret/bridge contract površini.
NE DIRATI: bootstrap.py, application/domain/infrastructure slojeve, app.css i druge GUI ekrane; fix je usko u bridge error-result helperu i provider-save JS handleru/testovima.
SLJEDEĆE: MiniMax treba usko zatvoriti BF-1/BF-2, dodati regression testove, pa poslati na Codex rereview.
```

## Verdict

**FAIL.** Scope je čist i većina security toka izgleda dobro, ali dva
konkretna acceptance/security edge-case-a ostaju otvorena:

1. `configure_provider()` error paths vraćaju pogrešan DTO shape
   (`CampaignPlanResultUiModel`) umjesto provider-config result shape-a.
2. JS `provider-save` handler ne briše uneseni API ključ ako bridge nije
   dostupan.

## Blocking findings

### BF-1 — `configure_provider` error paths return campaign-result fields instead of provider-config result fields

Evidence:

- `src/ai_campaign_studio/presentation/contracts.py:54-56` declares
  `configure_provider(...) -> ProviderConfigResultUiModel`.
- `src/ai_campaign_studio/presentation/ui_models.py:63-76` defines
  `ProviderConfigResultUiModel` with fields:
  `ok`, `provider_code`, `error_code`, `error_message`.
- `src/ai_campaign_studio/presentation_webview/bridge/__init__.py:319-330`
  maps validation failures through `self._err(...)`.
- `src/ai_campaign_studio/presentation_webview/bridge/__init__.py:355`
  maps `RegistryError`/`InvariantViolation` through `self._err(...)`.
- `src/ai_campaign_studio/presentation_webview/bridge/__init__.py:365-368`
  maps generic/internal errors through `self._err(...)`.
- `src/ai_campaign_studio/presentation_webview/bridge/__init__.py:517-526`
  implements `_err()` using `CampaignPlanResultUiModel`, which returns
  `campaign_id` and `plan_item_count`, not `provider_code`.

Live probe against the reviewed branch:

```json
{
  "missing_api_key": {
    "campaign_id": null,
    "error_code": "VALIDATION_ERROR",
    "error_message": "api_key je obavezan (string).",
    "ok": false,
    "plan_item_count": null
  },
  "non_dict": {
    "campaign_id": null,
    "error_code": "VALIDATION_ERROR",
    "error_message": "Pošiljka nije objekat.",
    "ok": false,
    "plan_item_count": null
  },
  "unknown_provider": {
    "campaign_id": null,
    "error_code": "VALIDATION_ERROR",
    "error_message": "unknown provider: NOT_A_PROVIDER",
    "ok": false,
    "plan_item_count": null
  }
}
```

Failure path:

- User clicks provider save with invalid input, unknown provider code, or a
  backend/keyring failure.
- Bridge returns a campaign-plan result dict instead of a provider-config result
  dict.
- JS currently only reads `ok` and `error_message`, so the UI may still show a
  toast, which is why tests pass. But the public bridge contract and ACS-GUI-007
  DTO acceptance are violated.

Impact:

- The newly added `ProviderConfigResultUiModel` is only used on success; all
  failure responses silently use the wrong result model.
- Future UI/status logic that relies on `provider_code` being present on every
  provider-config response will break or need special cases.
- Existing tests miss this because they check `error_code`/message but not the
  complete error response shape.

Recommended correction:

- Add a provider-specific error helper, e.g.
  `_provider_err(code, message, provider_code=None)`, returning
  `ProviderConfigResultUiModel(ok=False, provider_code=..., error_code=code,
  error_message=message)`.
- Use it for every `configure_provider()` error path.
- Add regression tests that assert exact key sets for success and all relevant
  error paths:
  `{"ok", "provider_code", "error_code", "error_message"}` and no
  `campaign_id`/`plan_item_count`.

### BF-2 — API key remains in the DOM when bridge availability check fails

Evidence:

- `src/ai_campaign_studio/presentation_webview/static/app.js:83` reads
  `const apiKey=input.value||''`.
- `src/ai_campaign_studio/presentation_webview/static/app.js:88-90` checks
  whether `window.pywebview.api.configure_provider` exists, shows a toast, and
  returns.
- The handler does not execute `input.value=''` before that return.
- The input-clearing code exists only later:
  - catch branch at `app.js:99-105`;
  - returned-result branch at `app.js:108-113`.

Failure path:

- User types a real provider API key into the password field.
- `window.pywebview`, `window.pywebview.api`, or
  `window.pywebview.api.configure_provider` is temporarily/misconfiguredly
  unavailable.
- The handler returns after showing `"bridge nije dostupan"` while leaving the
  typed key in `#provider-key-<CODE>`.

Impact:

- Violates the ACS-GUI-007 acceptance/focus requirement that the key must be
  cleared on failure, not just on successful bridge calls or thrown `await`
  exceptions.
- The field is `type="password"`, so it is masked visually, but the secret still
  remains in the DOM value and can be exposed by later script/debug/UI behavior.

Recommended correction:

- Clear the input before every failure return after a non-empty key has been
  captured, especially the bridge-unavailable branch.
- Consider using `try/finally` around the whole provider-save flow after
  `apiKey` is read, so `input.value=''` is guaranteed for every non-empty-key
  path.
- Add a JS/DOM regression test or equivalent static/unit coverage proving:
  success clears, bridge-returned error clears, thrown exception clears, and
  bridge-unavailable clears.

## Non-blocking notes

### N1 — Class/file comments still describe a single public bridge method

`CampaignBridgeApi` now intentionally exposes two public js_api methods:
`create_campaign_and_generate_plan` and `configure_provider`. Some comments at
the top of `bridge/__init__.py` still say only one public method is exposed.
This is stale documentation, not a runtime bug. It is worth correcting while
touching the file for BF-1, but I do not consider it blocking by itself.

## Positive checks

- Scope check passed: changed files are limited to the ACS-GUI-007
  `allowed_paths`. No domain/application/ports/infrastructure/bootstrap/main/
  app.css/other-screen changes were found in `git diff --name-only`.
- `settings.environment` grep independently confirmed the important claim:
  the only production-code read of `settings.environment` is
  `bootstrap.py:144`, where it selects the SecretStore adapter. The bridge only
  constructs `AppSettings(environment="production")`.
- `configure_provider()` validates non-dict/missing/wrong-type/blank values
  before calling `ConfigureProvider`.
- Generic backend errors do not surface `str(exc)` to JS.
- I did not find an API-key leak in Python returned values or log lines in the
  reviewed `configure_provider()` call path.
- Double-click guard is proportionate for real user clicks:
  `el.disabled=true` is set synchronously before the `await`.

## Verification performed

Targeted tests:

```text
pytest tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py \
       tests/unit/presentation_webview/test_podesavanja_ssr.py \
       tests/unit/presentation \
       tests/architecture/test_import_boundaries.py -q -p no:cacheprovider

91 passed in 5.30s
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

Full pytest from my sibling-worktree sandbox arrangement:

```text
pytest tests -q -p no:cacheprovider
2 failed, 797 passed, 1 warning in 57.43s
```

The two failures are the same runner/worktree permission artifacts seen in
prior GUI reviews, not ACS-GUI-007 product regressions:

- `test_main_against_clean_repo_passes`: subprocess `git ls-files -z --`
  exits 128 under this restricted sibling-worktree runner.
- `test_gate_report_against_current_repo_passes`: cannot write
  `artifacts/phase0_foundation_gate.json` in the sibling worktree.

With the gate-report test ignored, my environment still has the
`check_no_secrets` subprocess/git permission artifact:

```text
1 failed, 791 passed, 1 warning in 26.18s
```

Live OS keyring verification was not repeated by Codex because I do not have
access to the real provider key in this review context. Claude's report says he
live-verified the real keyring write and a fresh-bridge Gemini call; I treated
that as external evidence, not as my own reproduced proof.

