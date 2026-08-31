# ACS-P0-002 — fix round 3 brief (BF-1 — scope-aware alias resolution)

Za: Pi (isti branch)
Od: Claude (koordinator), poslije Codex round-3 REJECT-a
Datum: 2026-08-31

## Status

Codex round 3: `agent_reports/2026-08-31-ACS-P0-002-review-codex-round3.md`
— `verdict: REJECT`. Svih 9 ranije poznatih bypass oblika ostaju zatvoreni.
Novi nalaz: `_collect_import_aliases()` gradi JEDAN globalni `dict[str, str]`
za cijeli fajl (`ast.walk` bez scope tracking-a), pa lokalni import u jednoj
funkciji može pregaziti alias koji stvarno koristi druga, nepovezana
funkcija. Koordinator je reprodukovao nezavisno — test PROLAZI kad ne bi
trebalo.

**Task se i dalje NE spaja.** Treća fix runda na istom fajlu.

## Reprodukovan slučaj (mora postati meta-test)

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

`evil()` po Python lexical semantici koristi MODULE-level `loader` (=
`importlib`) jer `innocent()`-ov lokalni `loader` je u potpuno odvojenom
function scope-u i ne utiče na `evil()`. Trenutni checker to ne razlikuje —
`innocent()`-ov lokalni import pregazi globalnu mapu i sakrije `evil()`-ov
stvaran forbidden import.

## Zahtjev

Alias resolution mora postati **lexical-scope aware**, minimalno:

1. Umjesto jednog flat `dict[str, str]` za cio fajl, pratiti scope kao stack:
   modul-level scope + po jedan scope za svaki `FunctionDef`/`AsyncFunctionDef`
   (a razumno je i za `ClassDef`, iako to nije direktno traženo scenarijem).
   Jednostavan pristup: `ast.NodeVisitor` koji na `visit_FunctionDef`/
   `visit_AsyncFunctionDef` push-uje novi prazan scope dict na stack, rekurzivno
   posjećuje tijelo, pa ga pop-uje na izlazu — bindings unutar te funkcije ne
   smiju procuriti van, niti u sibling funkcije.
2. Import statement-i i `Call` čvorovi se registruju/rešavaju u SVOM
   trenutnom scope-u u vrijeme posjete (module-level import → module scope;
   import unutar funkcije → taj function scope).
3. Rešavanje imena (`_resolve_expr` ekvivalent) ide kroz scope chain od
   trenutnog ka spoljašnjem (LEGB stil, bez potrebe za full builtin/
   comprehension edge cases — dovoljno je module + function nivo za ovaj P0
   scope): prvo traži u najbližem enclosing function scope-u (ako je Call
   unutar funkcije), zatim u module scope-u.
4. NIJE potrebno rješavati dataflow kroz obične varijable (`b = a; b.foo()`)
   niti proizvoljne runtime re-assignment lance — to ostaje eksplicitno van
   scope-a (isto kao prethodne runde). Samo import-binding scope mora biti
   tačan.

## Obavezno

- Novi meta-test koji tačno reprodukuje `evil()`/`innocent()` primjer iznad
  (module-level alias korišten u jednoj funkciji, nepovezan shadow-import u
  drugoj) — mora dokazano FAIL-ovati na trenutnom (pre-fix) checkeru i
  PASS-ovati na popravljenom.
- Zadržati SVIH 13 postojećih testova zelenih (9 bypass oblika + 2 safe
  control + postojeći osnovni testovi) — nema regresije.
- Opciono, ako je jeftino: test da eksplicitni assignment shadow (`loader =
  Safe()` sa vlastitim `.import_module()` metodom) ne izazove false
  positive — Codex je ovo pomenuo kao sekundaran nalaz, nije blocking, ali
  vrijedi provjeriti da fix ne uvodi novi false-positive u tom smjeru.
- I dalje SAMO `tests/architecture/test_import_boundaries.py`. Ništa u
  `src/`, config, paths, logging/redaction, bootstrap/main, dependencies ili
  drugim test fajlovima.
- Ne uvoditi dependency-analysis biblioteku niti pokušavati interpretirati
  proizvoljan runtime dataflow/chain assignment — samo import-binding scope.

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

Koordinator provjerava novi delta protiv `3ab8eb7` (ne cijeli task), zatim
fresh Codex round 4. Human Owner odluka (2026-08-31): nastaviti fix rundu
umjesto da se cross-scope shadowing prihvati kao dokumentovano ograničenje —
ovo je stvaran correctness bug u checkeru, ne samo teoretski edge case.
