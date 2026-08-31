# ACS-P0-002 — fix round 4 brief (BF-1 — class scope must not leak into methods)

Za: Pi (isti branch)
Od: Claude (koordinator), poslije Codex round-4 REJECT-a
Datum: 2026-08-31

## Status

Codex round 4: `agent_reports/2026-08-31-ACS-P0-002-review-codex-round4.md`
— `verdict: REJECT`. Round-3 cross-function shadowing je zatvoren, nested
closures i two-class primjer rade ispravno. Novi nalaz: scanner tretira
class body kao enclosing lexical scope za svoje metode, što NIJE tačna
Python semantika — unqualified ime unutar metode se traži u
local/enclosing-function/global/builtins scope-ovima, class namespace se
PRESKAČE.

Koordinator je reprodukovao dvostruko:
1. Test PROLAZI na sintetičkom fajlu kad ne bi trebalo (checker ga ne hvata).
2. Runtime dokaz (`Evil().method()` sa bezopasnim `math` target-om) potvrđuje
   da stvaran Python `loader.import_module(...)` unutar `method()` koristi
   MODULE-level `loader` (`importlib`), ne class-level `loader` (`types`) —
   tačno kako Codex tvrdi.

**Task se i dalje NE spaja.** Četvrta fix runda na istom fajlu.

## Reprodukovan slučaj (mora postati meta-test)

```python
import importlib as loader

class Evil:
    import types as loader

    def method(self):
        return loader.import_module(
            "ai_campaign_studio.infrastructure"
        )
```

`Evil.method()` po Python semantici koristi module-level `loader =
importlib` — class atribut `Evil.loader = types` NIJE dio method lexical
scope-a. Runtime to potvrđuje. Trenutni scanner ipak push-uje class scope
kao da je enclosing scope za metodu, pa `_resolve_name` nalazi
`loader→types` prije nego stigne do module scope-a — false negative na
izvršivom kodu.

## Zahtjev

Scope frame mora nositi svoju vrstu (`module` / `function` / `class`).
Pri `_resolve_name` (upward walk kroz `self.scopes`):

1. Ako se rešavanje dešava iz FUNCTION scope-a (uključujući ugniježđene
   funkcije/metode), **preskočiti svaki `class`-tipa frame** pri penjanju uz
   stack — nastaviti direktno na sljedeći `function` ili `module` frame iza
   njega. Ovo odgovara stvarnoj Python LEGB semantici (class scope nije dio
   enclosing scope chain za ugniježđene funkcije).
2. Ako se rešavanje dešava direktno u CLASS body-ju (nije unutar metode,
   npr. dynamic import poziv pisan direktno kao class attribute statement),
   taj class scope i dalje važi kao trenutni (lokalni) scope za to mjesto —
   samo se ne prenosi dalje u ugniježđene metode. (Rijedak slučaj, nije
   fokus Codex-ovog nalaza, ali ne smije regresirati postojeće ponašanje za
   taj oblik ako je pokriven testom.)
3. Module scope ostaje uvijek dostupan na dnu chain-a, bez obzira na broj
   class/function nivoa između.
4. Ne mijenjati ponašanje za funkcije unutar funkcija (round-3 nested
   closure slučaj) — te enclosing function scope-ove treba i dalje
   pretraživati normalno, samo se class frame-ovi preskaču.

## Obavezno

- Novi meta-test koji tačno reprodukuje `Evil`/`method()` primjer iznad —
  mora dokazano FAIL-ovati na trenutnom (pre-fix) checkeru i PASS-ovati na
  popravljenom.
- Zadržati SVIH 14 postojećih testova zelenih (10 bypass/scope oblika + 2
  safe/no-crash control + osnovni testovi) — bez regresije, uključujući
  round-3 nested-closure i two-class scenario koje je Codex već potvrdio da
  rade.
- I dalje SAMO `tests/architecture/test_import_boundaries.py`. Ništa u
  `src/`, config, paths, logging/redaction, bootstrap/main, dependencies ili
  drugim test fajlovima.
- Ne modelirati arbitrary runtime dataflow, lambde, comprehensions, niti
  non-literal import targete (i dalje van scope-a).

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

Koordinator provjerava novi delta protiv `f30c5b3` (ne cijeli task), zatim
fresh Codex round 5. Codex je u round 4 eksplicitno primijenio
proporcionalnost (naglasio da bi false positive na nevažećem kodu bio samo
opservacija, ali ovo je false negative na izvršivom kodu pa ostaje
blocking) — ista mjerila se primjenjuju i na round 5.
