---
task_id: ACS-F1-016
title: "OpenAI live adapter + provider setup use-cases"
phase: Faza-1
risk: HIGH
coordinator: claude
implementer: TBD (Human Owner assigns)
reviewers: [codex, claude]
status: "BLOCKED — čeka ACS-F1-015 merge (provider config persistence prerequisite)"
created_at: 2026-09-03
dependencies: [ACS-F1-015]
allowed_paths:
  - src/ai_campaign_studio/infrastructure/ai/openai_adapter.py
  - src/ai_campaign_studio/application/ai_provider/__init__.py
  - src/ai_campaign_studio/application/ai_provider/configure_provider.py
  - src/ai_campaign_studio/application/ai_provider/test_provider_connection.py
  - src/ai_campaign_studio/application/ai_provider/discover_models.py
  - src/ai_campaign_studio/application/ai_provider/select_default_model.py
  - pyproject.toml
  - tests/unit/infrastructure/ai/test_openai_adapter.py
  - tests/unit/application/ai_provider/
  - tests/integration/application/ai_provider/
forbidden_paths:
  - src/ai_campaign_studio/ports/provider_config.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_provider_config_repository.py
  - src/ai_campaign_studio/ports/ai_registry.py
  - src/ai_campaign_studio/ai_registry/
  - src/ai_campaign_studio/ports/secrets.py
  - src/ai_campaign_studio/infrastructure/secrets/
  - src/ai_campaign_studio/ports/ai.py
  - src/ai_campaign_studio/ports/prompts.py
  - src/ai_campaign_studio/infrastructure/prompts/
  - src/ai_campaign_studio/infrastructure/ai/mock_adapter.py
  - src/ai_campaign_studio/application/posts/
  - src/ai_campaign_studio/application/campaigns/
  - src/ai_campaign_studio/application/brands/
  - src/ai_campaign_studio/domain/
  - resources/migrations/
  - src/ai_campaign_studio/infrastructure/database/connection.py
  - src/ai_campaign_studio/infrastructure/database/migrations.py
  - src/ai_campaign_studio/infrastructure/database/unit_of_work.py
  - src/ai_campaign_studio/presentation/
  - src/ai_campaign_studio/presentation_webview/
  - src/ai_campaign_studio/bootstrap.py
  - src/ai_campaign_studio/main.py
gitnexus_required: true
adversarial_required: true
gitnexus:
  required: true
  repository: "H:\\AI Campaing Studio"
  worktree: main (pre-branch pre-impact)
  branch: main
  head: 550d8b6
  index_status: "fresh at contract-write time — RE-CHECK required after ACS-F1-015 merges, since
    this task's base commit moves"
  targets:
    - symbol: "new infrastructure/ai/openai_adapter.py + application/ai_provider/ package"
      upstream_risk: NONE
      upstream_count: 0
      downstream_notes: "Brand-new files, zero existing importers. Does not modify mock_adapter.py, ports/ai.py, ports/ai_registry.py, or ports/secrets.py — only consumes them."
      affected_processes: []
  scope_fit: PASS
  unknowns:
    - "ACS-F1-015 nije još mergovan u trenutku pisanja ovog kontrakta — implementer MORA raditi
      na main-u NAKON ACS-F1-015 merge-a (rebase/re-branch ako je worktree kreiran ranije), ne na
      main @ 550d8b6 koji nema ProviderConfigRepositoryPort/ModelSelectionRepositoryPort."
    - "Tačan OpenAI API mehanizam za structured output (json_schema) zavisi od trenutne OpenAI
      API/SDK verzije u vrijeme implementacije — implementer istražuje i dokumentuje tačan poziv
      koji koristi (Chat Completions sa response_format, ili Responses API), ovaj kontrakt
      namjerno ne propisuje tačan HTTP shape."
---

# Kontekst

**Drugi od dva taska za A8** (prvi = ACS-F1-015, provider config/model selection persistence).
Human Owner je eksplicitno odlučio (2026-09-03) da se A8 radi provajder-po-provajder počevši od
**OpenAI** — Anthropic/Google/DeepSeek/OpenRouter/OpenAI-compatible dolaze kao odvojeni budući
taskovi kad se ovaj obrazac dokaže, ne odjednom.

