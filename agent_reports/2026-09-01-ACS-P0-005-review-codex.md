---
verdict: REJECT
scope: PASS
acceptance: REJECT
architecture: PASS
security: REJECT
tests: REJECT
gitnexus_impact: UNKNOWN
blocking_findings:
  - BF-1: "KeyringSecretStore preserves backend exception __cause__, which can leak secret values through traceback/cause inspection."
  - BF-2: "secret_to_env_var accepts malformed/non-canonical names that collide with canonical provider secret env vars."
  - BF-3: "Model registry accepts manual/discovered models for unknown providers."
---

# CILJ

Nezavisni Codex adversarial/test review za ACS-P0-005 (AI Provider/Model
Registry + SecretStore foundation), commit `5517c8b` na branch-u
`task/ACS-P0-005-ai-registry-secrets`, prema
`agent_reports/ACS-P0-005-task-contract.md` i review brief-u
`agent_reports/2026-09-01-ACS-P0-005-codex-review-request.md`.

# PROVJERENO

- Pročitan bazni protocol read-set: `AGENTS.md`, `CLAUDE.md`,
  `docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md`, `.agent/CURRENT_STATE.md`,
  `.agent/PROJECT_MAP.md`, `.agent/TASK_ROUTING.md`,
  `.agent/GITNEXUS_PROTOCOL.md`.
- Pročitan task contract, coordinator evidence i Claude review:
  `agent_reports/ACS-P0-005-task-contract.md`,
  `agent_reports/2026-09-01-ACS-P0-005-pi-confirmed.md`,
  `agent_reports/2026-09-01-ACS-P0-005-review-claude.md`.
- Pročitan stvarni diff protiv merge-base-a `820bbf9`.
- Diff shape: 19 novih fajlova, svi u `allowed_paths`; nema promjena u
  zabranjenim scope-ovima niti u paralelnom ACS-P0-006 scope-u.
- Pročitan kompletan novi kod i testovi:
  `ai_registry/{provider_models,model_profiles,registry}.py`,
  `ports/{ai_registry,secrets}.py`,
  `infrastructure/secrets/{environment_secret_store,keyring_secret_store}.py`,
  6 provider YAML fajlova,
  `tests/unit/ai_registry/test_ai_provider_registry.py`,
  `tests/integration/ai_registry/test_provider_resources.py`,
  `tests/unit/secrets/test_secret_store.py`.
- Potvrđeno da nema provider SDK/network importa u novom kodu. `git grep`
  za `openai`/`anthropic`/`google.generativeai`/`requests`/`httpx`/`urllib`
  našao je samo dozvoljene metadata stringove u YAML/docstring kontekstu.
- Potvrđeno da provider YAML fajlovi ne sadrže stvarne API key/token
  vrijednosti; sadrže samo schema flag `requires_api_key: true`.
- Potvrđeno da `KeyringSecretStore.__repr__`, `str(store)` i
  `repr(store.__dict__)` ne sadrže secret value nakon `set_secret`.
- Potvrđeno da fake keyring backend postoji i da unit testovi ne pišu u pravi
  korisnički keyring.
- Potvrđeno da duplicate model rejection i
  `register_discovered_models()` provider-code mismatch rade na happy/negative
  putanji.

# GITNEXUS / IMPACT

`UNKNOWN`.

`npx gitnexus status` iz worktree-a vraća:

```text
Repository not indexed.
Run: gitnexus analyze
```

`npx gitnexus detect-changes --scope compare --base-ref main --repo .` iz
worktree-a vraća poznato worktree-binding ograničenje:

```text
Repository "." not found. Available: deklarant_pro, FieldFix-IT, Dentaland,
FlowOS, AI-Campaing-Studio
```

Kompenzacija: ručni `git diff 820bbf9 task/ACS-P0-005-ai-registry-secrets`
potvrđuje da su svi fajlovi novi i unutar contract scope-a.

# BLOCKING FINDINGS

## BF-1 — `KeyringSecretStore` čuva leaky backend exception kao `__cause__`

`KeyringSecretStore` hvata backend exception i radi `raise SecretStoreError(...)
from exc`. `str(SecretStoreError)` i `repr(SecretStoreError)` ne sadrže
secret, ali originalni backend exception ostaje dostupan kao `exc.__cause__`.
Ako backend exception sadrži secret value, traceback/cause inspection može
otkriti vrijednost.

