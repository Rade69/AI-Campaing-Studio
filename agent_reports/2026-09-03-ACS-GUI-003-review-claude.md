# ACS-GUI-003 — koordinator review (Claude, 2026-09-03)

**Implementer:** Pi · **Reviewer:** Claude (koordinator, MEDIUM risk — §29,
Claude-only review dovoljan za merge) · **Verdict:** `PASS`

Worktree: `H:\ai-campaign-studio-worktrees\ACS-GUI-003-campaign-workflow-screens`
Branch: `task/ACS-GUI-003-campaign-workflow-screens`

## Nezavisna verifikacija (stvarno pokrenuto)

- Pregledao liniju-po-liniju svih 6 dirani/novi izvornih fajlova: `shell/__init__.py`
  (`stepper_html` helper), `_static_pages.py` (`WORKFLOW_ITEMS` + drugi loop), `kampanje/__init__.py`
  ("Otvori" real link), i sva 4 nova screen modula (`opis_kampanje`, `plan_kampanje`,
  `studio_sadrzaja`, `pregled_izvoz`) — svi tačno prate postojeći fixture/render_body/`__all__`
  pattern, sadrže tačan sadržaj iz mokapa.
- `git status --short`: sve izmjene u `allowed_paths` OSIM `kalendar/__init__.py` (vidi post-hoc
  scope napomena u kontraktu — koordinatorova ispravka sopstvene greške u pisanju kontrakta, ne
  implementer scope creep).
- Otkrivena i ispravljena poznata ".pth zamka" u worktree-u prije prvog test run-a.
- `python -m pytest -q` → **618 passed** (uključujući +9 novih testova koje je koordinator dodao
  tokom live-fix runde).
- `python -m ruff check src tests scripts` / `python -m mypy src` / `test_import_boundaries.py` →
  svi čisti.
- R1 (Pi): `test_write_all_pages_relative_links_resolve_to_real_files` ispravno proširen da
  strip-uje `?campaign=` query prije filesystem rezolucije — potvrđeno ispravno, ne slabljenje testa.
- R2 (Pi): `test_shell.py` je nov fajl, opravdano (crumbs parametar nije imao pokrivenost) — potvrđeno.

## Live vizuelna provjera (Human Owner ekran) — tri runde ispravki

Implementer nije mogao izvesti interaktivnu vizuelnu provjeru (harness bez UI-automatizacije,
dokumentovano u evidence-u). Koordinator je pokrenuo aplikaciju uživo na Human Owner-ovom ekranu
tri puta tokom review-a, sa fix-ovima između svake runde:

1. **Jezik sadržaja (Opis kampanje)** — Pi-jeva verzija (single-option `<select>`, kopija mokapa)
   nije nudila stvaran izbor. Koordinator iterirao kroz dva pokušaja do finalne verzije koju je
   Human Owner potvrdio: pravi `<select>` dropdown, SR/HR/BS/EN, bez "BHS" prefiksa, bez
   "neutralno" opcije.
2. **Kalendar — dead end u workflow-u.** Human Owner uočio da nakon koraka 3 (Kalendar) nema puta
   naprijed. Root cause: kontrakt je pogrešno stavio `kalendar/__init__.py` u `forbidden_paths`,
   iako je postojeći kod već najavljivao da ACS-GUI-003 treba da doda `?campaign=` banner tamo.
   Koordinator dodao skriveni stepper + "Nastavi na Studio sadržaja →" (otkriva ih POSTOJEĆI
   generički JS handler, `static/app.js` nedirano).
3. **Studio sadržaja — skrol + još jedan dead end.** Human Owner uočio vertikalni skrol i da nema
   načina da se stigne do Pregled i izvoz (export ekrana). Koordinator smanjio textarea min-height
   (180→120px) i dodao stvaran `<a>` link "Pregled i izvoz →".

Sve tri runde nezavisno re-testirane (pytest/ruff/mypy) prije sljedeće live provjere. Human Owner
potvrdio finalno stanje kao zadovoljavajuće za sve stavke iz ACS-GUI-003 scope-a.

## Poznat, namjerno odgođen item

Podešavanja ekran i dalje ima manji vertikalni skrol (postojeći, poznat od ACS-GUI-004,
izraženiji na trenutno sačuvanoj 830px visini prozora nego na 900px baseline-u). Human Owner
eksplicitno odlučio da se odgodi za zaseban budući task — van scope-a ACS-GUI-003, `podesavanja/`
ostaje netaknut (forbidden path).

## Zaključak

PASS. Merge odobren (MEDIUM risk, §29). Implementacija + tri runde live-verifikovanih ispravki
zadovoljavaju kontrakt i eksplicitan Human Owner feedback. Pun trag odluka u post-hoc scope
napomeni kontrakta.