**Zašto HIGH**: ovaj task prvi put u projektu (1) čita/piše STVARAN API ključ preko
`SecretStorePort` (workflow §3 eksplicitno navodi "API credential handling" kao HIGH kriterijum),
i (2) pravi STVARAN vanjski mrežni poziv ka OpenAI API-ju. Puni Codex + Claude + eksplicitno Human
Owner odobrenje, bez izuzetka.

**Testiranje bez pravog API ključa (Human Owner odluka, 2026-09-03)**: cijeli automatski test
suite (pytest/CI) MORA proći BEZ stvarnog OpenAI API ključa i BEZ stvarnog mrežnog poziva — HTTP/
SDK transport sloj se mock-uje u potpunosti (isti duh kao `bootstrap.py`-jev dokumentovan "fully
offline by design" princip). Implementer/koordinator SMIJE ručno probati sa pravim ključem izvan
test suite-a kao dodatnu evidenciju, ali to NIJE obavezan dio review-a i NE smije biti jedini
dokaz da adapter radi.

**Šta VEĆ postoji i ne treba graditi**:

```text
ports/ai.py — TextGenerationPort, AIRequest, AIResponse, AITelemetry (ACS-F1-008)
infrastructure/ai/mock_adapter.py — strukturni STIL primjer (ACS-F1-008), NE DIRATI
ports/ai_registry.py — AIProviderRegistryPort, ModelRegistryPort, AIProviderConnectionPort
ai_registry/ — AIProviderRegistry (implementira prva dva porta), resources/ai_providers/openai.yaml
  (provider_code: OPENAI, adapter_type: openai, requires_api_key: true,
  supports_model_discovery: true, base_url_mode: FIXED)
ports/secrets.py + infrastructure/secrets/ — SecretStorePort, KeyringSecretStore/
  EnvironmentSecretStore, canonical credential name format `provider/<PROVIDER_CODE>/api_key`
  (regex `^provider/([A-Za-z0-9_]+)/api_key$`)
ACS-F1-015 — ProviderConfigRepositoryPort/ModelSelectionRepositoryPort + SQLite adapter
```

**`AIProviderConnectionPort` (test_connection/discover_models) SE NE IMPLEMENTIRA u ovom tasku.**
Njegov potpis (`test_connection(self, provider_code: str, **config)`) pretpostavlja JEDNU klasu
koja rutira pozive ka N provajdera — prerano uopštavanje dok postoji samo jedan (OpenAI). Umjesto
toga, `OpenAIAdapter` izlaže SVOJE VLASTITE, jednostavne metode (`test_connection() -> bool`,
`discover_models() -> list[ModelProfile]`, bez `provider_code`/`**config` parametara — instanca je
već vezana za OpenAI preko konstruktora). Kad drugi provajder stigne, TADA odlučiti da li
`AIProviderConnectionPort` dobija stvarnu implementaciju (npr. mala dispatch klasa) — ne prije.
Ovo je namjerna, dokumentovana scope granica, ne propust.

**Retry policy (plan sekcija 20, doslovno)**:

```text
attempt 1 → schema valid? da → nastavi
                          ne → attempt 2 sa eksplicitnom schema-repair instrukcijom
                               → schema valid? da → nastavi
                                                ne → AI_SCHEMA_ERROR
```

Schema-repair retry je **application-layer** odgovornost (implementer NE gradi ga u ovom tasku —
to je budući `GenerateSocialPost`/`GenerateCampaignPlan` unapređenje, van scope-a). Network/
rate-limit retry SMIJE biti u adapteru, ali OGRANIČEN (implementer bira razuman limit, npr. 2
pokušaja, dokumentuje izbor) — "Ne praviti beskonačne retry petlje". **Svaki retry MORA biti
logovan** (standardni `logging` modul, ne novi logging sistem).

Prije koda pročitati:

```text
AGENTS.md
CLAUDE.md
docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md
.agent/CURRENT_STATE.md
AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md
  AI-R1 do AI-R8 (provider/model dizajn pravila — posebno AI-R5 settings UX flow, AI-R8 MVP
  routing — samo default_text_model), sekcija 20 "AI adapter implementacija" (retry policy)
```

Pročitati postojeći kod (STIL primjer, ne pogađati potpise):

```text
src/ai_campaign_studio/ports/ai.py (TextGenerationPort, AIRequest, AIResponse, AITelemetry)
src/ai_campaign_studio/infrastructure/ai/mock_adapter.py (strukturni obrazac — konstruktor,
  generate() implementacija, NE kopirati sadržaj, samo shape)
src/ai_campaign_studio/ports/ai_registry.py (AIProviderRegistryPort, ModelRegistryPort,
  AIProviderConnectionPort docstring — "future-only, no P0 component implements or calls it")
src/ai_campaign_studio/ai_registry/model_profiles.py (ModelProfile — provider_code, model_id,
  display_name, capabilities, context_window?, supports_temperature?, enabled, source)
src/ai_campaign_studio/ai_registry/provider_models.py (AIProviderDefinition)
src/ai_campaign_studio/ports/secrets.py (SecretStorePort — get_secret vraća None za nepostojeći,
  ne grešku)
src/ai_campaign_studio/ports/provider_config.py (ACS-F1-015 — ProviderConfig, ModelSelection,
  ProviderConfigRepositoryPort, ModelSelectionRepositoryPort — PROČITATI NAKON tog merge-a)
```

# Objective

1. `infrastructure/ai/openai_adapter.py` — `OpenAIAdapter` (implementira `TextGenerationPort`
   + vlastite `test_connection()`/`discover_models()` metode).
2. `application/ai_provider/` paket — 4 use-case-a: `ConfigureProvider`,
   `TestProviderConnection`, `DiscoverModels`, `SelectDefaultModel`.
3. `pyproject.toml` — dodati `openai` (ili implementer-ov izabran HTTP klijent) kao zavisnost,
   dokumentovati izbor.

# Implementation steps

## `OpenAIAdapter`

```python
class OpenAIAdapter:
    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None: ...
    def generate(self, request: AIRequest) -> AIResponse: ...  # TextGenerationPort
    def test_connection(self) -> bool: ...
    def discover_models(self) -> list[ModelProfile]: ...
```

- `generate()`: mora ispoštovati `request.json_schema` (structured output) — implementer
  istražuje tačan trenutni OpenAI API mehanizam (Chat Completions `response_format` ili Responses
  API) i DOKUMENTUJE izbor u evidence izvještaju. Mapira grešku providera u odgovarajuću domain
  grešku (ne curi sirov SDK exception dalje bez konteksta). Popunjava `AIResponse.telemetry`
  (`latency_ms` stvarno mjeren, `input_tokens`/`output_tokens` iz provider response-a ako
  dostupno).
- `test_connection()`: najlakši mogući poziv koji potvrđuje da je API ključ validan (npr. list
  models endpoint ili ekvivalent) — vraća `bool`, NE baca grešku za "invalid key" (to je legitiman
  `False` rezultat, ne exception; exception je rezervisan za neočekivane greške — implementer
  dokumentuje tu granicu).
- `discover_models()`: vraća `list[ModelProfile]` (mapira provider-specifičan model list response
  u domain `ModelProfile`, `source=ModelSource.DISCOVERED`, `provider_code="OPENAI"`).
- Bounded retry (network/rate-limit) + logging na svakom retry-u, kako je opisano u Kontekst
  sekciji.
- Nema business logike, nema CampaignRole logike, nema claim validacije, nema perzistencije (isto
  pravilo kao `mock_adapter.py`).

## `application/ai_provider/configure_provider.py`

```python
class ConfigureProvider:
    def __init__(self, provider_registry: AIProviderRegistryPort,
                 provider_config_repo: ProviderConfigRepositoryPort,
                 secret_store: SecretStorePort) -> None: ...
    def execute(self, provider_code: str, api_key: str,
                base_url: str | None = None) -> ProviderConfig: ...
```

Tok: `provider_registry.get_provider(provider_code)` (potvrđuje da provider postoji i
`requires_api_key`; nepoznat `provider_code` → propagira `RegistryError`) → konstruiše
`credential_ref = f"provider/{provider_code}/api_key"` → `secret_store.set_secret(credential_ref,
api_key)` → `provider_config_repo.save_provider_config(ProviderConfig(provider_code,
configured=True, validated=False, credential_ref=credential_ref, base_url=base_url,
updated_at=utc_now()))` → vraća sačuvan `ProviderConfig`. `validated` UVIJEK `False` poslije
`ConfigureProvider` — validacija je `TestProviderConnection`-ov posao, ne ovog use-case-a
(razdvojeno po AI-R5 flow-u: configure → test connection → discover models → select model).

## `application/ai_provider/test_provider_connection.py`

```python
@dataclass(frozen=True)
class ConnectionTestResult:
    success: bool
    error_message: str | None = None

class TestProviderConnection:
    def __init__(self, provider_config_repo: ProviderConfigRepositoryPort,
                 secret_store: SecretStorePort) -> None: ...
    def execute(self, provider_code: str) -> ConnectionTestResult: ...
```

Tok: učitava `ProviderConfig` (nepostojeći/`configured=False` → `ConnectionTestResult(success=
False, error_message=...)`, NE exception — ovo je očekivan, ne izuzetan slučaj) → učitava secret
preko `credential_ref` → konstruiše `OpenAIAdapter` → `adapter.test_connection()` → ažurira
`ProviderConfig.validated` na rezultat → perzistuje → vraća `ConnectionTestResult`. Za sad
hardkodirano vezano za `OpenAIAdapter` (samo jedan provajder postoji) — dokumentovati da će
buduć provider-factory zamijeniti direktnu instancijaciju kad 2+ provajdera postoje.

## `application/ai_provider/discover_models.py`

```python
class DiscoverModels:
    def __init__(self, provider_registry: AIProviderRegistryPort,
                 model_registry: ModelRegistryPort,
                 provider_config_repo: ProviderConfigRepositoryPort,
                 secret_store: SecretStorePort) -> None: ...
    def execute(self, provider_code: str) -> list[ModelProfile]: ...
```

Tok: `provider_registry.get_provider(provider_code)` → ako `supports_model_discovery` (OpenAI:
`True`) → učitava config+secret → `OpenAIAdapter.discover_models()` →
`model_registry.register_discovered_models(provider_code, models)` → vraća listu. Ako
`supports_model_discovery` je `False` za dati provider → `InvariantViolation` jasno objašnjava da
ovaj task ne implementira registry/manual fallback (AI-R7 fallback grana namjerno van scope-a —
OpenAI uvijek podržava discovery, fallback put nije exercised ovim taskom, dolazi sa provajderom
koji ga stvarno treba).

## `application/ai_provider/select_default_model.py`

```python
class SelectDefaultModel:
    def __init__(self, model_registry: ModelRegistryPort,
                 model_selection_repo: ModelSelectionRepositoryPort) -> None: ...
    def execute(self, provider_code: str, model_id: str) -> ModelSelection: ...
```

Tok: `model_registry.get_model(provider_code, model_id)` (potvrđuje da model postoji među
registrovanim — nepoznat model → propagira `RegistryError`, NE tiho prihvata proizvoljan
model_id) → `model_selection_repo.save_model_selection(ModelSelection(purpose=
"default_text_model", provider_code, model_id, updated_at=utc_now()))` → vraća sačuvan
`ModelSelection`. Samo `"default_text_model"` purpose (AI-R8 — ne graditi routing za druge
purpose-e).

# Acceptance

- [ ] **Nijedan automatski test ne pravi stvaran mrežni poziv** — HTTP/SDK transport je mock-ovan
      u potpunosti; test suite prolazi bez `OPENAI_API_KEY` postavljenog bilo gdje (provjeri da
      CI/lokalni run ne zavisi od env varijable sa stvarnim ključem).
- [ ] `OpenAIAdapter.generate()` ispoštuje `json_schema` (test sa mock-ovanim structured
      response-om, provjerava da `AIResponse.structured_payload` odgovara).
- [ ] `OpenAIAdapter.generate()` mapira provider grešku u jasnu grešku, ne curi sirov SDK
      exception bez konteksta (test sa mock-ovanim error response-om).
- [ ] Bounded retry na network/rate-limit grešci (mock simulira 1-2 tranzijentne greške pa
      uspjeh) — test dokazuje da adapter STVARNO retry-uje (broj poziva na mock transportu), i da
      NE retry-uje beskonačno (mock koji uvijek failuje mora na kraju dati jasnu grešku, ne
      visjeti).
- [ ] Svaki retry logovan (test provjerava log output ili poziva logger mock, implementer bira
      tačan mehanizam provjere).
- [ ] `OpenAIAdapter.test_connection()` vraća `True`/`False` (ne baca za "loše kredencijale" —
      test za oba ishoda).
- [ ] `OpenAIAdapter.discover_models()` mapira provider response u `ModelProfile` listu sa
      `source=ModelSource.DISCOVERED`, `provider_code="OPENAI"` (test).
- [ ] `ConfigureProvider`: čuva secret preko `SecretStorePort` (NIKAD direktno u `ProviderConfig`/
      bazi — test dokazuje da sačuvan `ProviderConfig.credential_ref` je STRING REFERENCA, ne
      sam ključ), `validated` uvijek `False` poslije (test).
- [ ] `ConfigureProvider`: nepoznat `provider_code` → propagira `RegistryError` PRIJE bilo kakvog
      `secret_store.set_secret` poziva (test — secret store netaknut).
- [ ] `TestProviderConnection`: nekonfigurisan provider → `ConnectionTestResult(success=False,
      ...)`, NE exception (test).
- [ ] `DiscoverModels`: provider bez `supports_model_discovery` → `InvariantViolation` jasno
      objašnjava scope granicu (test — implementer može koristiti fake provider definition sa
      `supports_model_discovery=False` za ovaj test, OpenAI sam po sebi ne triggera ovu granu).
- [ ] `SelectDefaultModel`: nepoznat `model_id` → propagira `RegistryError`, ništa perzistovano
      (test).
- [ ] Nijedan test/kod ne sadrži literal koji liči na stvaran API key (isti duh kao
      `check_no_secrets.py` — provjeri fixture/mock vrijednosti u testovima koriste očigledno
      lažne stringove poput `"sk-EXAMPLE-..."` ili `"fake-key"`, ne nešto što liči na pravi ključ).
- [ ] `bootstrap.py` NIJE diran — use-case-i/adapter se ne žice u composition root u ovom tasku.
- [ ] `python -m pytest -q`, `ruff check .`, `mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest -q
python -m pytest tests/architecture/test_import_boundaries.py -v
python -m pytest tests/unit/infrastructure/ai/test_openai_adapter.py tests/unit/application/ai_provider tests/integration/application/ai_provider -v
python -m ruff check .
python -m mypy src
python scripts/check_no_secrets.py
```

# Adversarialna provjera (obavezna, `adversarial_required: true`)

Barem JEDAN test koji dokazuje: retry mehanizam se STVARNO zaustavlja (privremeno postaviti mock
transport da UVIJEK failuje → test mora dobiti jasnu grešku u razumnom broju poziva, NE beskonačnu
petlju/timeout). Dokumentovati "prije" (bez bounded retry-a, hipotetički beskonačna petlja ili
nedovoljno pokušaja) i "poslije" (ograničen broj, jasna greška) — isti obrazac kao ranije
adversarialne provjere u projektu.

# Review focus — Codex (primarni) + Claude (arhitektura)

**Codex**: retry logika stvarno ograničena i logovana; error mapping ne curi sirove SDK detalje
opasno (npr. ne uključuje API ključ u exception poruku/log); mock transport pokriva realne failure
modove (timeout, 429, 500, malformed JSON response); test koji NE pravi stvaran mrežni poziv je
STVARNO izolovan (nema slučajnog `requests.get`/`httpx` poziva koji prođe kroz mock sloj a
zapravo pogodi mrežu).

**Claude**: `AIProviderConnectionPort` namjerno NIJE implementiran (dokumentovana scope granica,
ne propust); `SecretStorePort` korišten ispravno (`credential_ref` je referenca, nikad sam
ključ, nikad logovan/serijalizovan); `bootstrap.py` netaknut; use-case-i zavise od portova
(Protocol), ne direktno od `OpenAIAdapter` konkretne klase gdje god je to razumno (iako je za sad
OpenAI jedini provajder, pa je direktna zavisnost privremeno prihvatljiva — provjeriti da je to
dokumentovano kao privremeno, ne trajno arhitektonsko rješenje).

# Rollback

HIGH risk — puna procedura. Ne commit-ovati/merge-ovati bez eksplicitne Codex review runde I
eksplicitnog Human Owner odobrenja. Ako implementer zaključi da treba dirati `bootstrap.py` ili
`ports/ai_registry.py`/`ports/secrets.py` — STOP, vratiti kontraktu na redizajn prije nastavka.

# Coordination

**BLOCKED dok ACS-F1-015 ne merguje.** Nakon merge-a, implementer mora `git merge main` u svoj
worktree PRIJE početka koda, da dobije `ProviderConfigRepositoryPort`/
`ModelSelectionRepositoryPort`. Prvi od 6 provajdera — Anthropic/Google/DeepSeek/OpenRouter/
OpenAI-compatible dolaze kao odvojeni budući taskovi.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-016-openai-adapter
Branch:   task/ACS-F1-016-openai-adapter
Base:     main @ 550d8b6 (implementer MORA merge-ovati main nakon ACS-F1-015 prije rada)
```