Stvarni probe output:

```text
WRAPPED_STR_HAS_SECRET: False
WRAPPED_REPR_HAS_SECRET: False
WRAPPED_CAUSE_HAS_SECRET: True
```

Zašto blokira: contract i P0.15 traže da secret nikad ne završi u logovima
ili exception reprezentaciji. Python traceback za chained exception često
prikaže i originalni cause. Za security-critical SecretStore ovo nije samo
estetski problem: adapter sam ne loguje value, ali ga zadržava u exception
chain-u.

Minimalni očekivani fix: ne chain-ovati backend exception koji može sadržati
secret value (`from None`) ili ga sanitizovati u safe technical context koji
ne ulazi u traceback/log repr. Dodati test koji koristi fake backend čiji
exception sadrži secret i potvrđuje da `str(exc)`, `repr(exc)`, traceback/cause
putanja i logs ne sadrže value.

## BF-2 — `secret_to_env_var()` dopušta alias/collision za nekanonska imena

`secret_to_env_var()` ne validira secret name prema contract konvenciji
`provider/<provider_code>/api_key`. Zbog toga različita imena mogu mapirati
na isti env var.

Stvarni probe output:

```text
ENV_MAP: 'provider/OPENAI/api_key' -> 'AI_CAMPAIGN_STUDIO_OPENAI_API_KEY'
ENV_MAP: 'OPENAI/api_key' -> 'AI_CAMPAIGN_STUDIO_OPENAI_API_KEY'
ENV_MAP: 'provider/OPENAI_API/key' -> 'AI_CAMPAIGN_STUDIO_OPENAI_API_KEY'
ENV_GET_CANONICAL: 'test-secret-value-123'
ENV_GET_NO_PREFIX_ALIAS: 'test-secret-value-123'
```

Zašto blokira: review brief je eksplicitno tražio provjeru collision-a. Ovo
je stvaran collision, ne teorija: nekanonski name bez `provider/` prefiksa
čita isti secret kao kanonski `provider/OPENAI/api_key`. U security-sensitive
SecretStore foundation-u secret namespace treba biti determinističan i
jednoznačan, posebno jer contract zaključava naming convention.

Minimalni očekivani fix: centralno validirati secret name i prihvatiti samo
`provider/<PROVIDER_CODE>/api_key` oblik (ili drugi eksplicitno odobren oblik
u contractu), uz odbijanje praznog stringa, praznog provider segmenta,
specijalnih karaktera koji nisu dozvoljeni i alias oblika bez `provider/`.
Dodati parametrizovane regresione testove za collision primjere.

## BF-3 — registry prihvata modele za nepoznatog providera

`register_manual_model()` ne provjerava da `model.provider_code` postoji u
provider registry-ju. Isto važi za `register_discovered_models()` ako caller
proslijedi isti nepoznati provider code i u parametru i u modelu.

Stvarni probe output:

```text
DUPLICATE_MODEL: RegistryError: duplicate model: OPENAI/dupe
DISCOVERED_PROVIDER_MISMATCH: RegistryError: model provider_code 'ANTHROPIC' does not match provider 'OPENAI'
MANUAL_UNKNOWN_PROVIDER: accepted
UNKNOWN_PROVIDER_MODELS: [ModelProfile(provider_code='UNKNOWN', model_id='x', ...)]
```

Zašto blokira: P0.14 traži provider validation, unknown provider →
`RegistryError`, i provider/model izbor koji je arhitektonski moguć bez
Campaign Engine zavisnosti. Ako model registry može sadržati enabled model za
`UNKNOWN`, kasniji `resolve_default_text_model()` može vratiti model čiji
provider nije konfigurisan/poznat u provider registry-ju.

Minimalni očekivani fix: prije registracije modela potvrditi da
`model.provider_code` postoji u `_providers` (`get_provider`/dict lookup), i
da `register_discovered_models(provider_code, models)` takođe odbija nepoznat
`provider_code` čak i kad se svi modeli slažu s njim. Dodati regresione
testove za manual i discovered unknown-provider slučajeve.

