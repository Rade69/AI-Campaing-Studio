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
non_blocking_notes: [N1]
---

# ACS-GUI-007 — Claude review (coordinator)

**Reviewer:** Claude (coordinator) · **Implementer:** MiniMax · **Date:** 2026-09-04
**Worktree:** `H:\ai-campaign-studio-worktrees\ACS-GUI-007-provider-config`
**Branch:** `task/ACS-GUI-007-provider-config`
**Base:** main @ `b489a93`

## Verdict

**PASS.** No blocking findings. One non-blocking note. Live-verified
end-to-end against the real OS keyring and a real Google Gemini call —
this closes the practical usability gap found during ACS-GUI-005 review.

## What I independently verified

1. Read `bridge/__init__.py` (both the `__init__` settings seam and the
   new `configure_provider` method), `screens/podesavanja/__init__.py`,
   `static/app.js`, `presentation/ui_models.py`,
   `presentation/contracts.py` diffs in full — matches the contract's
   locked decisions exactly (settings seam scope, boundary validation
   order, error-code mapping, `str(exc)` withheld on the generic
   exception path, input-always-cleared JS behavior including the
   thrown-error path).
2. Ran the targeted + full suite myself (own editable-install repoint):
   792 passed. `mypy src` clean (140 files). Import boundaries 18/18.
   `check_no_secrets.py` clean. Scoped `ruff check` clean.
3. **Live-tested the actual new capability**, not just mocks:
   - Called `CampaignBridgeApi().configure_provider({"provider_code":
     "google", "api_key": <real key>})` with NO settings override (the
     real production default) — result `{"ok": true, "provider_code":
     "GOOGLE", ...}`, no `api_key` in the response.
   - Independently read `keyring.get_password("AI Campaign Studio",
     "provider/GOOGLE/api_key")` directly (bypassing the app) and
     confirmed it matches the real key — proves the write actually
     landed in the real OS keyring, not a mock.
   - **Then, in a FRESH `CampaignBridgeApi()` instance** (simulating a
     new app launch, not the same in-memory object), called
     `create_campaign_and_generate_plan(...)` with no other setup —
     it found the GUI-configured provider automatically and completed a
     real Gemini call, `{"ok": true, "campaign_id": ..., "plan_item_count":
     3}`. This is the first time this end-to-end path has worked without
     me manually seeding a `ProviderConfig` DB row by hand (as I had to
     do during ACS-GUI-005's live test) — the practical blocker is
     closed.

## Architecture / security review

- `settings` test seam mirrors the existing `paths` seam exactly; default
  in production code is `AppSettings(environment="production")`,
  `bootstrap.py`'s own default is untouched (confirmed via `git diff`)
  and stays `"development"` for every other caller.
- Grep-confirmed (independently, not just trusting the contract's own
  claim) that `settings.environment` has exactly one read site in the
  whole codebase (`bootstrap.py:144`, secret-store selection) — the
  production switch has no other side effect.
- All 15 pre-existing bridge tests were updated to pass an explicit
  `settings=AppSettings(environment="development")` — verified none of
  them silently fell back to the new production default (would have
  started touching the real OS keyring during `pytest`).
- `configure_provider` validates `raw_payload` shape before touching
  `ConfigureProvider` — non-dict, missing/empty/wrong-type
  `provider_code`/`api_key` all rejected pre-side-effect.
- `api_key` never appears in the returned dict (`ProviderConfigResultUiModel`
  has no such field, structurally enforced by a test) and never in a log
  line — verified by reading every exception branch: `RegistryError`/
  `InvariantViolation` → `str(exc)`, but tracing both raise sites in
  `configure_provider.py`/the registry lookup confirms neither message
  can ever include the api_key (only `provider_code`, not a secret);
  the generic `Exception` branch (would catch `SecretStoreError`)
  deliberately withholds `str(exc)` entirely, logging only
  `type(exc).__name__` and `provider_code`.
- JS: `input.value = ''` runs in the `catch` branch AND unconditionally
  before reacting to a returned result (both `ok` and error paths) —
  the key does not linger in the DOM under any code path I traced.
- Double-click guard: `el.disabled = true` set synchronously before the
  `await`, same pattern as `save-and-plan` (ACS-GUI-005 precedent).
- `openai_compatible` correctly excluded from the real-wiring map,
  explicit comment states why (needs `base_url` + `model_id`, different
  form shape) — stays a toast stub, not silently mis-wired.

## Non-blocking notes

**N1** — `_provider_row`'s `openai_compatible` branch and the defensive
"unknown/unmapped code" fallback branch are byte-identical (both render
the same toast-stub markup). Minor DRY duplication, no functional
impact, not worth a fix round. Fine to leave or fold into one branch
next time this function is touched.

## Recommendation

Ready for Codex adversarial review (HIGH risk, full cycle per contract).
Brief being sent now.
