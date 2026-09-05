---
verdict: FAIL
scope: PASS
acceptance: FAIL
architecture: PASS
security: FAIL
tests: PASS_WITH_NOTES
live_verification: NOT_AVAILABLE_BY_CODEX
gitnexus_impact: NOT_AVAILABLE
closed_findings: [BF-1, BF-2]
blocking_findings: [BF-3]
non_blocking_notes: []
---

# ACS-GUI-007 — Codex re-review after BF-1/BF-2 fixes

Reviewer: Codex  
Date: 2026-09-04  
Worktree: `H:\ai-campaign-studio-worktrees\ACS-GUI-007-provider-config`  
Branch: `task/ACS-GUI-007-provider-config`

```text
CILJ: Re-review za dva prethodna Codex nalaza na ACS-GUI-007 secret bridge flow-u.
URAĐENO: FAIL — BF-1 i BF-2 su zatvoreni, ali pronađen je novi blocking security nalaz u generic exception log path-u.
NE DIRATI: application/domain/infrastructure/bootstrap/app.css i ostale ekrane; fix je usko u `configure_provider` generic exception logging i regression testu.
SLJEDEĆE: MiniMax treba zatvoriti BF-3 bez širenja scope-a, pa poslati kratku round-3 rereview rundu.
```

## Verdict

**FAIL.**

Oba prethodna Codex nalaza su zatvorena:

- **BF-1 closed:** `configure_provider()` error paths sada vraćaju
  `ProviderConfigResultUiModel` shape.
- **BF-2 closed:** JS `provider-save` flow sada koristi `try/finally`, pa
  password input biva očišćen i u bridge-unavailable grani.

Međutim, dodatna adversarial proba nad istom secret-handling granom našla je
novi blocking nalaz: generic exception logging i dalje može zapisati API ključ
u log ako downstream exception message sadrži taj key.

## Closed findings

### BF-1 — closed: provider error DTO shape

Evidence:

- `src/ai_campaign_studio/presentation_webview/bridge/__init__.py:329`,
  `:336`, `:340`, `:366`, `:376` sada koriste `_provider_err(...)` za
  `configure_provider()` error paths.
- `src/ai_campaign_studio/presentation_webview/bridge/__init__.py:540`
  definiše `_provider_err()` koji vraća `ProviderConfigResultUiModel`.
- `tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py:727`
  dodaje regression test
  `test_configure_provider_error_shape_has_no_campaign_flow_keys`.

Live probe protiv popravljene branch verzije:

```json
{
  "internal_error": {
    "error_code": "INTERNAL_ERROR",
    "error_message": "Konfiguracija provajdera nije uspjela (interna greška).",
    "ok": false,
    "provider_code": null
  },
  "missing_api_key": {
    "error_code": "VALIDATION_ERROR",
    "error_message": "api_key je obavezan (string).",
    "ok": false,
    "provider_code": null
  },
  "non_dict": {
    "error_code": "VALIDATION_ERROR",
    "error_message": "Pošiljka nije objekat.",
    "ok": false,
    "provider_code": null
  },
  "unknown_provider": {
    "error_code": "VALIDATION_ERROR",
    "error_message": "unknown provider: NOT_A_PROVIDER",
    "ok": false,
    "provider_code": null
  }
}
```

No `campaign_id` / `plan_item_count` keys remain on provider-config errors.

### BF-2 — closed: bridge-unavailable JS path now clears password input

Evidence:

- `src/ai_campaign_studio/presentation_webview/static/app.js:92` reads the
  trimmed key into local `apiKey`.
- `src/ai_campaign_studio/presentation_webview/static/app.js:99-107` includes
  the bridge availability check inside the `try`.
- `src/ai_campaign_studio/presentation_webview/static/app.js:109-115` clears
  `input.value=''` and re-enables the button in `finally`.

This structurally covers the previous missed path:

```text
non-empty apiKey
→ bridge unavailable
→ show toast
→ result=null
→ finally
→ input.value=''
```

