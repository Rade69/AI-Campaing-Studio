# ACS-P0-005 — Final decision packet

**Task:** ACS-P0-005 — AI Provider/Model Registry + SecretStore foundation (P0.14–P0.15)
**Branch:** `task/ACS-P0-005-ai-registry-secrets`, HEAD `2ff5f4e`
**Base:** `main@820bbf9`
**Contract:** `agent_reports/ACS-P0-005-task-contract.md`

## D1 — Readiness recommendation: **READY FOR HUMAN APPROVAL**

Requested scope (P0.14–P0.15) is fully implemented, all reviewer-raised
security/correctness defects are confirmed fixed with independent
re-verification, no blocking finding remains, and residual items are
either the same structural GitNexus gap accepted on every prior merge, or
an explicitly non-blocking design note Codex itself scoped out.

## Blocking findings

None open.

## Accepted/fixed findings

| ID | Reviewer | Defect | Round fixed | Evidence |
|---|---|---|---|---|
| BF-1 | Codex (round 1) | `KeyringSecretStore` chained the backend exception as `__cause__`, so a backend error echoing the secret value back could leak it through traceback/cause inspection even though `str(exc)` didn't contain it | round 1 (`2ff5f4e`) | `agent_reports/2026-09-01-ACS-P0-005-fix-round-pi-confirmed.md`; Codex round 2 (`PASS_WITH_NOTES`) confirmed `__cause__` is `None` and only the safe `technical_context` (backend class name) is kept |
| BF-2 | Codex (round 1) | `secret_to_env_var()` had no naming-convention validation, so a non-canonical alias (e.g. `"OPENAI/api_key"` without the `provider/` prefix) collided with the canonical `"provider/OPENAI/api_key"` env var | round 1 (`2ff5f4e`) | same; closed via strict regex validation, all alias/collision forms now raise `ValueError` |
| BF-3 | Codex (round 1) | `register_manual_model()`/`register_discovered_models()` accepted models for providers that don't exist in the provider registry | round 1 (`2ff5f4e`) | same; both paths now call `get_provider()` first, raising `RegistryError` for unknown providers |

Each fix was independently re-verified by the coordinator — not just Pi's
diff — including re-executing all three of Codex's original probe scripts
against the fixed code at every round.

Claude's architecture review (`agent_reports/2026-09-01-ACS-P0-005-review-claude.md`,
PASS, on the pre-fix commit `5517c8b`) covered the future-only
`AIProviderConnectionPort` separation, absence of provider SDK/network
calls, and dependency direction — none of which were touched by the fix
round (scoped to `registry.py` and the two secret store adapters), so that
verdict still holds.

## Residual risks (human should knowingly accept)

- **GitNexus impact analysis unavailable for this task** (same structural
  worktree-binding limitation as every prior task this session).
- **`EnvironmentSecretStore` propagates a raw `ValueError`** (not
  `SecretStoreError`) for a malformed secret name — the task contract
  explicitly allowed either choice, and Codex confirmed this doesn't
  weaken the collision fix itself. Flagged as a possible future
  standardization (all `SecretStorePort` errors as `SecretStoreError`) if
  a later bootstrap/UI caller finds the mixed exception type surprising.

## Confirmed validation (final HEAD `2ff5f4e`)

```text
python -m pytest -q      → 121 passed
python -m ruff check .   → All checks passed!
python -m mypy src       → Success (38 source files)
```

All three blocking findings' original reproduction scenarios re-run by
both the coordinator and Codex against the final code: all now behave
correctly (no secret leak via `__cause__`/traceback, no env-var collision,
no unknown-provider model acceptance).

## Scope status

All P0.14–P0.15 implementation steps are complete (`AIProviderDefinition`,
`ModelProfile`, `AIProviderRegistryPort`/`AIProviderConnectionPort`/
`ModelRegistryPort`, in-memory model registry, 6 provider YAML resources,
`SecretStorePort` with environment and keyring adapters). No
`OUT_OF_SCOPE_FINDING` was raised. The one fix round was pure
defect-correction on already-in-scope files — no scope expansion.

## Human decision needed

Approve merge of `task/ACS-P0-005-ai-registry-secrets` (`2ff5f4e`) into
`main`, accepting the residual item noted above — or request further
revision.
