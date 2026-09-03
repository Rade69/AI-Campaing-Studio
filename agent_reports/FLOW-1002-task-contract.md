---
task_id: FLOW-1002
title: "Provider config + model selection persistence"
phase: Faza-1
risk: MEDIUM
coordinator: claude
implementer: TBD (Human Owner assigns)
reviewers: [claude]
status: "OPEN — contract written before code"
created_at: 2026-09-03
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/ports/provider_config.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_provider_config_repository.py
  - tests/unit/ports/test_provider_config.py
  - tests/integration/database/repositories/test_sqlite_provider_config_repository.py
forbidden_paths:
  - src/ai_campaign_studio/ports/repositories.py
  - src/ai_campaign_studio/ports/ai_registry.py
  - src/ai_campaign_studio/ports/ai.py
  - src/ai_campaign_studio/ports/prompts.py
  - src/ai_campaign_studio/ports/secrets.py
  - src/ai_campaign_studio/ai_registry/
  - src/ai_campaign_studio/infrastructure/secrets/
  - src/ai_campaign_studio/infrastructure/ai/
  - src/ai_campaign_studio/infrastructure/database/repositories/__init__.py
  - src/ai_campaign_studio/infrastructure/database/connection.py
  - src/ai_campaign_studio/infrastructure/database/migrations.py
  - src/ai_campaign_studio/infrastructure/database/unit_of_work.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_brand_repository.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_campaign_repository.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_content_repository.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_fact_repository.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_revision_repository.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_visual_repository.py
  - resources/migrations/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/presentation/
  - src/ai_campaign_studio/presentation_webview/
  - src/ai_campaign_studio/bootstrap.py
  - src/ai_campaign_studio/main.py
gitnexus_required: true
adversarial_required: false
gitnexus:
  required: true
  repository: "H:\\AI Campaing Studio"
  worktree: main (pre-branch pre-impact)
  branch: main
  head: 550d8b6
  index_status: fresh (analyze re-run 2026-09-03 post FLOW-1001 merge)
  targets:
    - symbol: "new ports/provider_config.py + sqlite_provider_config_repository.py"
      upstream_risk: NONE
      upstream_count: 0
      downstream_notes: "Brand-new files, zero existing importers. provider_configs/model_selections tables already exist (P0 migration 0000_foundation.sql) but zero code reads/writes them today (confirmed via repo-wide grep) — this task is the first consumer, not a schema change. No migration needed."
      affected_processes: []
  scope_fit: PASS
  unknowns: []
---

# Kontekst

**Prvi od dva taska za A8** (plan sekcija "A8 — Live AI adapters + prompt/model execution nad
postojećim P0 registryjem"). A8 je prevelik za jedan kontrakt (6 provajdera × 4 use-case-a + retry
policy) — podijeljen je po istom principu kao A9→(F1-010+011): **ovaj task (FLOW-1002) je čist
persistence sloj, bez SecretStore-a, bez mrežnih poziva, MEDIUM risk. Drugi task (FLOW-1003,
BLOCKED na ovom) je OpenAI live adapter + 4 use-case-a koji stvarno dodiruju SecretStore i prave
vanjski API poziv — HIGH risk, puni Codex+Human Owner ciklus.** Human Owner je eksplicitno
odlučio (2026-09-03) da se A8 radi provajder-po-provajder počevši od OpenAI — Anthropic/Google/
DeepSeek/OpenRouter/OpenAI-compatible dolaze kao odvojeni budući taskovi kad se obrazac dokaže.

**Šta VEĆ postoji (P0) i ne treba graditi**:

```text
resources/migrations/0000_foundation.sql — provider_configs i model_selections tabele VEĆ POSTOJE:

CREATE TABLE provider_configs (
    provider_code TEXT PRIMARY KEY,
    configured INTEGER NOT NULL DEFAULT 0,
    validated INTEGER NOT NULL DEFAULT 0,
    credential_ref TEXT NULL,
    base_url TEXT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE model_selections (
    purpose TEXT PRIMARY KEY,
    provider_code TEXT NOT NULL,
    model_id TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

**Ovaj task NE pravi novu migraciju** — samo čita/piše postojeće tabele. Repo-wide grep potvrđuje
da NIJEDAN kod trenutno referencira ove dvije tabele van same migracije — ovaj task je prvi
stvaran konzument.

`ai_registry/` paket (`AIProviderRegistry`, `AIProviderDefinition`, `ModelProfile`,
`ModelRegistryPort`) je potpuno gotov i NE TREBA da se mijenja — on je čisto definicioni/in-memory
registar (nikad ne pravi mrežni poziv), ne persistuje "korisnik je konfigurisao provider X". Ova
dva koncepta (definicija provajdera vs. korisnikovo stanje konfiguracije provajdera) su namjerno
odvojena — `AIProviderRegistry` kaže "OpenAI adapter postoji i podržava discovery"; ovaj task-ov
repository sloj kaže "korisnik JE konfigurisao OpenAI, ključ je na `credential_ref`, validiran je
u X vremenu".

**Risk**: MEDIUM — čist CRUD nad već-postojećim P0 tabelama, isti klasa rizika kao ACS-F1-005/006
(originalna business persistence). Ne dira SecretStore, ne pravi mrežne pozive, ne mijenja
migraciju. §29: Claude-only review, PASS → odmah merge.

Prije koda pročitati:

```text
AGENTS.md
CLAUDE.md
docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md
.agent/CURRENT_STATE.md
AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md
  AI-R1 ("ProviderConfig { provider_code, configured, credential_ref, base_url? }" — dopunjeno
  ovdje sa `validated` poljem koje tabela već ima), sekcija "A8" task-lista stavka
  "provider_configs foundation" / "model_selections foundation"
```

Pročitati postojeći kod (STIL primjer, ista disciplina):

```text
src/ai_campaign_studio/ports/repositories.py (Protocol stil primjer — @runtime_checkable,
  framework-neutral, plain dataclass domain objects)
src/ai_campaign_studio/infrastructure/database/repositories/sqlite_campaign_repository.py
  (SQLite adapter stil primjer — upsert preko ON CONFLICT DO UPDATE, enum/bool kao INTEGER,
  isti idempotency pattern)
src/ai_campaign_studio/ports/ai_registry.py (AIProviderDefinition/ModelProfile — NE duplirati ova
  polja, ProviderConfig je NOVI, drugačiji koncept)
resources/migrations/0000_foundation.sql (tačan DDL, ne pogađati kolone)
```

# Objective

1. `ports/provider_config.py` — `ProviderConfig`/`ModelSelection` dataclass-e +
   `ProviderConfigRepositoryPort`/`ModelSelectionRepositoryPort` Protocol-i.
2. `infrastructure/database/repositories/sqlite_provider_config_repository.py` — SQLite adapter
   za oba porta.

# Implementation steps

## `ports/provider_config.py`

```python
@dataclass(frozen=True)
class ProviderConfig:
    provider_code: str
    configured: bool
    validated: bool
    credential_ref: str | None
    base_url: str | None
    updated_at: datetime


@dataclass(frozen=True)
class ModelSelection:
    purpose: str
    provider_code: str
    model_id: str
    updated_at: datetime


@runtime_checkable
class ProviderConfigRepositoryPort(Protocol):
    def save_provider_config(self, config: ProviderConfig) -> None: ...
    def get_provider_config(self, provider_code: str) -> ProviderConfig | None: ...
    def list_provider_configs(self) -> tuple[ProviderConfig, ...]: ...


@runtime_checkable
class ModelSelectionRepositoryPort(Protocol):
    def save_model_selection(self, selection: ModelSelection) -> None: ...
    def get_model_selection(self, purpose: str) -> ModelSelection | None: ...
