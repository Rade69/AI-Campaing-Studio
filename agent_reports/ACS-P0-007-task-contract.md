---
task_id: ACS-P0-007
phase: P0
title: "JobManager + Presentation contracts/state + Bootstrap wiring + Health-check"
risk: HIGH
coordinator: claude
implementer: pi
reviewers: [codex, claude]
status: "OPEN — contract written before code"
created_at: 2026-09-01
dependencies: [ACS-P0-003, ACS-P0-004, ACS-P0-005, ACS-P0-006]
allowed_paths:
  - src/ai_campaign_studio/jobs/__init__.py
  - src/ai_campaign_studio/jobs/models.py
  - src/ai_campaign_studio/jobs/events.py
  - src/ai_campaign_studio/jobs/cancellation.py
  - src/ai_campaign_studio/jobs/manager.py
  - src/ai_campaign_studio/presentation/__init__.py
  - src/ai_campaign_studio/presentation/contracts.py
  - src/ai_campaign_studio/presentation/state.py
  - src/ai_campaign_studio/presentation/ui_models.py
  - src/ai_campaign_studio/bootstrap.py
  - src/ai_campaign_studio/main.py
  - scripts/health_check.py
  - tests/unit/jobs/
  - tests/unit/presentation/
  - tests/integration/startup/
forbidden_paths:
  - src/ai_campaign_studio/domain/brand/
  - src/ai_campaign_studio/domain/campaign/
  - src/ai_campaign_studio/domain/content/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/channels/
  - src/ai_campaign_studio/localization/
  - src/ai_campaign_studio/ai_registry/
  - src/ai_campaign_studio/infrastructure/secrets/
  - src/ai_campaign_studio/infrastructure/database/
  - src/ai_campaign_studio/ports/
  - presentation_qt/
  - presentation_webview/
gitnexus_required: true
adversarial_required: true
gitnexus:
  required: true
  repository: "H:\\AI Campaing Studio"
  worktree: main (pre-branch pre-impact)
  branch: main
  head: 4e78a90
  index_status: up-to-date
  targets:
    - symbol: "src/ai_campaign_studio/bootstrap.py (Bootstrap, create_bootstrap)"
      upstream_risk: LOW
      upstream_count: 1 (main.py:main)
      downstream_notes: "trenutno wire-uje samo Settings→Paths→Logger; ovaj task ga proširuje na puni P0.22 build sequence. Jedini caller (main.py) se mijenja u istom tasku."
      affected_processes: ["main"]
    - symbol: "PlatformRegistry.from_bundled_resources / AIProviderRegistry.from_bundled_resources"
      upstream_risk: LOW
      upstream_count: 0
      downstream_notes: "nijedan postojeći caller — ovaj task je PRVI koji ih stvarno wire-uje u composition root"
      affected_processes: []
  scope_fit: PASS
  unknowns: []
---

# Kontekst

Sedmi coding task Implementation Phase 0 — najveći i arhitektonski
najosjetljiviji P0 task do sada. Zavisi od ACS-P0-003/004/005/006 (svi
merged) jer `bootstrap.py` prvi put stvarno povezuje translator, platform
registry, AI provider/model registry, secret store i database/migrations u
jedan composition root.

**HIGH risk, ostaje na punom Codex+Claude+Human Owner ciklusu** (workflow
§29) — bootstrap/composition root je eksplicitno na "nepromijenjeno" listi
bez obzira na review politiku za LOW/MEDIUM.

Prije koda implementer mora pročitati:

```text
AGENTS.md
CLAUDE.md
docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md
docs/AI_CAMPAIGN_STUDIO_NACIN_RADA.md
.agent/CURRENT_STATE.md
.agent/PROJECT_MAP.md
.agent/TASK_ROUTING.md
AI_Campaign_Studio_Implementation_Phase_0_v1_1_Agent_Workflow_Integrated.md
  sekcije 27–30 (P0.20–P0.23)
```

GitNexus pre-impact: `bootstrap.py`/`create_bootstrap` ima tačno 1 upstream
caller (`main.py:main`), koji se mijenja u istom tasku — nema iznenađenja.
`from_bundled_resources()` na oba registryja imaju 0 upstream callera —
ovaj task ih prvi put stvarno koristi.

# Objective

Framework-neutral JobManager, framework-neutral Presentation contracts/state
(prije PySide6 vs pywebview gate-a), i pravi composition root koji wire-uje
SVE P0 foundation module (translator, oba registryja, secret store,
database+migrations, job manager) — potpuno offline, bez GUI-ja, bez mreže.
`--health-check` vraća machine-readable JSON status.

# Implementation steps

## P0.20 — Framework-neutral JobManager

1. `jobs/models.py`: `JobStatus` enum (`PENDING, RUNNING, CANCELLING,
   CANCELLED, SUCCEEDED, FAILED`); `JobState` — `id`, `job_type`, `status`,
   `progress_current`, `progress_total`, `phase`, `message`, `error_code?`,
   `error_message?`, `started_at?`, `finished_at?`.
