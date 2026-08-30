---
task_id: ACS-P0-002
phase: P0
title: "Config/logging/common + architecture boundaries"
risk: HIGH
coordinator: claude
implementer: pi
reviewers: [codex, claude]
status: "OPEN — contract written before code"
created_at: 2026-08-30
dependencies: [ACS-P0-001]
allowed_paths:
  - src/ai_campaign_studio/__init__.py
  - src/ai_campaign_studio/main.py
  - src/ai_campaign_studio/bootstrap.py
  - src/ai_campaign_studio/config/__init__.py
  - src/ai_campaign_studio/config/settings.py
  - src/ai_campaign_studio/config/paths.py
  - src/ai_campaign_studio/logging/__init__.py
  - src/ai_campaign_studio/logging/config.py
  - src/ai_campaign_studio/logging/events.py
  - src/ai_campaign_studio/logging/redaction.py
  - src/ai_campaign_studio/domain/__init__.py
  - src/ai_campaign_studio/domain/common/__init__.py
  - src/ai_campaign_studio/domain/common/ids.py
  - src/ai_campaign_studio/domain/common/errors.py
  - src/ai_campaign_studio/domain/common/timestamps.py
  - src/ai_campaign_studio/application/__init__.py
  - src/ai_campaign_studio/ports/__init__.py
  - src/ai_campaign_studio/presentation/__init__.py
  - config.example.toml
  - tests/
forbidden_paths:
  - src/ai_campaign_studio/domain/brand/
  - src/ai_campaign_studio/domain/campaign/
  - src/ai_campaign_studio/domain/content/
  - src/ai_campaign_studio/infrastructure/
  - src/ai_campaign_studio/localization/
  - src/ai_campaign_studio/channels/
  - src/ai_campaign_studio/ai_registry/
  - src/ai_campaign_studio/jobs/
  - presentation_qt/
  - presentation_webview/
gitnexus_required: true
adversarial_required: true
gitnexus:
  required: true
  repository: "H:\\AI Campaing Studio"
  worktree: "H:\\AI Campaing Studio (main, pre-branch pre-impact)"
  branch: main
  head: 1725aaa
  index_status: up-to-date (indexed at 1725aaa)
  targets:
    - symbol: "src/ai_campaign_studio/bootstrap.py (Bootstrap, create_bootstrap)"
      upstream_risk: LOW
      upstream_count: 2
      downstream_notes: "no outgoing deps yet (empty class)"
      affected_processes: []
    - symbol: "src/ai_campaign_studio/main.py (main)"
      upstream_risk: LOW
      upstream_count: 1
      downstream_notes: "only caller of create_bootstrap; only entrypoint"
      affected_processes: []
  scope_fit: PASS
  unknowns: []
---

# Kontekst

Ovo je drugi coding task Implementation Phase 0, prvi nakon merge-a ACS-P0-001.
Repo trenutno ima samo `__init__.py`, `main.py`, `bootstrap.py` (prazan
composition root) i `tests/test_foundation.py`.

Prije koda implementer mora pročitati:

```text
AGENTS.md
CLAUDE.md
docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md
.agent/CURRENT_STATE.md
.agent/PROJECT_MAP.md
.agent/TASK_ROUTING.md
AI_Campaign_Studio_Implementation_Phase_0_v1_1_Agent_Workflow_Integrated.md
  sekcije 13–17 (P0.06–P0.10)
```

GitNexus pre-impact je već urađen od strane koordinatora (vidi `gitnexus:` blok
iznad) — `bootstrap.py`/`create_bootstrap`/`main` imaju mali, poznat blast
radius (samo `main.py` i postojeći testovi). `scope_fit: PASS`.

# Objective

Dodati config/paths/logging/error-taxonomy foundation i automatski
architecture-boundary test, bez ijedne business/domain feature
implementacije i bez GUI/provider SDK zavisnosti.

# Implementation steps (P0.06–P0.10)

## P0.06 — Package bootstrap

1. `src/ai_campaign_studio/__init__.py`: opciono dodati `__version__`. Ne
   re-eksportovati cijelu aplikaciju.
2. `main.py`: dodati minimalni startup option parsing i podršku za
   `--health-check` flag (health-check = kreirati bootstrap i vratiti exit
   code 0 ako uspije, ne pokretati GUI). Zadržati `main()` kao entrypoint
   koji vraća exit code.
3. `bootstrap.py`: proširiti `Bootstrap`/`create_bootstrap()` da sklopi samo
   ono što ovaj task stvarno pravi — `Settings`, `Paths`, `Logger` (preko
   `configure_logging`). NE referencirati `Translator`, `PlatformRegistry`,
   `AIProviderRegistry`, `SecretStore`, `DatabaseConnectionFactory`,
   `MigrationRunner`, `JobManager` — ti dolaze u ACS-P0-003..007 i bootstrap
   se tada inkrementalno proširuje. Ne postati service locator: `Bootstrap`
   nosi samo ono što je ovim taskom stvarno sastavljeno, bez generičkog
   registry/container obrasca.
