---
verdict: REJECT
scope: PASS
acceptance: REJECT
architecture: PASS
security: PASS
tests: REJECT
gitnexus_impact: UNKNOWN
blocking_findings:
  - "BF-1 OPEN: `Translator.t()` može baciti neuhvaćen `ValueError` za malformed format template."
  - "BF-2 OPEN: i18n validator prihvata nested/non-string JSON vrijednosti, a `Translator.t()` zatim puca sa `AttributeError`."
  - "BF-3 OPEN: invalid JSON može srušiti `validate_i18n()` prije readable validation error-a zbog `_duplicate_keys()` poziva izvan JSONDecodeError handling-a."
---

# CILJ

Nezavisni Codex adversarial/test review ACS-P0-003 (Localization EN/BHS +
BHS regional resources), commit `0c23bcf` na
`task/ACS-P0-003-localization`, prema
`agent_reports/ACS-P0-003-task-contract.md` i
`agent_reports/2026-08-31-ACS-P0-003-codex-review-request.md`.

**URAĐENO:** `REJECT` — osnovni translator fallback, i18n parity, regional
YAML happy path i standardna verifikacija rade, ali tri realna edge case-a
krše graceful translator/resource-validation očekivanja.

**NE DIRATI:** Ne dirati ACS-P0-004 channel registry, Campaign/Content/Brand
slojeve, bootstrap/main, UI framework, fact/provenance logiku ili regionalnu
lingvističku bazu.

**SLJEDEĆE:** Pi/koordinator rade usku fix rundu u `translator.py`,
`scripts/validate_resources.py` i pripadajućim localization testovima.

# PROVJERENO

- Worktree: `H:\ai-campaign-studio-worktrees\ACS-P0-003-localization`.
- Branch: `task/ACS-P0-003-localization`.
- HEAD: `0c23bcf`.
- Merge-base: `a712ce3f78b40e157c4aa9aa4190167f87294e77`.
- Diff `a712ce3..0c23bcf`: 15 novih fajlova, 699 insertions, sve u
  ACS-P0-003 `allowed_paths`.
- `forbidden_paths` nisu dirani: `channels/`, `ai_registry/`,
  `infrastructure/`, `domain/{brand,campaign,content}/`, `bootstrap.py`,
  `main.py`, `presentation_*`.
- Pročitani su `enums.py`, `language_context.py`, `translator.py`,
  `ports/localization.py`, `scripts/validate_resources.py`, svi i18n JSON,
  svi regional YAML fajlovi i localization testovi.

Pozitivno potvrđeno:

- `TranslatorPort` je framework-neutral.
- `ContentLanguageContext` nema fact/provenance logiku.
- Regional YAML fajlovi imaju prazne liste i ne izmišljaju BS/SR/HR razlike.
- Duplicate JSON key detekcija stvarno radi kada JSON sintaksno može biti
  parsiran: live probe vraća `duplicate JSON keys: ['a']`.
- `version: "1"` u regional YAML-u se odbija kao integer type error.
- Dodatni YAML field se trenutno toleriše; to nije eksplicitno zabranjeno u
  kontraktu i nije blocker.
- `language_family=BHS`, `regional_variant=NEUTRAL`, `locale=EN` se prihvata.
  To tretiram kao non-blocking jer Faza 0.6 eksplicitno razdvaja UI locale i
  generated-content language context.

# GITNEXUS / IMPACT

`UNKNOWN`, ne PASS. Iz aktivnog linked worktree-a:

```text
npx gitnexus status
Repository not indexed.
Run: gitnexus analyze

npx gitnexus detect-changes --scope compare --base-ref main --repo .
Error: Repository "." not found. Available: ..., AI-Campaing-Studio
```

Poznato worktree-binding ograničenje kompenzovano je merge-base diffom,
čitanjem svih novih fajlova, full verification i živim edge-case probama.

# BLOCKING FINDINGS

## BF-1 — malformed template u katalogu ruši `Translator.t()`

`translator.py` na liniji 61 poziva `template.format(**params)`, a na liniji
62 hvata samo `KeyError` i `IndexError`. `str.format` za malformed template,
npr. `"Broken {"`, baca `ValueError`, koji izlazi iz `t()`.

Live probe:

```text
malformed_template: UNHANDLED ValueError -> Single '{' encountered in format string
```

Ovo je direktno iz Codex briefa: "da li `t()` ikad može baciti neuhvaćenu
exception (npr. malformed template string sa `{` bez zatvaranja)". Trenutno
može. Pošto i18n resource validator ne provjerava format-string sintaksu,
jedna loša translation vrijednost može srušiti UI call na `t()`.

Minimalni fix: uhvatiti `ValueError` u interpolaciji kao graceful warning +
return original template, ili validirati format stringove u
`validate_resources.py` i `Translator._load()`. Dodati unit test za malformed
template.