2. `jobs/events.py`: `JobEventType` enum (`CREATED, STARTED, PROGRESS,
   PHASE_CHANGED, SUCCEEDED, FAILED, CANCELLATION_REQUESTED, CANCELLED`);
   `JobEvent` — `job_id`, `event_type`, `timestamp`, `payload`.
3. `jobs/cancellation.py`: `CancellationToken` — `request_cancel()`,
   `is_cancel_requested()`, `raise_if_cancelled()`. Thread-safe (koristiti
   `threading.Event`/`threading.Lock`, ne Qt). Ne zavisi od Qt-a.
4. `jobs/manager.py`: `JobManager` preko `ThreadPoolExecutor`. Mora
   podržati `submit(job_type, callable)`, `get_state(job_id)`,
   `cancel(job_id)`, `subscribe(callback)`/event callback, `shutdown()`. NE
   treba još process pool, Playwright subprocess, AI retry logiku.

## P0.21 — Framework-neutral Presentation contracts/state

5. `presentation/state.py`: `AppRuntimeState` — `app_locale`,
   `startup_status`, `database_ready`, `resources_ready`,
   `configured_providers[]`, `default_text_model?`, `current_job?`,
   `notifications[]`. NE sadržati još `selected_campaign`/`selected_post`/
   `campaign_plan` — business domain nije implementiran.
6. `presentation/ui_models.py`: framework-neutral DTO —
   `NotificationUiModel` (`level`, `message_key`, `params`,
   `technical_details?`), `ProviderStatusUiModel` (`provider_code`,
   `display_name`, `configured`, `validated`, `model_count`). Ne koristiti
   Qt model klase.
7. `presentation/contracts.py`: foundation facade/protocol —
   `set_app_locale(locale)`, `get_app_state()`, `list_ai_providers()`,
   `get_provider_status(provider_code)`, `run_health_check()`,
   `cancel_job(job_id)`. Ne implementirati Campaign UI akcije u P0.
   **Zabranjeno u ovom folderu:** `QObject`, `Signal`, Qt enums, JavaScript
   bridge object, Flask route — ni direktan ni tranzitivan import.

## P0.22 — Bootstrap / Composition Root (jezgro taska)

8. `bootstrap.py`: proširiti postojeći `Bootstrap` (NE uvoditi paralelnu
   `FoundationContainer` klasu — isti koncept, jedno ime, izbjeći
   dupliranje) sa poljima: `settings`, `paths`, `logger`, `translator`,
   `platform_registry`, `provider_registry` (= `AIProviderRegistry`
   instanca, koja već implementira i `ModelRegistryPort` — NE praviti
   odvojenu `model_registry` instancu istog registryja, samo eventualno
   dodatni alias/property ako je zgodno za caller-e), `secret_store`,
   `database_connection` (iz `create_connection`), `migration_runner`
   (referenca na `run_migrations` funkciju ili tanak wrapper — ne
   duplirati P0-006 logiku), `job_manager`.
9. Build sequence, tačno tim redoslijedom: Settings → AppPaths → configure
   logging → Translator resursi → PlatformRegistry → AIProviderRegistry →
   SecretStore adapter selection (environment za dev/test, keyring za
   production — po `settings.environment`, NE pristupati provider secretu
   tokom običnog boot-a) → DB connection (`create_connection`) → migracije
   (`run_migrations`) → JobManager → vrati container.
10. **Bootstrap NE SMIJE**: zvati OpenAI/bilo koji provider SDK, testirati
    internet, pokretati Chromium/Playwright, pokretati GUI, generisati
    kampanju. Potpuno offline.

## P0.23 — Health-check entrypoint

11. `main.py`: `--health-check` sada vraća pun machine-readable JSON:
    `{"status": "ok"|"error", "python": "...", "database": "ok"|"error",
    "migrations": "ok"|"error", "translations": "ok"|"error",
    "platform_registry": "ok"|"error", "provider_registry": "ok"|"error",
    "secret_store": "available"|"unavailable", "ui_framework":
    "not_selected"}`. NE ispisivati API key/provider credential/privatni
    filesystem sadržaj. Exit 0 ako sve prolazi, 1 ako bilo šta padne.
12. `scripts/health_check.py`: praktičan wrapper ako je potreban (poziva
    isti health-check kod, ne duplira logiku).

# Acceptance

- [ ] JobManager: `submit`→`PENDING→RUNNING→SUCCEEDED` happy path radi.
- [ ] JobManager: exception u callable-u → `FAILED` sa typed error info
      (`error_code`/`error_message`).
- [ ] JobManager: cooperative cancellation → `RUNNING→CANCELLING→CANCELLED`,
      cancel-aware callable stvarno provjerava token.
- [ ] JobManager: event sequence za sva tri scenarija (success/failure/
      cancel) odgovara očekivanom redoslijedu.
- [ ] Presentation folder ne importuje `PySide6`/`pywebview`/Qt/Flask ni
      direktno ni tranzitivno (provjeriti postojećim
      `tests/architecture/test_import_boundaries.py` + eventualno dopuniti
      ako boundary checker ne pokriva `presentation/` layer dovoljno
      granularno za ovaj slučaj).
