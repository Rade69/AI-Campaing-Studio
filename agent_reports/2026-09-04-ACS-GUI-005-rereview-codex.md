# ACS-GUI-005 — Codex re-review after BF-1 fix

Date: 2026-09-04  
Reviewer: Codex  
Branch/worktree reviewed: `task/ACS-GUI-005-campaign-bridge` in `H:\ai-campaign-studio-worktrees\ACS-GUI-005-campaign-bridge`

```text
CILJ: Re-review uskog fixa za prethodni Codex BF-1 — `_open_window` unit test nije bio hermetičan jer je konstruisao pravi `CampaignBridgeApi()`/bootstrap.
URAĐENO: PASS_WITH_NOTES — BF-1 je zatvoren; nema novih blocking nalaza u pregledanom opsegu.
NE DIRATI: Širi GUI bridge/provider/security scope iz prethodne runde nije reotvaran osim regresionih provjera.
SLJEDEĆE: Koordinator može poslati Human Owneru na odluku/odobrenje, uz napomenu o sandbox-only full-suite ograničenjima ispod.
```

## Verdict

**PASS_WITH_NOTES — no blocking findings.**

The previous Codex blocker is fixed. `_open_window()` no longer constructs the
real `CampaignBridgeApi()` inline in the pywebview acceptance unit test path;
it delegates to a patchable module-level `_build_bridge()` seam.

## BF-1 closure evidence

Code evidence:

- `src/ai_campaign_studio/presentation_webview/__main__.py:166` defines
  `_build_bridge()`.
- `src/ai_campaign_studio/presentation_webview/__main__.py:184` imports
  `CampaignBridgeApi` inside that helper.
- `src/ai_campaign_studio/presentation_webview/__main__.py:197` calls
  `bridge = _build_bridge()`.
- `src/ai_campaign_studio/presentation_webview/__main__.py:205` passes
  `js_api=bridge` to `webview.create_window()`.
- `tests/unit/presentation_webview/test_webview2_fail_loud.py` now patches
  `ai_campaign_studio.presentation_webview.__main__._build_bridge`, so the
  WebView2/security acceptance test no longer touches real bootstrap/logging/
  DB/keyring composition.

Live reproduction of the previously failing test:

```text
pytest tests/unit/presentation_webview/test_webview2_fail_loud.py -q -p no:cacheprovider
5 passed in 0.05s
```

This is the exact test file that failed in the prior Codex review with a
`PermissionError` while real logging/bootstrap was being constructed. It now
passes in the same Codex sandbox workaround environment.

## Regression checks

Targeted bridge/factory/boundary set:

```text
pytest tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py \
       tests/unit/infrastructure/ai/test_provider_adapter_factory.py \
       tests/architecture/test_import_boundaries.py -q -p no:cacheprovider

42 passed, 1 warning in 7.94s
```

Static checks on touched areas:

```text
ruff check <presentation_webview/presentation/provider_factory/test touched paths>
All checks passed!
```

```text
mypy <presentation_webview/presentation/provider_factory touched paths>
Success: no issues found in 20 source files
```

Full pytest from the Codex sandbox arrangement:

```text
pytest tests -q -p no:cacheprovider
2 failed, 713 passed, 1 warning in 63.51s
```

The important signal: the previous ACS-GUI-005 pywebview test failure is gone.
The two remaining failures are the same sibling-worktree/harness permission
issues observed in the prior review and are not product regressions from this
fix:

- `tests/unit/scripts/test_check_no_secrets.py::test_main_against_clean_repo_passes`
  fails because the subprocess `git ls-files -z --` exits 128 in this restricted
  sibling-worktree runner.
- `tests/unit/scripts/test_generate_phase0_gate_report.py::test_gate_report_against_current_repo_passes`
  fails because the test subprocess cannot write
  `H:\ai-campaign-studio-worktrees\ACS-GUI-005-campaign-bridge\artifacts\phase0_foundation_gate.json`
  under this sandbox permission profile.

Claude's reported local verification (`708 passed` with the gate-report test
ignored, plus clean ruff/mypy/architecture/secrets) is consistent with this:
the actual ACS-GUI-005 blocker has been removed, while my residual full-suite
failures are runner/worktree permission artifacts.

## Reviewed scope

- `src/ai_campaign_studio/presentation_webview/__main__.py`
- `tests/unit/presentation_webview/test_webview2_fail_loud.py`
- Targeted regression surface:
  - `presentation_webview/bridge`
  - `infrastructure/ai/provider_adapter_factory.py`
  - architecture import-boundary tests

No confirmed new code defect found in the reviewed scope.

