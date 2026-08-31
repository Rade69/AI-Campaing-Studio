---
verdict: REJECT
scope: PASS
acceptance: REJECT
architecture: REJECT
security: PASS
tests: REJECT
gitnexus_impact: UNKNOWN
blocking_findings:
  - "BF-1 OPEN: scanner pogrešno nasljeđuje class namespace u method scope, pa class-local import alias može sakriti stvarni forbidden module-level dynamic import."
---

# CILJ

Delta re-review ACS-P0-002 između `3ab8eb7` i `f30c5b3`, sa proporcionalnim
fokusom na nested closures i stvarnu Python class/method lexical semantiku.

**URAĐENO:** `REJECT` — round-3 cross-function bug je zatvoren, nested closure
i prethodni bypassi prolaze provjeru, ali scanner tretira class namespace kao
lexical parent metode. To proizvodi reproducibilan false negative na validnom
Python kodu koji runtime zaista izvršava preko forbidden module-level aliasa.

**NE DIRATI:** Ne mijenjati produkcijski kod ili druge testove. Fix ostaje u
`tests/architecture/test_import_boundaries.py` i treba biti ograničen na
class-to-method scope resolution.

**SLJEDEĆE:** Pi dodaje scope-kind semantiku tako da metoda preskače class
namespace pri unqualified name resolution, uz FAIL→PASS meta-test. Potreban je
fresh Codex re-review; nema merge-a.

# PROVJERENO

- Worktree:
  `H:\ai-campaign-studio-worktrees\ACS-P0-002-config-boundaries`.
- Branch: `task/ACS-P0-002-config-boundaries`.
- Novi HEAD: `f30c5b3933c7845d7160579338eaf1071ce22aac`.
- Delta `3ab8eb7..f30c5b3` je scope-clean: tačno jedan fajl,
  `tests/architecture/test_import_boundaries.py`, 137 insertions i 89
  deletions. `git diff --check` je čist.
- Četiri untracked Pi evidence reporta nisu dio commita niti delta diffa.
- `_ImportScanner(ast.NodeVisitor)` i svi novi testovi pročitani su u cjelini.
- Prethodni round-3 `evil()`/`innocent()` cross-function scenario sada se
  hvata; lokalni import u nepovezanoj funkciji više ne pregazi module alias.
- Dvonivojski nested closure `outer -> inner -> module` ispravno pronalazi
  module-level `importlib` alias i prijavljuje forbidden import.
- Two-class primjer iz briefa prolazi: metoda u `Evil` nalazi module alias,
  dok class-local import u odvojenom `Innocent` scope-u ne utiče na nju.
- Import nakon upotrebe u istoj funkciji i non-literal concatenated `getattr`
  ne ruše checker. Prvi je runtime-nevažeći (`UnboundLocalError`/`NameError`),
  a drugi je eksplicitno van literal-target scope-a; nijedan nije blocker.
- Svih ranijih direktnih, relative, lowercase, `getattr`, `__import__` i alias
  bypass oblika ostaje uhvaćen u regresionim testovima.

# GITNEXUS / IMPACT

`UNKNOWN`, ne PASS. Iz aktivnog linked worktree-a:

```text
npx gitnexus status
Repository not indexed.

npx gitnexus detect-changes --scope compare --base-ref main --repo .
Error: Repository "." not found. Available: ..., AI Campaing Studio
```

Poznato worktree-binding ograničenje nije protumačeno kao zero impact. Delta
je kompenzaciono provjeren direktnim Git diffom i potpunim čitanjem jedinog
izmijenjenog fajla.

# BLOCKING FINDINGS

## BF-1 ostaje otvoren — metode pogrešno nasljeđuju class import scope

Scanner radi `push` class scope-a, pa zatim prilikom posjete metodi radi još
jedan `push` function scope-a. `_resolve_name()` pretražuje oba scope-a unazad.
To ne odgovara Python semantici: class namespace nije enclosing lexical scope
za tijelo metode. Unqualified ime u metodi traži se u local/enclosing function/
global/builtins scope-ovima, ne u class atributima.

Reproducirani validni domain fajl:

```python
import importlib as loader

class Evil:
    import types as loader

    def method(self):
        return loader.import_module(
            "ai_campaign_studio.infrastructure"
        )
```

