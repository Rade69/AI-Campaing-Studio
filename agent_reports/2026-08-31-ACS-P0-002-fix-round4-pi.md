# ACS-P0-002 — fix round 4 evidence — coordinator-confirmed

**Implementer:** Pi — vlastiti report:
`agent_reports/2026-08-31-ACS-P0-002-pi-fix-round4.md` (pročitan i potvrđen)
**Prethodni HEAD:** `f30c5b3` (Codex round 4 REJECT)
**Novi commit:** `d6dc783` (author Pi, committed by coordinator)

## Diff protiv f30c5b3 — nezavisno potvrđeno

Tačno jedan fajl, `tests/architecture/test_import_boundaries.py`
(53 insertions, 9 deletions).

## Pristup — pročitan cio diff

`_ScopeFrame` dataclass (`kind: str`, `bindings: dict[str,str]`) zamjenjuje
goli `dict` u scope stack-u. `_resolve_name()`: ako je `self.scopes[-1].kind
== "function"` (rešavanje se dešava iz function/method tijela), svaki
`class`-tipa frame se preskače pri penjanju uz stack; rešavanje direktno u
class body-ju ostaje nepromijenjeno (class frame se ne preskače kad JE
trenutni scope). Ovo tačno odgovara Python LEGB semantici — class namespace
nikad nije enclosing scope za ugniježđenu funkciju/metodu.

## Adversarial re-dokaz — nezavisno ponovljen, KOMBINOVANO svih 11 oblika

Ubačen Codex-ov `Evil`/`method()` class-scope slučaj ZAJEDNO sa svih 10
ranije poznatih bypass/scope oblika (4 iz round 1 + 5 iz round 2 + 1 iz
round 3) u `domain/`, jedan kombinovan prolaz:

```text
$ pytest -q tests/architecture/test_import_boundaries.py::test_real_tree_has_no_boundary_violations
F
Left contains 11 more items, first extra item: "domain/_z1_relative.py: forbidden domain/ import 'ai_campaign_studio.infrastructure'"
1 failed
```

Svih 11 uhvaćeno, bez regresije. Nakon uklanjanja:

```text
$ pytest -q tests/architecture/
............... [100%]
15 passed
```

## Standardna verifikacija — nezavisno ponovljena

```text
python -m pytest -q        → 43 passed
python -m ruff check .     → All checks passed!
python -m mypy src         → Success (18 source files)
--health-check              → exit 0
```

## GitNexus MCP — isprobano ovog ciklusa

`mcp__gitnexus__detect_changes(repo="AI Campaing Studio", scope="compare",
base_ref="main")` sada je dostupan u ovoj (koordinator) sesiji. Rezultat:
ista worktree-binding limitacija kao CLI — vraća diff GLAVNOG registrovanog
checkout-a (`H:\AI Campaing Studio`, `list_repos` pokazuje taj path, 11
commit-a "behind"), ne task branch. Vidio je samo nekomitovane
AGENTS.md/CLAUDE.md izmjene iz glavnog radnog stabla. Ne rješava problem —
i dalje se oslanjamo na ručni diff/file review za MEDIUM/HIGH taskove dok
se worktree-binding ne riješi (npr. registracijom worktree-a kao zaseban
GitNexus repo, van scope-a trenutnog review ciklusa).

## Zaključak

Class-scope leak zatvoren, dokazano adversarialno, bez regresije na
prethodno zatvorenih 10 oblika. Spreman za fresh Codex round 5 na `d6dc783`.
