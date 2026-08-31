# Codex re-review request — ACS-P0-002 (BF-1 fix round)

Za: Codex
Od: Claude (koordinator)
Datum: 2026-08-31

## Kontekst

Tvoj prethodni review (`agent_reports/2026-08-31-ACS-P0-002-review-codex.md`)
vratio je `REJECT` sa `BF-1` (boundary checker propušta relative import,
dynamic `importlib.import_module`/`__import__`, i case bug `Flask`/`flask`).
Nalaz je bio ispravan — reprodukovao sam ga nezavisno prije nego što sam
tražio fix.

Pi je uradio usku fix rundu, samo na
`tests/architecture/test_import_boundaries.py`. Ovo NIJE novi task — isti
branch, delta review, ne cijeli task ponovo.

## Šta pregledati

```text
Branch:        task/ACS-P0-002-config-boundaries
Prošli HEAD:   c6fa0b8  (na kom si dao REJECT)
Novi HEAD:     cb58c14
```

```bash
git -C "H:\AI Campaing Studio" diff c6fa0b8 cb58c14 --stat
git -C "H:\AI Campaing Studio" diff c6fa0b8 cb58c14
```

Trebalo bi biti TAČNO jedan fajl:
`tests/architecture/test_import_boundaries.py` (120 insertions, 12
deletions). Ako vidiš bilo šta drugo promijenjeno, to je scope violation —
prijavi kao novi blocking finding (fix runda nije smjela dirati ništa drugo).

## Fokus re-reviewa

1. **Da li su sva 4 tvoja originalna bypass-a stvarno zatvorena?**
   Ponovi svoju originalnu adversarial probu (relative import, dva dynamic
   import oblika, lowercase `flask`) protiv NOVOG checkera. Očekivano: sva 4
   FAIL-uju (checker ih hvata).
2. **Da li relative-import resolucija ima svoju rupu?** Pi je dodao
   `_package_for()` + level-arithmetic. Probaj granične slučajeve koje
   originalni fix možda nije pokrio — npr. `from . import x` (level 1, ne
   level 2), duboko ugniježđen fajl (`domain/common/x.py`) sa `from ... import
   y` (level 3, ako uopšte validno na ovoj dubini paketa), ili relative
   import koji cilja NEŠTO DRUGO osim forbidden prefiksa (treba da prođe,
   ne treba false-positive).
3. **Da li dynamic-import detekcija ima svoju rupu?** Probaj varijante koje
   test-only meta-testovi možda ne pokrivaju: `importlib.__import__(...)`,
   `getattr(importlib, "import_module")(...)`, string konkatenacija
   (`importlib.import_module("ai_campaign_studio" + ".infrastructure")`) —
   ovo POSLJEDNJE je van scope-a po brief-u ("ne treba rješavati proizvoljno
   runtime-konstruisane stringove"), samo provjeri da checker ne puca (ne
   baca exception) na takvom kodu, čak i ako ga ne hvata.
4. **Da li je nešto van `tests/architecture/test_import_boundaries.py`
   promijenjeno?** (vidi diff stat gore — mora biti tačno 1 fajl).
5. **Regresija na ostatku test suite-a** — 34 testa ukupno (bilo 30 prije
   fix runde, +4 nova meta-testa). Ponovo pokreni pun set:
   ```bash
   cd "H:\ai-campaign-studio-worktrees\ACS-P0-002-config-boundaries"
   .\.venv\Scripts\python.exe -m pytest -q
   .\.venv\Scripts\python.exe -m ruff check .
   .\.venv\Scripts\python.exe -m mypy src
   .\.venv\Scripts\python.exe -m ai_campaign_studio.main --health-check
   ```

## Ranije ne-blokirajuće opservacije (iz oba prethodna reviewa)

I dalje otvorene, nisu u scope-u ove fix runde, ne treba ih ponovo prijavljivati
kao nove nalaze osim ako si otkrio da su zapravo ozbiljnije nego što smo
mislili:

- redaction ne normalizuje separatore (`x-api-key`/`api-key` prolaze ako ne
  sadrže neki od postojećih fragmenata doslovno);
- `AppPaths._default_resources_dir()` pretpostavlja source-tree layout;
- `main.py` široki `except Exception`.

## Traženi output

`agent_reports/2026-08-31-ACS-P0-002-review-codex-round2.md`, isti format
(YAML header + narativ). Ako je `verdict: PASS` ili `PASS_WITH_NOTES` bez
novih blocking findings, tražim Human Owner odobrenje za merge odmah nakon.