The project still has no JS execution test framework, so this is a code-structure
verification rather than a jsdom-style runtime test. For this specific fix I do
not consider that blocking: the `finally` is small and directly covers the
previous missing branch.

## Blocking findings

### BF-3 — generic `configure_provider` exception logging can leak a secret-bearing exception message into logs

Severity: **high** for this task because ACS-GUI-007 is the first JS→bridge
secret write flow.

Evidence:

- `src/ai_campaign_studio/presentation_webview/bridge/__init__.py:345-356`
  passes the raw `api_key` into `ConfigureProvider(...).execute(...)`.
- `src/ai_campaign_studio/presentation_webview/bridge/__init__.py:372-374`
  catches generic `Exception` and calls `self._bootstrap.logger.exception(...)`.
- `logger.exception(...)` logs the active exception traceback, including the
  exception message.

Adversarial live probe:

I patched `bridge._bootstrap.secret_store.set_secret` to raise:

```python
RuntimeError("backend mentions sk-SENTINEL-secret")
```

The returned JS dict was safe:

```json
{
  "ok": false,
  "provider_code": null,
  "error_code": "INTERNAL_ERROR",
  "error_message": "Konfiguracija provajdera nije uspjela (interna greška)."
}
```

But the log output included the raw exception message:

```text
RuntimeError: backend mentions sk-SENTINEL-secret
```

Failure path:

1. JS sends a real API key to `configure_provider`.
2. The bridge passes it into `ConfigureProvider` / `SecretStorePort.set_secret`.
3. A downstream component raises an unexpected exception whose message includes
   the value or part of it.
4. The bridge's generic handler with `logger.exception(...)` writes the
   traceback and exception message to the application log.

Why this is not just theoretical:

- The ACS-GUI-007 brief explicitly asked Codex to check whether **any error
  path, including unexpected exception types, can leak `api_key` to return
  values or logs**.
- The method docstring says the `api_key` is "NEVER logged".
- The existing test `test_configure_provider_does_not_log_api_key` only uses
  `RuntimeError("backend boom")`, so it does not exercise a secret-bearing
  exception message.
- Current `KeyringSecretStore` is carefully implemented and does not include
  the secret value in `SecretStoreError`, which reduces current happy-path risk.
  The bridge, however, is not robust at its trust boundary: any unexpected
  exception message under this call stack is logged verbatim.

Impact:

- A keyring backend, fake/test backend, future SecretStore implementation, or
  later `ConfigureProvider` change that includes the input value in an exception
  message would put the API key into `ai_campaign_studio.log`.
- This violates the HIGH-risk secret handling requirement even though the JS
  return value is safe.

Recommended correction:

- In `configure_provider()` generic `except Exception as exc`, do not use
  `logger.exception(...)` / `exc_info=True`.
- Log only bounded metadata, e.g. provider code and `type(exc).__name__`:

  ```python
  self._bootstrap.logger.error(
      "configure_provider failed for provider %s (err=%s)",
      provider_code,
      type(exc).__name__,
  )
  ```

- Add an adversarial regression test where `set_secret` raises
  `RuntimeError(f"contains {sentinel_key}")`, then assert:
  - returned dict does not contain the sentinel;
  - every captured log record message does not contain the sentinel.

## Verification performed

Targeted tests:

```text
pytest tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py \
       tests/unit/presentation_webview/test_podesavanja_ssr.py \
       tests/unit/presentation \
       tests/architecture/test_import_boundaries.py -q -p no:cacheprovider

92 passed in 8.29s
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

Live OS keyring verification was not repeated by Codex because I do not have
access to the real provider key in this review context. Claude's earlier report
says he live-verified real keyring write + fresh-bridge Gemini call; I treated
that as external evidence, not my own reproduced proof.

## Scope reviewed

- `src/ai_campaign_studio/presentation_webview/bridge/__init__.py`
- `src/ai_campaign_studio/presentation_webview/static/app.js`
- `tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py`
- Supporting read of current `KeyringSecretStore` and `ConfigureProvider`
  exception behavior.

