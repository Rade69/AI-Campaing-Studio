---
task_id: ACS-P0-005
phase: P0
title: "AI Provider/Model Registry + SecretStore foundation"
risk: HIGH
coordinator: claude
implementer: pi
reviewers: [codex, claude]
status: "OPEN — contract written before code"
created_at: 2026-09-01
dependencies: [ACS-P0-002]
allowed_paths:
  - src/ai_campaign_studio/ai_registry/__init__.py
  - src/ai_campaign_studio/ai_registry/provider_models.py
  - src/ai_campaign_studio/ai_registry/model_profiles.py
  - src/ai_campaign_studio/ai_registry/registry.py
  - src/ai_campaign_studio/ports/ai_registry.py
  - src/ai_campaign_studio/ports/secrets.py
  - src/ai_campaign_studio/infrastructure/__init__.py
  - src/ai_campaign_studio/infrastructure/secrets/__init__.py
  - src/ai_campaign_studio/infrastructure/secrets/environment_secret_store.py
  - src/ai_campaign_studio/infrastructure/secrets/keyring_secret_store.py
  - resources/ai_providers/openai.yaml
  - resources/ai_providers/anthropic.yaml
  - resources/ai_providers/google.yaml
  - resources/ai_providers/deepseek.yaml
  - resources/ai_providers/openrouter.yaml
  - resources/ai_providers/openai_compatible.yaml
  - tests/unit/ai_registry/
  - tests/integration/ai_registry/
  - tests/unit/secrets/
forbidden_paths:
  - src/ai_campaign_studio/channels/
  - src/ai_campaign_studio/localization/
  - src/ai_campaign_studio/domain/brand/
  - src/ai_campaign_studio/domain/campaign/
  - src/ai_campaign_studio/domain/content/
  - src/ai_campaign_studio/infrastructure/database/
  - src/ai_campaign_studio/infrastructure/ai/
  - src/ai_campaign_studio/bootstrap.py
  - src/ai_campaign_studio/main.py
  - presentation_qt/
  - presentation_webview/
gitnexus_required: true
adversarial_required: true
gitnexus:
  required: true
  repository: "H:\\AI Campaing Studio"
  worktree: main (pre-branch pre-impact)
  branch: main
  head: 820bbf9
  index_status: up-to-date
  targets:
    - symbol: "src/ai_campaign_studio/ports (folder)"
      upstream_risk: LOW
      upstream_count: 0
      downstream_notes: "i dalje 0 upstream callera (bootstrap.py još ne wire-uje channels/localization/ai_registry/secrets) — ports/ai_registry.py i ports/secrets.py su novi sestrinski fajlovi, nema overlap-a sa ports/channels.py (003) ili ports/localization.py (004)"
      affected_processes: []
    - symbol: "domain/common/errors.py:RegistryError, SecretStoreError"
      upstream_risk: LOW
      upstream_count: 1 (RegistryError iz channels/registry.py)
      downstream_notes: "postojeće AppError podklase iz ACS-P0-002 se ponovo koriste, ne redefinišu — RegistryError za provider/model validaciju, SecretStoreError za secret store greške"
      affected_processes: []
  scope_fit: PASS
  unknowns: []
---

# Kontekst

Peti coding task Implementation Phase 0. Zavisi samo od ACS-P0-002 (merged).
Može raditi paralelno sa ACS-P0-006 — `allowed_paths` su disjoint (provjereno
protiv ACS-P0-006 kontrakta), nema shared fajla ni skrivene semantic
zavisnosti (registry i secret store ne dijele state sa SQLite foundation-om).

**HIGH risk** — workflow §22 eksplicitno navodi ovaj task kao HIGH (SecretStore
je security-osjetljiv invarijant), i workflow §4 elevated P0 standard
eksplicitno navodi "AI Provider/Model Registry" i "SecretStore" kao oblasti
koje zahtijevaju Codex + Claude review bez izuzetka.

Prije koda implementer mora pročitati:

```text
AGENTS.md
CLAUDE.md
docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md
.agent/CURRENT_STATE.md
.agent/PROJECT_MAP.md
.agent/TASK_ROUTING.md
AI_Campaign_Studio_Implementation_Phase_0_v1_1_Agent_Workflow_Integrated.md
  sekcije 21–22 (P0.14–P0.15)
```

