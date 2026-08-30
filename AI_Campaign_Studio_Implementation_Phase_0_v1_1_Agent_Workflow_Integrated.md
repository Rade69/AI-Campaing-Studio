# AI Campaign Studio
# Implementation Phase 0 v1.1 — Project Foundation
## Maksimalno detaljan agent-ready plan za postavljanje projekta prije Domain/Campaign Engine implementacije

**Status:** obavezni izvršni plan prije Faze 1 business implementacije  
**Nadređeni projektni dokument:** `AI_Campaign_Studio_Faza_0_6_Channel_Model_LLM_Registry.md`  
**Naredni implementacioni dokument:** `AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md`  
**Cilj ovog dokumenta:** napraviti čist, testiran, pokretljiv i arhitektonski zaključan tehnički temelj projekta  
**Jezik implementacije:** Python 3.12+  
**Arhitektura:** Clean/Hexagonal core + Ports/Adapters + framework-neutral Presentation foundation  
**UI framework:** još NIJE izabran  
**Persistence:** SQLite foundation, bez Campaign/Brand production šeme u ovoj fazi  
**AI provideri:** registry/contracts/secrets foundation, bez Campaign generation logike  
**Social:** Channel/Platform/Format registry foundation, bez social content generatora  
**Glavni izlaz:** `P0-GATE = PASS`

---

# 0. Šta ovaj dokument jeste

Ovo je **radni nalog coding agentu**.

Nije:

- proizvodni koncept;
- arhitektonski esej;
- brainstorming;
- lista budućih želja;
- Faza 1 Campaign Engine implementacija.

Agent treba da može otvoriti ovaj dokument i tačno znati:

```text
šta radi
gdje radi
koji folder kreira
koji fajl kreira
šta fajl sadrži
šta fajl NE sadrži
koji test piše
koju komandu pokreće
šta mora biti rezultat
kada smije preći na sljedeći task
```

---

# 1. Obavezno čitanje prije prvog reda koda

Ovaj plan se NE izvršava kao jedan veliki prompt bez agentskog procesa.

Agent MORA prije implementacije pročitati, ovim redom:

```text
1. AGENTS.md
2. CLAUDE.md
3. docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md
4. .agent/CURRENT_STATE.md
5. .agent/PROJECT_MAP.md
6. konkretan agent_reports/<TASK-ID>-task-contract.md
7. .agent/TASK_ROUTING.md
8. AI_Campaign_Studio_Faza_0_6_Channel_Model_LLM_Registry.md
9. relevantne sekcije ovog dokumenta
10. AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md samo za downstream contract kontekst kada je potreban
```

Uloge dokumenata:

```text
Faza 0.6
= PRODUCT + ARCHITECTURE SOURCE OF TRUTH

Implementation Phase 0 v1.1
= TAČAN PROCEDURALNI FOUNDATION PLAN

Faza 1 v1.4
= BUSINESS / VERTICAL SLICE IMPLEMENTATION PLAN

docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md
= KANONSKI NAČIN RADA AGENATA
```

Ako postoji konflikt:

```text
1. najnovija eksplicitna odluka Human Ownera
2. Faza 0.6
3. ovaj Implementation Phase 0 plan za foundation tehničke detalje
4. kanonski agentski workflow za proces rada
5. Faza 1 v1.4 za kasniju business implementaciju
6. Task Contract — smije suziti task, ne smije tiho prepisati više odluke
```

Agent ne smije tiho promijeniti odluku iz Faze 0.6 zato što mu je druga implementacija lakša.

Svaki P0 coding blok se izvršava kroz Task Contract, worktree, coordination claim, execution evidence, review i Human Owner approval prema kanonskom workflowu.

---


# 1A. P0 execution governance — obavezno

Implementation Phase 0 se ne daje jednom agentu da ga nekontrolisano "odradi od početka do kraja".

Koordinator ga razlaže na sljedeće default Task Contract pakete:

```text
ACS-P0-001 → P0.00–P0.05  repo/tooling/bootstrap skeleton
ACS-P0-002 → P0.06–P0.10  config/logging/common/architecture boundaries
ACS-P0-003 → P0.11–P0.12  localization + BHS regional resources
ACS-P0-004 → P0.13        Channel/Platform/Format registry
ACS-P0-005 → P0.14–P0.15  AI Provider/Model Registry + SecretStore
ACS-P0-006 → P0.16–P0.19  SQLite + migrations + UoW + foundation ports
ACS-P0-007 → P0.20–P0.23  JobManager + Presentation contracts + bootstrap/health
ACS-P0-008 → P0.24–P0.30  validators + CI + security + final P0 gate
```

Dependency DAG:

```text
ACS-P0-001
     ↓
ACS-P0-002
     ↓
 ┌────┬────┬─────┐
 ↓    ↓    ↓     ↓
003  004  005   006
 └────┴────┴─────┘
        ↓
      007
        ↓
      008
        ↓
   P0-GATE PASS
```

003–006 se smiju paralelizovati samo ako:

```text
allowed_paths presjek = ∅
coordination.py nema konflikt
GitNexus/semantic dependency provjera ne pokaže skriveno preklapanje
```

Default uloge:

```text
Human Owner → final merge approval
Claude       → coordinator + architecture/integration reviewer
Codex        → adversarial/test reviewer
Pi / Crush   → implementeri
```

Za foundation/shared-contract taskove 002, 004, 005, 006, 007 i 008 default je dual review:

```text
Codex + Claude
```

Implementer ne može reviewati svoj task.

---

# 1B. GitNexus je obavezan od prvog korisnog code graph-a

`ACS-P0-001` je jedini P0 paket koji može početi bez GitNexus impact analize jer repository još nema koristan source graph.

Odmah nakon što ACS-P0-001 napravi package skeleton, koordinator MORA iz root-a repoa pokrenuti:

```bash
npx gitnexus analyze --skip-agents-md
npx gitnexus status
```

Repo sadrži custom `AGENTS.md` i `CLAUDE.md`, zato GitNexus ne smije postati njihov source of truth.

Od `ACS-P0-002` nadalje svaki MEDIUM/HIGH ili shared-contract task slijedi:

```text
.agent/GITNEXUS_PROTOCOL.md
```

Minimalno prije izmjene:

```text
GitNexus context
GitNexus upstream impact
downstream impact kada je relevantno
repo/worktree/index identity
```

Minimalno prije reviewa:

```bash
npx gitnexus detect-changes --scope compare --base-ref main --repo .
```

Poslije svakog merge-a u main:

```bash
npx gitnexus analyze --skip-agents-md
npx gitnexus check --cycles --repo .
```

Ako GitNexus pokaže veći blast radius nego Task Contract:

```text
STOP
```

Task se redefiniše. Implementer ne širi scope samostalno.

---

# 2. Šta Implementation Phase 0 mora završiti

Na kraju ove faze mora postojati:

```text
✓ validan Python package
✓ reproducibilan dev setup
✓ pyproject.toml
✓ src-layout
✓ test suite
✓ Ruff
✓ Mypy
✓ architecture-boundary testovi
✓ framework-neutral config/path sistem
✓ structured logging foundation
✓ centralni error taxonomy foundation
✓ UUID/time primitives
✓ EN/BHS localization foundation
✓ BHS regional-language foundation
✓ Channel/Platform/Format registry
✓ početne social platform definicije
✓ AI Provider Registry
✓ Model Registry contract
✓ SecretStore abstraction + dev/keyring adapteri
✓ SQLite connection foundation
✓ migration runner
✓ transaction/UoW foundation
✓ framework-neutral JobManager
✓ framework-neutral Presentation state/contracts
✓ bootstrap/composition root
✓ startup health check
✓ resource validation
✓ CI quality gate
✓ no-secret checks
✓ GitNexus repository index nakon početnog skeletona
✓ GitNexus impact/detect-changes evidence za relevantne P0 taskove
✓ P0 gate report
```

---

# 3. Šta Implementation Phase 0 NE smije implementirati

Ovo je vrlo važno.

U ovoj fazi NE implementirati:

