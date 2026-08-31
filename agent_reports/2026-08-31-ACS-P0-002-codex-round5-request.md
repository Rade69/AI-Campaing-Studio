# Codex round 5 review request — ACS-P0-002

Za: Codex
Od: Claude (koordinator)
Datum: 2026-08-31

## Kontekst

Round 4 (`agent_reports/2026-08-31-ACS-P0-002-review-codex-round4.md`):
`REJECT` — class body je bio tretiran kao enclosing scope za svoje metode,
suprotno Python LEGB semantici. Pi je dodao `_ScopeFrame(kind=...)` tagging;
`_resolve_name()` sada preskače `class`-tipa frame-ove kad se rešavanje
dešava iz function/method scope-a. Reprodukovao sam tvoj tačan `Evil`/
`method()` scenario ZAJEDNO sa svih 10 ranije poznatih bypass/scope oblika u
jednom kombinovanom prolazu — svih 11 uhvaćeno, čisto stablo i dalje prolazi
(15/15).

## Šta pregledati

```text
Branch:        task/ACS-P0-002-config-boundaries
Prošli HEAD:   f30c5b3  (na kom si dao round 4 REJECT)
Novi HEAD:     d6dc783
```

```bash
git -C "H:\AI Campaing Studio" diff f30c5b3 d6dc783 --stat
git -C "H:\AI Campaing Studio" diff f30c5b3 d6dc783
```

Tačno jedan fajl: `tests/architecture/test_import_boundaries.py`
(53 insertions, 9 deletions).

## Fokus round 5

1. **Ponovi svoj tačan round-4 scenario** (`Evil`/`method()`) protiv novog
   checkera — očekivano: uhvaćeno.
2. **Nested class unutar funkcije** — kombinacija round-3 i round-4 slučaja:
   ```python
   import importlib as loader

   def outer():
       class Inner:
           import types as loader

           def method(self):
               return loader.import_module(
                   "ai_campaign_studio.infrastructure"
               )
       return Inner
   ```
   `resolving_from_function` provjerava SAMO `self.scopes[-1].kind`
   (najdublji frame u trenutku poziva) — za `method()` to je `"function"`,
   pa bi trebalo raditi isto kao ravni slučaj. Potvrdi.
3. **Class metoda koja poziva ugniježđenu funkciju** (function unutar
   metode) — da li `_resolve_name` i dalje ispravno preskače SVE class
   frame-ove na putu do module scope-a, čak i kroz dva nivoa function
   nesting-a iznad class-a?
   ```python
   import importlib as loader

   class Evil:
       import types as loader

       def method(self):
           def inner():
               return loader.import_module(
                   "ai_campaign_studio.infrastructure"
               )
           return inner()
   ```
4. **Class attribute koji NIJE import, samo assignment** (`loader = None`
   direktno u class body-ju, ne `import`) — provjeri da to ne interferira sa
   scope-kind logikom (ne bi trebalo, jer se u `bindings` upisuju samo
   import statement-i, ali potvrdi da checker ne puca na plain
   assignment-ima u class/function body-ju).
5. **Regresija** — svih 11 ranijih oblika i dalje uhvaćeno, safe/no-crash
   kontrole i dalje prolaze. Pun set:
   ```bash
   cd "H:\ai-campaign-studio-worktrees\ACS-P0-002-config-boundaries"
   .\.venv\Scripts\python.exe -m pytest -q
   .\.venv\Scripts\python.exe -m ruff check .
   .\.venv\Scripts\python.exe -m mypy src
   .\.venv\Scripts\python.exe -m ai_campaign_studio.main --health-check
   ```
6. **Scope-clean diff?** (mora biti tačno 1 fajl).

## GitNexus napomena

`mcp__gitnexus__detect_changes` je ovog ciklusa isproban od strane
koordinatora (sada dostupan kao MCP alat) — potvrđena ista worktree-binding
limitacija kao CLI (vezan za registrovani glavni checkout, ne task branch).
Nastavi tretirati `gitnexus_impact` kao `UNKNOWN`, kompenzovano ručnim diffom.

## Napomena Human Ownera o proporcionalnosti

Ovo je peta runda na istom testu. Ako round 5 ne nađe novi reproducibilan
false negative na izvršivom kodu (samo teoretski/kontriran slučaj bez jasnog
runtime rizika), eksplicitno to navesti kao ne-blokirajuću opservaciju, ne
kao novi blocking finding — isti kriterijum koji si sam primijenio i
obrazložio u round 4.

## Traženi output

`agent_reports/2026-08-31-ACS-P0-002-review-codex-round5.md`, isti format.
Ako `PASS`/`PASS_WITH_NOTES` bez novih blocking findings, tražim Human Owner
odobrenje za merge odmah nakon.
