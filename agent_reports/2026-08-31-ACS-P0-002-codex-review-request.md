# Codex review request — ACS-P0-002

Za: Codex (adversarial/test reviewer)
Od: Claude (koordinator)
Datum: 2026-08-31

## Read protocol prije review-a

1. `AGENTS.md`, `CLAUDE.md`
2. `docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md` §14 (review format), §15
   (Codex fokus)
3. `.agent/CURRENT_STATE.md`
4. `agent_reports/ACS-P0-002-task-contract.md` (Task Contract — acceptance,
   allowed/forbidden paths, obavezni adversarial test)
5. `agent_reports/2026-08-31-ACS-P0-002-pi.md` (coordinator-confirmed
   execution evidence, sadrži i Pi-jev originalni report)
6. Sam diff (vidi ispod)

## Šta pregledati

```text
Repo:     H:\AI Campaing Studio  (main branch)
Worktree: H:\ai-campaign-studio-worktrees\ACS-P0-002-config-boundaries
Branch:   task/ACS-P0-002-config-boundaries
Commit:   c6fa0b8 (base: main@1725aaa)
```

```bash
git -C "H:\AI Campaing Studio" diff main task/ACS-P0-002-config-boundaries --stat
git -C "H:\AI Campaing Studio" diff main task/ACS-P0-002-config-boundaries
```

**Napomena o GitNexus:** `detect-changes` sa `--repo .` iz glavnog checkout-a
vraća diff glavnog worktree-a, ne task branch-a — GitNexus binduje "repo" na
registrovani glavni checkout, ne na linked worktree (poznato ograničenje,
isto je pogodilo i implementera i koordinatora). Tretiraj GitNexus impact
kao `UNKNOWN`, ne kao "nema impacta"; oslanjaj se na stvarni `git diff`.

## Codex review fokus — primijenjeno na ovaj task

Ovaj task uvodi PRVI stvarni arhitektonski invariant projekta (import
boundary), pa je adversarial dio suštinski, ne formalnost:

1. **Da li `test_import_boundaries.py` stvarno dokazuje invariant?**
   Pogledaj `_iter_imports()` u
   `tests/architecture/test_import_boundaries.py` — hvata i `import x.y.z`
   i `from x.y import z` oblik. Probaj naći zaobilazak koji test NE hvata:
   npr. `import importlib; importlib.import_module("ai_campaign_studio.infrastructure")`,
   `__import__("PySide6")`, uslovni import unutar funkcije, `import
   ai_campaign_studio.infrastructure as _x` (alias). Da li checker i dalje
   hvata sve varijante, ili postoji rupa?
2. **Redaction key-name heuristika** — `SENSITIVE_KEY_FRAGMENTS` u
   `logging/redaction.py` koristi substring match (`fragment in
   normalized`). Provjeri false-negative slučajeve (key koji SADRŽI
   osjetljivu vrijednost ali čiji naziv ne sadrži nijedan fragment, npr.
   `"x-api-secret-key"` treba da pogodi preko `secret`/`api_key` fragmenta —
   provjeri da li stvarno pogađa) i da li substring match ima
   false-positive rizik koji bi mogao sakriti legitiman podatak nepotrebno
   (manji rizik, ali provjeri).
3. **`AppSettings`/`AppPaths` edge cases** — da li Pydantic validacija
   stvarno odbija nepoznat `environment` (test tvrdi da odbija — probaj
   sam). Da li `AppPaths` sa Windows/POSIX specifičnim putanjama radi
   ispravno (repo je na Windows-u, `platformdirs` se ponaša različito po OS-u
   — provjeri da li test pokriva ovo ili samo pretpostavlja jedan OS).
4. **`main.py --health-check`** — `except Exception: return 1` je široki
   catch. Probaj scenario gdje `create_bootstrap()` baci `SystemExit` ili
   `KeyboardInterrupt` (nisu `Exception` podklase) — da li se `main()`
   ponaša razumno ili neuhvaćeno propagira na neočekivan način?
5. **Acceptance evidence vs stvaran output** — ponovo pokreni nezavisno:
   ```bash
   cd "H:\ai-campaign-studio-worktrees\ACS-P0-002-config-boundaries"
   .\.venv\Scripts\python.exe -m pytest -q
   .\.venv\Scripts\python.exe -m ruff check .
   .\.venv\Scripts\python.exe -m mypy src
   .\.venv\Scripts\python.exe -m ai_campaign_studio.main --health-check
   git status --short
   ```
6. **Scope/regression** — diff van `allowed_paths`? Skriveni I/O ili mrežni
   poziv pri importu bilo kog novog modula (npr. da li `config/paths.py` ili
   `logging/config.py` slučajno dira filesystem pri samom importu, ne samo
   pri eksplicitnom pozivu)?

## Traženi output format

Sačuvaj kao `agent_reports/2026-08-31-ACS-P0-002-review-codex.md`, isti
format kao `agent_reports/2026-08-31-ACS-P0-002-review-claude.md` (YAML
header + CILJ/PROVJERENO/GITNEXUS-IMPACT/BLOCKING FINDINGS/STANDARDNA
VERIFIKACIJA/ADVERSARIALNA PROVJERA/NE DIRATI U FIX RUNDI/SLJEDEĆE).

Nakon tvog verdikta tražim Human Owner odobrenje za merge.