```text
NO Brand entity business model
NO ApprovedFact business model
NO BrandSnapshot business model
NO CampaignBrief business logic
NO CampaignPlan
NO CampaignItem planning
NO CampaignRole planner
NO ContentPiece generation
NO SocialPost generator
NO claim validation/linter
NO prompt generation pipeline
NO live AI Campaign calls
NO Campaign persistence tables
NO Post/Content persistence tables
NO renderer
NO Playwright
NO PySide6 production UI
NO pywebview production UI
NO Website Ingestion
NO PDF/DOCX/XLSX parsing
NO RAG
NO embeddings
NO vector DB
NO publishing/scheduler
NO social APIs
NO VPS backup
```

Dozvoljeno je kreirati **paket/folder granice** za kasnije module, ali ne pisati lažnu ili praznu business implementaciju.

---

# 4. Ključni princip ove faze

Implementation Phase 0 treba da završi sa:

```text
foundation koja je korisna i testirana
```

a ne sa:

```text
mnogo placeholder fajlova bez funkcije
```

Pravilo:

> Ako fajl u Phase 0 nema stvarnu foundation odgovornost ili test, ne kreirati ga još.

---

# 5. P0 gate struktura

Taskovi se izvršavaju ovim redom:

```text
P0.00  Read & reconcile documents
P0.01  Inspect workspace/repository
P0.02  Establish Git safety baseline
P0.03  Python environment
P0.04  pyproject.toml + tooling
P0.05  Create Phase-0 repository tree
P0.06  Package bootstrap
P0.07  Config + paths
P0.08  Logging foundation
P0.09  Error taxonomy + common primitives
P0.10  Architecture boundaries
P0.11  Localization EN/BHS
P0.12  BHS regional language resources
P0.13  Channel/Platform/Format registry
P0.14  AI Provider/Model Registry
P0.15  SecretStore
P0.16  SQLite connection foundation
P0.17  Migration runner
P0.18  Unit of Work / transaction foundation
P0.19  Foundation ports
P0.20  JobManager
P0.21  Presentation contracts/state
P0.22  Bootstrap/Composition Root
P0.23  Health-check entrypoint
P0.24  Foundation resource validators
P0.25  CI quality gate
P0.26  Security/no-secret checks
P0.27  Full foundation verification
P0.28  Gate report
P0.29  Foundation commit
P0.30  STOP
```

Agent NE prelazi na Domain/Faza 1 dok `P0.28` ne kaže:

```text
P0-GATE: PASS
```

---

# 6. Ciljna struktura nakon Implementation Phase 0

Nakon ove faze repository treba izgledati približno ovako:

```text
ai-campaign-studio/
│
├── pyproject.toml
├── README.md
├── .gitignore
├── config.example.toml
├── .python-version                  # samo ako projekat standardizuje pyenv/asdf; inače ne praviti
│
├── src/
│   └── ai_campaign_studio/
│       ├── __init__.py
│       ├── bootstrap.py
│       ├── main.py
│       │
│       ├── config/
│       │   ├── __init__.py
│       │   ├── settings.py
│       │   └── paths.py
│       │
│       ├── logging/
│       │   ├── __init__.py
│       │   ├── config.py
│       │   ├── events.py
│       │   └── redaction.py
│       │
│       ├── localization/
│       │   ├── __init__.py
│       │   ├── enums.py
│       │   ├── language_context.py
│       │   └── translator.py
│       │
│       ├── channels/
│       │   ├── __init__.py
│       │   ├── enums.py
│       │   ├── definitions.py
│       │   └── registry.py
│       │
│       ├── ai_registry/
│       │   ├── __init__.py
│       │   ├── provider_models.py
│       │   ├── model_profiles.py
│       │   └── registry.py
│       │
│       ├── domain/
│       │   ├── __init__.py
│       │   └── common/
│       │       ├── __init__.py
│       │       ├── ids.py
│       │       ├── errors.py
│       │       └── timestamps.py
│       │
│       ├── application/
│       │   └── __init__.py
│       │
│       ├── ports/
│       │   ├── __init__.py
│       │   ├── localization.py
│       │   ├── channels.py
│       │   ├── ai_registry.py
│       │   ├── secrets.py
│       │   └── database.py
│       │
│       ├── infrastructure/
│       │   ├── __init__.py
│       │   ├── database/
│       │   │   ├── __init__.py
│       │   │   ├── connection.py
│       │   │   ├── migrations.py
│       │   │   └── unit_of_work.py
│       │   └── secrets/
│       │       ├── __init__.py
│       │       ├── environment_secret_store.py
│       │       └── keyring_secret_store.py
│       │
│       ├── jobs/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   ├── events.py
│       │   ├── cancellation.py
│       │   └── manager.py
│       │
│       └── presentation/
│           ├── __init__.py
│           ├── contracts.py
│           ├── state.py
│           └── ui_models.py
│
├── resources/
│   ├── i18n/
│   │   ├── en.json
│   │   └── bhs.json
│   │
│   ├── regional_language/
│   │   ├── bhs_neutral_v1.yaml
│   │   ├── bhs_bs_v1.yaml
│   │   ├── bhs_sr_v1.yaml
│   │   └── bhs_hr_v1.yaml
│   │
│   ├── platforms/
│   │   ├── instagram.yaml
│   │   ├── facebook.yaml
│   │   ├── linkedin.yaml
│   │   ├── x.yaml
│   │   ├── tiktok.yaml
│   │   ├── youtube.yaml
│   │   ├── pinterest.yaml
│   │   ├── threads.yaml
│   │   └── snapchat.yaml
│   │
│   ├── ai_providers/
│   │   ├── openai.yaml
│   │   ├── anthropic.yaml
│   │   ├── google.yaml
│   │   ├── deepseek.yaml
│   │   ├── openrouter.yaml
│   │   └── openai_compatible.yaml
│   │
│   └── migrations/
│       └── 0000_foundation.sql
│
├── scripts/
│   ├── health_check.py
│   └── validate_resources.py
│
├── tests/
│   ├── architecture/
│   │   └── test_import_boundaries.py
│   │
│   ├── unit/
│   │   ├── config/
│   │   │   ├── test_settings.py
│   │   │   └── test_paths.py
│   │   ├── logging/
│   │   │   └── test_redaction.py
│   │   ├── localization/
│   │   │   ├── test_language_context.py
│   │   │   └── test_translator.py
│   │   ├── channels/
│   │   │   └── test_registry.py
│   │   ├── ai_registry/
│   │   │   └── test_registry.py
│   │   ├── secrets/
│   │   │   └── test_secret_store.py
│   │   ├── database/
│   │   │   └── test_unit_of_work.py
│   │   └── jobs/
│   │       ├── test_cancellation.py
│   │       └── test_manager.py
│   │
│   └── integration/
│       ├── localization/
│       │   └── test_translation_resources.py
│       ├── channels/
│       │   └── test_platform_resources.py
│       ├── ai_registry/
│       │   └── test_provider_resources.py
│       ├── database/
│       │   ├── test_connection.py
│       │   └── test_migrations.py
│       └── startup/
│           └── test_bootstrap_health.py
│
├── artifacts/
│   └── .gitkeep
│
└── .github/
    └── workflows/
        └── ci.yml
```

Napomena:

- `domain/brand`, `domain/facts`, `domain/campaign`, `domain/content`, `domain/visual` se NE kreiraju u ovoj fazi ako nemaju implementaciju.
- oni dolaze u Fazi 1.
- `infrastructure/ai` live adapteri takođe dolaze poslije P0 gate-a.
- `presentation_qt/` i `presentation_webview/` NE postoje u Phase 0.

---

# 7. P0.00 — Read & reconcile documents

## Cilj

Agent prvo mora potvrditi šta je aktuelno.

## Akcija

Pročitati:

```text
AI_Campaign_Studio_Faza_0_6_Channel_Model_LLM_Registry.md
AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md
AI_Campaign_Studio_Implementation_Phase_0_Project_Foundation_Agent_Plan.md
```

## Agent mora izvući samo internu radnu checklistu

Ne pravi novi `.md`.

Checklist mora potvrditi:

```text
desktop-first
local-first
UI framework not selected
EN/BHS UI
BHS regional variants
channel-agnostic core
social-first output
Channel → Platform → Format
provider/model registry
API key per provider
OS keyring
SQLite
Clean/Hexagonal
no Campaign Engine implementation in P0
```

## STOP uslov

Ako aktuelni dokumenti nedostaju ili postoje dvije verzije sa istim statusom "active", agent ne smije nagađati.

Mora prijaviti tačno koje fajlove vidi.

---

# 8. P0.01 — Inspect workspace/repository

