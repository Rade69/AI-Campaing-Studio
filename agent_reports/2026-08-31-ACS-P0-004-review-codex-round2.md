---
verdict: REJECT
scope: PASS
acceptance: REJECT
architecture: PASS
security: PASS
tests: REJECT
gitnexus_impact: UNKNOWN
blocking_findings:
  - "BF-4 OPEN: `formats: false` / `formats: \"\"` / `formats: 0` su falsy non-list YAML vrijednosti koje prolaze kao prazna lista kada je `supported_formats: []`."
---

# CILJ

Nezavisni Codex re-review ACS-P0-004 fix runde na commit-u `6a2bd79`
(`task/ACS-P0-004-channel-registry`), prema
`agent_reports/2026-08-31-ACS-P0-004-codex-rereview-request.md`.

**URAĐENO:** `REJECT` — prethodna tri Codex nalaza su zatvorena, ali BF-1 fix
ima jednu realnu schema-validation rupu u istoj liniji promjene.

**NE DIRATI:** Ne dirati platformsku taksonomiju, `Channel` enum,
`PlatformRegistryPort`, Campaign/Content slojeve, localization, bootstrap ili
dependency set.

**SLJEDEĆE:** Crush treba napraviti usku fix rundu u `registry.py` +
`tests/unit/channels/test_registry.py`: `None` tretirati kao praznu listu ili
kao readable `RegistryError` po odluci koordinatora, ali svaki drugi non-list
`formats` scalar/container mora dati `RegistryError`.

# PROVJERENO

- Worktree: `H:\ai-campaign-studio-worktrees\ACS-P0-004-channel-registry`.
- Branch: `task/ACS-P0-004-channel-registry`.
- HEAD: `6a2bd79` (`ACS-P0-004 fix round: close BF-1/BF-2/BF-3`).
- Prethodni Codex REJECT commit: `d379813`.
- Fix delta `d379813..6a2bd79`: tačno 3 fajla:
  - `src/ai_campaign_studio/channels/definitions.py`
  - `src/ai_campaign_studio/channels/registry.py`
  - `tests/unit/channels/test_registry.py`
- Full branch delta `a712ce3..6a2bd79`: 16 fajlova, svi u ACS-P0-004
  `allowed_paths`.
- Pročitan cijeli diff fix runde i relevantni source/test fajlovi.
- Grep za network/API pozive u `channels`/`ports` nije našao runtime poziv
  (samo docstring kaže da ih registry ne radi).
- Grep/callsite provjera tuple promjene nije našla runtime list-specific
  operacije nad novim tuple poljima izvan namjernog regression testa.

# GITNEXUS / IMPACT

`UNKNOWN`, ne PASS. GitNexus i dalje ima poznato linked-worktree binding
ograničenje:

```text
npx gitnexus status
Repository not indexed.
Run: gitnexus analyze

npx gitnexus detect-changes --scope compare --base-ref main --repo .
Error: Repository "." not found. Available: ..., AI-Campaing-Studio
```

Kompenzacija: direktan git diff protiv prethodnog REJECT commit-a i merge-base
commit-a, čitanje izmijenjenih fajlova, grep pogođenih kolekcijskih polja,
full verification i live YAML/API probe.

# BLOCKING FINDINGS

## BF-4 — falsy non-list `formats` vrijednosti prolaze kao prazna lista

U `src/ai_campaign_studio/channels/registry.py`, fix za BF-1 koristi:

```python
raw_formats = raw.get("formats") or []
if not isinstance(raw_formats, list):
    raise RegistryError(f"formats must be a list in {path.name}")
```

Ovo zatvara `formats:` / `None`, ali istovremeno pretvara svaki falsy non-list
YAML scalar u `[]` prije type-checka. Ako je `supported_formats: []`, registry
prihvata schema-invalid platform fajl bez `RegistryError`.

Live probe protiv `6a2bd79`:

```text
formats_false: FAILED accepted -> ['ALPHA']
formats_empty_string: FAILED accepted -> ['ALPHA']
formats_zero: FAILED accepted -> ['ALPHA']
```

