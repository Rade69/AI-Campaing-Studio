---
verdict: REJECT
scope: PASS
acceptance: REJECT
architecture: REJECT
security: PASS
tests: REJECT
gitnexus_impact: UNKNOWN
blocking_findings:
  - "BF-1 OPEN: globalni alias map nije lexical-scope aware; bezazleni shadow import u drugoj funkciji može sakriti stvarni forbidden dynamic import."
---

# CILJ

Delta re-review ACS-P0-002 BF-1 fix runde između HEAD-ova `cb58c14` i
`3ab8eb7` na branch-u `task/ACS-P0-002-config-boundaries`, sa fokusom na novi
generički alias resolver i shadow/re-import ponašanje.

**URAĐENO:** `REJECT` — svih devet ranije poznatih bypass oblika sada se
hvataju i puni gate je zelen, ali scope-insensitive alias kolekcija uvodi novi,
reproducibilan false negative baš u shadow/re-import scenariju iz round-3
briefa. BF-1 ostaje otvoren.

**NE DIRATI:** Ne mijenjati produkcijski kod niti druge test fajlove. Fix ostaje
u `tests/architecture/test_import_boundaries.py`.

**SLJEDEĆE:** Pi treba učiniti alias resolution lexical-scope aware ili drugim
minimalnim AST pristupom spriječiti da import iz nepovezanog scope-a pregazi
alias koji koristi forbidden call. Potreban je novi FAIL→PASS meta-test i fresh
Codex re-review; nema merge-a.

# PROVJERENO

- Worktree:
  `H:\ai-campaign-studio-worktrees\ACS-P0-002-config-boundaries`.
- Branch: `task/ACS-P0-002-config-boundaries`.
- Novi HEAD: `3ab8eb7158b40f8afb3702e3ee9db696b14306f7`.
- Delta `cb58c14..3ab8eb7` je scope-clean: tačno jedan fajl,
  `tests/architecture/test_import_boundaries.py`, 157 insertions i 23
  deletions. `git diff --check` je čist.
- Tri untracked Pi evidence reporta nisu dio commita niti task delta.
- `_collect_import_aliases`, `_resolve_expr`, `_dynamic_import_target` i svi
  novi meta-testovi pročitani su u cjelini.
- Svih devet ranije poznatih BF-1 oblika sada se hvata:
  - relative `from .. import infrastructure`;
  - `importlib.import_module(literal)`;
  - bare `__import__(literal)`;
  - lowercase `flask`;
  - `importlib.__import__(literal)`;
  - `getattr(importlib, "import_module")(literal)`;
  - `import importlib as loader` alias;
  - `from importlib import import_module as load` alias;
  - `builtins.__import__(literal)`.
- `from importlib import import_module` bez aliasa i
  `getattr(loader, "import_module")` gdje je `loader` alias za `importlib`
  takođe se hvataju.
- Safe relative importi ne daju false positive.
- Lančani assignment alias i concatenated attribute/target stringovi ne ruše
  checker; ostaju neuhvaćeni kako round-3 brief dopušta za runtime dataflow i
  non-literal izraze.

# GITNEXUS / IMPACT

`UNKNOWN`, ne PASS. Iz aktivnog linked worktree-a:

```text
npx gitnexus status
Repository not indexed.

npx gitnexus detect-changes --scope compare --base-ref main --repo .
Error: Repository "." not found. Available: ..., AI Campaing Studio
```

Poznato worktree-binding ograničenje ostaje. Rezultat nije protumačen kao zero
impact; delta je kompenzaciono provjeren direktnim Git diffom i potpunim
čitanjem jedinog promijenjenog fajla.

# BLOCKING FINDINGS

## BF-1 ostaje otvoren — alias mapa miješa nepovezane lexical scope-ove

`_collect_import_aliases(tree)` koristi jedan globalni `dict[str, str]` za
cijeli modul i puni ga kroz `ast.walk`. Ne prati lexical scope niti mjesto
poziva. Zato isti lokalni alias iz druge funkcije može pregaziti stvarni
globalni `importlib` alias.