## BF-2 — nested/non-string JSON vrijednosti prolaze validator, pa translator puca

`validate_resources.py` provjerava da je cijeli katalog `dict` i da key-set
odgovara, ali ne provjerava da su vrijednosti `str`. `Translator._load()`
takođe vraća `dict[str, str]` tip, ali runtime ne validira vrijednosti prije
nego što `t()` pozove `.format`.

Live probe:

```text
validate_i18n_nested: []
nested_value: UNHANDLED AttributeError -> 'dict' object has no attribute 'format'
```

Minimalni reproducible katalog:

```json
{
  "app.title": {"bad": "nested"},
  "...": "svi ostali obavezni ključevi kao stringovi"
}
```

Validator ga prihvata bez greške, a translator zatim puca kad se zatraži
`app.title`. Ovo krši pretpostavku `dict[str, str]` i acceptance da translator
bude stabilan framework-neutral resource layer.

Minimalni fix: u `validate_i18n()` odbiti svaki non-string value sa readable
errorom; po mogućnosti isto provjeriti u `Translator._load()` da runtime ne
zavisi samo od vanjskog validatora. Dodati integration/unit test za nested
object value.

## BF-3 — invalid JSON može srušiti validator prije readable error-a

U `validate_i18n()`, `_duplicate_keys(raw)` poziva `json.loads(...)` prije
kasnijeg `try: json.loads(raw) except JSONDecodeError`. Zato invalid JSON ne
daje uredan validation error nego baca `JSONDecodeError` iz duplicate-key
prechecka.

Live probe:

```text
validate_i18n_invalid_json: UNHANDLED JSONDecodeError -> Expecting value: line 1 column 15 (char 14)
```

Kontrakt traži valid JSON provjeru i CLI validator sa exit 0/1 ponašanjem, ne
traceback iz helpera.

Minimalni fix: uhvatiti `JSONDecodeError` oko `_duplicate_keys()` ili spojiti
duplicate-key i parse check u jedan helper koji vraća `(data, duplicates,
errors)`. Dodati test da invalid JSON vrati error list / CLI exit 1 bez
neuhvaćenog traceback-a.

# STANDARDNA VERIFIKACIJA

Pokrenuto nezavisno u ACS-P0-003 worktree-u:

```text
.\.venv\Scripts\python.exe -m pytest -q
.................................................................        [100%]
65 passed in 0.36s

.\.venv\Scripts\python.exe -m ruff check --no-cache .
All checks passed!

.\.venv\Scripts\python.exe -m mypy src
Success: no issues found in 23 source files

.\.venv\Scripts\python.exe scripts\validate_resources.py
All localization resources are valid.

git diff --check a712ce3 0c23bcf
exit 0, no output
```

Napomena: obični `ruff check .` je u sandboxu pao samo zato što nije mogao
pisati `.ruff_cache` u linked worktree; rerun sa `--no-cache` je čist.

# ADVERSARIALNA PROVJERA

Live probe output:

```text
set_locale str: ValueError OK -> Unsupported locale: 'NOPE'
set_locale object: ValueError OK -> Unsupported locale: <object object at ...>
set_locale str_EN: accepted, get_locale='EN'
multi_partial: A {first} B {second}
malformed_template: UNHANDLED ValueError -> Single '{' encountered in format string
nested_value: UNHANDLED AttributeError -> 'dict' object has no attribute 'format'
mixed_context: BHS NEUTRAL EN
validate_i18n_nested: []
validate_i18n_duplicate: ["... duplicate JSON keys: ['a']", ...]
validate_i18n_invalid_json: UNHANDLED JSONDecodeError -> Expecting value: line 1 column 15 (char 14)
validate_yaml_version_string_extra: ["... 'version' must be an integer"]
```

Existing adversarial claims iz implementer/koordinator evidence-a su
vjerodostojni za svoje ciljeve: fallback-to-EN test i key-set parity test
razlikuju good/bad varijantu. Novi nalazi su izvan ta dva testirana
invarianta, ali unutar Codex brief focus-a.

# NE DIRATI U FIX RUNDI

Ne uvoditi UI framework, regionalne terminološke razlike, Campaign/Content
logiku, fact/provenance polja, provider/model handling, niti mijenjati
ACS-P0-004 registry. Fix treba ostati u localization/resource validator
površini.

# SLJEDEĆE

Uska fix runda:

1. `Translator.t()` ne smije baciti na malformed format template ili
   non-string catalog value.
2. `scripts/validate_resources.py` mora odbiti non-string i18n vrijednosti i
   invalid JSON prijaviti bez traceback-a.
3. Dodati regression testove za BF-1/BF-2/BF-3, pokrenuti full verification,
   pa vratiti Codexu na re-review.