```

`credential_ref` je STRING REFERENCA (npr. `"provider/OPENAI/api_key"`, isti format kao
`EnvironmentSecretStore`-ov canonical secret name — implementer NE mora znati tačan SecretStore
detalj, samo skladišti string koji mu je prosleđen), NIKAD sam API ključ — ovaj port/adapter
NIKAD ne uvozi `ports/secrets.py`/`infrastructure/secrets/` niti dodiruje SecretStore. `purpose`
u `ModelSelection` je plain string (npr. `"default_text_model"` — AI-R8 kaže Faza 1 implementira
SAMO `default_text_model`, ne graditi routing za druge purpose-e).

## SQLite adapter

Isti obrazac kao `sqlite_campaign_repository.py`: `save_*` je idempotentan upsert
(`ON CONFLICT(...) DO UPDATE`), `bool` kolone (`configured`/`validated`) čuvane kao `INTEGER`
(`1`/`0`), rekonstruisane nazad u `bool` (`row["configured"] == 1` ili `bool(row["configured"])`).
`get_provider_config`/`get_model_selection` vraćaju `None` za nepostojeći red (NE grešku).
`list_provider_configs` vraća sve redove, sortirane po `provider_code` (deterministički
redoslijed za testove).

# Acceptance

- [ ] Round-trip test: `ProviderConfig` (svi polja popunjena, uključujući `credential_ref`/
      `base_url`) → save → get → dataclass `==` jednakost.
- [ ] Round-trip test: `ProviderConfig` sa `credential_ref=None`/`base_url=None` → ostaje `None`
      nazad (ne prazan string).
- [ ] `save_provider_config` idempotentan — re-save sa promijenjenim `validated` ažurira red, ne
      duplira (`COUNT(*) == 1` provjera).
- [ ] `get_provider_config`/`get_model_selection` za nepostojeći ključ → `None`, ne greška.
- [ ] `list_provider_configs` vraća sve sačuvane konfiguracije, sortirane deterministički.
- [ ] Round-trip test za `ModelSelection` (isti nivo kao `ProviderConfig`).
- [ ] `bool` polja (`configured`/`validated`) STVARNO round-trip-uju kao `bool`, ne kao `0`/`1`
      int (test provjerava `isinstance(result.configured, bool)` ili ekvivalentno).
- [ ] Oba porta su `@runtime_checkable` i imaju test koji to potvrđuje (isti obrazac kao
      `tests/unit/ports/test_repositories.py`).
- [ ] Nema importa `ports/secrets.py`/`infrastructure/secrets/` bilo gdje u ovom tasku (grep
      provjera).
- [ ] `python -m pytest -q`, `ruff check .`, `mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths` — POSEBNO ne
      `infrastructure/database/repositories/__init__.py` (koordinator dodaje re-export nakon
      merge-a, isti obrazac kao ACS-F1-006).

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest -q
python -m pytest tests/architecture/test_import_boundaries.py -v
python -m pytest tests/unit/ports/test_provider_config.py tests/integration/database/repositories/test_sqlite_provider_config_repository.py -v
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- `credential_ref` je STRING reference, nikad stvaran secret — provjeriti da nijedan test/kod ne
  ubacuje nešto što liči na stvaran API key literal (isti duh kao `check_no_secrets.py`);
  nema importa SecretStore-a nigdje;
- bool round-trip stvarno radi (INTEGER 0/1 ↔ Python bool), ne curi kao int;
- idempotentnost potvrđena (`COUNT(*)` provjera, ne samo "test prolazi");
- nema nove migracije, nema izmjene postojeće DDL;
- scope discipline — `ai_registry/`/`ports/ai_registry.py` netaknuti (drugi koncept).

# Rollback

MEDIUM risk — nova, izolovana persistence adapter nad već-postojećim, praznim tabelama. Fix na
istoj branch bez proširenja scope-a.

# Coordination

Blokira **FLOW-1003** (OpenAI adapter + ConfigureProvider/TestProviderConnection/DiscoverModels/
SelectDefaultModel use-cases, HIGH). FLOW-1003 kontrakt će biti napisan/dostupan poslije ovog
merge-a. Nezavisan od svega ostalog trenutno otvorenog.

```text
Worktree: ../ai-campaign-studio-worktrees/FLOW-1002-provider-config-persistence
Branch:   task/FLOW-1002-provider-config-persistence
Base:     main @ 550d8b6
```
