# Codex re-review request — ACS-P0-005

Za: Codex
Od: Claude (koordinator)
Datum: 2026-09-01

## Kontekst

Tvoj review (`agent_reports/2026-09-01-ACS-P0-005-review-codex.md`):
`REJECT` (`security: REJECT`) sa BF-1 (secret leak kroz `__cause__`), BF-2
(env-var collision), BF-3 (modeli za nepoznatog providera). Pi je uradio
fix rundu. Reprodukovao sam sva tri tvoja originalna probe scenarija
protiv popravljenog koda — sva tri sad rade ispravno.

## Šta pregledati

```text
Branch:      task/ACS-P0-005-ai-registry-secrets
Prošli HEAD: 5517c8b  (na kom si dao REJECT)
Novi HEAD:   2ff5f4e
```

```bash
git -C "H:\AI Campaing Studio" diff 5517c8b 2ff5f4e --stat
git -C "H:\AI Campaing Studio" diff 5517c8b 2ff5f4e
```

5 fajlova: `ai_registry/registry.py`,
`infrastructure/secrets/{environment_secret_store,keyring_secret_store}.py`,
`tests/unit/ai_registry/test_ai_provider_registry.py`,
`tests/unit/secrets/test_secret_store.py`.

## Fokus re-reviewa (i dalje security-critical)

1. Ponovi svoja tri originalna probe scenarija (cause-leak, env-var
   collision, unknown-provider model) protiv novog koda.
2. **BF-2 fix nuspojava** — `secret_to_env_var()` sad baca `ValueError`
   (ne `SecretStoreError`) za malformed name, i to propagira neuhvaćeno iz
   `EnvironmentSecretStore.get_secret()`/`set_secret()`/`delete_secret()`.
   Provjeri: da li je ovo dosljedno sa ostatkom error taxonomy-ja
   (`domain/common/errors.py` iz ACS-P0-002 definiše `SecretStoreError` baš
   za ovakve slučajeve)? Nije nužno blocker (brief je eksplicitno dozvolio
   `ValueError` ili `SecretStoreError`, implementer bira), ali procijeni da
   li bi caller kod (buduć bootstrap wiring) mogao netačno pretpostaviti da
   SVE greške iz `SecretStorePort` metoda dolaze kao `SecretStoreError`, pa
   propušten `ValueError` postane neuhvaćena iznenađujuća exception vrsta.
3. **BF-1 fix kompletnost** — `technical_context=f"backend={type(exc).__name__}"`
   se sad prosljeđuje u `SecretStoreError` konstruktor. Provjeri da
   `AppError.__init__` (iz ACS-P0-002) zaista isključuje `technical_context`
   iz `super().__init__(human_message)` args (tako da ni ono ne uđe u
   `repr()`/`str()`/traceback) — ovo je već bio invarijant iz ACS-P0-002,
   samo potvrdi da novi caller ne krši tu pretpostavku.
4. **Regresija** — 121 test. Ponovo pokreni:
   ```bash
   cd "H:\ai-campaign-studio-worktrees\ACS-P0-005-ai-registry-secrets"
   .\.venv\Scripts\python.exe -m pytest -q
   .\.venv\Scripts\python.exe -m ruff check .
   .\.venv\Scripts\python.exe -m mypy src
   ```
5. Scope-clean diff (5 fajlova, sve u `allowed_paths`)?

## Traženi output

`agent_reports/2026-09-01-ACS-P0-005-review-codex-round2.md`, isti format.
Ako `PASS`/`PASS_WITH_NOTES` bez novih blocking findings, tražim Human
Owner odobrenje za merge.