## Cilj

Spriječiti:

```text
ai-campaign-studio/ai-campaign-studio/
```

ili accidental init unutar pogrešnog foldera.

## Akcija

Provjeriti:

```text
pwd / current working directory
git status
git rev-parse --show-toplevel
directory listing
existing pyproject.toml
existing src/
```

Windows/PowerShell ili shell ekvivalent je prihvatljiv.

## Odluka

### Ako Git repo već postoji

Ne raditi:

```text
git init
```

Koristiti postojeći root.

### Ako repo ne postoji

Kreirati jedan root:

```text
ai-campaign-studio/
```

i inicijalizovati Git samo tu.

## Ne smije

- brisati postojeće fajlove;
- preimenovati korisničke dokumente;
- pomjerati Faza 0/1 dokumente bez zahtjeva;
- force resetovati Git.

## Acceptance

Agent može navesti tačan:

```text
REPO_ROOT
```

i `git status` je razumljiv prije promjena.

---

# 9. P0.02 — Git safety baseline

## Cilj

Osigurati provjerljiv početak.

## Akcija

Ako repo ima postojeći kod:

```text
git status --short
git branch --show-current
git log -1 --oneline
```

Ne mijenjati postojeće dirty fajlove koji nisu dio zadatka.

Ako je repo nov:

```text
git init
```

## Branch

Ako workflow koristi feature grane:

```text
foundation/phase-0
```

Ako korisnik/okruženje ima drugačije Git pravilo, slijediti ga.

## Zabranjeno

```text
git reset --hard
git clean -fd
git push --force
```

bez eksplicitnog razloga/odobrenja.

## Acceptance

Prije coding promjena zabilježeno je:

```text
branch
HEAD
dirty files
```

u agentovom radnom kontekstu, ne u novom dokumentu.

---

# 10. P0.03 — Python environment

## Cilj

Jedan jasan Python baseline.

## Verzija

```text
Python >=3.12
```

Ne uvoditi novu minor verziju samo zbog novine ako dependency kompatibilnost nije potvrđena.

## Virtual environment

Kreirati lokalni:

```text
.venv/
```

Primjer:

```text
python -m venv .venv
```

Aktivirati odgovarajuće za OS.

## `.gitignore`

Obavezno ignorisati:

```text
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
dist/
build/
*.egg-info/
artifacts/*
!artifacts/.gitkeep
*.log
.env
.env.*
```

Ne ignorisati:

```text
config.example.toml
resources/
tests/
```

## Acceptance

```text
python --version
python -c "import sys; print(sys.executable)"
```

pokazuju interpreter iz `.venv`.

---

# 11. P0.04 — `pyproject.toml` + tooling

## Cilj

Jedan source of truth za packaging i dev tooling.

## Kreirati

```text
pyproject.toml
```

## Obavezni sections

```text
[build-system]
[project]
[project.optional-dependencies]
[tool.pytest.ini_options]
[tool.ruff]
[tool.ruff.lint]
[tool.mypy]
```

## Project metadata

Minimalno:

```text
name = "ai-campaign-studio"
requires-python = ">=3.12"
```

Version može početi:

```text
0.1.0
```

ali ne graditi release proces u P0.

## Runtime dependencies za P0

Samo foundation potrebe:

```text
pydantic
PyYAML
platformdirs
keyring
```

Ako je za logging dovoljan stdlib:

```text
ne dodavati logging biblioteku
```

SQLite dolazi iz stdlib `sqlite3`.

## Dev dependencies

```text
pytest
pytest-cov
ruff
mypy
```

Opcionalno:

```text
pytest-timeout
```

samo ako test hang postane stvaran problem.

## NE instalirati u P0

```text
PySide6
pywebview
playwright
openai
anthropic
google provider SDK
DeepSeek SDK/client
Flask
FastAPI
Pillow
PyMuPDF
python-docx
openpyxl
vector DB
```

Razlog:

njihova stvarna implementacija dolazi kasnije.

## Ruff

Uključiti najmanje provjere za:

```text
E
F
I
UP
B
```

Ne praviti ekstremno restriktivan lint profil prije realnog koda.

## Mypy

Početno:

```text
python_version = "3.12"
warn_unused_configs = true
check_untyped_defs = true
no_implicit_optional = true
```

Ne uključivati odmah `strict = true` ako to proizvodi više šuma nego vrijednosti.

## Pytest

Test paths:

```text
tests
```

## Komande

```text
python -m pip install -e ".[dev]"
python -m pytest -q
python -m ruff check .
python -m mypy src
```

## Acceptance

Sve četiri komande moraju završiti bez infrastructure/setup greške.

---

# 12. P0.05 — Kreiraj Phase-0 repository tree

## Cilj

Napraviti samo stvarne foundation module.

## Kreirati direktorije iz sekcije 6.

## `__init__.py`

Kreirati samo tamo gdje je Python package potreban.

Ne stavljati:

```python
from .everything import *
```

u `__init__.py`.

Početno mogu biti prazni ili imati samo package docstring.

## Ne kreirati još

```text
domain/brand/entities.py
domain/campaign/entities.py
application/campaigns/
application/content/
prompts/
renderer/
spikes/
presentation_qt/
presentation_webview/
```

## Test

```text
python -c "import ai_campaign_studio"
```

## Acceptance

Import package-a radi sa editable installom.

---

# 13. P0.06 — Package bootstrap

## `src/ai_campaign_studio/__init__.py`

Sadrži samo package metadata ako je potrebno.

Dozvoljeno:

```text
__version__
```

Nije potrebno re-exportovati cijelu aplikaciju.

## `main.py`

U P0 još NE pokreće GUI.

Njegova jedina uloga:

```text
parse minimal startup options
build bootstrap
support --health-check
return process exit code
```

## `bootstrap.py`

U P0 kreira samo foundation container.

Ne kreira:

```text
Campaign use cases
AI generation adapters
renderer
GUI
```

Minimalni dependency graph:

```text
Settings
Paths
Logger
Translator
PlatformRegistry
AIProviderRegistry
SecretStore
DatabaseConnectionFactory
MigrationRunner
JobManager
```

## Acceptance

`bootstrap.py` se može importovati bez:

- API ključa;
- mreže;
- GUI;
- browsera.

---

# 14. P0.07 — Config + paths

## Fajlovi

```text
src/ai_campaign_studio/config/settings.py
src/ai_campaign_studio/config/paths.py
config.example.toml
tests/unit/config/test_settings.py
tests/unit/config/test_paths.py
```

---

## `settings.py`

Koristiti Pydantic model ili ekvivalent validacije.

### `AppSettings`

Minimalna polja:

```text
app_name
environment
log_level
app_locale
database_filename
resource_dir_override?
data_dir_override?
```

Dozvoljeni environment:

```text
development
test
production
```

Default app locale:

```text
BHS_LATIN
```

ili `EN` ako Faza 0.6 drugačije odluči; ne hardkodovati regional variant ovdje.

### NE sadržati

```text
api_key
openai_key
anthropic_key
provider secrets
campaign defaults
model hardcoded list
```

---

## `paths.py`

Koristiti:

```text
platformdirs
pathlib.Path
```

### `AppPaths`

Mora dati:

```text
data_dir
database_dir
database_path
cache_dir
logs_dir
projects_dir
artifacts_dir
resources_dir
```

### Pravilo

Nigdje ne hardkodovati:

```text
C:\Users\Nikola
/home/...
Desktop/
```

### Test

Koristiti temp path override.

Provjeriti:

- svi paths su `Path`;
- override radi;
- kreiranje direktorija je eksplicitna metoda, ne side effect importa.

### Acceptance

Import `paths.py` ne kreira filesystem side effect.

---

# 15. P0.08 — Logging foundation

## Fajlovi

```text
src/ai_campaign_studio/logging/config.py
src/ai_campaign_studio/logging/events.py
src/ai_campaign_studio/logging/redaction.py
tests/unit/logging/test_redaction.py
```

## Cilj

Centralni structured logging bez vendor lock-in biblioteke.

## `events.py`

Definisati kategorije:

```text
UI
APPLICATION
DOMAIN
AI
RENDER
DATABASE
SOURCE
BACKUP
SYSTEM
SECURITY
```

P0 aktivno koristi uglavnom:

```text
SYSTEM
DATABASE
SECURITY
APPLICATION
```

## `redaction.py`

