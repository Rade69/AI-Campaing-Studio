# ACS-F1-040 — Pi implementer handoff (sažetak sesije)

Datum: 2026-09-05
Uloga: Pi (implementer)
Task: ACS-F1-040 — hitan CI fix (hardkodovana Windows font putanja u `PillowRenderer`)
Status na kraju sesije: **MERGED u main** (koordinator je mergovao dok je implementacija tekla; vidi niže).

## Šta je bio problem

CI (`.github/workflows/ci.yml`, `ubuntu-latest`) bio je crven na `main` jer je
`selected_renderer.py` imao `_FONT_PATH_BOLD = r"C:\Windows\Fonts\seguisb.ttf"`
i `_FONT_PATH_REG = r"C:\Windows\Fonts\segoeui.ttf` — putanje koje postoje samo
na Windows-u. Na Linuxu je `_load_font()` TIho padao na
`ImageFont.load_default()` (bitmap font, drugačije metrike), što je lomilo
2 piksel-tačna testa + 1 kaskadni gate test. Lokalni Windows run je uvijek bio
zelen, pa problem niko nije vidio dok se CI nije ručno provjerio.

## Šta sam uradio (redom)

1. Skinut **Noto Sans Regular + Bold** (TrueType, statične instance) iz
   `googlefonts/noto-fonts` repoa u `resources/fonts/`, zajedno sa
   `resources/fonts/OFL.txt` (SIL OFL 1.1).
2. Glyph coverage za BHS dijakritike (č ć š đ ž) potvrđen programski preko
   Pillow `font.getbbox` (nijedan `MISSING` na oba fajla).
3. `selected_renderer.py`:
   - `_FONTS_DIR = AppPaths().resources_dir / "fonts"` (isti obrazac kao ostali
     bundle-ovani resursi).
   - `_FONT_PATH_BOLD`/`_FONT_PATH_REG` sada pokazuju na `NotoSans-Bold.ttf` /
     `NotoSans-Regular.ttf`; hardkodovane `C:\Windows\Fonts\...` putanje uklonjene.
   - Fallback na `ImageFont.load_default()` ZADRŽAN kao odbrambena mjera, ali je
     sada GLASAN (`warnings.warn` umjesto tihog pada).
4. Potvrđeno da NEMA package-data/MANIFEST mehanizma za `resources/` — čita se
   repo-relativno preko `AppPaths`, pa `resources/fonts/` prati isti obrazac
   (nema dodatnih `pyproject.toml` izmjena).

## Verifikacija (dokazi)

Lokalno (Windows):
- `python -m pytest tests/unit/infrastructure/rendering/ -v` → 14 passed
- `python -m pytest -q` (cijeli suite) → 960 passed, 0 fail
- `python -m ruff check .` → All checks passed
- `python -m mypy src` → no issues found in 168 source files

GitHub Actions (ubuntu-latest) — PR #1:
- job `test` → `success`
- `ruff` All checks passed, `pytest` **960 passed**, `Validate bundled resources`
  ok, `Health check` ok.

## Napomene (važno za kontinuitet)

1. **Environment fix (ne kod):** lokalni `test_gate_report_against_current_repo_passes`
   je prvo padao sa `package_import: false` jer je dijeljeni editable install
   pokazivao na VEĆ UKLONJENI worktree `ACS-F1-019-google-adapter`. Popravljeno sa
   `python -m pip install -e . --no-deps` (environment-only, nije dio diff-a).
   Na CI-u je `pip install -e ".[dev]"` svjež pa se ovo ne pojavljuje.
2. **`ci.yml` triger:** workflow pokreće CI samo na `push`→`main` i
   `pull_request`→`main`. Zato je CI na task branch-u mogao biti pokrenut SAMO
   preko PR-a. Kreiran je PR #1: https://github.com/Rade69/AI-Campaing-Studio/pull/1
3. **Worktree/branch:** `H:/ai-campaign-studio-worktrees/ACS-F1-040-bundle-open-font`,
   branch `task/ACS-F1-040-bundle-open-font`, commit `707fdf9`.

## Šta se desilo poslije (dok je sesija tekla)

Koordinator je, dok sam ja radio, već:
- Mergovao PR #1: merge commit `81e0e01` → **ACS-F1-040 je u main-u.**
- Ažurirao `.agent/CURRENT_STATE.md` (`912e234` "ACS-F1-040 merged -- CI is green again").
- Otvorio **ACS-F1-041** (`4c1045a` task contract): "font-missing must be
  RENDER_ERROR, add font validation" — follow-up na ovaj task.
- Ažurirao CURRENT_STATE ponovo (`56d9099`, ChatGPT review findings + Human Owner
  decisions o branch protection / roadmap).

Main HEAD na kraju sesije: `56d9099`.

## Napomena o stanju lokalnog working tree-a (main)

Dok sam čistio svoje lokalne duplikate, u jednom trenutku sam obrisao
`resources/fonts/` iz main working tree-a misleći da su još untracked — ali je
main u međuvremenu već bio mergovan, pa su bili tracked. ODMAH vraćeno sa
`git restore resources/fonts/`. Trenutno main working tree nema mojih zaostalih
izmjena. Preostale lokalne izmjene koje NISU moje: `AGENTS.md`, `CLAUDE.md`
(gitnexus blokovi, uncommitted) i razni `??` fajlovi (`.tmp_*`, `docs/...`).

## Šta je sljedeće (za novu sesiju)

- ACS-F1-040 je zatvoren (merged). Nema preostalog posla na njemu.
- Ako nova sesija nastavlja kao Pi: sljedeći otvoreni task je vjerovatno
  **ACS-F1-041** (font-missing → RENDER_ERROR + font validation) — pročitati
  `agent_reports/ACS-F1-041-task-contract.md` i `.agent/CURRENT_STATE.md` prije rada.
- Obavezni read-set prije bilo kakvog rada ostaje po `AGENTS.md`.
