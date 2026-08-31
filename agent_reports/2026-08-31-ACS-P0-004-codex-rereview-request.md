# Codex re-review request — ACS-P0-004

Za: Codex
Od: Claude (koordinator)
Datum: 2026-08-31

## Kontekst

Tvoj review (`agent_reports/2026-08-31-ACS-P0-004-review-codex.md`):
`REJECT` sa BF-1 (blank `formats:` → TypeError), BF-2 (mutable cached
collections), BF-3 (case-varijanta duplicate supported_formats reference
prolazi). Crush je uradio usku fix rundu. Reprodukovao sam sva tri tvoja
originalna live-proba scenarija protiv popravljenog koda — sva tri sada
ispravno bacaju `RegistryError`/blokiraju mutaciju.

## Šta pregledati

```text
Branch:      task/ACS-P0-004-channel-registry
Prošli HEAD: d379813  (na kom si dao REJECT)
Novi HEAD:   6a2bd79
```

```bash
git -C "H:\AI Campaing Studio" diff d379813 6a2bd79 --stat
git -C "H:\AI Campaing Studio" diff d379813 6a2bd79
```

Tačno 3 fajla: `channels/definitions.py`, `channels/registry.py`,
`tests/unit/channels/test_registry.py`.

## Fokus re-reviewa

1. **Ponovi svoja tri originalna live-proba scenarija** (blank `formats:`,
   mutate-after-get, case-duplicate supported_formats) protiv novog koda.
2. **BF-2 fix nuspojave** — `tuple[str, ...]` umjesto `list[str]` mijenja
   javni tip vraćen iz `PlatformDefinition.supported_formats`/
   `content_rules`, `FormatDefinition.required_fields`/`optional_fields`,
   `VisualConstraints.supported_aspect_ratios`. Provjeri da li išta u
   `registry.py` ili testovima i dalje očekuje `list`-specifične operacije
   (npr. `.append()`, list concatenation) na tim poljima — `mypy` je prošao
   pa je tipski konzistentno, ali provjeri runtime ponašanje takođe.
3. **BF-3 fix mjesto** — duplicate-check je u `mode="before"` Pydantic
   validatoru, pa se dešava PRIJE ostalih validacija tog polja. Provjeri da
   redoslijed validacije (case-normalizacija → duplicate-check unutar iste
   funkcije) nema rupu za edge slučaj koji ti vidiš a ja nisam testirao
   (npr. duplikat koji NIJE case-varijanta nego already-identičan string,
   ili prazna `supported_formats: []` lista).
4. **Regresija** — 62 testa (59 prethodnih + 3 nova). Ponovo pokreni:
   ```bash
   cd "H:\ai-campaign-studio-worktrees\ACS-P0-004-channel-registry"
   .\.venv\Scripts\python.exe -m pytest -q
   .\.venv\Scripts\python.exe -m ruff check .
   .\.venv\Scripts\python.exe -m mypy src
   ```
5. **Scope-clean diff?** (mora biti tačno 3 fajla, sve u `allowed_paths`).

## Ranije ne-blocking napomena

`enabled: "true"` (string) Pydantic lax coercion u `bool True` — ostaje
otvorena, nije u scope-u ove fix runde (kako si i sam naveo).

## Traženi output

`agent_reports/2026-08-31-ACS-P0-004-review-codex-round2.md`, isti format.
Ako `PASS`/`PASS_WITH_NOTES` bez novih blocking findings, tražim Human Owner
odobrenje za merge.
