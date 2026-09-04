---
verdict: PASS
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
tests: PASS
live_verification: PASS
gitnexus_impact: NOT_AVAILABLE (MCP disconnected this session)
blocking_findings: []
non_blocking_notes: [N1, N2]
---

# ACS-GUI-005 — Claude review (coordinator)

**Reviewer:** Claude (coordinator) · **Implementer:** MiniMax · **Date:** 2026-09-04
**Worktree:** `H:\ai-campaign-studio-worktrees\ACS-GUI-005-campaign-bridge`
**Branch:** `task/ACS-GUI-005-campaign-bridge`
**Base:** main @ `80d2c6e`, reviewed after main advanced to `7c7a91d` (ACS-F1-017 merge, unrelated files)

## Verdict

**PASS.** No blocking findings. Two non-blocking notes (below). This is the
first `js_api` bridge in the project and, after one fix round, is live-
verified end-to-end against a real SQLite DB and a real Google Gemini call.

## What I independently verified (not just trusted the evidence report)

1. Read `bridge/__init__.py`, `provider_adapter_factory.py`, the
   `app.js`/`opis_kampanje` diff, `contracts.py`/`ui_models.py` diff, and
   the `test_import_boundaries.py` diff in full — code matches the
   contract's locked decisions (brand-seed idempotency pattern, provider
   priority, forma→brief mapping table incl. the LinkedIn edge case,
   narrow single-method bridge surface, no secrets/tracebacks crossing
   the JS boundary).
2. Ran the targeted + full test suite myself in the worktree (own editable
   install repoint): 714 passed (1 known-harmless gate-report artifact
   failure, see Errors section of project memory — whole-repo `ruff check .`
   picking up untracked root scratch files, not an ACS-GUI-005 defect;
   scoped `ruff check src tests scripts` is clean). `mypy src` clean (138
   files). Import boundaries 18/18. `check_no_secrets.py` clean.
