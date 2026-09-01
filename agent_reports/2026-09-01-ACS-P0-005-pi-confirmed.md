# ACS-P0-005 — implementer/execution evidence — coordinator-confirmed

**Implementer:** Pi — vlastiti report:
`agent_reports/2026-09-01-ACS-P0-005-pi.md` (pročitan i sadržajno potvrđen)
**Branch/worktree:** `task/ACS-P0-005-ai-registry-secrets`,
`../ai-campaign-studio-worktrees/ACS-P0-005-ai-registry-secrets`
**Base:** `main@820bbf9`
**Commit:** `5517c8b` (author Pi, committed by coordinator)

## Files changed — nezavisno potvrđeno

Svi novi fajlovi, tačno unutar `allowed_paths`: `ai_registry/{__init__,
provider_models,model_profiles,registry}.py`, `ports/{ai_registry,secrets}.py`,
`infrastructure/{__init__,secrets/__init__,secrets/environment_secret_store,
secrets/keyring_secret_store}.py`, 6 provider YAML fajlova,
`tests/unit/ai_registry/test_ai_provider_registry.py`,
`tests/integration/ai_registry/test_provider_resources.py`,
`tests/unit/secrets/test_secret_store.py`. `pyproject.toml` netaknut.
Nijedan `forbidden_path` diran (uključujući paralelni ACS-P0-006 scope —
`infrastructure/database/` nije dirnut).

## Kod — pročitan u cjelini

- `provider_models.py`/`model_profiles.py`: frozen pydantic modeli, tuple
  za `capabilities` (ne list — konzistentno primijenjena lekcija iz
  ACS-P0-004 BF-2).
- `ports/ai_registry.py`: `AIProviderConnectionPort` je eksplicitno
  odvojen future-only contract (`test_connection`/`discover_models`) —
  ništa u P0 ga ne implementira niti poziva. Ispravno razdvajanje P0-ready
  vs future-capability.
- `registry.py`: `AIProviderRegistry(AIProviderRegistryPort,
  ModelRegistryPort)` — YAML loader samo za PROVIDERE (modeli se NE
  učitavaju iz YAML-a, samo runtime registruju preko `register_manual_model`/
  `register_discovered_models` — tačno prema "P0 ne mora imati realnu listu
  modela" iz plana). Duplicate provider/model detection, capability filter
  (`supports`), `resolve_default_text_model`. Nema network/SDK poziva.
- `environment_secret_store.py`: `secret_to_env_var` mapiranje ručno
  provjereno — `"provider/OPENAI/api_key"` → `"AI_CAMPAIGN_STUDIO_OPENAI_API_KEY"`
  (odbacuje `"provider"` segment, ostatak uppercase + underscore). `set_secret`/
  `delete_secret` eksplicitno read-only, bacaju `SecretStoreError` sa porukom
  koja NE sadrži value.
- `keyring_secret_store.py`: injectable `_KeyringBackend` Protocol (testabilno
  bez pravog OS keyring-a), sve tri operacije zamotavaju backend exception u
  `SecretStoreError` bez value u poruci, nema logovanja nigdje u fajlu.
- 6 provider YAML fajlova: pregledano grep-om, samo `requires_api_key: true`
  (boolean shema polje) — nema stvarne key/token vrijednosti.

## Nezavisna verifikacija — DOSLOVAN output (svjež `.venv`)

```text
$ ./.venv/Scripts/python.exe -m pytest -q
........................................................................ [ 64%]
.......................................                                  [100%]
111 passed in 0.99s

$ ./.venv/Scripts/python.exe -m ruff check .
All checks passed!

$ ./.venv/Scripts/python.exe -m mypy src
Success: no issues found in 38 source files
```

## Adversarial proof — nezavisno ponovljen (oba, security-kritično)

**Secret nikad ne loguje se:** privremeno dodata `logger.info(...)` linija sa
secret value u `KeyringSecretStore.set_secret` →
`test_keyring_store_never_logs_secret` FAIL (secret value pronađena u
`caplog.text`). Vraćeno (byte-identično originalu) → PASS.

**Duplicate model rejection:** privremeno uklonjena duplicate-check u
`_register()` → `test_duplicate_model_rejected` FAIL (`DID NOT RAISE
RegistryError`). Vraćeno → PASS.

`git status --short` čist poslije obje restauracije (bez `M` markera).

## GitNexus

`gitnexus_impact: UNKNOWN` (poznato ograničenje). Kompenzovano: svi fajlovi
novi, `ports/` folder je imao 0 upstream callera prije taska (pre-impact iz
kontrakta), `RegistryError`/`SecretStoreError` iz ACS-P0-002 ponovo
korišteni, ne redefinisani.

## Acceptance checklist

Svih 11 stavki iz kontrakta — PASS, potvrđeno gore + testovima.

## Not verified

- GitNexus automated impact (structural limitation).
- Formalni Codex review — brief pripremljen zasebno.