# Objective

Data-driven AI Provider/Model registry (bez network poziva) + SecretStore
foundation (environment i keyring adapteri) tako da provider/model izbor i
API-ključ handling budu arhitektonski mogući bez ijedne provider SDK
zavisnosti ili Campaign Engine logike.

# Implementation steps

## P0.14 — AI Provider/Model Registry

1. `ai_registry/provider_models.py`: `AIProviderDefinition` — `provider_code`,
   `display_name`, `adapter_type`, `requires_api_key`,
   `supports_model_discovery`, `base_url_mode` (`FIXED`|`USER_CONFIGURABLE`|
   `NONE`), `enabled`. Immutable (isti obrazac kao `PlatformDefinition` iz
   ACS-P0-004 — frozen pydantic, `tuple` za bilo koju kolekciju, NE `list`,
   iz iskustva BF-2 na ACS-P0-004).
2. `ai_registry/model_profiles.py`: `ModelCapability` enum
   (`TEXT_GENERATION`, `STRUCTURED_OUTPUT`, `VISION`, `IMAGE_GENERATION`,
   `TOOL_USE`), `ModelSource` enum (`DISCOVERED`, `REGISTRY`, `MANUAL`),
   `ModelProfile` — `provider_code`, `model_id`, `display_name`,
   `capabilities` (tuple), `context_window?`, `supports_temperature?`,
   `enabled`, `source`. P0 ne mora imati realnu listu modela (model ID-jevi
   se mijenjaju).
3. `ports/ai_registry.py`: dva odvojena protocol-a —
   `AIProviderRegistryPort` (`list_providers()`, `get_provider(provider_code)`)
   i odvojeno `AIProviderConnectionPort` (`test_connection(...)`,
   `discover_models(...)` — future-capability contract, NE implementirati u
   P0, samo definisati); `ModelRegistryPort` (`list_models(provider_code=None)`,
   `get_model(provider_code, model_id)`, `register_discovered_models(...)`,
   `register_manual_model(...)`, `resolve_default_text_model(...)`,
   `supports(...)`).
4. `ai_registry/registry.py`: provider resource loader (YAML iz
   `resources/ai_providers/`), provider validation, in-memory model registry,
   manual model registration, capability filtering, duplicate detection.
   NE raditi network/API connection/provider SDK pozive — to dolazi poslije
   P0-GATE-a. Ponovo koristiti `RegistryError` iz `domain/common/errors.py`
   (ACS-P0-002) — ne definisati novu exception klasu.
5. 6 provider YAML fajlova (`OPENAI`, `ANTHROPIC`, `GOOGLE`, `DEEPSEEK`,
   `OPENROUTER`, `OPENAI_COMPATIBLE`) prema shemi iz plana. **NIKAD** ne
   stavljati API key/secret default/neprovjeren model ID u YAML.

## P0.15 — SecretStore foundation

6. `ports/secrets.py`: `SecretStorePort` protocol —
   `get_secret(name) -> str | None`, `set_secret(name, value) -> None`,
   `delete_secret(name) -> None`.
7. Secret naming convention: `provider/<provider_code>/api_key` (npr.
   `provider/OPENAI/api_key`). Model ID se NIKAD ne koristi u secret name-u.
8. `infrastructure/secrets/environment_secret_store.py`: dev/test adapter.
   Mapiranje `provider/OPENAI/api_key` → `AI_CAMPAIGN_STUDIO_OPENAI_API_KEY`
   (provider code uppercase, slash → underscore, prefiks
   `AI_CAMPAIGN_STUDIO_`). `set_secret` je ili read-only sa jasnim
   `SecretStoreError`, ili test-only in-memory override — implementer bira,
   ali mora biti eksplicitno dokumentovano u docstringu. NE pisati
   automatski `.env` fajl.
9. `infrastructure/secrets/keyring_secret_store.py`: production desktop
   adapter preko Python `keyring` biblioteke (već dependency iz P0-001).
   Service name: `"AI Campaign Studio"`. Implementira get/set/delete. NIKAD
   ne logovati vrijednost secreta (ni u exception message, ni u log liniji).

# Acceptance

