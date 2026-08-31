# ACS-P0-004 — fix round 2 evidence — coordinator-confirmed

**Prethodni HEAD:** `6a2bd79` (Codex round 2 REJECT — BF-4)
**Novi commit:** `be3767a` (author Crush, committed by coordinator)

## Diff protiv 6a2bd79

Tačno 2 fajla: `channels/registry.py` (+6/-2), `tests/unit/channels/test_registry.py`
(+21 novi parametrizovan test za `false`/`""`/`0`).

## Fix

`raw.get("formats") or []` → eksplicitan `is None` check prije
`isinstance(..., list)`, tačno kako je brief tražio. Blank-key/missing-key
ponašanje netaknuto (i dalje tretirano kao prazna lista).

## Nezavisna verifikacija

```text
$ ./.venv/Scripts/python.exe -m pytest -q
.................................................................        [100%]
65 passed in 0.45s

$ ./.venv/Scripts/python.exe -m ruff check .
All checks passed!

$ ./.venv/Scripts/python.exe -m mypy src
Success: no issues found in 23 source files
```

## Re-dokaz BF-4 — nezavisno ponovljen

```text
formats: false -> RegistryError OK: formats must be a list in alpha.yaml
formats: "" -> RegistryError OK: formats must be a list in alpha.yaml
formats: 0 -> RegistryError OK: formats must be a list in alpha.yaml
blank formats: -> still OK as empty list: ['ALPHA']   (regresija provjerena, i dalje radi)
```

## Zaključak

BF-4 zatvoren, bez regresije na ranije zatvorene BF-1/2/3 niti na
blank/missing-key ponašanje. Spreman za fresh Codex round 3 (očekivano
kratak) na `be3767a`.
