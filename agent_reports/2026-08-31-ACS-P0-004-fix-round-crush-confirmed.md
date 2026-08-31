# ACS-P0-004 — fix round evidence — coordinator-confirmed

**Implementer:** Crush (nema self-report — isti obrazac kao original ACS-P0-004
i ACS-P0-001)
**Prethodni HEAD:** `d379813` (Codex REJECT — BF-1/BF-2/BF-3)
**Novi commit:** `6a2bd79` (author Crush, committed by coordinator)

## Diff protiv d379813 — nezavisno potvrđeno

Tačno 3 fajla: `channels/definitions.py` (+21/-… ), `channels/registry.py`
(+5/-…), `tests/unit/channels/test_registry.py` (+58 novih testova). Sve
unutar `allowed_paths`. Ništa iz "NE DIRATI" liste (platform taksonomija,
`Channel` enum, `ports/channels.py` API, Campaign/Content, localization,
bootstrap, dependencies) nije dirnuto.

## Fix — pročitan cio diff

- **BF-1:** `raw.get("formats") or []` (bilo `raw.get("formats", [])`) —
  ispravno hvata i missing-key i explicit-`None` slučaj. Dodata provjera
  `isinstance(raw_formats, list)` → `RegistryError` ako nije lista.
- **BF-2:** svih 5 pogođenih polja promijenjeno sa `list[str]` na
  `tuple[str, ...]` (`Field(default_factory=tuple)`). `_normalize_supported_formats`
  sad je `mode="before"` validator koji vraća `tuple` i radi input-type
  provjeru.
- **BF-3:** isti validator sada odbija duplikate poslije normalizacije
  (`ValueError` → Pydantic `ValidationError` → uhvaćeno u `_build_platform`
  → re-raised kao `RegistryError`, konzistentno sa ostalim schema greškama).

## Nezavisna verifikacija — DOSLOVAN output

```text
$ ./.venv/Scripts/python.exe -m pytest -q
..............................................................           [100%]
62 passed in 0.48s

$ ./.venv/Scripts/python.exe -m ruff check .
All checks passed!

$ ./.venv/Scripts/python.exe -m mypy src
Success: no issues found in 23 source files
```

## Re-dokaz sva tri originalna Codex live-proba scenarija — nezavisno ponovljen

```text
BF-1: RegistryError OK -> unknown format reference: ALPHA/STORY
BF-2: mutation blocked OK (tuple has no .clear); before/after: ['STORY'] ['STORY']
BF-3: RegistryError OK -> ... duplicate supported format reference: ['STORY', 'story']
```

Napomena o BF-1 poruci: prazan `formats:` blok sad se tretira kao prazna
lista formata, pa postojeća "unknown format reference" provjera
(supported_formats referencira STORY koji ne postoji u praznom by_code)
prirodno hvata slučaj sa semantički preciznijom porukom — nije potrebna
posebna "blank formats" poruka, isti mehanizam pokriva oba slučaja
(eksplicitno prazna `formats: []` i `formats:` bez vrijednosti).

## Regresija

Svih 59 prethodnih testova ostaje zeleno + 3 nova (62 ukupno). Nema
regresije na ranije zatvorene adversarial dokaze (duplicate-platform-code,
unknown-format-reference i dalje rade — potvrđeno u punom pytest run-u).

## Zaključak

BF-1/BF-2/BF-3 zatvoreni, dokazano nezavisnim ponavljanjem originalnih
Codex live-proba scenarija. Spreman za fresh Codex re-review na `6a2bd79`.