Mora redigovati osjetljive vrijednosti po key-name heuristici:

```text
api_key
token
secret
authorization
password
credential
```

Rezultat:

```text
"<redacted>"
```

## `config.py`

Funkcija:

```text
configure_logging(settings, paths)
```

Mora:

- podesiti level;
- console handler;
- rotating file handler samo ako je jednostavno sa stdlib;
- koristiti UTF-8;
- ne logovati secrets.

## Test

Input:

```text
{"api_key": "abc123", "provider": "openai"}
```

Output/log-safe payload ne smije sadržati:

```text
abc123
```

## Acceptance

Redaction test je obavezan prije SecretStore rada.

---

# 16. P0.09 — Error taxonomy + common primitives

## Fajlovi

```text
src/ai_campaign_studio/domain/common/ids.py
src/ai_campaign_studio/domain/common/errors.py
src/ai_campaign_studio/domain/common/timestamps.py
```

---

## `ids.py`

Funkcija:

```text
new_id() -> str
```

Implementacija:

```text
UUID4 string
```

Ne uvoditi custom ULID/UUID7 library u P0 bez potrebe.

Može definisati `NewType` aliases samo ako olakšava type checking.

---

## `timestamps.py`

Funkcija:

```text
utc_now()
```

Mora vraćati timezone-aware UTC datetime.

Persistence serialization kasnije koristi ISO-8601.

Ne koristiti naive `datetime.now()`.

---

## `errors.py`

Definisati:

```text
AppError
DomainError
ApplicationError
InfrastructureError
ConfigurationError
RegistryError
SecretStoreError
DatabaseError
MigrationError
JobError
```

### Machine-readable `ErrorCode`

Foundation subset:

```text
CONFIGURATION_ERROR
REGISTRY_ERROR
SECRET_STORE_ERROR
DATABASE_ERROR
MIGRATION_ERROR
NETWORK_ERROR
RATE_LIMIT
PROVIDER_ERROR
INVALID_API_KEY
UI_BRIDGE_ERROR
UNKNOWN_ERROR
```

Ne implementirati još:

```text
MISSING_FACT
PROHIBITED_CLAIM
LAYOUT_VALIDATION_ERROR
```

kao aktivnu logiku.

Mogu se dodati kasnije kada feature postoji.

## Acceptance

Sve foundation exceptions imaju:

```text
error_code
human_message
technical_context?  # bez secrets
```

---

# 17. P0.10 — Architecture boundaries

## Fajl

```text
tests/architecture/test_import_boundaries.py
```

## Cilj

Automatski spriječiti arhitektonsko klizanje.

## Implementacija

Dovoljan je AST scan Python fajlova.

Ne uvoditi novu dependency-analysis biblioteku ako nije potrebna.

## Pravila

### `domain/`

Ne smije importovati:

```text
ai_campaign_studio.infrastructure
ai_campaign_studio.presentation
ai_campaign_studio.jobs
PySide6
PyQt6
pywebview
playwright
openai
anthropic
requests
Flask
```

### `application/`

Ne smije importovati:

```text
ai_campaign_studio.presentation
ai_campaign_studio.infrastructure
PySide6
pywebview
playwright
provider SDK
```

### `ports/`

Ne smije importovati infrastructure adaptere.

### `presentation/`

U P0 ne smije importovati provider SDK ili sqlite repository implementation.

## Obavezni meta-test

Privremeno u test fixture-u napraviti synthetic forbidden import i potvrditi da boundary checker pada.

Ne commitovati taj forbidden file.

## Acceptance

Boundary test:

```text
PASS
```

na realnom tree-u.

---

# 18. P0.11 — Localization EN/BHS

## Fajlovi

```text
src/ai_campaign_studio/localization/enums.py
src/ai_campaign_studio/localization/language_context.py
src/ai_campaign_studio/localization/translator.py
src/ai_campaign_studio/ports/localization.py
resources/i18n/en.json
resources/i18n/bhs.json
tests/unit/localization/test_language_context.py
tests/unit/localization/test_translator.py
tests/integration/localization/test_translation_resources.py
```

---

## `enums.py`

Definisati:

```text
AppLocale:
EN
BHS_LATIN

ContentLanguageFamily:
EN
BHS

BHSRegionalVariant:
NEUTRAL
BS
SR
HR

Script:
LATIN
```

Ne koristiti:

```text
BOSNIAN_UI
SERBIAN_UI
CROATIAN_UI
```

---

## `language_context.py`

Definisati immutable/validated:

```text
ContentLanguageContext
```

Polja:

```text
language_family
regional_variant
script
locale
preferred_terms
forbidden_terms
regional_vocabulary
tone_examples
```

### Invariants

```text
EN → regional_variant = NEUTRAL
BHS → regional_variant ∈ NEUTRAL, BS, SR, HR
Phase 0/1 → script = LATIN
```

Ne smije imati fact/provenance logiku.

---

## `ports/localization.py`

Protocol:

```text
TranslatorPort
```

Metode:

```text
set_locale(locale)
get_locale()
t(key, **params)
```

---

## `translator.py`

Framework-neutral implementation.

Mora:

```text
load en.json
load bhs.json
support runtime locale switch
support simple parameter interpolation
fallback BHS missing key → EN
log missing key
```

Ako nema ni EN key:

može vratiti:

```text
[missing:campaign.create]
```

i logovati warning.

Ne smije rušiti aplikaciju zbog jednog UI stringa.

---

## `en.json` i `bhs.json`

Početni foundation keys:

```text
app.title
app.starting
app.ready
settings.title
settings.language
settings.ai_providers
settings.api_key
settings.test_connection
settings.connected
settings.not_configured
common.save
common.cancel
common.close
common.retry
error.generic
error.configuration
error.database
```

Oba fajla moraju imati isti obavezni set ključeva.

---

## Testovi

### `test_language_context.py`

Provjeriti:

```text
EN + NEUTRAL valid
EN + BS invalid
BHS + NEUTRAL valid
BHS + BS valid
BHS + SR valid
BHS + HR valid
non-Latin invalid u Phase 0 modelu
```

### `test_translator.py`

Provjeriti:

```text
EN translation
BHS translation
runtime switch
fallback to EN
parameter interpolation
unknown key warning behavior
```

### `test_translation_resources.py`

Provjeriti:

```text
JSON valid
UTF-8
same required key set
čćšžđ survives
no duplicate keys
```

## Acceptance

```text
EN ↔ BHS
```

radi bez UI frameworka.

---

# 19. P0.12 — BHS regional-language resources

## Fajlovi

```text
resources/regional_language/bhs_neutral_v1.yaml
resources/regional_language/bhs_bs_v1.yaml
resources/regional_language/bhs_sr_v1.yaml
resources/regional_language/bhs_hr_v1.yaml
```

## Važno

Ovo NISU UI prevodi.

Koriste se kasnije za AI copy context.

## Minimalna schema

```yaml
language_family: BHS
regional_variant: BS
version: 1
preferred_terms: []
forbidden_terms: []
regional_vocabulary: []
notes: []
```

## Pravilo

Ne izmišljati desetine regionalnih razlika.

Ako nemamo potvrđenu razliku:

```text
ostaviti listu praznu
```

Umjesto lažne lingvističke baze.

## Validator

U `scripts/validate_resources.py` ili zajedničkom validatoru provjeriti:

```text
family = BHS
variant matches filename
version exists
lists are lists
UTF-8
```

## Acceptance

Sva 4 YAML fajla prolaze validation.

---

# 20. P0.13 — Channel / Platform / Format registry

## Fajlovi

```text
src/ai_campaign_studio/channels/enums.py
src/ai_campaign_studio/channels/definitions.py
src/ai_campaign_studio/channels/registry.py
src/ai_campaign_studio/ports/channels.py
resources/platforms/*.yaml
tests/unit/channels/test_registry.py
tests/integration/channels/test_platform_resources.py
```

---

## `enums.py`

Stabilni `Channel` enum:

```text
SOCIAL
EMAIL
WEB
PAID_AD
PRINT
DIRECT_MESSAGE
```

Ne praviti social platform enum.

---

## `definitions.py`

Definisati immutable Pydantic/dataclass modele:

### `TextConstraints`

Moguća polja:

```text
max_chars?
max_caption_chars?
max_title_chars?
supports_hashtags
supports_links
```