- [ ] 6 provider YAML fajlova se učitava, provider kodovi unique.
- [ ] `base_url_mode` validan (`FIXED`|`USER_CONFIGURABLE`|`NONE`).
- [ ] Nepoznat provider → `RegistryError`.
- [ ] Manual model registration radi (`register_manual_model`).
- [ ] Capability filter radi (`supports(...)` / filter po `ModelCapability`).
- [ ] Isti provider/model duplikat odbijen.
- [ ] Nijedan resource (YAML) ne sadrži nešto što liči na API key/token
      (test koji grep-uje/regex-uje sadržaj YAML fajlova).
- [ ] SecretStore: set/get/delete rade na oba adaptera (environment sa test
      env vars, keyring sa fake/mock backend — **NIKAD** ne pisati u pravi
      korisnički keyring tokom testova).
- [ ] Missing secret → `None`, ne exception.
- [ ] Secret se nikad ne pojavljuje u logovima niti u exception `repr()`
      (test koji provjerava da `str(exc)`/`repr(exc)` ne sadrži test secret
      vrijednost).
- [ ] `python -m pytest -q`, `ruff check .`, `mypy src` prolaze.
- [ ] Nema provider SDK dependency-ja (openai/anthropic/google-generativeai/
      itd.), nema network poziva u `registry.py` ili secret store adapterima.

# Adversarial test (obavezno — adversarial_required: true, security-critical)

Za "secret nikad ne procuri u log/exception":

1. test tvrdi da `KeyringSecretStore`/`EnvironmentSecretStore` operacije
   nikad ne loguju vrijednost secreta;
2. privremeno dodati debug `logger.info(f"... {value}")` liniju u
   set_secret/get_secret implementaciji — test mora FAIL (detektuje secret
   value u log output-u);
3. ukloniti debug liniju — test mora PASS;
4. dokumentovati oba outputa.

Isto za duplicate-detection u `ai_registry/registry.py` (isti obrazac kao
ACS-P0-004: privremeno ukloniti duplicate-check, test mora FAIL, vratiti,
test mora PASS).

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest -q
python -m ruff check .
python -m mypy src
git status --short
```

# Review focus — Codex

- da li adversarial log/exception-leak test stvarno dokazuje da nema
  procurenja (ne samo happy-path provjera);
- da li `EnvironmentSecretStore`/`KeyringSecretStore` testovi koriste
  stvaran fake/mock backend, ne pravi keyring;
- edge cases: `get_secret` za nepostojeći name, `delete_secret` na
  nepostojećem secretu (idempotentno ili baca?), malformed provider YAML;
- da li je neka zabranjena provider SDK dependency ušla direktno ili
  tranzitivno.

# Review focus — Claude

- `ai_registry/registry.py` ne poziva network/provider SDK;
- `ports/ai_registry.py` razdvaja `AIProviderRegistryPort` (P0-ready) od
  `AIProviderConnectionPort` (future-capability, samo contract);
- `SecretStorePort` je framework-neutral, infrastructure adapteri ga
  implementiraju (ne obrnuto);
- nijedan secret nije hardkodovan/default-vrijednost bilo gdje (YAML,
  kod, testovi — testovi smiju koristiti očigledno-fake test vrijednosti
  kao `"test-secret-value"`, ne nešto što liči na pravi ključ format);
  provider/model izbor arhitektonski nezavisan od Campaign Engine-a.

# Rollback

HIGH task (SecretStore security invariant). Ako review otkrije da secret
leak-adversarial test ne dokazuje invariant, ili da je ijedan secret
hardkodovan/default — NE spajati, fix na istoj branch bez proširenja
scope-a.

# Dependency baseline

Zavisi od ACS-P0-002 (merged, `main`@`820bbf9`, koji uključuje i ACS-P0-003
i ACS-P0-004 mergove). Ne granati sa starijeg main-a.

# Coordination

Paralelno sa ACS-P0-006 — `allowed_paths` potpuno disjoint (provjereno).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-P0-005-ai-registry-secrets
Branch:   task/ACS-P0-005-ai-registry-secrets
Base:     main @ 820bbf9
```

Nakon merge-a: post-merge gate, GitNexus detect-changes prije reviewa (ili
manuelni ekvivalent zbog poznatog worktree-binding ograničenja), GitNexus
re-index poslije merge-a, CURRENT_STATE update.
