# ACS-P0-002 — fix round 2 brief (BF-1 still open)

Za: Pi (isti branch)
Od: Claude (koordinator), poslije Codex round-2 REJECT-a
Datum: 2026-08-31

## Status

Codex round 2: `agent_reports/2026-08-31-ACS-P0-002-review-codex-round2.md`
— `verdict: REJECT`. Prvih 4 bypass-a (relative import, `importlib.import_module`,
bare `__import__`, `flask` case) ostaju zatvorena — Codex je to potvrdio. Ali
brief za round 1 re-review eksplicitno je tražio probu i dodatnih oblika koje
checker i dalje propušta. Koordinator je sve reprodukovao nezavisno: svih 5
navedenih bypass fajlova prošlo je kroz `test_real_tree_has_no_boundary_violations`
neopaženo.

**Task se i dalje NE spaja.** Ista branch (`task/ACS-P0-002-config-boundaries`),
treća runda na istom fajlu.

## Preostali bypass oblici koje treba uhvatiti

```python
# 1. importlib.__import__(literal)
import importlib
importlib.__import__("ai_campaign_studio.infrastructure")

# 2. getattr(importlib, "import_module")(literal)
import importlib
getattr(importlib, "import_module")("ai_campaign_studio.infrastructure")

# 3. import alias (modul)
import importlib as loader
loader.import_module("ai_campaign_studio.infrastructure")

# 4. from-import alias (funkcija)
from importlib import import_module as load
load("ai_campaign_studio.infrastructure")

# 5. builtins.__import__ (eksplicitan module-qualified oblik)
import builtins
builtins.__import__("PySide6")
```

Van scope-a (NE pokušavati riješiti, samo osigurati da checker na tome ne
puca — Codex je ovo već provjerio i potvrdio da ne ruši checker):

```python
importlib.import_module("ai_campaign_studio" + ".infrastructure")  # concatenated string
```

## Predložen pristup (nije obavezujući, implementer bira konkretnu implementaciju)

Trenutni `_dynamic_import_target()` prepoznaje samo fiksne, doslovne oblike
(`importlib.import_module(...)`, `import_module(...)`, `__import__(...)`).
Da bi se pokrila i alias/getattr varijanta, potreban je generičkiji pristup:

1. U istom AST prolazu (ili prije njega), sakupiti mapu lokalnih imena →
   kanonski target za relevantne import statement-e u fajlu:
   - `import importlib` → `"importlib"` se veže na ime `importlib`;
   - `import importlib as loader` → `"importlib"` se veže na ime `loader`;
   - `from importlib import import_module` → `"importlib.import_module"` se
     veže na ime `import_module`;
   - `from importlib import import_module as load` → `"importlib.import_module"`
     se veže na ime `load`;
   - `import builtins` (ili alias) → `"builtins"` se veže na odgovarajuće ime.
2. Pri provjeri `ast.Call` čvorova, razriješiti `call.func` (bilo
   `ast.Attribute` bilo `ast.Name`) kroz tu mapu prije poređenja sa
   `"importlib.import_module"`/`"importlib.__import__"`/`"builtins.__import__"`/
   `"__import__"`.
3. Za `getattr(importlib_ref, "import_module")(<literal>)`: prepoznati
   spoljni `ast.Call` čiji je `.func` sam `ast.Call` na `getattr` sa
   argumentima `(modul_ref, ast.Constant string)`, gdje `modul_ref` razrešava
   (preko iste alias mape) na `"importlib"` i string argument je
   `"import_module"`. Argument spoljnjeg poziva je literal target module.
4. Ne pokušavati riješiti proizvoljne runtime-konstruisane izraze (string
   concat, f-string, promjenljive) — samo literal `ast.Constant` argumenti,
   kao do sada.

## Obavezno

- Meta-test za SVAKIH 5 oblika iznad, svaki dokazano FAIL na trenutnom
  (prije ove runde) checkeru → PASS na popravljenom, isti FAIL→PASS obrazac
  kao prethodne dvije runde.
- Zadržati postojeće "safe control" testove (npr. `from . import helper`,
  `from .. import helper` na dozvoljen target) da se potvrdi da nova logika
  ne uvodi false positive.
- Zadržati (ili dodati, ako ne postoji) test da concatenated-string dynamic
  import NE ruši checker (ne mora biti uhvaćen, samo ne smije baciti
  exception).
- I dalje SAMO `tests/architecture/test_import_boundaries.py`. Ništa u
  `src/`, config, paths, logging/redaction, error taxonomy, bootstrap/main,
  dependencies ili drugim test fajlovima.
- Ponoviti pun verification set.

## Verification

```bash
cd "H:\ai-campaign-studio-worktrees\ACS-P0-002-config-boundaries"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy src
.\.venv\Scripts\python.exe -m ai_campaign_studio.main --health-check
git status --short
```

## Sljedeće

Koordinator provjerava novi delta protiv `cb58c14` (ne cijeli task), zatim
fresh Codex re-review (round 3). `pytest`/`ruff`/`mypy` zeleni i scope-clean
diff i dalje nisu dovoljni za PASS dok svih 5 eksplicitnih adversarial
slučajeva iz ovog brief-a nisu dokazano uhvaćena.