Sve opcionalno gdje nemamo pouzdan hard constraint.

### `VisualConstraints`

```text
supported_aspect_ratios[]
supports_static_image
supports_video
supports_carousel
```

### `FormatDefinition`

```text
code
display_name
required_fields[]
optional_fields[]
text_constraints
visual_constraints
enabled
```

### `PlatformDefinition`

```text
code
display_name
channel
supported_formats[]
content_rules[]
enabled
```

---

## `ports/channels.py`

`PlatformRegistryPort`:

```text
list_platforms(channel=None)
get_platform(code)
list_formats(platform_code)
get_format(platform_code, format_code)
```

---

## `registry.py`

Mora:

```text
load YAML files from resources/platforms
validate schema
normalize codes
reject duplicate platform code
reject duplicate format code within platform
reject unknown channel
reject supported format reference that does not exist
cache parsed registry after valid load
```

Ne smije:

```text
call web
call social API
hardcode Instagram behavior
contain Campaign logic
```

---

## Početne platform definicije

Kreirati:

```text
INSTAGRAM
FACEBOOK
LINKEDIN
X
TIKTOK
YOUTUBE
PINTEREST
THREADS
SNAPCHAT
```

## Važno

P0 registry ne mora tvrditi kompletna produkcijska ograničenja svih mreža.

Ako constraint nije potvrđen:

```yaml
max_chars: null
```

Ne izmišljati vrijednost.

P0 cilj je:

```text
registry architecture + schema
```

ne market knowledge database.

---

## Minimalni format examples

### Instagram

```text
FEED_POST
STORY
REEL
CAROUSEL
```

### Facebook

```text
FEED_POST
STORY
REEL
```

### LinkedIn

```text
PROFESSIONAL_POST
ARTICLE_LINK_POST
```

### X

```text
TEXT_POST
THREAD
IMAGE_POST
```

### TikTok

```text
SHORT_VIDEO
```

### YouTube

```text
SHORT
COMMUNITY_POST
VIDEO_METADATA
```

### Pinterest

```text
PIN
```

### Threads

```text
TEXT_POST
IMAGE_POST
```

### Snapchat

```text
STORY
```

Nije obavezno da Faza 1 implementira generatore za svaki format.

---

## Testovi

Provjeriti:

```text
9 YAML files load
all platform codes unique
all format codes unique per platform
all channels valid
unknown platform raises RegistryError
unknown format raises RegistryError
disabled item excluded by default list
adding a temporary YAML platform requires no Campaign Engine code
```

## Acceptance

Registry je potpuno data-driven.

---

# 21. P0.14 — AI Provider / Model Registry

## Fajlovi

```text
src/ai_campaign_studio/ai_registry/provider_models.py
src/ai_campaign_studio/ai_registry/model_profiles.py
src/ai_campaign_studio/ai_registry/registry.py
src/ai_campaign_studio/ports/ai_registry.py
resources/ai_providers/*.yaml
tests/unit/ai_registry/test_registry.py
tests/integration/ai_registry/test_provider_resources.py
```

---

## `provider_models.py`

### `AIProviderDefinition`

Polja:

```text
provider_code
display_name
adapter_type
requires_api_key
supports_model_discovery
base_url_mode
enabled
```

`base_url_mode`:

```text
FIXED
USER_CONFIGURABLE
NONE
```

### Početni provider codes

```text
OPENAI
ANTHROPIC
GOOGLE
DEEPSEEK
OPENROUTER
OPENAI_COMPATIBLE
```

---

## `model_profiles.py`

### `ModelCapability`

```text
TEXT_GENERATION
STRUCTURED_OUTPUT
VISION
IMAGE_GENERATION
TOOL_USE
```

### `ModelSource`

```text
DISCOVERED
REGISTRY
MANUAL
```

### `ModelProfile`

```text
provider_code
model_id
display_name
capabilities[]
context_window?
supports_temperature?
enabled
source
```

P0 ne mora imati realnu listu modela.

Model IDs se mijenjaju.

---

## `ports/ai_registry.py`

Definisati dva contracta.

### `AIProviderRegistryPort`

```text
list_providers()
get_provider(provider_code)
```

U P0 još NE zahtijevati live `test_connection()` implementaciju ako nema provider adaptera.

Ali definisati future-capability contract odvojeno:

```text
AIProviderConnectionPort
- test_connection(...)
- discover_models(...)
```

### `ModelRegistryPort`

```text
list_models(provider_code=None)
get_model(provider_code, model_id)
register_discovered_models(...)
register_manual_model(...)
resolve_default_text_model(...)
supports(...)
```

---

## `registry.py`

U P0 implementira:

```text
provider resource loader
provider validation
in-memory model registry
manual model registration
capability filtering
duplicate detection
```

Ne radi:

```text
network
API connection
provider SDK calls
```

To dolazi poslije gate-a.

---

## Provider YAML schema

Primjer:

```yaml
provider_code: OPENAI
display_name: OpenAI
adapter_type: openai
requires_api_key: true
supports_model_discovery: true
base_url_mode: FIXED
enabled: true
```

Za `OPENAI_COMPATIBLE`:

```yaml
provider_code: OPENAI_COMPATIBLE
display_name: OpenAI-compatible
adapter_type: openai_compatible
requires_api_key: true
supports_model_discovery: false
base_url_mode: USER_CONFIGURABLE
enabled: true
```

## Ne stavljati

```text
API keys
secret defaults
neprovjerene model IDs
```

u YAML.

---

## Testovi

Provjeriti:

```text
6 providers load
provider codes unique
base_url_mode valid
unknown provider raises RegistryError
manual model registration works
capability filter works
same provider/model duplicate rejected
no resource contains likely API key/token
```

## Acceptance

Provider/model izbor je arhitektonski moguć bez Campaign Engine zavisnosti.

---

# 22. P0.15 — SecretStore foundation

## Fajlovi

```text
src/ai_campaign_studio/ports/secrets.py
src/ai_campaign_studio/infrastructure/secrets/environment_secret_store.py
src/ai_campaign_studio/infrastructure/secrets/keyring_secret_store.py
tests/unit/secrets/test_secret_store.py
```

---

## `ports/secrets.py`

Protocol:

```text
SecretStorePort
```

Metode:

```text
get_secret(name) -> str | None
set_secret(name, value) -> None
delete_secret(name) -> None
```

---

## Secret naming convention

Koristiti:

```text
provider/<provider_code>/api_key
```

Primjer:

```text
provider/OPENAI/api_key
```

Ne koristiti model ID u secret name-u.

---

## `environment_secret_store.py`

Dev/test adapter.

Mapiranje:

```text
provider/OPENAI/api_key
→ AI_CAMPAIGN_STUDIO_OPENAI_API_KEY
```

`set_secret` može:

- biti read-only i jasno baciti `SecretStoreError`,
- ili držati test-only in-memory override.

Ne pisati automatski `.env`.

---

## `keyring_secret_store.py`

Production desktop adapter.

Koristi Python `keyring`.

Service name:

```text
AI Campaign Studio
```

Mora:

```text
get
set
delete
```

Ne logovati value.

---

## Testiranje

Ne pisati u stvarni korisnički keyring tokom unit testova.

Koristiti fake/mock keyring backend.

Provjeriti:

```text
set/get/delete
missing secret → None
secret never appears in logs
secret never appears in exception repr
```

## Acceptance

Nijedan secret nije u:

```text
SQLite
config.example.toml
resources YAML
logs
```

---

# 23. P0.16 — SQLite connection foundation

## Fajlovi

```text
src/ai_campaign_studio/ports/database.py
src/ai_campaign_studio/infrastructure/database/connection.py
tests/integration/database/test_connection.py
```

---

## `ports/database.py`

Foundation Protocol:

```text
DatabaseConnectionPort
```

Ne definirati još Brand/Campaign repository portove.

---

## `connection.py`

Funkcija/factory:

```text
create_connection(database_path)
```

Pravila:

```text
sqlite3
row_factory = sqlite3.Row
foreign_keys = ON
busy_timeout postavljen razumno
```

WAL mode:

može se uključiti ako test potvrdi da je potreban/bez problema.

Ne uvoditi preranu DB optimizaciju.

## Connection ownership

Ne praviti globalni mutable connection singleton.

Factory/connection manager mora jasno definisati lifecycle.

## Test

Temp DB:

```text
open
execute SELECT 1
close
re-open
```

