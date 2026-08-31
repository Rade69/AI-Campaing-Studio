# ACS-P0-002 — fix round 3 evidence — coordinator-confirmed

**Implementer:** Pi — vlastiti report:
`agent_reports/2026-08-31-ACS-P0-002-pi-fix-round3.md` (pročitan i potvrđen)
**Prethodni HEAD:** `3ab8eb7` (Codex round 3 REJECT)
**Novi commit:** `f30c5b3` (author Pi, committed by coordinator)

## Diff protiv 3ab8eb7 — nezavisno potvrđeno

Tačno jedan fajl, `tests/architecture/test_import_boundaries.py`
(137 insertions, 89 deletions).

## Pristup — pročitan cio diff

Flat `_collect_import_aliases()`/`_resolve_expr()` funkcije zamijenjene
klasom `_ImportScanner(ast.NodeVisitor)`:

- `self.scopes: list[dict[str, str]]` — stack, počinje sa `[{}]` (module
  scope).
- `visit_FunctionDef`/`visit_AsyncFunctionDef`/`visit_ClassDef`: push novog
  praznog scope-a, `generic_visit` (rekurzivno posjeti tijelo), pop na
  izlazu — standardni scope-stack obrazac.
- `visit_Import`/`visit_ImportFrom`: registruju binding u `_current_scope()`
  (vrh stack-a u trenutku posjete), umjesto u jedan globalni dict.
- `visit_Call`: rešava dynamic-import target kroz `_resolve_name` koji ide
  `reversed(self.scopes)` — od trenutnog (najdubljeg u tom momentu
  traversal-a) ka module scope-u — pa `generic_visit` da nastavi u ugniježđene
  pozive.

Ručno pratio traversal red za Codex-ov `evil()`/`innocent()` primjer: modul
scope dobija `loader→importlib` prije nego se uđe u bilo koju funkciju (jer
je `import` statement prvi u fajlu); `evil()` scope je prazan pri rešavanju
poziva unutar njega, pa `_resolve_name("loader")` pada kroz na module scope
→ `importlib` (tačno); `innocent()`-ov lokalni `loader→types` binding se
upisuje u NJEN vlastiti scope, koji se pop-uje čim se izađe iz `innocent()`
— nikad ne dodiruje `evil()`-ov resolution. Logika je ispravna.

## Adversarial re-dokaz — nezavisno ponovljen, KOMBINOVANO svih 10 oblika

Ubačen Codex-ov `evil()`/`innocent()` scenario ZAJEDNO sa svih 9 ranije
poznatih bypass fajlova (4 iz round 1 + 5 iz round 2), sve odjednom u
`domain/`:

```text
$ pytest -q tests/architecture/test_import_boundaries.py::test_real_tree_has_no_boundary_violations
F
Left contains 10 more items, first extra item: "domain/_z1_relative.py: forbidden domain/ import 'ai_campaign_studio.infrastructure'"
1 failed
```

Svih 10 uhvaćeno (nema regresije na prethodnih 9, plus novi scope-shadow
slučaj). Nakon uklanjanja:

```text
$ pytest -q tests/architecture/
.............. [100%]
14 passed
```

## Standardna verifikacija — nezavisno ponovljena

```text
python -m pytest -q        → 42 passed
python -m ruff check .     → All checks passed!
python -m mypy src         → Success (18 source files)
--health-check              → exit 0
```

## Zaključak

Cross-scope shadowing bug zatvoren, dokazano adversarialno, bez regresije na
prethodno zatvorene bypass oblike. Spreman za fresh Codex round 4 na
`f30c5b3`.