4. Acceptance: `bootstrap.py` se importuje i instancira bez API ključa, mreže,
   GUI-ja ili browsera.

## P0.07 — Config + paths

5. `src/ai_campaign_studio/config/settings.py`: `AppSettings` (Pydantic
   model ili ekvivalent) sa poljima `app_name`, `environment`
   (`development|test|production`), `log_level`, `app_locale` (default
   `BHS_LATIN`), `database_filename`, opciono `resource_dir_override`,
   `data_dir_override`. NE sadržati `api_key`/provider secrets/campaign
   defaults/hardkodovanu model listu.
6. `src/ai_campaign_studio/config/paths.py`: `AppPaths` preko `platformdirs`
   + `pathlib.Path`, daje `data_dir`, `database_dir`, `database_path`,
   `cache_dir`, `logs_dir`, `projects_dir`, `artifacts_dir`, `resources_dir`.
   Nigdje hardkodovan korisnički path. Kreiranje direktorija mora biti
   eksplicitna metoda, ne side effect importa.
7. `config.example.toml`: uskladiti sa `AppSettings` poljima (već postoji
   osnovni fajl iz ACS-P0-001 — dopuniti, ne duplirati konfiguracioni sistem).

## P0.08 — Logging foundation

8. `src/ai_campaign_studio/logging/events.py`: kategorije `UI, APPLICATION,
   DOMAIN, AI, RENDER, DATABASE, SOURCE, BACKUP, SYSTEM, SECURITY`.
9. `src/ai_campaign_studio/logging/redaction.py`: redaguje vrijednosti čiji
   key-name (case-insensitive) sadrži `api_key`, `token`, `secret`,
   `authorization`, `password`, `credential` → `"<redacted>"`.
10. `src/ai_campaign_studio/logging/config.py`: `configure_logging(settings,
    paths)` — level, console handler, rotating file handler samo ako je
    trivijalno sa stdlib, UTF-8, nikad ne logovati secrets direktno (koristiti
    redaction).

## P0.09 — Error taxonomy + common primitives

11. `src/ai_campaign_studio/domain/common/ids.py`: `new_id() -> str` (UUID4).
    Ne uvoditi custom ULID/UUID7 biblioteku.
12. `src/ai_campaign_studio/domain/common/timestamps.py`: `utc_now()` —
    timezone-aware UTC `datetime`, ne naivni `datetime.now()`.
13. `src/ai_campaign_studio/domain/common/errors.py`: `AppError`,
    `DomainError`, `ApplicationError`, `InfrastructureError`,
    `ConfigurationError`, `RegistryError`, `SecretStoreError`,
    `DatabaseError`, `MigrationError`, `JobError`; svaka nosi `error_code`
    (foundation `ErrorCode` subset: `CONFIGURATION_ERROR`, `REGISTRY_ERROR`,
    `SECRET_STORE_ERROR`, `DATABASE_ERROR`, `MIGRATION_ERROR`,
    `NETWORK_ERROR`, `RATE_LIMIT`, `PROVIDER_ERROR`, `INVALID_API_KEY`,
    `UI_BRIDGE_ERROR`, `UNKNOWN_ERROR`), `human_message`, opciono
    `technical_context` (bez secrets). Ne implementirati još
    `MISSING_FACT`/`PROHIBITED_CLAIM`/`LAYOUT_VALIDATION_ERROR`.

## P0.10 — Architecture boundaries

14. `src/ai_campaign_studio/application/__init__.py`,
    `src/ai_campaign_studio/ports/__init__.py`,
    `src/ai_campaign_studio/presentation/__init__.py`: prazni paketi —
    ovo su arhitektonski seam-ovi (Clean/Hexagonal slojevi), ne premature
    business moduli, potrebni da `tests/architecture/test_import_boundaries.py`
    ima šta da skenira. Ne stavljati logiku u njih.
15. `tests/architecture/test_import_boundaries.py`: AST-scan (bez nove
    dependency-analysis biblioteke) koji provjerava:
    - `domain/` ne importuje `infrastructure`, `presentation`, `jobs`,
      `PySide6`, `PyQt6`, `pywebview`, `playwright`, `openai`, `anthropic`,
      `requests`, `Flask`;
    - `application/` ne importuje `presentation`, `infrastructure`,
      `PySide6`, `pywebview`, `playwright`, provider SDK;
    - `ports/` ne importuje infrastructure adaptere;
    - `presentation/` (paket, ne `presentation_qt`/`presentation_webview`)
      ne importuje provider SDK ni sqlite repository implementaciju.
    Napomena: `presentation_qt/`/`presentation_webview/` na repo root-u su
    van scope-a ovog boundary testa (ne postoje još, forbidden ovim taskom).

# Acceptance