3. **Live-tested the actual bridge method twice** (`CampaignBridgeApi.
   create_campaign_and_generate_plan`, the exact code path the button
   calls) against the real local SQLite DB and a real Google Gemini API
   call, with GOOGLE genuinely marked `configured=True` in the real
   `provider_configs` table and a real key resolved through
   `EnvironmentSecretStore` (the default dev-mode secret store — see N2).
   - **First run** (before fix): both calls returned
     `GENERATION_FAILED`; `CreateCampaign` + brand-seed worked perfectly
     (`brands=1, campaigns=2` after 2 calls), but Google rejected
     `gemini-1.5-flash` with a 404 — this is BF-1, see below.
   - **After MiniMax's fix**: both calls returned `ok=True,
     plan_item_count=3`, with new rows in `campaign_plans`
     (`brands=1, campaigns=4, campaign_plans=2` cumulative — `brands`
     stayed at 1 across both test sessions, confirming brand-seed
     idempotency survives across process runs, not just within one).

## BF-1 (found + fixed this round)

`_DEFAULT_MODEL_IDS["GOOGLE"]` was `gemini-1.5-flash`, which the
evidence report claimed was "live-verified in ACS-F1-019 evidence" — it
was not; the actual live-verified string
(`agent_reports/2026-09-04-ACS-F1-019-review-claude.md:16`) is
`gemini-2.5-flash`. A transcription error, not a guess (MiniMax's stated
verification *method* — citing a specific live-tested source file — was
correct in principle; the *value* copied from it was wrong). Confirmed
fixed and re-verified live, see above. MiniMax also fixed the two
associated unit test assertions and tightened the source-of-truth comment
to cite the exact file+line.

## Process note (resolved, not a code finding)

The evidence report's §6 states the `test_import_boundaries.py` exception
was "koordinator odobrio kroz ask_user" — I (this coordinator session)
had no such interaction. Confirmed directly with the Human Owner: MiniMax's
own tool asked the Human Owner for permission directly (not routed through
the coordinator), and the Human Owner approved it. I independently reviewed
the resulting diff on its technical merits (see below) — it is correct and
matches what the contract anticipated — so this does not block the task.
Noting it here so future review passes know to verify this kind of claim
directly with the Human Owner rather than take "coordinator approved" at
face value from an evidence report.

## Architecture / security review

- `CampaignBridgeApi` exposes exactly one public method
  (`create_campaign_and_generate_plan`); everything else is
  underscore-prefixed. Matches PYWEBVIEW_SECURITY.md §3 (narrow,
  purpose-built bridge class, not a raw facade/domain service).
- Boundary validation: non-dict payload and Pydantic `ValidationError`
  both map to `VALIDATION_ERROR` before touching any repository.
- No secret/token/traceback ever crosses into the returned dict — verified
  by reading every `except` branch: generation failures interpolate only
  `type(exc).__name__`, never `str(exc)`, for the AI-call path (the one
  path most likely to carry SDK-internal detail); domain validation
  failures (`InvariantViolation`/`ValueError`/`TypeError`,
  `EntityNotFound`) do interpolate `str(exc)`, which is acceptable — those
  messages describe the user's own submitted data (e.g. "duplicate
  topics"), not secrets.
- `test_returned_dict_is_json_serializable_and_contains_no_secrets` uses a
  sentinel API-key value and asserts it never appears in the result — good
  adversarial-style test authored proactively, not just after my review.
- `test_import_boundaries.py` change: `presentation_webview/bridge/` is
  correctly scoped as a composition-root sub-layer, with the SAME
  top-level SDK/browser/web-framework denylist as the rest of
  `presentation_webview/` — it is not a blanket carve-out, only an
  infrastructure-import allowance. Verified the `_layer_for` ordering is
  correct (bridge check happens before the parent `presentation_webview`
  check, so it isn't masked).
- Brand-seed idempotency: self-healing on both "file missing" and "file
  present but snapshot deleted" — confirmed via live test surviving two
  separate process invocations, not just the in-process unit test.
- Provider/model resolution: hardcoded, contract-locked table; unknown
  provider raises `ConfigurationError` (not silent fallback, not
  `KeyError`) — confirmed via `resolve_model_id` reading and its test.
- `provider_adapter_factory` never touches `SecretStorePort` — confirmed
  by reading the full file; `build_text_generation_adapter` only accepts
  a ready `api_key: str`.

## Non-blocking notes

**N1** — `presentation_webview/__main__.py::_open_window` now constructs
`CampaignBridgeApi()` (which runs `create_bootstrap()`) inline, with no
dedicated error branch. If bootstrap construction fails (e.g. corrupt DB,
migration failure), the failure surfaces as a raw, unbranded Python
traceback rather than the loud-but-friendly treatment
`WebView2MissingError` gets. Not a security issue, not silent (it does
crash loudly), just less polished than the existing pattern in the same
file. Fine to leave for a follow-up GUI-BASE hardening task rather than
block this one.

**N2** — Confirmed hands-on: the real GUI app, as currently wired,
always constructs `AppSettings(environment="development")` (no call site
anywhere sets `environment="production"`), which means it always gets
`EnvironmentSecretStore` — a **read-only** adapter. This means
`ConfigureProvider` (the use-case the bridge's own `NO_PROVIDER_CONFIGURED`
error message points users toward — "Podesi API ključ ručno (skripta)")
cannot actually persist a key end-to-end in the app's default runtime
today; the only way I could get a real provider "configured" for the live
test was to write the `ProviderConfig` DB row directly and supply the key
via the `AI_CAMPAIGN_STUDIO_<CODE>_API_KEY` env var. This is a pre-existing
gap from A8's SecretStore design, not something ACS-GUI-005 introduced or
was contracted to fix — flagging it as a known blocker for the next
"Podešavanja provider config" GUI task, since that task cannot ship without
addressing it (either wire `environment="production"` into the real GUI
entry point, or give `EnvironmentSecretStore` a documented dev-mode
config path).

## Recommendation

Ready for Codex adversarial review (HIGH risk, full cycle per contract).
Brief being sent now.
