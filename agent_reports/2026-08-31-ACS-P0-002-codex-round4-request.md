# Codex round 4 review request — ACS-P0-002

Za: Codex
Od: Claude (koordinator)
Datum: 2026-08-31

## Kontekst

Round 3 (`agent_reports/2026-08-31-ACS-P0-002-review-codex-round3.md`):
`REJECT` — flat alias dict nije bio lexical-scope aware, cross-scope
shadowing (`evil()`/`innocent()`) sakrivao je stvaran forbidden import. Pi je
zamijenio flat dict sa `_ImportScanner(ast.NodeVisitor)` — pravi scope-stack
(modul + po funkcija/async funkcija/klasa). Reprodukovao sam tvoj tačan
`evil()`/`innocent()` scenario ZAJEDNO sa svih 9 ranije poznatih bypass
oblika u jednom kombinovanom prolazu — svih 10 uhvaćeno, čisto stablo i dalje
prolazi (14/14).

## Šta pregledati

```text
Branch:        task/ACS-P0-002-config-boundaries
Prošli HEAD:   3ab8eb7  (na kom si dao round 3 REJECT)
Novi HEAD:     f30c5b3
```

```bash
git -C "H:\AI Campaing Studio" diff 3ab8eb7 f30c5b3 --stat
git -C "H:\AI Campaing Studio" diff 3ab8eb7 f30c5b3
```

Tačno jedan fajl: `tests/architecture/test_import_boundaries.py`
(137 insertions, 89 deletions).

## Fokus round 4

Pristup je sad pravi scope-stack (`ast.NodeVisitor` sa push/pop po
`FunctionDef`/`AsyncFunctionDef`/`ClassDef`). Provjeri:

1. **Ponovi svoj tačan round-3 scenario** (`evil()`/`innocent()`) protiv
   novog checkera — očekivano: uhvaćeno.
2. **Nested/ugniježđene funkcije** — closure koji koristi vanjski scope-ov
   alias:
   ```python
   import importlib as loader

   def outer():
       def inner():
           return loader.import_module("ai_campaign_studio.infrastructure")
       return inner
   ```
   Da li `_resolve_name` ispravno nalazi `loader` u module scope-u kroz DVA
   nivoa ugniježđenja (outer→inner→module), pošto scope stack raste za
   svaki nivo?
3. **Class-level scope interakcija** — metoda unutar klase koja koristi
   module-level alias, i class body koji ima sopstveni (irelevantan) local
   import:
   ```python
   import importlib as loader

   class Evil:
       def method(self):
           return loader.import_module("ai_campaign_studio.infrastructure")

   class Innocent:
       import types as loader
   ```
   Da li `method()` i dalje ispravno rešava `loader` do `importlib` (class
   body scope se ne nasljeđuje u method scope po pravoj Python semantici —
   provjeri da checker to ne remeti pogrešno u bilo kom smjeru)?
4. **Redoslijed unutar iste funkcije** — import NAKON upotrebe u istoj
   funkciji (nevažeći Python kod runtime-wise, ali provjeri da checker ne
   puca):
   ```python
   def f():
       result = loader.import_module("x")  # NameError at runtime
       import importlib as loader
       return result
   ```
5. **Regresija** — svih prethodnih 9+1 (scope-shadow) oblika i dalje uhvaćeno,
   safe control i non-literal no-crash i dalje prolaze. Pun set:
   ```bash
   cd "H:\ai-campaign-studio-worktrees\ACS-P0-002-config-boundaries"
   .\.venv\Scripts\python.exe -m pytest -q
   .\.venv\Scripts\python.exe -m ruff check .
   .\.venv\Scripts\python.exe -m mypy src
   .\.venv\Scripts\python.exe -m ai_campaign_studio.main --health-check
   ```
6. **Scope-clean diff?** (mora biti tačno 1 fajl).

## Napomena Human Ownera

Ovo je četvrta runda na istom testu. Human Owner je eksplicitno odlučio
(2026-08-31) nastaviti dok se ne zatvori svaki reproducibilan correctness
bug, umjesto da se prihvati dokumentovano ograničenje — ali ako round 4
otkrije samo teoretski/kontriran slučaj bez jasnog realnog rizika za P0
foundation kod, eksplicitno navedi to u opservacijama, ne nužno kao novi
blocking finding, da Human Owner može odmjeriti proporcionalnost.

## Traženi output

`agent_reports/2026-08-31-ACS-P0-002-review-codex-round4.md`, isti format.
Ako `PASS`/`PASS_WITH_NOTES` bez novih blocking findings, tražim Human Owner
odobrenje za merge odmah nakon.