Stvarni runtime dokaz sa bezopasnim `math` targetom:

```text
RUNTIME_GLOBAL_IS_IMPORTLIB: importlib
RUNTIME_CLASS_LOADER: types
RUNTIME_METHOD_RESULT: math
```

Dakle `Evil.method()` koristi globalni `loader = importlib`; class atribut
`Evil.loader = types` nije dio method lexical resolutiona. Sa forbidden
literalom runtime bi zaista pokušao importovati
`ai_campaign_studio.infrastructure`.

Checker ipak ne prijavljuje `domain/same_class_shadow.py`, jer pronalazi
class-scope `loader -> types` prije module-scope `loader -> importlib`.
Kombinovana proba dala je:

```text
VIOLATIONS:
domain/getattr_alias.py: forbidden domain/ import 'ai_campaign_studio.infrastructure'
domain/nested_closure.py: forbidden domain/ import 'ai_campaign_studio.infrastructure'
domain/round3_scope.py: forbidden domain/ import 'ai_campaign_studio.infrastructure'
domain/two_classes.py: forbidden domain/ import 'ai_campaign_studio.infrastructure'

MISSED: [
  'domain/import_after_use.py',
  'domain/nonliteral_attr.py',
  'domain/same_class_shadow.py'
]
```

Prva dva propuštena slučaja su namjerne ne-blocking kontrole iz briefa.
`same_class_shadow.py` je stvarni correctness bug: validan je, izvršiv i
direktno dopušta architecture-boundary bypass.

### Proporcionalnost

Ovo nije proglašeno blockerom samo zato što postoji egzotičan AST oblik.
Razlog za blocker su tri konkretna uslova:

1. kod je validan Python i njegova runtime name resolution je nezavisno
   izvršena;
2. scanner i runtime daju suprotne odgovore o tome koji objekat ime označava;
3. nesklad propušta stvarni forbidden dynamic import, što je centralni
   acceptance invariant ovog HIGH taska.

Istina je da je ponovno korištenje istog aliasa u class namespace-u relativno
rijedak stil. Da je rezultat samo false positive na nevažećem ili
runtime-nedostižnom kodu, bio bi opservacija. Ovdje je rezultat false negative
na izvršivom kodu, pa prema eksplicitnoj odluci Human Ownera ostaje blocking.

Minimalni fix treba razlikovati scope frame vrste. Pri resolutionu iz metode
treba preskočiti class frame, ali i dalje omogućiti module scope i eventualni
enclosing function scope (npr. class definisan unutar funkcije). Nije potrebno
modelirati arbitrary runtime dataflow, lambde/comprehensions ili non-literal
module stringove u ovoj rundi.

# STANDARDNA VERIFIKACIJA

Nezavisno pokrenuto na `f30c5b3`:

```text
python -m pytest -q -p no:cacheprovider
  --basetemp %TEMP%\codex-acs-p0-002-round4-pytest
..........................................                               [100%]
42 passed in 0.32s

python -m ruff check .
All checks passed!

python -m mypy --cache-dir %TEMP%\codex-acs-p0-002-round4-mypy src
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

- svih prethodnih devet bypassa i round-3 cross-function shadow bypass;
- nested closure kroz dva function scope-a;
- metoda uz irrelevant import u odvojenoj klasi;
- safe/non-literal/invalid-order no-crash kontrole;
- 42-test puni regresioni suite.

FAIL:

- metoda uz same-class import shadow pogrešno se razrješava kroz class scope i
  stvarni forbidden module-level dynamic import ostaje neuhvaćen.

# NE DIRATI U FIX RUNDI

Ne mijenjati `src/`, config, paths, logging/redaction, bootstrap/main,
dependencies ili druge test fajlove. Ne rješavati ranije ne-blokirajuće
opservacije. Ne širiti checker na arbitrary runtime dataflow, lambde,
comprehensions ili non-literal import targete.

# SLJEDEĆE

Pi radi usku class/method lexical-scope fix rundu samo u boundary checker
fajlu, dodaje same-class shadow FAIL→PASS meta-test i ponavlja puni gate.
Koordinator provjerava novi delta protiv `f30c5b3` i vraća novi HEAD na fresh
Codex review. Human Owner ne treba odobriti merge dok ovaj izvršivi false
negative ostaje reproducibilan.
