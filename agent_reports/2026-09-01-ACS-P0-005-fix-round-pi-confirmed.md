# ACS-P0-005 — fix round evidence — coordinator-confirmed

**Prethodni HEAD:** `5517c8b` (Codex REJECT — BF-1/2/3, security: REJECT)
**Novi commit:** `2ff5f4e` (author Pi, committed by coordinator)

## Diff protiv 5517c8b

5 fajlova: `registry.py`, `environment_secret_store.py`,
`keyring_secret_store.py`, `test_ai_provider_registry.py` (+2 nova testa),
`test_secret_store.py` (+8 novih testova, uklj. parametrizovan test za 6
malformed name oblika).

## Fix

- BF-1: sve tri `KeyringSecretStore` operacije sada `from None` umjesto
  `from exc`; safe `technical_context=f"backend={type(exc).__name__}"` (samo
  klasa, ne poruka).
- BF-2: `secret_to_env_var()` sad koristi strogi regex
  `^provider/([A-Za-z0-9_]+)/api_key$`, `fullmatch`, baca `ValueError` na sve
  ostalo. `EnvironmentSecretStore.get_secret` propagira taj `ValueError`
  neuhvaćen (dokumentovano u brief-u kao prihvatljivo — implementer je birao
  između `ValueError`/`SecretStoreError`, izabrao `ValueError`).
- BF-3: `register_manual_model`/`register_discovered_models` sad pozivaju
  `self.get_provider(...)` prije registracije (baca `RegistryError` za
  nepoznat provider).

Sve tačno kako je brief tražio.

## Nezavisna verifikacija

```text
$ ./.venv/Scripts/python.exe -m pytest -q
........................................................................ [ 59%]
.................................................                        [100%]
121 passed in 0.94s

$ ./.venv/Scripts/python.exe -m ruff check .
All checks passed!

$ ./.venv/Scripts/python.exe -m mypy src
Success: no issues found in 38 source files
```

## Re-dokaz sva tri originalna Codex scenarija — nezavisno ponovljen

```text
BF-1 __cause__ has secret: False (bilo True prije fixa)
BF-1 __cause__ is None: True
BF-2 alias rejected OK: invalid secret name 'OPENAI/api_key'; expected 'provider/<PROVIDER_CODE>/api_key'
BF-3 rejected OK: unknown provider: UNKNOWN
```

## Zaključak

BF-1/2/3 zatvoreni, dokazano nezavisnim ponavljanjem originalnih Codex
probe scenarija, bez regresije (121/121 zeleno). Spreman za fresh Codex
re-review na `2ff5f4e` (HIGH/security task, ostaje na punom ciklusu po
review politici §29).