Provjeriti:

```text
PRAGMA foreign_keys = 1
```

## Acceptance

DB connection je izolovan i testabilan.

---

# 24. P0.17 — Migration runner

## Fajlovi

```text
src/ai_campaign_studio/infrastructure/database/migrations.py
resources/migrations/0000_foundation.sql
tests/integration/database/test_migrations.py
```

---

## Migration convention

Filename:

```text
NNNN_name.sql
```

Primjer:

```text
0000_foundation.sql
```

---

## `schema_migrations`

Runner mora održavati tabelu:

```text
schema_migrations
- version INTEGER PRIMARY KEY
- name TEXT NOT NULL
- applied_at TEXT NOT NULL
- checksum TEXT NOT NULL
```

---

## `0000_foundation.sql`

Sadrži samo foundation state koji stvarno treba prije Campaign domaina.

Preporučene tabele:

```text
app_metadata
provider_configs
model_selections
```

### `app_metadata`

```text
key TEXT PRIMARY KEY
value TEXT NOT NULL
updated_at TEXT NOT NULL
```

### `provider_configs`

```text
provider_code TEXT PRIMARY KEY
configured INTEGER NOT NULL DEFAULT 0
validated INTEGER NOT NULL DEFAULT 0
credential_ref TEXT NULL
base_url TEXT NULL
updated_at TEXT NOT NULL
```

Ne postoji:

```text
api_key
token
secret
```

kolona.

### `model_selections`

```text
purpose TEXT PRIMARY KEY
provider_code TEXT NOT NULL
model_id TEXT NOT NULL
updated_at TEXT NOT NULL
```

Početni purpose kasnije:

```text
DEFAULT_TEXT
```

Ali P0 ne mora upisati izbor.

---

## `migrations.py`

Mora:

```text
discover SQL migration files
parse version/name
sort
calculate checksum
ensure schema_migrations
apply unapplied migrations in transaction
rollback on error
record applied migration
refuse modified already-applied migration if checksum differs
```

Ne koristiti:

```text
CREATE TABLE IF NOT EXISTS
```

kao zamjenu za migration tracking kroz cijeli sistem.

---

## Testovi

### Fresh DB

```text
0 → 0000
```

### Idempotency

Drugi run:

```text
0 novih migracija
```

### Failure rollback

Namjerno invalid migration u temp fixture:

```text
no partial apply
```

### Checksum mismatch

Promijenjen already-applied SQL:

```text
MigrationError
```

## Acceptance

Migration runner je pouzdan prije domain šeme.

---

# 25. P0.18 — Unit of Work / transaction foundation

## Fajl

```text
src/ai_campaign_studio/infrastructure/database/unit_of_work.py
tests/unit/database/test_unit_of_work.py
```

## Cilj

Kasniji use-caseovi ne trebaju direktno kontrolisati SQL transaction detalje.

## Foundation interface

```text
SqliteUnitOfWork
```

Context manager:

```text
with uow:
    ...
    uow.commit()
```

Ako exception:

```text
rollback
```

Ako `commit()` nije pozvan:

jasno definisati da li context auto-rollbacks.

Preporuka:

```text
explicit commit
otherwise rollback
```

## Ne sadržati

```text
brand_repository
campaign_repository
post_repository
```

u P0.

To se dodaje kada domain postoji.

## Test

```text
insert inside uow + commit → exists
insert + exception → absent
insert without commit → absent
```

## Acceptance

Transaction behavior je determinističan.

---

# 26. P0.19 — Foundation ports

## Cilj

Portovi moraju predstavljati stvarne boundary potrebe.

## Fajlovi

```text
ports/localization.py
ports/channels.py
ports/ai_registry.py
ports/secrets.py
ports/database.py
```

## Ne kreirati još

```text
TextGenerationPort
RendererPort
BrandRepositoryPort
CampaignRepositoryPort
ContentRepositoryPort
```

ako ih P0 ne koristi.

Oni dolaze u odgovarajućem business koraku Faze 1.

## Pravilo

Port:

- ne importuje infrastructure adapter;
- ne zna GUI;
- ne zna provider SDK.

## Acceptance

Architecture test potvrđuje smjer zavisnosti.

---

# 27. P0.20 — Framework-neutral JobManager

## Fajlovi

```text
src/ai_campaign_studio/jobs/models.py
src/ai_campaign_studio/jobs/events.py
src/ai_campaign_studio/jobs/cancellation.py
src/ai_campaign_studio/jobs/manager.py
tests/unit/jobs/test_cancellation.py
tests/unit/jobs/test_manager.py
```

---

## `models.py`

### `JobStatus`

```text
PENDING
RUNNING
CANCELLING
CANCELLED
SUCCEEDED
FAILED
```

### `JobState`

Polja:

```text
id
job_type
status
progress_current
progress_total
phase
message
error_code?
error_message?
started_at?
finished_at?
```

---

## `events.py`

### `JobEventType`

```text
CREATED
STARTED
PROGRESS
PHASE_CHANGED
SUCCEEDED
FAILED
CANCELLATION_REQUESTED
CANCELLED
```

### `JobEvent`

```text
job_id
event_type
timestamp
payload
```

---

## `cancellation.py`

`CancellationToken`:

```text
request_cancel()
is_cancel_requested()
raise_if_cancelled()
```

Thread-safe.

Ne zavisi od Qt-a.

---

## `manager.py`

P0 implementacija može koristiti:

```text
ThreadPoolExecutor
```

Mora podržati:

```text
submit(job_type, callable)
get_state(job_id)
cancel(job_id)
subscribe(callback) / event callback
shutdown()
```

Ne treba:

```text
process pool
Playwright subprocess
AI retry
```

još.

---

## Testovi

### Success

Job:

```text
PENDING → RUNNING → SUCCEEDED
```

### Failure

Exception:

```text
FAILED
```

i typed error info.

### Cancellation

Cooperative callable provjerava token:

```text
RUNNING → CANCELLING → CANCELLED
```

### Event order

Provjeriti očekivani event sequence.

## Acceptance

JobManager radi bez GUI frameworka.

---

# 28. P0.21 — Framework-neutral Presentation contracts/state

## Fajlovi

```text
src/ai_campaign_studio/presentation/contracts.py
src/ai_campaign_studio/presentation/state.py
src/ai_campaign_studio/presentation/ui_models.py
```

## Cilj

Definisati shared Presentation boundary prije PySide6 vs pywebview gate-a.

---

## `state.py`

U P0 samo foundation state.

### `AppRuntimeState`

```text
app_locale
startup_status
database_ready
resources_ready
configured_providers[]
default_text_model?
current_job?
notifications[]
```

Ne sadržati još:

```text
selected_campaign
selected_post
campaign_plan
```

jer business domain nije implementiran.

---

## `ui_models.py`

Framework-neutral DTO:

### `NotificationUiModel`

```text
level
message_key
params
technical_details?
```

### `ProviderStatusUiModel`

```text
provider_code
display_name
configured
validated
model_count
```

Ne koristi Qt model klase.

---

## `contracts.py`

Foundation facade/protocol može sadržati:

```text
set_app_locale(locale)
get_app_state()
list_ai_providers()
get_provider_status(provider_code)
run_health_check()
cancel_job(job_id)
```

Ne implementirati Campaign UI akcije u P0.

---

## Zabranjeno

```text
QObject
Signal
Qt enums
JavaScript bridge object
Flask route
```

u shared Presentation folderu.

## Acceptance

I PySide i pywebview kandidat kasnije mogu koristiti iste contracte.

---

# 29. P0.22 — Bootstrap / Composition Root

## Fajl

```text
src/ai_campaign_studio/bootstrap.py
tests/integration/startup/test_bootstrap_health.py
```

## Cilj

Jedino mjesto gdje se povezuju konkretni foundation adapteri.

## `FoundationContainer`

Može biti dataclass sa:

```text
settings
paths
translator
platform_registry
provider_registry
model_registry
secret_store
database_factory
migration_runner
job_manager
```

## Build sequence

```text
load Settings
      ↓
resolve AppPaths
      ↓
configure logging
      ↓
load Translator resources
      ↓
load Platform Registry
      ↓
load AI Provider Registry
      ↓
select SecretStore adapter
      ↓
prepare DB connection
      ↓
run migrations
      ↓
create JobManager
      ↓
return container
```

## SecretStore adapter selection

