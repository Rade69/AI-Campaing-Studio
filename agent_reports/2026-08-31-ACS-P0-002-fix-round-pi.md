# ACS-P0-002 — fix round evidence (BF-1) — coordinator-confirmed

**Implementer:** Pi — vlastiti report:
`agent_reports/2026-08-31-ACS-P0-002-pi-fix-round.md` (u worktree-u,
nekomitovan van `allowed_paths` — pročitan i potvrđen)
**Branch/worktree:** `task/ACS-P0-002-config-boundaries`,
`../ai-campaign-studio-worktrees/ACS-P0-002-config-boundaries`
**Prethodni HEAD:** `c6fa0b8` (Codex REJECT na ovom commitu)
**Novi commit:** `cb58c14` (author Pi, committed by coordinator)

## Diff protiv c6fa0b8 — nezavisno potvrđeno

```text
tests/architecture/test_import_boundaries.py | 132 ++++++++++++++++++++++++---
1 file changed, 120 insertions(+), 12 deletions(-)
```

Tačno jedan fajl, kako fix-round brief traži. Ništa iz "NE DIRATI" liste
(`AppSettings`, `AppPaths`, `Bootstrap`, logging, error taxonomy, package
seam-ovi, dependencies, health-check ponašanje) nije dirnuto — potvrđeno
`git diff cb58c14 c6fa0b8 --stat` pokazuje samo taj jedan fajl.

## BF-1 fix — pročitan cio fajl

- Relative import: `_iter_imports` sada prima `package` (puni
  `ai_campaign_studio...` put skeniranog fajla, iz `_package_for`) i
  razrešava `node.level` protiv njega umjesto da `continue`-uje na
  `node.level > 0`. Provjerio sam aritmetiku ručno za `domain/evil.py`
  (`from .. import infrastructure` → `ai_campaign_studio.infrastructure`) i
  za dvostruko ugniježđen slučaj (`domain/common/x.py`, level 2 → i dalje
  ispravno cilja `ai_campaign_studio.domain.y`) — tačno.
- Dynamic import: `_dynamic_import_target()` prepoznaje
  `importlib.import_module(...)`, direktno importovan `import_module(...)`,
  i `__import__(...)`, samo sa `ast.Constant` string argumentom (ne pokušava
  riješiti runtime-konstruisane stringove — u skladu sa "nije potrebno
  rješavati proizvoljno runtime-konstruisane stringove" iz brief-a).
- Case bug: `_WEB_MODULES` je `{"requests", "flask", "fastapi"}` (bilo
  `{"requests", "Flask"}"`). Provjereno da `application`/`ports`/`presentation`
  namjerno NE nasljeđuju `_WEB_MODULES` — to odgovara P0.10 tekstu specifikacije
  (samo `domain/` eksplicitno zabranjuje `requests`/`Flask`), nije regresija.

## Adversarial re-dokaz — nezavisno ponovljen od strane koordinatora

Ubačena sva 4 BF-1 bypass fajla odjednom u `domain/` na POPRAVLJENOM
checkeru:

```text
$ pytest -q tests/architecture/test_import_boundaries.py::test_real_tree_has_no_boundary_violations
F
assert ["domain/_bf1...rastructure'"] == []
Left contains 4 more items, first extra item: "domain/_bf1_dunder.py: forbidden domain/ import 'PySide6'"
1 failed
```

Sva 4 bypass-a uhvaćena (ne samo jedan) — potvrđuje da fix pokriva sve, ne
samo test-specifične slučajeve. Nakon uklanjanja:

```text
$ pytest -q tests/architecture/
...... [100%]
6 passed
```

## Standardna verifikacija — nezavisno ponovljena

```text
python -m pytest -q        → 34 passed
python -m ruff check .     → All checks passed!
python -m mypy src         → Success (18 source files)
--health-check              → exit 0
```

## Zaključak

BF-1 zatvoren, dokazano adversarialno. Task spreman za fresh Codex re-review
na novom HEAD-u `cb58c14`.
