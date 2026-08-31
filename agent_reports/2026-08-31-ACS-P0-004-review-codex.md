---
verdict: REJECT
scope: PASS
acceptance: REJECT
architecture: REJECT
security: PASS
tests: REJECT
gitnexus_impact: UNKNOWN
blocking_findings:
  - "BF-1 OPEN: YAML sa praznim `formats:` blokom curi kao sirovi TypeError umjesto RegistryError."
  - "BF-2 OPEN: frozen Pydantic modeli sadrže mutable liste, pa caller može promijeniti cached registry state."
  - "BF-3 OPEN: duplirani supported_formats reference prolaze validaciju i list_formats vraća duplirane kodove."
---

# CILJ

Nezavisni adversarial/test review ACS-P0-004 (Channel/Platform/Format
registry) prema `agent_reports/ACS-P0-004-task-contract.md`, commit
`d379813` na `task/ACS-P0-004-channel-registry`.

**URAĐENO:** `REJECT` — osnovni data-driven flow, cross-file izolacija,
normalizacija i obavezni duplicate/unknown-reference testovi rade, ali tri
validna YAML/runtime scenarija krše error, immutability i uniqueness ugovore.

**NE DIRATI:** Ne mijenjati platformsku taksonomiju, Campaign Engine,
localization, bootstrap ili druge paralelne taskove. Fix treba ostati unutar
ACS-P0-004 `allowed_paths`.

**SLJEDEĆE:** Crush radi usku fix rundu u definitions/registry testovima;
koordinator potvrđuje delta i vraća novi HEAD na fresh Codex re-review. Nema
merge-a prije zatvaranja nalaza i eksplicitnog Human Owner odobrenja.

# PROVJERENO

- Worktree:
  `H:\ai-campaign-studio-worktrees\ACS-P0-004-channel-registry`.
- Branch: `task/ACS-P0-004-channel-registry`.
- HEAD: `d3798133bc7bc8b2086d41ba88687e72de0538a8`.
- Merge-base: `a712ce3f78b40e157c4aa9aa4190167f87294e77`.
- Delta je scope-clean: 16 novih fajlova, 946 insertions, svi unutar
  `allowed_paths`; `git diff --check` je čist.
- Pročitani su svi novi Python, test i devet platform YAML fajlova.
- Svih devet bundleovanih platformi i očekivani format primjeri odgovaraju
  P0.13 listi; nepotvrđeni numerički constraint-i ostaju `null`.
- Nema network/social API poziva, platform-specific `if`/`elif` grananja ili
  Campaign/Content business logike.

# GITNEXUS / IMPACT

`UNKNOWN`, ne PASS. Iz aktivnog linked worktree-a:

```text
npx gitnexus status
Repository not indexed.

npx gitnexus detect-changes --scope compare --base-ref main --repo .
Error: Repository "." not found. Available: ..., AI-Campaing-Studio
```

Poznato worktree-binding ograničenje kompenzovano je merge-base diffom,
čitanjem svih novih fajlova i živim API/YAML probama. Rezultat nije
protumačen kao zero impact.

# BLOCKING FINDINGS

## BF-1 — prazan `formats:` blok izbacuje sirovi `TypeError`

`PlatformRegistry._load()` radi:

```python
for raw_format in raw.get("formats", []):
```

Za validan YAML zapis `formats:` bez vrijednosti `yaml.safe_load()` vraća
`None`. Iteracija zato završava izvan registry error taxonomy-ja:

```yaml
code: ALPHA
display_name: Alpha
channel: SOCIAL
supported_formats: [STORY]
formats:
```

Živi rezultat:

```text
formats_blank_key ERR TypeError 'NoneType' object is not iterable
```

Isti semantički slučaj sa `formats: []` ispravno daje:

```text
RegistryError unknown format reference: ALPHA/STORY
```

Brief eksplicitno zahtijeva `RegistryError`, ne `TypeError`/`KeyError`.
Problem je validan i neposredno izvršiv resource input, ne teorijski AST ili
nepodržan parser oblik.

Minimalni fix: normalizovati `null` formats blok na praznu listu prije
reference provjere, odbiti druge non-list container tipove kao čitljiv
`RegistryError`, te dodati regresioni test za blank-key oblik.

## BF-2 — modeli nisu stvarno immutable i cached state je spolja promjenjiv

`ConfigDict(frozen=True)` sprečava reassignment polja, ali ne zamrzava
unutrašnje `list` vrijednosti (`supported_formats`, `content_rules`,
`required_fields`, `optional_fields`, `supported_aspect_ratios`). Registry
vraća upravo cached objekte calleru.

Reproducirani API scenario:

```python
platform = registry.get_platform("ALPHA")
before = [f.code for f in registry.list_formats("ALPHA")]
platform.supported_formats.clear()
after = [f.code for f in registry.list_formats("ALPHA")]
```

Rezultat:

```text
cached_model_mutation ['STORY'] []
```

Dakle caller bez pristupa registry internals može promijeniti ponašanje svih
kasnijih čitanja. To direktno krši P0.13 zahtjev za immutable definicijama i
čini cache shared mutable stateom.

Minimalni fix: koristiti immutable kolekcije (npr. tuple polja uz
normalizacione validatore koji vraćaju tuple) ili vratiti dokazano duboko
immutable/defanzivne vrijednosti. Dodati test koji pokušava in-place mutaciju
svake kolekcijske granice relevantne za javni registry rezultat.

## BF-3 — duplirani supported-format reference prolaze kao dupliran output

Format definicije se provjeravaju kroz per-platform `by_code`, ali
`PlatformDefinition.supported_formats` se samo normalizuje. Duplirani
reference poslije uppercase normalizacije nisu odbijeni:

```yaml
code: ALPHA
display_name: Alpha
channel: SOCIAL
supported_formats: [STORY, story]
formats:
  - code: STORY
    display_name: Story
```

Živi rezultat:

```text
duplicate_supported_reference OK ['STORY', 'STORY']
```

Time `list_formats()` vraća dva ista format koda, suprotno acceptance
invariantu da su format kodovi unique per platform. Bundled-resource test to
ne otkriva jer provjerava samo trenutno čiste YAML fajlove.

Minimalni fix: poslije normalizacije odbiti duplicate reference sa
`RegistryError` i dodati test koji koristi case-varijantu da potvrdi da se
unique provjera radi nad normalizovanim kodovima.

# STANDARDNA VERIFIKACIJA

Nezavisno pokrenuto na `d379813`:

```text
python -c <package import probe>
package_import 0.1.0

python -m pytest -q -p no:cacheprovider
  --basetemp %TEMP%\codex-acs-p0-004-pytest
...........................................................              [100%]
59 passed in 0.52s

python -m ruff check --no-cache .
All checks passed!

python -m mypy --cache-dir %TEMP%\codex-acs-p0-004-mypy src
Success: no issues found in 23 source files
```

`--no-cache`/temp cache opcije su sandbox workaround i ne mijenjaju lint,
test ili type semantics. Full suite je zelen, ali ne sadrži regresione testove
za tri blocking scenarija.

# OBAVEZNI ADVERSARIAL DOKAZI

Originalna implementacija:

```text
test_duplicate_platform_code_rejected
test_unknown_format_reference_rejected
2 passed in 0.14s
```

Isti testovi su zatim izvršeni protiv runtime-mutiranih `_load()` varijanti
bez pisanja u branch fajlove:

```text
duplicate_check_removed TEST_FAIL Failed DID NOT RAISE RegistryError
reference_check_removed TEST_FAIL Failed DID NOT RAISE RegistryError
```

Oba testa stvarno dokazuju svoj namijenjeni invariant i nisu lažno zelena.

# DODATNE EDGE-CASE PROBE

PASS:

- isti platform code u dva različita YAML fajla → `RegistryError`;
- format koji postoji samo na drugoj platformi → local unknown-reference
  `RegistryError`;
- `supported_formats: [story]` uz format `STORY` → normalizuje se i poklapa;
- potpuno prazan YAML → čitljiv mapping `RegistryError`;
- `{}` → čitljiv invalid-schema `RegistryError`;
- `formats: []` uz neprazan supported list → unknown-reference
  `RegistryError`.

NOTE, nije blocker po trenutnom kontraktu: `enabled: "true"` Pydantic lax
validacija prihvata i koercira u stvarni `bool True`. Strict schema mode nije
eksplicitno zahtijevan; ako Human Owner želi strogo YAML tipiziranje, to treba
zaključati kao zasebnu odluku ili uključiti u istu usku validation fix rundu.

# NE DIRATI U FIX RUNDI

Ne mijenjati devet platformskih taksonomija/formata, Channel enum, port API,
Campaign/Content slojeve, localization, bootstrap ili dependency set. Ne
uvoditi network adaptere ili generalizovani resource-validator CLI.

# SLJEDEĆE

Crush dodaje tri uska FAIL→PASS testa i minimalne validation/immutability
izmjene samo unutar ACS-P0-004 allowed paths. Koordinator ponavlja puni gate,
provjerava čist delta prema `d379813` i šalje novi commit na fresh Codex
re-review. Human Owner merge odluka dolazi tek poslije zatvorenih nalaza.
