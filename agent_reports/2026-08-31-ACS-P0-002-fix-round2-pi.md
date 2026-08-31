# ACS-P0-002 — fix round 2 evidence — coordinator-confirmed

**Implementer:** Pi — vlastiti report:
`agent_reports/2026-08-31-ACS-P0-002-pi-fix-round2.md` (u worktree-u,
nekomitovan, pročitan i potvrđen)
**Branch/worktree:** `task/ACS-P0-002-config-boundaries`,
`../ai-campaign-studio-worktrees/ACS-P0-002-config-boundaries`
**Prethodni HEAD:** `cb58c14` (Codex round 2 REJECT na ovom commitu)
**Novi commit:** `3ab8eb7` (author Pi, committed by coordinator)

## Diff protiv cb58c14 — nezavisno potvrđeno

```text
tests/architecture/test_import_boundaries.py | 180 +++++++++++++++++++++++----
1 file changed, 157 insertions(+), 23 deletions(-)
```

Tačno jedan fajl, ništa iz "NE DIRATI" liste dirnuto.

## Pristup — pročitan cio diff

`_dynamic_import_target()` generalizovan sa fiksnih pattern-a na
alias-resolving pristup:

- `_collect_import_aliases(tree)`: jedan AST prolaz po fajlu, gradi mapu
  lokalno-ime → kanonski target (`import importlib as loader` →
  `{"loader": "importlib"}`; `from importlib import import_module as load` →
  `{"load": "importlib.import_module"}`).
- `_resolve_expr()`: rekurzivno razrešava `Name`/`Attribute` izraz kroz tu
  mapu (npr. `loader.import_module` → `"importlib" + ".import_module"` =
  `"importlib.import_module"`).
- `_dynamic_import_target()`: prvo provjerava `getattr(<obj>, "import_module")(<literal>)`
  oblik (call.func je sam Call na `getattr`), inače razrešava `call.func`
  kroz alias mapu i poredi sa `{"importlib.import_module",
  "importlib.__import__", "builtins.__import__", "__import__"}`.
- Samo literal `ast.Constant` string argumenti — runtime-konstruisani izrazi
  se i dalje ne razrešavaju (namjerno, van scope-a) i ne ruše checker
  (eksplicitno testirano).

Ručno pratio logiku za sve prijavljene bypass slučajeve (`loader.import_module`,
`load(...)`, `importlib.__import__`, `getattr(importlib,"import_module")(...)`,
`builtins.__import__`) — razrešenje kroz alias mapu je tačno u svakom.

## Adversarial re-dokaz — nezavisno ponovljen, KOMBINOVANO svih 9 oblika

Ubačeno svih 9 poznatih bypass fajlova odjednom (4 iz round 1 + 5 iz round 2)
u `domain/`:

```text
$ pytest -q tests/architecture/test_import_boundaries.py::test_real_tree_has_no_boundary_violations
F
assert [...] == []
Left contains 9 more items, first extra item: "domain/_z1_relative.py: forbidden domain/ import 'ai_campaign_studio.infrastructure'"
1 failed
```

Svih 9 uhvaćeno u jednom prolazu. Nakon uklanjanja:

```text
$ pytest -q tests/architecture/
............. [100%]
13 passed
```

## Standardna verifikacija — nezavisno ponovljena

```text
python -m pytest -q        → 41 passed
python -m ruff check .     → All checks passed!
python -m mypy src         → Success (18 source files)
--health-check              → exit 0
```

## Zaključak

BF-1 zatvoren u potpunosti (svih 9 poznatih bypass oblika + Codex-ov
non-literal no-crash zahtjev + safe-relative-import kontrola). Spreman za
fresh Codex round 3 review na `3ab8eb7`.
