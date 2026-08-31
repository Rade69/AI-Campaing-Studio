# ACS-P0-004 — fix round brief (BF-1, BF-2, BF-3)

Za: Crush (isti branch)
Od: Claude (koordinator), poslije Codex REJECT-a
Datum: 2026-08-31

## Status

Codex review: `agent_reports/2026-08-31-ACS-P0-004-review-codex.md` —
`verdict: REJECT`, tri blocking findings. Koordinator je sva tri nezavisno
reprodukovao. Nalazi su stvarni, ne teorijski — sva tri su validan,
izvršiv resource/API input, ne egzotičan AST slučaj.

**Task se NE spaja.** Fix runda na istoj branch-i
(`task/ACS-P0-004-channel-registry`), ne novi task.

## BF-1 — prazan `formats:` blok baca `TypeError` umjesto `RegistryError`

```yaml
code: ALPHA
formats:
```

`yaml.safe_load` vraća `None` za prazan `formats:` ključ. `raw.get("formats", [])`
NE hvata taj slučaj — `.get()` sa default vrijednošću vraća default samo kad
ključ NE POSTOJI, ne kad postoji sa vrijednošću `None`. Trenutni kod onda
iterira `for raw_format in None` → `TypeError: 'NoneType' object is not
iterable`.

Reprodukovano: `PlatformRegistry(...).list_platforms()` na gornjem YAML-u
baca `TypeError`, ne `RegistryError`.

**Fix:** `raw.get("formats") or []` (hvata i missing-key i `None`-vrijednost).
Ako `formats` postoji ali nije lista (npr. string ili dict), odbiti sa
čitljivim `RegistryError`, ne pustiti da padne dalje u kod koji očekuje
iterable.

## BF-2 — cache-ovani modeli su mutable spolja, dijele state između poziva

`ConfigDict(frozen=True)` sprečava reassignment polja (`platform.code = "X"`
baca), ali NE zamrzava sadržaj `list` polja. Caller koji dobije
`PlatformDefinition` iz registry-ja može mutirati njegovu `supported_formats`
listu IN-PLACE, i ta ista (cache-ovana) instanca se vraća SVIM budućim
pozivima — jedan caller može pokvariti registry state za sve ostale.

Reprodukovano:
```python
platform = registry.get_platform("ALPHA")
registry.list_formats("ALPHA")            # ['STORY']
platform.supported_formats.clear()
registry.list_formats("ALPHA")            # [] -- pokvareno za sve dalje pozive
```

Pogođena polja: `PlatformDefinition.supported_formats`,
`PlatformDefinition.content_rules`, `FormatDefinition.required_fields`,
`FormatDefinition.optional_fields`, `VisualConstraints.supported_aspect_ratios`.

**Fix:** promijeniti ta polja sa `list[str]` na `tuple[str, ...]` (isti
obrazac koji ACS-P0-003 već koristi u `ContentLanguageContext` za
`preferred_terms`/`forbidden_terms`/itd. — tuple je stvarno immutable, ne
samo "reassignment blocked"). `field_validator` za normalizaciju
(`supported_formats` upper-casing) mora vraćati `tuple`, ne `list`.
Default vrijednosti (`Field(default_factory=list)`) postaju
`Field(default_factory=tuple)`.

## BF-3 — duplirani `supported_formats` reference (case-varijanta) prolazi

```yaml
supported_formats: [STORY, story]
```

Poslije uppercase normalizacije oba postaju `STORY`, ali nema duplicate-check
na `supported_formats` listi — `list_formats()` onda vraća `['STORY',
'STORY']`, krši "format kodovi unique per platform" acceptance invariant.

**Fix:** poslije normalizacije u `field_validator` (ili u `registry._load`),
odbiti duplikate u `supported_formats` sa `RegistryError`/`ValueError` (koji
god sloj je prirodnije mjesto — ako se radi u Pydantic validatoru, koristiti
`ValueError` koji će `registry.py` već hvatati kao `ValidationError` i
re-raise-ovati kao `RegistryError`, konzistentno sa ostalim schema greškama).

## Obavezno

- Tri nova regresiona testa, svaki dokazano FAIL na trenutnom (`d379813`)
  kodu prije fixa, PASS poslije — isti FAIL→PASS obrazac kao u svim
  prethodnim rundama:
  1. `formats:` blank-key YAML → `RegistryError` (ne `TypeError`).
  2. Mutacija vraćene `PlatformDefinition`/`FormatDefinition` kolekcije NE
     smije uticati na naredne `registry.list_formats()`/`get_platform()`
     pozive (test da mutacija sama baca `AttributeError`/`TypeError` jer je
     tuple, ILI da state ostaje netaknut — u zavisnosti od pristupa).
  3. `supported_formats` sa case-varijantom duplikata (`[STORY, story]`) →
     `RegistryError`, ne tihi duplikat u `list_formats()`.
- Zadržati sve postojeće testove zelenim (59 iz `d379813`).
- I dalje SAMO fajlovi unutar ACS-P0-004 `allowed_paths`
  (`channels/definitions.py`, `channels/registry.py`,
  `tests/unit/channels/test_registry.py`, eventualno
  `tests/integration/channels/test_platform_resources.py` ako treba dodatna
  bundled-resource provjera). Ne dirati platform YAML taksonomiju, `Channel`
  enum, `ports/channels.py` API oblik, Campaign/Content slojeve,
  localization (paralelni ACS-P0-003), bootstrap, dependency set.
- Ne-blocking napomena iz Codex reviewa (`enabled: "true"` string→bool lax
  coercion) — NE rješavati u ovoj rundi, nije u scope-u.

## Verification

```bash
cd "H:\ai-campaign-studio-worktrees\ACS-P0-004-channel-registry"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy src
git status --short
```

## Sljedeće

Koordinator provjerava novi delta protiv `d379813` (ne cijeli task ponovo),
zatim fresh Codex re-review. Human Owner merge odluka čeka zatvorene nalaze.