- [ ] `python -m ai_campaign_studio.main --health-check` vraća exit code 0.
- [ ] `AppSettings`/`AppPaths` importuju se bez filesystem side effect-a osim
      eksplicitnog poziva za kreiranje direktorija.
- [ ] `tests/unit/config/test_settings.py`, `tests/unit/config/test_paths.py`
      postoje i koriste temp path override za `AppPaths`.
- [ ] `tests/unit/logging/test_redaction.py`: payload sa `api_key: "abc123"`
      posle redakcije ne sadrži `"abc123"`.
- [ ] `tests/architecture/test_import_boundaries.py` PASS na realnom tree-u.
- [ ] `python -m pytest -q` prolazi (svi novi + postojeći testovi).
- [ ] `python -m ruff check .` prolazi.
- [ ] `python -m mypy src` prolazi.
- [ ] nema PySide6/pywebview/provider SDK/Flask/FastAPI dependency-ja.
- [ ] nema Campaign/Brand/Content business implementacije.
- [ ] `bootstrap.py` i dalje nije service locator (samo Settings+Paths+Logger
      wiring, ništa generičko).
- [ ] `config.example.toml` odgovara `AppSettings` poljima.

# Adversarial test (obavezno — adversarial_required: true)

Za `tests/architecture/test_import_boundaries.py`:

1. test tvrdi da dokazuje da `domain/` ne importuje `infrastructure`/GUI/provider SDK;
2. privremeno (u test-only fixture-u, NE commitovati) dodati synthetic fajl u
   `domain/` koji importuje npr. `PySide6` ili
   `ai_campaign_studio.infrastructure`;
3. test mora FAIL na toj varijanti;
4. ukloniti synthetic fajl;
5. test mora PASS na realnom tree-u;
6. dokumentovati oba outputa (FAIL pa PASS) u implementer evidence.

Isto za redaction: dokumentovati da test FAIL-uje ako `redact()` privremeno
postane no-op (vraća payload nepromijenjen), pa PASS-uje sa stvarnom
implementacijom.

# Verification

```bash
python --version
python -c "import sys; print(sys.executable)"
python -c "import ai_campaign_studio"
python -m pytest -q
python -m ruff check .
python -m mypy src
python -m ai_campaign_studio.main --health-check
git status --short
```

# Review focus — Codex

- da li `test_import_boundaries.py` stvarno pada na poznato lošoj varijanti
  (adversarial dokaz), ne samo da prolazi na dobrom stanju;
- da li redaction test pokriva sve navedene key-name heuristike, ne samo
  `api_key`;
- da li `AppPaths`/`AppSettings` testovi koriste stvaran temp override, ne
  mock koji sakriva side effect;
- da li je neka zabranjena dependency ušla direktno ili tranzitivno;
- da li `bootstrap.py` proširenje uvodi skriveni I/O ili mrežni poziv pri
  importu.

# Review focus — Claude

- da li `domain/common/` ostaje čist (bez uvoza infrastructure/application/
  presentation);
- da li `bootstrap.py` i dalje NIJE service locator/business container —
  samo eksplicitno wiring ono što ovaj task stvarno pravi;
- da li su `application/`, `ports/`, `presentation/` zaista prazni seam-ovi
  bez logike (ne premature business struktura);
- da li `config/paths.py` zaista nema hardkodovan korisnički path i da li je
  kreiranje direktorija eksplicitno, ne side effect importa;
- integracija sa GitNexus pre-impact nalazom (bootstrap/main upstream risk
  LOW) — da li stvarni diff ostaje u tom očekivanom obimu ili je blast radius
  širi nego što je najavljeno.

# Rollback

Ovo je HIGH task tokom foundation paketa (architecture boundaries +
bootstrap/composition root + config/path contracts). Ako review otkrije da
`test_import_boundaries.py` ne dokazuje invariant (prolazi i na lošoj
varijanti), ili da `bootstrap.py` postaje service locator: NE spajati.
Implementer ispravlja u istoj branch, bez proširenja scope-a. Ako je
otkriven scope gap koji zahtijeva novi simbol van `allowed_paths`, prijaviti
`OUT_OF_SCOPE_FINDING`, ne širiti tiho.

# Dependency baseline

Zavisi od ACS-P0-001 (merged, `def4ea1` na `main`, potvrđeno
`git log -1 --oneline main`). Ne granati sa starijeg main-a.

# Coordination

Nema paralelnog P0 coding taska prije merge-a ACS-P0-002 (003–006 ne granaju
dok 002 nije merged).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-P0-002-config-boundaries
Branch:   task/ACS-P0-002-config-boundaries
Base:     main @ 1725aaa
```

Nakon merge-a:

```text
post-merge gate
GitNexus detect-changes (scope compare, base-ref main) prije reviewa
GitNexus re-index poslije merge-a
CURRENT_STATE update
unblock ACS-P0-003/004/005/006 (provjeriti allowed_paths disjoint prije
paralelnog pokretanja)
```