Minimalni realni YAML koji prolazi:

```yaml
code: ALPHA
display_name: Alpha
channel: SOCIAL
supported_formats: []
formats: false
```

Ovo nije čisto teoretski slučaj: `supported_formats: []` je eksplicitno
naveden kao edge case u rereview briefu, a P0.13 contract traži schema
validaciju i readable `RegistryError` za malformed registry resources.

Minimalni fix:

```python
raw_formats = raw.get("formats")
if raw_formats is None:
    raw_formats = []
elif not isinstance(raw_formats, list):
    raise RegistryError(...)
```

Dodati regression test za bar `formats: false` uz `supported_formats: []`.
Po želji pokriti i `formats: ""` / `formats: 0`, jer isti bug pattern prolazi.

# ZATVORENI PRETHODNI NALAZI

- BF-1 original (`formats:` -> raw `TypeError`) zatvoren za blank-key slučaj:
  live probe sada daje `RegistryError -> unknown format reference: ALPHA/STORY`.
- BF-2 zatvoren: `supported_formats`, `content_rules`, `required_fields`,
  `optional_fields` i `supported_aspect_ratios` su tuple; `.clear()` je
  blokiran i cached registry state ostaje stabilan.
- BF-3 zatvoren: `supported_formats: [STORY, story]` i
  `supported_formats: [STORY, STORY]` oba daju `RegistryError` kroz Pydantic
  validation path.

Live probe output:

```text
blank_formats: RegistryError OK -> unknown format reference: ALPHA/STORY
immutable_types: tuple tuple tuple tuple tuple
supported_formats: clear blocked
content_rules: clear blocked
required_fields: clear blocked
optional_fields: clear blocked
supported_aspect_ratios: clear blocked
immutable_after: ['STORY']
duplicate_supported_case: RegistryError OK -> invalid platform schema in platform.yaml: ...
duplicate_supported_identical: RegistryError OK -> invalid platform schema in platform.yaml: ...
empty_supported_formats: ['ALPHA'] []
```

# STANDARDNA VERIFIKACIJA

Prvi sandboxed run je pao zbog permission/cache okruženja, ne zbog test
assertion-a:

```text
python -m pytest -q
28 passed, 34 errors
PermissionError: [WinError 5] Access is denied:
'C:\\Users\\38765\\AppData\\Local\\Temp\\pytest-of-radovan'

python -m mypy src
error: INTERNAL ERROR ... version: 2.3.1
```

Nakon rerun-a uz dozvoljen normalan cache/temp write u feature worktree-u:

```text
.\.venv\Scripts\python.exe -m pytest -q
..............................................................           [100%]
62 passed in 0.62s

.\.venv\Scripts\python.exe -m ruff check .
All checks passed!

.\.venv\Scripts\python.exe -m mypy src
Success: no issues found in 23 source files
```

# ADVERSARIALNA PROVJERA

Rereview je ponovio tri originalna Codex live-proba scenarija protiv novog
koda i dodao jednu ciljanu negativnu varijantu za sam BF-1 fix.

Rezultat:

- originalni `formats:` blank-key više ne curi kao `TypeError`;
- cached collection mutation je blokirana na svih pet pogođenih kolekcija;
- duplicate supported-format reference se odbijaju poslije normalizacije;
- novi falsy non-list `formats` scalar-i prolaze kada nema supported-format
  referenci koje bi kasnije okinule unknown-reference provjeru.

# NE DIRATI U FIX RUNDI

Ne širiti scope na strict bool validaciju (`enabled: "true"` ostaje ranija
non-blocking napomena), platform taxonomy, port API ili resource-validator CLI.
Ovo je uska `formats` type-check korekcija.

# SLJEDEĆE

Fix BF-4 u `registry.py`, dodati uski unit regression test, pokrenuti 62+
testova, `ruff`, `mypy`, pa vratiti Codexu na kratki round3 re-review.