Development/test može koristiti:

```text
EnvironmentSecretStore
```

Production desktop:

```text
KeyringSecretStore
```

Ali ne pristupati provider secretu tokom običnog boot-a.

## Bootstrap NE smije

- zvati OpenAI;
- testirati internet;
- pokretati Chromium;
- pokretati GUI;
- generisati kampanju.

## Test

Sa temp paths:

```text
build foundation container
database exists
migration applied
platform registry loaded
provider registry loaded
translator loaded
no network called
```

## Acceptance

Bootstrap radi potpuno offline.

---

# 30. P0.23 — Health-check entrypoint

## Fajlovi

```text
src/ai_campaign_studio/main.py
scripts/health_check.py
```

## `main.py`

Podržati:

```text
python -m ai_campaign_studio.main --health-check
```

## Health result

Machine-readable dict/JSON:

```json
{
  "status": "ok",
  "python": "...",
  "database": "ok",
  "migrations": "ok",
  "translations": "ok",
  "platform_registry": "ok",
  "provider_registry": "ok",
  "secret_store": "available",
  "ui_framework": "not_selected"
}
```

Ne ispisivati:

- API key;
- provider credential;
- filesystem private content.

## Exit codes

```text
0 = all foundation checks pass
1 = one or more checks fail
```

## `scripts/health_check.py`

Samo praktičan wrapper ako je potreban.

Ne duplicirati health logic.

## Acceptance

Health check radi na čistom setupu bez API ključa.

---

# 31. P0.24 — Resource validators

## Fajl

```text
scripts/validate_resources.py
```

Bolje je da validaciona logika bude u reusable Python modulu, a script samo entrypoint.

Ako validator postaje dovoljno velik, kreirati:

```text
src/ai_campaign_studio/resources_validation.py
```

## Provjeriti

### i18n

```text
valid JSON
UTF-8
required key parity
BHS diacritics
```

### regional language

```text
valid YAML
family/variant/version
```

### platforms

```text
valid schema
unique codes
valid channels
valid formats
```

### AI providers

```text
valid schema
unique provider codes
no secret-like fields
```

### migrations

```text
filename format
unique versions
ordered
checksum readable
```

## Command

```text
python scripts/validate_resources.py
```

## Acceptance

Exit code 0.

---

# 32. P0.25 — CI quality gate

## Fajl

```text
.github/workflows/ci.yml
```

## Cilj

Svaki push/PR provjerava foundation.

## CI koraci

```text
checkout
setup Python 3.12
install -e ".[dev]"
ruff check
mypy src
pytest
resource validation
health check sa temp/data override
```

## Ne koristiti live services

CI ne smije zahtijevati:

```text
OpenAI key
Anthropic key
internet API
Playwright browser
desktop GUI
real OS keyring
```

Za keyring koristiti test/fake behavior.

## Acceptance

CI YAML sintaktički validan i lokalne ekvivalentne komande prolaze.

Ako GitHub Actions nije dio repo workflowa, zadržati task kao preporučeni gate, ali ne uvoditi drugu CI platformu bez potrebe.

---

# 33. P0.26 — Security / no-secret checks

## Cilj

Spriječiti API key leak prije nego aplikacija uopšte počne koristiti AI.

## Test/scan

Agent treba pretražiti:

```text
sk-
api_key=
Authorization:
Bearer 
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
```

u tracked fajlovima.

Ne tretirati `config.example.toml` placeholder kao stvarni secret.

## `.gitignore`

Mora pokriti:

```text
.env
.env.*
```

ali može imati:

```text
!.env.example
```

ako se kasnije uvede.

## Provider YAML

Ne smije sadržati credential polja sa vrijednostima.

## SQLite migration

Ne smije imati:

```text
api_key TEXT
secret TEXT
token TEXT
```

## Logging

Redaction test green.

## Acceptance

```text
NO CONFIRMED SECRET IN TRACKED FILES
```

---

# 34. P0.27 — Full foundation verification

Agent sada pokreće sve.

## Obavezne komande

```text
python -m ruff check .
python -m mypy src
python -m pytest -q
python scripts/validate_resources.py
python -m ai_campaign_studio.main --health-check
```

Ako postoji coverage:

```text
python -m pytest --cov=ai_campaign_studio --cov-report=term-missing
```

Coverage broj nije gate sam po sebi u P0.

Bitnije je da kritični foundation moduli imaju test.

## Provjeriti Git status

```text
git status --short
```

Ne smije biti:

- generated DB;
- logs;
- `.venv`;
- cache;
- secrets;

kao tracked kandidat.

---

# 35. P0.28 — P0 Gate report

## Fajl

```text
artifacts/phase0_foundation_gate.json
```

Ovo je machine-readable artefakt, ne još jedan `.md`.

## Schema

```json
{
  "phase": "implementation-phase-0",
  "status": "PASS",
  "checks": {
    "package_import": true,
    "ruff": true,
    "mypy": true,
    "pytest": true,
    "architecture_boundaries": true,
    "translations": true,
    "regional_language_resources": true,
    "platform_registry": true,
    "provider_registry": true,
    "secret_store": true,
    "database_connection": true,
    "migrations": true,
    "unit_of_work": true,
    "job_manager": true,
    "bootstrap": true,
    "health_check": true,
    "no_secrets_detected": true
  },
  "ui_framework": "NOT_SELECTED",
  "campaign_engine_implemented": false,
  "website_ingestion_implemented": false,
  "notes": []
}
```

Ako nešto nije prošlo:

```text
status = FAIL
```

Ne stavljati `PASS` sa `false` ključnim checkom.

---

# 36. P0.29 — Foundation commit

Tek nakon P0 gate PASS.

Preporučeni commit:

```text
feat(core): establish phase-0 project foundation
```

Commit treba sadržati:

- package structure;
- config;
- logging;
- common primitives;
- localization;
- registries;
- secrets;
- DB foundation;
- jobs;
- presentation contracts;
- bootstrap;
- tests;
- CI.

Ne miješati prvi Campaign feature u isti commit.

---

# 37. P0.30 — STOP

Ovo je obavezni STOP.

Agent NE nastavlja automatski sa:

```text
Brand
Facts
CampaignPlan
ContentPiece
OpenAI generation
GUI
renderer
```

dok nije potvrđeno:

```text
P0-GATE = PASS
```

Nakon toga se prelazi na naredni implementacioni blok iz:

```text
AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md
```

Početna tačka naredne faze treba biti:

```text
Domain business models
```

jer foundation je već napravljen.

---

# 38. Precizna dependency pravila nakon P0

Dozvoljeno:

```text
domain/common
    → stdlib only

localization
    → stdlib + Pydantic/YAML where needed

channels
    → stdlib + Pydantic/YAML

ai_registry
    → stdlib + Pydantic/YAML

ports
    → domain/common + foundation models

infrastructure
    → ports + foundation models + external libs

jobs
    → domain/common errors + stdlib concurrency

presentation
    → localization/channels/ai_registry DTO/contracts
    → jobs state
```

Zabranjeno:

```text
domain → infrastructure
domain → presentation
application → infrastructure concrete adapters
presentation → sqlite3 implementation
presentation → keyring implementation
presentation → provider SDK
channels → Campaign domain
ai_registry → Campaign domain
```

---

# 39. Naming conventions

## Python

Fajlovi:

```text
snake_case.py
```

Klase:

```text
PascalCase
```

Functions:

```text
snake_case
```

Enums:

```text
PascalCase
```

Enum values:

```text
UPPER_SNAKE_CASE
```

## Resource codes

Platform:

```text
INSTAGRAM
FACEBOOK
X
```

Format:

```text
FEED_POST
SHORT_VIDEO
TEXT_POST
```

Provider:

```text
OPENAI
ANTHROPIC
GOOGLE
```

Translation keys:

```text
campaign.create
settings.ai_providers
error.database
```

Ne miješati:

```text
camelCase
snake_case
random-human-label
```

za canonical codes.

---

# 40. Data serialization rules

## JSON

- UTF-8;
- `ensure_ascii = false` kada se serializuje BHS sadržaj;
- stable indentation samo za human-readable resources/exports.

## YAML

Koristi se za:

```text
platform definitions
provider definitions
regional language rules
```

Ne za runtime mutable state.

## SQLite JSON fields

Dolaze kasnije kada domain postoji.

