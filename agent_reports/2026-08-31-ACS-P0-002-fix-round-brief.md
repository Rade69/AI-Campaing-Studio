# ACS-P0-002 — fix round brief (BF-1)

Za: Pi (isti implementer, isti branch)
Od: Claude (koordinator), poslije Codex REJECT-a
Datum: 2026-08-31

## Status

Codex review: `agent_reports/2026-08-31-ACS-P0-002-review-codex.md` —
`verdict: REJECT`, `blocking_findings: [BF-1]`. Koordinator je nezavisno
reprodukovao BF-1 u worktree-u (svi 4 bypass-a prolaze kroz
`test_real_tree_has_no_boundary_violations` bez FAIL-a). Nalaz je potvrđen,
nije lažna uzbuna.

**Task se NE spaja.** Ovo je fix runda na istoj branch-i
(`task/ACS-P0-002-config-boundaries`), ne novi task.

## BF-1 — šta popraviti

`tests/architecture/test_import_boundaries.py` propušta 4 semantički
zabranjena import oblika u `domain/` (i po istoj logici u
`application/`/`ports/`/`presentation/`):

1. **Relative import** ciljajući forbidden sibling layer:
   ```python
   from .. import infrastructure
   ```
   `_iter_imports()` trenutno `continue`-uje čim `node.level > 0`. Treba
   razriješiti relative import na puni module path (koristeći poznati paket
   `ai_campaign_studio` kao root) ili barem konzervativno flag-ovati kada
   `node.module`/`alias.name` cilja na ime koje se poklapa sa forbidden
   prefix-om (`infrastructure`, `presentation`, `jobs`).

2. **Dynamic import sa literal string argumentom:**
   ```python
   import importlib
   importlib.import_module("ai_campaign_studio.infrastructure")
   ```
   Ne treba rješavati proizvoljno runtime-konstruisane stringove — samo
   `ast.Call` na `importlib.import_module(...)` (ili `import_module(...)`
   ako je importovan direktno) gdje je prvi argument `ast.Constant` string.

3. **`__import__(...)` sa literal string argumentom:**
   ```python
   __import__("PySide6")
   ```
   Isto — `ast.Call` na `__import__` sa `ast.Constant` string argument.

4. **Case-sensitivity bug — `Flask` vs stvarni modul `flask`:**
   `_WEB_MODULES = {"requests", "Flask"}` u
   `tests/architecture/test_import_boundaries.py` koristi pogrešan case;
   stvaran Python import je `import flask` (lowercase). Ispraviti na
   `"flask"`. Dodati i `"fastapi"` u isti set (projektna zabrana pokriva i
   FastAPI, trenutni checker ga uopšte ne provjerava).

## Obavezno

- Dodati meta-test(ove) koji pokrivaju sva 4 bypass-a iznad, analogno
  postojećem `test_checker_flags_forbidden_imports_in_every_layer` — svaki
  mora dokazano FAIL-ovati na TRENUTNOM (prije-fix) checkeru i PASS-ovati na
  popravljenom. Dokumentovati oba outputa (isti obrazac kao za originalni
  adversarial dokaz).
- Ponoviti pun verification set (`pytest`, `ruff`, `mypy`, `--health-check`).
- Ne mijenjati ništa van boundary checkera i njegovih testova — Codex-ov
  "NE DIRATI U FIX RUNDI" ostaje na snazi: `AppSettings`, `AppPaths`,
  `Bootstrap`, logging setup, error taxonomy, package seam-ovi, runtime
  dependencies, health-check ponašanje. Ne uvoditi novu
  dependency-analysis biblioteku (i dalje čist AST scan).
- Ne-blokirajuće opservacije iz oba reviewa (redaction separator normalizacija,
  `resources_dir` layout pretpostavka, `main.py` exception handling) ostaju
  zabilježene za buduće taskove — ne rješavati ih ovdje, nisu blocking i nisu
  u scope-u ove fix runde.

## Verification (fix runda)

```bash
cd "H:\ai-campaign-studio-worktrees\ACS-P0-002-config-boundaries"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy src
.\.venv\Scripts\python.exe -m ai_campaign_studio.main --health-check
git status --short
```

## Sljedeće

Poslije fix runde: koordinator provjerava diff SAMO protiv trenutnog task
commita (`c6fa0b8`), ne cijeli task ponovo od main-a. Zatim fresh Codex
re-review na novom HEAD-u. Claude-ov raniji PASS i standardni green gate ne
nadjačavaju blocking adversarial nalaz — merge čeka čist re-review.