# STANDARDNA VERIFIKACIJA

Pokrenuto iz worktree-a uz `TMP`/`TEMP` i mypy cache preusmjerene u workspace
zbog Windows sandbox ograničenja:

```text
.\.venv\Scripts\python.exe -m pytest -q
........................................................................ [ 64%]
.......................................                                  [100%]
111 passed, 1 warning in 1.38s
```

```text
.\.venv\Scripts\python.exe -m ruff check . --no-cache
All checks passed!
```

```text
.\.venv\Scripts\python.exe -m mypy src
Success: no issues found in 38 source files
```

Napomena: full suite je green, ali ne pokriva tri blocking edge case-a gore.

# ADVERSARIALNA PROVJERA

Pokrenute dodatne runtime probe izvan source tree-a:

```text
ENV_MAP: 'provider/OPENAI/api_key' -> 'AI_CAMPAIGN_STUDIO_OPENAI_API_KEY'
ENV_MAP: 'OPENAI/api_key' -> 'AI_CAMPAIGN_STUDIO_OPENAI_API_KEY'
ENV_MAP: '' -> 'AI_CAMPAIGN_STUDIO_'
ENV_MAP: 'provider//api_key' -> 'AI_CAMPAIGN_STUDIO__API_KEY'
ENV_MAP: 'provider/OPENAI/api-key' -> 'AI_CAMPAIGN_STUDIO_OPENAI_API-KEY'
ENV_MAP: 'provider/OPENAI_API/key' -> 'AI_CAMPAIGN_STUDIO_OPENAI_API_KEY'
ENV_GET_CANONICAL: 'test-secret-value-123'
ENV_GET_NO_PREFIX_ALIAS: 'test-secret-value-123'
ENV_GET_EMPTY_VALUE: ''
KEYRING_REPR_HAS_SECRET: False
KEYRING_STR_HAS_SECRET: False
KEYRING_DICT_HAS_SECRET: False
WRAPPED_STR_HAS_SECRET: False
WRAPPED_REPR_HAS_SECRET: False
WRAPPED_CAUSE_HAS_SECRET: True
DUPLICATE_MODEL: RegistryError: duplicate model: OPENAI/dupe
DISCOVERED_PROVIDER_MISMATCH: RegistryError: model provider_code 'ANTHROPIC' does not match provider 'OPENAI'
MANUAL_UNKNOWN_PROVIDER: accepted
UNKNOWN_PROVIDER_MODELS: [ModelProfile(provider_code='UNKNOWN', model_id='x', display_name='X', capabilities=(), context_window=None, supports_temperature=None, enabled=True, source=<ModelSource.MANUAL: 'MANUAL'>)]
```

Zaključci:

- Duplicate model rejection i discovered-provider mismatch rade.
- `KeyringSecretStore` ne cache-uje secret u sebi i obični repr/str store-a
  ne curi secret.
- Prazan env var value vraća `""`, ne `None`. Ovo bilježim kao opservaciju,
  ne blocker: env var postoji, pa je ponašanje dosljedno `os.environ.get`;
  kasniji provider connection validation može odbiti prazan key.
- BF-1/BF-2/BF-3 su stvarni contract/security edge-case bugovi.

# NE DIRATI U FIX RUNDI

- Ne širiti scope na live provider SDK/network adaptere.
- Ne dirati ACS-P0-006 SQLite/database scope.
- Ne dodavati stvarne model ID liste u YAML.
- Ne pisati u pravi OS keyring iz testova; zadržati fake/mock backend.
- Ne mijenjati postojeći data-driven provider YAML oblik osim ako je direktno
  potrebno za validaciju.

# SLJEDEĆE

Fix na istoj branch-i, usko:

1. Sanitizovati `KeyringSecretStore` exception chaining tako da secret ne može
   procuriti kroz `__cause__`/traceback/log putanju; dodati regresioni test.
2. Validirati SecretStore name format prije env-var mapiranja; dodati testove
   za alias/collision/malformed slučajeve.
3. Validirati da svaki registrovani model pripada poznatom provideru; dodati
   manual i discovered unknown-provider regresione testove.
4. Ponoviti `pytest`, `ruff`, `mypy` i security probe.
