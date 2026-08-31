# Codex review request — ACS-P0-004

Za: Codex (adversarial/test reviewer)
Od: Claude (koordinator)
Datum: 2026-08-31

## Kontekst

Paralelni task uz ACS-P0-003 (localization, review se vodi odvojeno).
`allowed_paths` su disjoint — nema preklapanja. Implementer (Crush) nije
predao formalni self-report (isti obrazac kao ACS-P0-001) — koordinator je
rekonstruisao evidence direktno iz koda i komandi, uključujući izvršenje
oba obavezna adversarial dokaza.

## Read protocol

1. `AGENTS.md`, `CLAUDE.md`
2. `docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md` §14/§15
3. `.agent/CURRENT_STATE.md`
4. `agent_reports/ACS-P0-004-task-contract.md`
5. `agent_reports/2026-08-31-ACS-P0-004-crush-confirmed.md` (coordinator evidence)
6. Sam diff (vidi ispod)

## Šta pregledati

```text
Repo:     H:\AI Campaing Studio  (main branch)
Worktree: H:\ai-campaign-studio-worktrees\ACS-P0-004-channel-registry
Branch:   task/ACS-P0-004-channel-registry
Commit:   d379813 (base: main@a712ce3)
```

```bash
git -C "H:\AI Campaing Studio" diff main task/ACS-P0-004-channel-registry --stat
git -C "H:\AI Campaing Studio" diff main task/ACS-P0-004-channel-registry
```

Koristi merge-base diff za čist prikaz ako dva-tačka diff pokaže i
nepovezane koordinator commit-e:
`git diff $(git merge-base main task/ACS-P0-004-channel-registry) task/ACS-P0-004-channel-registry`.
Svi fajlovi ovog taska su NOVI. GitNexus `detect-changes` iz worktree-a neće
raditi (poznato ograničenje) — tretiraj kao `UNKNOWN`.

## Napomena o environment-u

Fresh `.venv` napravljen za review je imao 2 oštećena native-wheel
install-a (`pydantic_core`, mypy-jev `librt`), nevezano za kod — riješeno sa
`pip install --force-reinstall --no-cache-dir pydantic pydantic-core mypy`.
Ako naiđeš na isto u svom environment-u, isti fix bi trebalo da pomogne;
ako ne pomogne, tretiraj kao environment ograničenje (kao mypy cache-dir
problem u ACS-P0-001/002 rundama), ne kao defekt u kodu.

## Fokus review-a

1. **Duplicate/unknown-reference testovi** (već izvršeni od koordinatora,
   FAIL→PASS potvrđeno) — ponovi nezavisno da potvrdiš.
2. **Cross-file duplicate detection** — trenutni `_load()` gradi
   `by_code` per-platform (resetuje se za svaki YAML fajl), ali `formats`
   (globalni `dict[tuple[str,str], FormatDefinition]`) je keyed po
   `(platform.code, fmt.code)` — format kodovi se NE moraju biti unique
   cross-platform (isti format code npr. `STORY` postoji i za Instagram i
   Facebook i Snapchat, što je namjerno i ispravno). Potvrdi da nema
   greške u ovoj pretpostavci — probaj scenario gdje dva RAZLIČITA
   platform fajla imaju isti platform `code` ali različit sadržaj (već
   pokriveno testom), i scenario gdje YAML `formats:` blok referencira
   format code koji postoji na DRUGOJ platformi ali ne na svojoj (mora biti
   odbijen kao unknown reference).
3. **Malformed/edge-case YAML** — prazan `formats:` blok sa neprazan
   `supported_formats:` (mora dati unknown-reference RegistryError, ne
   IndexError/KeyError); YAML sa `enabled` kao string `"true"` umjesto bool
   (Pydantic strict/lax coercion — provjeri stvarno ponašanje); potpuno
   prazan YAML fajl (`{}` ili prazan sadržaj) u `resources/platforms/` —
   da li baca čitljiv `RegistryError` ili nešto ružnije.
4. **Case-sensitivity u code normalizaciji** — `PlatformDefinition.code` i
   `supported_formats` se normalizuju na uppercase preko field_validator,
   ali da li `FormatDefinition.code` (u `formats:` bloku) prolazi kroz istu
   normalizaciju prije poređenja sa `supported_formats`? Provjeri edge
   case: platform YAML sa `supported_formats: [story]` (lowercase) i
   `formats: [{code: STORY, ...}]` (uppercase) — da li se poklapaju poslije
   normalizacije?
5. **Regresija/standardna verifikacija** — ponovo pokreni nezavisno:
   ```bash
   cd "H:\ai-campaign-studio-worktrees\ACS-P0-004-channel-registry"
   .\.venv\Scripts\python.exe -m pytest -q
   .\.venv\Scripts\python.exe -m ruff check .
   .\.venv\Scripts\python.exe -m mypy src
   ```
   (worktree ima svoj `.venv`, kreiran od koordinatora).

## Traženi output

`agent_reports/2026-08-31-ACS-P0-004-review-codex.md`, isti format kao
`agent_reports/2026-08-31-ACS-P0-004-review-claude.md`.

Ako `PASS`/`PASS_WITH_NOTES` bez blocking findings, tražim Human Owner
odobrenje za merge (nezavisno od ACS-P0-003 statusa).
