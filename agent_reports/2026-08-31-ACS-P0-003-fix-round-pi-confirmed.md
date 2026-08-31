# ACS-P0-003 — fix round evidence — coordinator-confirmed

**Implementer:** Pi — vlastiti report:
`agent_reports/2026-08-31-ACS-P0-003-pi-fix-round.md` (pročitan i potvrđen)
**Prethodni HEAD:** `0c23bcf` (Codex REJECT — BF-1/2/3)
**Novi commit:** `7df75c3` (author Pi, committed by coordinator)

## Diff protiv 0c23bcf — nezavisno potvrđeno

3 izmijenjena fajla + 1 novi: `scripts/validate_resources.py` (+39/-14),
`localization/translator.py` (+12/-4... wait), `tests/unit/localization/test_translator.py`
(+32), `tests/integration/localization/test_validate_resources.py` (novi).
Sve unutar `allowed_paths`. `agent_reports/2026-08-31-ACS-P0-003-pi.md`
(raniji report) i dalje netaknut untracked, kako je Pi napomenuo.

## Fix — pročitan cio diff

- **BF-1:** `except (KeyError, IndexError):` → `except (KeyError, IndexError,
  ValueError):` u `Translator.t()`.
- **BF-2:** `Translator.t()` sad provjerava `isinstance(template, str)`
  prije `.format()` (i za direktan i za EN-fallback put) — non-string
  tretira kao missing (`[missing:key]` + warning). `validate_i18n()` sad
  odbija non-string vrijednosti sa čitljivom porukom.
- **BF-3:** `_duplicate_keys()` preimenovan/proširen u `_parse_json()` koji
  vraća `(data, duplicates)` i baca `JSONDecodeError` na loš JSON;
  `validate_i18n()` sad poziva taj helper unutar `try/except
  JSONDecodeError` PRIJE bilo kakve druge obrade tog fajla (`continue` na
  grešku), umjesto starog redoslijeda gdje je duplicate-check trčao
  nezaštićen prije parse-a.

## Nezavisna verifikacija — DOSLOVAN output (worktree `.venv`)

```text
$ ./.venv/Scripts/python.exe -m pytest -q
.....................................................................    [100%]
69 passed in 0.43s

$ ./.venv/Scripts/python.exe -m ruff check .
All checks passed!

$ ./.venv/Scripts/python.exe -m mypy src
Success: no issues found in 23 source files

$ ./.venv/Scripts/python.exe scripts/validate_resources.py
All localization resources are valid.
```

## Re-dokaz sva tri originalna Codex live-proba scenarija — nezavisno ponovljen

```text
BF-1: t('x') sa template "Broken {" -> 'Broken {' (warning logovan, nema exception)
BF-2: t('x') sa vrijednošću {'bad': 'nested'} -> '[missing:x]' (warning logovan, nema AttributeError)
BF-3: validate_i18n() na invalid JSON -> ["...: invalid JSON: Expecting property name..."] (nema neuhvaćenog JSONDecodeError)
```

## Zaključak

BF-1/2/3 zatvoreni, dokazano nezavisnim ponavljanjem originalnih Codex live-proba
scenarija, bez regresije (69/69 zeleno). Spreman za fresh Codex re-review na
`7df75c3`.