Reproducirani synthetic domain fajl:

```python
import importlib as loader

def evil():
    return loader.import_module(
        "ai_campaign_studio.infrastructure"
    )

def innocent():
    import types as loader
    return loader
```

Python lexical semantics su jednoznačne: `evil()` koristi globalni
`loader = importlib`, pa izvršava forbidden infrastructure import. Lokalni
`loader` u `innocent()` nema nikakav uticaj na `evil()`.

Novi checker ipak vraća praznu listu za taj fajl, jer globalna alias mapa na
kraju sadrži `loader -> types`. Kombinovana adversarial proba prikazuje:

```text
MISSED: [
  'domain/chain_alias.py',
  'domain/common/safe_dot.py',
  'domain/common/safe_parent.py',
  'domain/cross_scope_bypass.py',
  'domain/getattr_concat.py',
  'domain/target_concat.py'
]
```

Od toga su chain/concat slučajevi eksplicitno van scope-a, a safe relative
slučajevi namjerne kontrole. `domain/cross_scope_bypass.py` je stvarni novi
false negative i direktno pripada round-3 re-import/shadow fokusu.

Suprotni problem je takođe potvrđen: nakon
`import importlib as loader`, legitimni assignment `loader = Safe()` sa
vlastitom metodom `import_module()` i dalje se prijavljuje kao forbidden
import. Taj false positive je sekundaran; blocking razlog je false negative
koji dopušta stvarni architecture violation.

Minimalni fix treba vezati alias resolution za lexical scope i relevantno
source mjesto, ili koristiti drugi mali AST model koji ne dozvoljava da binding
iz nepovezane funkcije utiče na poziv. Obavezni meta-test mora sadržati gornji
`evil()`/`innocent()` primjer i dokazati FAIL na `3ab8eb7`, PASS poslije fixa.
Poželjna je i kontrola da eksplicitni assignment shadow ne proizvodi false
positive, ali ona nije glavni blocker.

# STANDARDNA VERIFIKACIJA

Nezavisno pokrenuto na `3ab8eb7`:

```text
python -m pytest -q -p no:cacheprovider
  --basetemp %TEMP%\codex-acs-p0-002-round3-pytest
.........................................                                [100%]
41 passed in 0.26s

python -m ruff check .
All checks passed!

python -m mypy --cache-dir %TEMP%\codex-acs-p0-002-round3-mypy src
Success: no issues found in 18 source files

python -m pip check
No broken requirements found.

python -m ai_campaign_studio.main --health-check
exit code 0
```

Health-check je pokrenut sa odobrenim pristupom zbog lokalnog log fajla izvan
sandbox write-roota. Temp/cache override-i su okolišni workaround i ne
mijenjaju test/type semantics.

# ADVERSARIALNA PROVJERA

PASS:

- svih devet prethodno poznatih bypassa sada se hvata;
- direct i aliased `getattr(import_module)` oblici se hvataju;
- direct `from importlib import import_module` se hvata;
- safe relative importi prolaze;
- chain/concatenated out-of-scope izrazi ne ruše checker;
- 41-test regresioni suite je zelen.

FAIL:

- import binding iz nepovezane funkcije može pregaziti alias mapu i sakriti
  stvarni forbidden call u drugom scope-u;
- assignment shadow može izazvati false positive.

# NE DIRATI U FIX RUNDI

Ne mijenjati `src/`, config, paths, logging/redaction, bootstrap/main,
dependencies ili druge test fajlove. Ne rješavati ranije ne-blokirajuće
opservacije. Ne uvoditi dependency-analysis biblioteku niti pokušavati
interpretirati proizvoljno runtime-generisane stringove ili chain assignment
dataflow.

# SLJEDEĆE

Pi radi još jednu usku BF-1 fix rundu samo u boundary checker fajlu, dodaje
scope-shadow FAIL→PASS meta-test i ponavlja puni gate. Koordinator provjerava
novi delta protiv `3ab8eb7` i vraća novi HEAD na fresh Codex review. Human
Owner ne treba odobriti merge dok scope-aware bypass ostaje reproducibilan.
