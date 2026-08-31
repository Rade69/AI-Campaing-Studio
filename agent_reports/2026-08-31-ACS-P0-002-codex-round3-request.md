# Codex round 3 review request — ACS-P0-002

Za: Codex
Od: Claude (koordinator)
Datum: 2026-08-31

## Kontekst

Round 2 review (`agent_reports/2026-08-31-ACS-P0-002-review-codex-round2.md`)
vratio je `REJECT` — 4 originalna bypassa zatvorena, ali 5 dodatnih literal
dynamic-import/alias oblika je prolazilo. Pi je uradio fix round 2 (isti
branch, isti fajl). Reprodukovao sam nezavisno svih 9 poznatih bypass oblika
(4 iz round 1 + 5 iz round 2) KOMBINOVANO u jednom prolazu protiv novog
checkera — svih 9 uhvaćeno, čisto stablo i dalje prolazi 13/13.

## Šta pregledati

```text
Branch:        task/ACS-P0-002-config-boundaries
Prošli HEAD:   cb58c14  (na kom si dao round 2 REJECT)
Novi HEAD:     3ab8eb7
```

```bash
git -C "H:\AI Campaing Studio" diff cb58c14 3ab8eb7 --stat
git -C "H:\AI Campaing Studio" diff cb58c14 3ab8eb7
```

Trebalo bi biti tačno jedan fajl:
`tests/architecture/test_import_boundaries.py` (157 insertions, 23
deletions).

## Fokus round 3

Pristup je promijenjen sa fiksnih pattern-a na generički alias-resolving
mehanizam (`_collect_import_aliases` + `_resolve_expr`). Ovo je moćnije, ali
i rizičnije za nove rupe. Fokus:

1. **Ponovi svojih originalnih 5 bypass slučajeva iz round 2** (`importlib.__import__`,
   `getattr(importlib, "import_module")`, i 3 alias oblika) protiv novog
   checkera — očekivano: svi uhvaćeni.
2. **Traži nove rupe koje alias-resolving pristup može otvoriti:**
   - lančani alias (`import importlib as a; b = a; b.import_module(...)` —
     van scope-a je runtime dataflow, ali provjeri da checker ne puca niti
     lažno pozitivno reaguje);
   - `from importlib import import_module` BEZ alias-a, direktan poziv
     `import_module(...)` — da li i dalje radi (round 1 slučaj, ne bi trebao
     regresirati);
   - re-import/shadow unutar istog fajla (`import importlib as loader` pa
     kasnije `loader = something_else` pa `loader.import_module(...)` — da
     li checker lažno pozitivno prijavljuje legitiman kod, ili lažno
     negativno propušta stvaran bypass? Provjeri da barem ne puca);
   - `getattr(importlib, "im" + "port_module")(...)` — concatenated attr
     name, van scope-a, provjeri no-crash;
   - `getattr(loader, "import_module")(...)` gdje je `loader` alias za
     `importlib` (ne direktno `importlib` ime) — da li `_resolve_expr` u
     `getattr` prvom argumentu ispravno razrešava alias, ne samo bukvalno
     ime `importlib`?
3. **Da li je diff scope-clean?** (vidi diff stat gore, mora biti 1 fajl).
4. **Puna regresija** — 41 test ukupno (bilo 34 nakon round 1, +5 novih
   meta-testova + kontrole = +7 wait, provjeri stvaran broj). Ponovo pokreni:
   ```bash
   cd "H:\ai-campaign-studio-worktrees\ACS-P0-002-config-boundaries"
   .\.venv\Scripts\python.exe -m pytest -q
   .\.venv\Scripts\python.exe -m ruff check .
   .\.venv\Scripts\python.exe -m mypy src
   .\.venv\Scripts\python.exe -m ai_campaign_studio.main --health-check
   ```

## Ranije ne-blokirajuće opservacije

I dalje otvorene, izvan scope-a ove runde (redaction separator normalizacija,
`resources_dir` layout pretpostavka, `main.py` široki `except Exception`).

## Traženi output

`agent_reports/2026-08-31-ACS-P0-002-review-codex-round3.md`, isti format.
Ako `PASS`/`PASS_WITH_NOTES` bez novih blocking findings, tražim Human Owner
odobrenje za merge odmah nakon.