Foundation provider config ne čuva secret JSON blob.

---

# 41. Threading rules u P0

JobManager smije koristiti thread pool.

SQLite connection:

- ne dijeliti connection object nasumično između threadova;
- svaki task/use-case kasnije dobija jasno definisan connection/UoW lifecycle.

UI thread:

još ne postoji kao konkretan framework.

Ne uvoditi:

```text
QThread
asyncio event loop
process pool
```

u foundation bez potrebe.

---

# 42. Startup behavior nakon P0

Normalan startup foundation treba moći:

```text
load config
resolve paths
configure logs
validate/load resources
open DB
run migrations
load registries
create job manager
report ready
```

Ne treba:

```text
connect to AI provider
ask for API key
open UI
crawl website
```

Health check mora raditi potpuno offline.

---

# 43. API provider UX — šta P0 priprema, a šta NE radi

P0 priprema:

```text
provider registry
model registry
secret store
provider status UI model
provider config DB table
```

P0 NE radi:

```text
OpenAI Test Connection
Anthropic Test Connection
Gemini Test Connection
DeepSeek Test Connection
OpenRouter Test Connection
model API discovery
```

To se implementira odmah nakon foundation gate-a u Fazi 1 provider blocku.

Razlog:

prvo mora postojati stabilan contract + secret handling.

---

# 44. Social platform support — šta P0 priprema, a šta NE radi

P0 priprema:

```text
Channel
PlatformDefinition
FormatDefinition
registry
9 initial social platform resource files
```

P0 NE radi:

```text
Instagram generator
TikTok video script generator
X thread generator
YouTube metadata generator
```

To je business generation logika.

---

# 45. Localization — šta P0 priprema, a šta NE radi

P0 priprema:

```text
EN/BHS UI resource engine
runtime locale switch
BHS regional context types
regional rule resources
```

P0 NE radi:

```text
AI regional copy generation
automatic language detection
translation of user content
Cyrillic support
```

---

# 46. Database — šta P0 priprema, a šta NE radi

P0 priprema:

```text
connection
migration runner
schema migrations tracking
provider config foundation
model selection foundation
UoW transaction behavior
```

P0 NE radi:

```text
Brand tables
Fact tables
Campaign tables
Content tables
Visual tables
Telemetry tables
```

Te tabele se uvode zajedno sa stvarnim domain modelima.

Ovo sprečava da DB schema prethodi domain dizajnu.

---

# 47. Logging — zabranjena ponašanja

Ne logovati:

```text
full API key
Authorization header
password
secret value
full environment dump
full config object ako može sadržati secret
```

Ne koristiti:

```text
print(settings)
```

u production code-u.

Health check može prikazati:

```text
provider configured: true/false
```

ali ne secret.

---

# 48. Tests — princip

Svaki P0 task koji uvodi runtime ponašanje mora imati test.

Ne traži se test za:

```text
prazan __init__.py
```

Traži se test za:

```text
registry
translator
migration runner
JobManager
SecretStore
bootstrap
```

Testovi moraju koristiti:

```text
tmp_path
fake adapters
mock keyring
offline behavior
```

Ne smiju koristiti pravi provider API.

---

# 49. Ne uvoditi framework "za svaki slučaj"

U P0 eksplicitno NE uvoditi:

```text
dependency injection framework
event-bus framework
plugin framework
ORM
Alembic
SQLAlchemy
Pydantic Settings library ako običan Pydantic + TOML loader dovoljan
React
Vue
Svelte
Electron
Docker
Redis
Celery
FastAPI
Flask
```

Ako se kasnije pojavi stvaran problem, odluka se ponovo otvara.

---

# 50. P0 acceptance matrix

| Kod | Provjera | Mora biti |
|---|---|---|
| P0-A1 | package import | PASS |
| P0-A2 | editable install | PASS |
| P0-A3 | Ruff | PASS |
| P0-A4 | Mypy | PASS |
| P0-A5 | Pytest | PASS |
| P0-A6 | architecture boundaries | PASS |
| P0-A7 | path handling | PASS |
| P0-A8 | log redaction | PASS |
| P0-A9 | EN/BHS translator | PASS |
| P0-A10 | regional BHS resources | PASS |
| P0-A11 | 9 social platform definitions | PASS |
| P0-A12 | 6 provider definitions | PASS |
| P0-A13 | SecretStore contract | PASS |
| P0-A14 | DB open/close | PASS |
| P0-A15 | migration runner | PASS |
| P0-A16 | migration rollback | PASS |
| P0-A17 | migration checksum | PASS |
| P0-A18 | UoW commit/rollback | PASS |
| P0-A19 | JobManager success/fail/cancel | PASS |
| P0-A20 | framework-neutral Presentation state | PASS |
| P0-A21 | offline bootstrap | PASS |
| P0-A22 | resource validation | PASS |
| P0-A23 | health-check | PASS |
| P0-A24 | no secret in tracked files | PASS |
| P0-A25 | UI framework selected | MUST BE NO |
| P0-A26 | Campaign Engine implemented | MUST BE NO |
| P0-A27 | Website Ingestion implemented | MUST BE NO |

---

# 51. Premortem za Implementation Phase 0

## R-P0-1 — Agent prerano krene praviti Campaign features

Signal:

```text
domain/campaign/entities.py
```

se pojavljuje prije P0 gate-a.

Akcija:

```text
STOP
vrati task u scope
```

## R-P0-2 — Agent veže Presentation za Qt

Signal:

```text
from PySide6...
```

u `presentation/`.

Akcija:

architecture gate mora pasti.

## R-P0-3 — API secret završi u config/SQLite

Signal:

kolona/polje:

```text
api_key
```

u tracked runtime config/schema.

Akcija:

FAIL P0 gate.

## R-P0-4 — Registry postane hardcoded Python switch

Signal:

```python
if platform == "instagram":
...
elif platform == "tiktok":
...
```

u centralnom registryju.

Akcija:

prebaciti platform-specific metadata u YAML definicije.

## R-P0-5 — Previše placeholder arhitekture

Signal:

desetine fajlova sa:

```text
TODO
pass
NotImplemented
```

bez testiranog contracta.

Akcija:

obrisati/ne kreirati dok nije potreban.

## R-P0-6 — Migration sistem nije stvaran

Signal:

svaki startup radi:

```text
CREATE TABLE IF NOT EXISTS ...
```

bez version/checksum trackinga.

Akcija:

ne prolazi P0 gate.

## R-P0-7 — Foundation zahtijeva internet

Signal:

health check pada bez AI API pristupa.

Akcija:

FAIL.

Foundation mora biti offline.

---

# 52. Agentov završni odgovor korisniku nakon P0

Agent treba kratko javiti:

```text
P0-GATE: PASS / FAIL

Potvrđeno:
- ...
- ...

Nisam potvrdio:
- ...

Nije implementirano namjerno:
- Campaign Engine
- GUI framework
- Website Ingestion

Sljedeći korak:
- Domain business models iz Faze 1
```

Ne tvrditi:

```text
"aplikacija radi"
```

jer tada radi samo foundation.

Ispravno:

```text
"Project foundation je postavljen i testiran."
```

---

# 53. Precizna granica prema narednoj fazi

Naredna faza smije početi tek kada postoji stabilan foundation.

Prvi business fajlovi koji tada mogu nastati:

```text
domain/brand/
domain/facts/
domain/campaign/
domain/content/
domain/visual/
```

i tek tada:

```text
ApprovedFact
BrandSnapshot
CampaignBrief
CampaignPlan
CampaignItem
ContentPiece
Claim
Revision
Visual contracts
```

To je **Phase 1 Domain Contract implementation**, ne dio ovog dokumenta.

---

# 54. Konačna instrukcija agentu

U Implementation Phase 0 ne pokušavaš dokazati kvalitet AI kampanje.

Dokazuješ da projekat ima temelj koji:

```text
ne zaključava UI framework
ne zaključava AI providera
ne zaključava social platformu
ne zaključava jezik na EN
ne gubi BHS regionalni kontekst
ne čuva secrets pogrešno
ne veže business logic za SQLite
ne dopušta architecture drift
može raditi offline
može se testirati deterministički
```

Ako je sve to potvrđeno:

```text
P0-GATE = PASS
```

i tek tada ideš dalje.

**Ne preskači gate. Ne širi scope. Ne kreiraj business feature prije foundationa.**