- [ ] Bootstrap sa temp paths: build container, DB postoji, migracija
      primijenjena, platform registry učitan, provider registry učitan,
      translator učitan, **nema mrežnog poziva** (dokazati, ne samo
      pretpostaviti — vidi Adversarial test).
- [ ] `--health-check` vraća tačan JSON oblik, exit 0 na čistom setupu bez
      API ključa, exit 1 kad nešto namjerno padne (test sa pokvarenim
      migrations dir-om ili sličnim).
- [ ] Health-check output ne sadrži API key/credential/privatni path.
- [ ] `python -m pytest -q`, `ruff check .`, `mypy src` prolaze.
- [ ] Nema Campaign/Brand/Content business logike.
- [ ] `Bootstrap` ostaje jedna klasa (nije uveden paralelan
      `FoundationContainer` naziv za isti koncept).

# Adversarial test (obavezno — adversarial_required: true)

## 1. Bootstrap network-isolation invarijant

1. Test tvrdi da `create_bootstrap()`/build sequence ne radi nijedan mrežni
   poziv.
2. Dokazati aktivno, ne pasivno: monkeypatch-ovati `socket.socket` (ili
   ekvivalentan network entry point) da baci exception ako se pozove tokom
   build-a, sa temp paths i bez API ključa u environment-u. Test mora PASS
   (znači: bootstrap stvarno ne dodiruje mrežu).
3. Privremeno dodati (samo za dokaz, ne commit-ovati) lažan mrežni poziv u
   `bootstrap.py` (npr. `socket.create_connection(...)`) — test mora FAIL
   (dokazuje da monkeypatch stvarno hvata poziv, test nije no-op).
4. Ukloniti lažni poziv, potvrditi PASS ponovo.
5. Dokumentovati sva tri outputa.

## 2. JobManager cancellation

1. Test tvrdi da cooperative cancellation stvarno zaustavlja rad (ne samo
   mijenja status flag dok posao nastavlja da radi u pozadini).
2. Privremeno ukloniti `raise_if_cancelled()`/token-check iz test callable-a
   ili iz manager-ove cancel putanje — test mora FAIL (posao završi kao
   `SUCCEEDED` umjesto `CANCELLED`, ili callable nastavi da radi poslije
   cancel zahtjeva).
3. Vratiti — test mora PASS.
4. Dokumentovati oba outputa.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest -q
python -m ruff check .
python -m mypy src
python -m ai_campaign_studio.main --health-check
python scripts/health_check.py
git status --short
```

# Review focus — Codex

- da li network-isolation adversarial dokaz stvarno hvata poziv (ne
  false-positive/false-negative monkeypatch);
- da li cancellation testovi koriste stvaran concurrent scenario
  (ThreadPoolExecutor + sleep/wait), ne samo direktan sinhroni poziv koji
  ne testira race;
- da li `--health-check` JSON ikad može procuriti secret (probaj sa
  konfigurisanim providerom u environment-u);
- edge cases: JobManager `shutdown()` dok je job u toku, `cancel()` na
  nepostojećem `job_id`, `get_state()` na nepostojećem `job_id`;
- da li bootstrap build sequence redoslijed iz kontrakta stvarno odgovara
  redoslijedu u kodu (npr. da li se secret store bira PRIJE ili POSLIJE DB
  koraka na način koji nešto tiho krši).

# Review focus — Claude

- `bootstrap.py` i dalje NIJE service locator u lošem smislu — svaki
  wired objekat ima jasnu, eksplicitnu svrhu, ne generički "get(name)"
  pristup;
- dependency direction: `presentation/` ne importuje `infrastructure/`
  direktno (mora ići kroz `bootstrap`/`contracts`);
- `jobs/` je framework-neutral (nema Qt signala/threading specifičnog za
  GUI);
- ponovna upotreba postojećih P0-002..006 primitiva (`AppError` taxonomy,
  registryji, secret store, `create_connection`/`run_migrations`) — bez
  dupliranja;
- scope discipline — nema Campaign/Brand/Content koda, nema
  presentation_qt/presentation_webview koda.

# Rollback

HIGH task (bootstrap/composition root, arhitektonski najšire-uticajan P0
task do sada). Ako review otkrije da network-isolation ili cancellation
adversarial dokaz ne dokazuje invarijant, ili da je uveden service-locator
antipattern — NE spajati, fix na istoj branch bez proširenja scope-a.

# Dependency baseline

Zavisi od ACS-P0-003, 004, 005, 006 (svi merged, `main`@`4e78a90`). Ne
granati sa starijeg main-a.

# Coordination

Nema paralelnog P0 taska trenutno — ACS-P0-007 je jedini unblocked task.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-P0-007-jobs-presentation-bootstrap
Branch:   task/ACS-P0-007-jobs-presentation-bootstrap
Base:     main @ 4e78a90
```

Nakon merge-a: post-merge gate, GitNexus re-index, CURRENT_STATE update,
ACS-P0-008 postaje unblocked (posljednji P0 task prije gate-a).
