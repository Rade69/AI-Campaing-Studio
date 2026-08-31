# ACS-P0-004 — fix round 2 brief (BF-4)

Za: Crush (isti branch)
Od: Claude (koordinator), poslije Codex round-2 REJECT-a
Datum: 2026-08-31

## Status

Codex round 2: `agent_reports/2026-08-31-ACS-P0-004-review-codex-round2.md`
— BF-1/2/3 potvrđeno zatvoreni. Novi nalaz: `raw.get("formats") or []` hvata
i SVAKI drugi falsy scalar (`False`, `""`, `0`), ne samo `None` — svi
prolaze kao prazna lista i zaobilaze `isinstance(..., list)` type-check koji
dolazi POSLIJE `or []`. Koordinator reprodukovao: `formats: false` /
`formats: ""` / `formats: 0` uz `supported_formats: []` prolaze bez greške.

**Task se i dalje NE spaja.** Druga fix runda na istoj branch-i.

## Fix

U `src/ai_campaign_studio/channels/registry.py`, zamijeniti:

```python
raw_formats = raw.get("formats") or []
if not isinstance(raw_formats, list):
    raise RegistryError(f"formats must be a list in {path.name}")
```

sa eksplicitnom `is None` provjerom PRIJE type-check-a (ne `or`, koji tretira
svaki falsy scalar isto kao `None`):

```python
raw_formats = raw.get("formats")
if raw_formats is None:
    raw_formats = []
elif not isinstance(raw_formats, list):
    raise RegistryError(f"formats must be a list in {path.name}")
```

## Obavezno

- Regression test za `formats: false` (minimum), po mogućnosti i
  `formats: ""` / `formats: 0` u istom ili odvojenim testovima — svaki
  dokazano FAIL na trenutnom (`6a2bd79`) kodu, PASS poslije fixa.
- Zadržati postojeći blank-key (`formats:` bez vrijednosti → tretira se kao
  `[]`) i missing-key ponašanje netaknuto — to i dalje treba raditi kao do
  sada (Codex je to potvrdio kao ispravno u round 2).
- I dalje SAMO `channels/registry.py` +
  `tests/unit/channels/test_registry.py`. Ne širiti na strict bool
  validaciju (`enabled: "true"` ostaje van scope-a), platform taksonomiju,
  port API, resource-validator CLI.

## Verification

```bash
cd "H:\ai-campaign-studio-worktrees\ACS-P0-004-channel-registry"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy src
git status --short
```

## Sljedeće

Koordinator provjerava novi delta protiv `6a2bd79`, zatim fresh Codex round
3 (očekivano kratak — uska korekcija).
