---
verdict: REJECT
scope: PASS
acceptance: REJECT
architecture: REJECT
security: PASS
tests: REJECT
gitnexus_impact: UNKNOWN
blocking_findings:
  - BF-1: "JobManager.submit() after shutdown leaves an orphan PENDING job and emits CREATED before raising RuntimeError."
  - BF-2: "Presentation GUI/web guard misses literal dynamic imports via importlib.import_module() and __import__()."
---

# CILJ

Independent Codex review za ACS-P0-007 — JobManager + presentation contracts/state + bootstrap/health-check wiring.

Pregledan je task branch `task/ACS-P0-007-jobs-presentation-bootstrap` u odnosu na `main`, uključujući implementer report, Claude review/fix evidence, task contract i svježu lokalnu verifikaciju. HIGH risk task ostaje na punom ciklusu: ovaj report nije merge approval.

# PROVJERENO

- `agent_reports/ACS-P0-007-task-contract.md`
- `agent_reports/2026-09-01-ACS-P0-007-pi.md`
- `agent_reports/2026-09-01-ACS-P0-007-review-claude.md`
- `agent_reports/2026-09-01-ACS-P0-007-fix-round1-pi.md`
- `agent_reports/2026-09-01-ACS-P0-007-pi-confirmed.md`
- `agent_reports/2026-09-01-ACS-P0-007-codex-review-request.md`
- Diff `main..task/ACS-P0-007-jobs-presentation-bootstrap`
- Touched runtime/test files under:
  - `src/ai_campaign_studio/jobs/`
  - `src/ai_campaign_studio/presentation/`
  - `src/ai_campaign_studio/bootstrap.py`
  - `src/ai_campaign_studio/main.py`
  - `scripts/health_check.py`
  - `tests/unit/jobs/`
  - `tests/unit/presentation/`
  - `tests/integration/startup/`
  - `tests/architecture/test_import_boundaries.py`
  - `tests/test_foundation.py`

Scope je prihvatljiv uz već zabilježen out-of-scope ripple: `tests/test_foundation.py` je van striktno dozvoljenih pathova, ali je vezan za izmijenjeno bootstrap/main ponašanje i prethodno je eksplicitno prihvaćen kao test-maintenance ripple.

# GITNEXUS / IMPACT

`gitnexus status` iz task worktree-ja vraća `Repository not indexed. Run: gitnexus analyze`.

`gitnexus detect-changes` bez eksplicitnog repo parametra vraća da postoji više indeksiranih repozitorija i da treba specificirati repo. Ranije poznato ograničenje linked worktree bindinga ostaje prisutno, pa GitNexus impact evidence za ovaj worktree označavam kao `UNKNOWN`.

Kompenzacija: urađen je ručni diff/source review relevantnih fajlova i standardna verifikacija.

# BLOCKING FINDINGS

## BF-1 — `JobManager.submit()` poslije `shutdown()` ostavlja lažni PENDING job

Status: BLOCKING

Lokacija: `src/ai_campaign_studio/jobs/manager.py`, `submit()` i `shutdown()`.

Problem:

`submit()` prvo kreira `job_id`, upisuje `PENDING` state u `_jobs`, upisuje token u `_tokens`, emituje `CREATED`, pa tek onda zove `self._executor.submit(...)`. Ako je `shutdown()` već pozvan, `ThreadPoolExecutor.submit()` baca `RuntimeError: cannot schedule new futures after shutdown`.

Rezultat je vidljiv i spolja kroz event callback:

- poziv `submit()` failuje;
- callback je već dobio `CREATED`;
- interni `_jobs` sadrži job koji ostaje `PENDING`;
- taj job se nikad neće pokrenuti niti terminalno završiti.

Reprodukcija:

```text
## submit-after-shutdown
RuntimeError cannot schedule new futures after shutdown
jobs 1
states ['PENDING']
events ['CREATED']
```

Zašto je blocking:

Codex review brief eksplicitno traži provjeru edge case-a `submit after shutdown`. Ovo nije čisto teorijski slučaj: svaka UI/CLI integracija koja drži referencu na `JobManager` nakon shutdowna može dobiti kontradiktoran event stream i trajno netačan job state. P0 foundation contract traži pouzdane lifecycle state/event invarijante.

Očekivana fix-runda:

- `JobManager` treba imati eksplicitan shutdown flag ili rollback oko executor schedulinga.
- Nakon shutdowna `submit()` ne smije emitovati `CREATED` niti ostaviti job u `_jobs`.
- Dodati regression test za `submit()` nakon `shutdown()`.

## BF-2 — presentation guard ne hvata literalne dinamičke GUI/infra import-e

Status: BLOCKING

Lokacija: `tests/unit/presentation/test_no_gui_imports.py`.

Problem:

Presentation-specific guard skenira samo AST `Import` i `ImportFrom` čvorove. Ne skenira literalne dinamičke import-e (`importlib.import_module(...)`, `__import__(...)`). Globalni `tests/architecture/test_import_boundaries.py` je jači i hvata dynamic import-e za neke layer zabrane, ali presentation-specific guard je jedini koji zabranjuje GUI/web framework import-e u shared `presentation/` folderu.

Adversarial probe:

```python
import importlib
importlib.import_module("PySide6")
importlib.import_module("ai_campaign_studio.infrastructure.database")
__import__("PySide6")
__import__("ai_campaign_studio.infrastructure.database")
```

Rezultat:

```text
## presentation-guard-dynamic-imports
importlib []
dunder []
```

Zašto je blocking:

ACS-P0-007 uvodi framework-neutral presentation contracts/state prije UI-GATE odluke. Task contract i Codex brief eksplicitno traže da presentation folder ostane bez GUI/web/provider/infrastructure import-a, uključujući bypass pokušaje. Ovo nije stil-nit: guard može propustiti upravo zabranu koju treba da čuva za buduće PySide6/pywebview odluke.

Očekivana fix-runda:

- Ili proširiti `test_no_gui_imports.py` da koristi isti dynamic-import scanner kao `tests/architecture/test_import_boundaries.py`,
- ili centralizovati AST import scanner da oba testa koriste istu provjerenu logiku.
- Dodati self-testove za `importlib.import_module("PySide6")`, `__import__("PySide6")`, i barem jedan dynamic infrastructure import u presentation kontekstu.

# STANDARDNA VERIFIKACIJA

Pokrenuto svježe:

```text
set PYTHONPATH=H:\ai-campaign-studio-worktrees\ACS-P0-007-jobs-presentation-bootstrap\src
.venv\Scripts\python.exe -m pytest -q H:\ai-campaign-studio-worktrees\ACS-P0-007-jobs-presentation-bootstrap\tests
```

Rezultat:

```text
165 passed, 1 warning in 5.31s
```

Warning je pytest cache cleanup warning u task worktree-ju, nije test failure.

```text
.venv\Scripts\python.exe -m ruff check H:\ai-campaign-studio-worktrees\ACS-P0-007-jobs-presentation-bootstrap --no-cache
```

Rezultat:

```text
All checks passed!
```

```text
.venv\Scripts\python.exe -m mypy H:\ai-campaign-studio-worktrees\ACS-P0-007-jobs-presentation-bootstrap\src
```

Rezultat:

```text
Success: no issues found in 51 source files
```

Health-check funkcija sa eksplicitnim temp data/resources paths:

```text
{"database": "ok", "migrations": "ok", "platform_registry": "ok", "provider_registry": "ok", "python": "3.14.1", "secret_store": "available", "status": "ok", "translations": "ok", "ui_framework": "not_selected"}
```

Napomena: direktni CLI health-check sa default korisničkim data/log pathom u ovom sandboxu vraća `error` zbog `PermissionError` pri pisanju u `C:\Users\...\AppData\Local\AI Campaign Studio\...\logs\ai_campaign_studio.log`. To tretiram kao environment/sandbox artefakt, ne kao blocking product finding, jer temp-path health-check i integration tests prolaze. JSON output nije procurio secret ni privatnu putanju.

# ADVERSARIALNA PROVJERA

Urađeno dodatno preko privremenog probe skripta:

- `submit()` nakon `shutdown()` → našao BF-1.
- presentation dynamic `importlib.import_module("PySide6")` → našao BF-2.
- presentation dynamic `__import__("PySide6")` → našao BF-2.
- dynamic infrastructure import u presentation guardu → takođe nije uhvaćen u tom guardu.
- health-check sa postavljenim lažnim env secretom `AI_CAMPAIGN_STUDIO_OPENAI_API_KEY=sk-codex-secret-probe-007` → temp-path result `ok`, bez secret leak-a u JSON-u.

# NE DIRATI U FIX RUNDI

Fix-runda treba ostati uska:

- Ne mijenjati domain/application/channel/localization/AI registry sem ako test pokaže direktnu potrebu.
- Ne širiti UI framework odluku; presentation ostaje framework-neutral.
- Ne uvoditi container/service-locator u `bootstrap.py`.
- Ne mijenjati health-check schema osim ako je direktno potrebno za postojeći contract.

# SLJEDEĆE

REJECT dok se ne zatvore BF-1 i BF-2.

Nakon fix-runde očekujem:

1. novi regression test za `submit()` nakon `shutdown()`;
2. dynamic import self-testove za presentation guard;
3. ponovljeno:
   - full pytest,
   - ruff,
   - mypy,
   - health-check/script check;
4. kratak implementer fix report sa tačnim diffom i evidence.
