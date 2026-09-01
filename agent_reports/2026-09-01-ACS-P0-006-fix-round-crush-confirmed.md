# ACS-P0-006 — fix round evidence — coordinator-confirmed

**Prethodni HEAD:** `92f3917` (Codex REJECT — BF-1/BF-2)
**Novi commit:** `8d45167` (author Crush, committed by coordinator)

## Diff protiv 92f3917

4 fajla: `unit_of_work.py` (+1), `migrations.py` (BEGIN premješten van try),
`test_migrations.py` (+21 novi test), `test_unit_of_work.py` (+16 novi
test).

## Fix

- BF-1: `__enter__()` sada radi `self._committed = False` prije `BEGIN`.
- BF-2: `connection.execute("BEGIN")` premješten IZVAN `try` bloka u
  `_apply_migration()` — ako BEGIN sam padne, exception propagira odmah,
  `except`/`ROLLBACK` grana se ne izvršava.

Tačno kako je brief tražio, minimalne, ciljane izmjene.

## Nezavisna verifikacija

```text
$ ./.venv/Scripts/python.exe -m pytest -q
........................................................................ [ 69%]
................................                                         [100%]
104 passed in 0.97s

$ ./.venv/Scripts/python.exe -m ruff check .
All checks passed!

$ ./.venv/Scripts/python.exe -m mypy src
Success: no issues found in 34 source files
```

## Re-dokaz BF-1/BF-2 — nezavisno ponovljen

```text
BF-1 count (expect 1): 1        (bilo 2 prije fixa)
BF-2 exception: OperationalError
BF-2 caller rows (expect 1): 1  (bilo 0 prije fixa)
```

## Zaključak

Oba nalaza zatvorena, dokazano nezavisnim ponavljanjem originalnih Codex
probe scenarija, bez regresije (104/104 zeleno). Spreman za fresh Codex
re-review na `8d45167` (HIGH task, ostaje na punom ciklusu po review
politici §29).
