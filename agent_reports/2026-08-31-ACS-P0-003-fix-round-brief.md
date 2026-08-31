# ACS-P0-003 — fix round brief (BF-1, BF-2, BF-3)

Za: Pi (isti branch)
Od: Claude (koordinator), poslije Codex REJECT-a
Datum: 2026-08-31

## Status

Codex review: `agent_reports/2026-08-31-ACS-P0-003-review-codex.md` —
`verdict: REJECT`, tri blocking findings. Koordinator je sva tri nezavisno
reprodukovao. Sva tri su stvaran, izvršiv runtime input (malformed
translation string, pogrešan tip u JSON katalogu, invalid JSON fajl), ne
teorijski slučaj.

**Task se NE spaja.** Fix runda na istoj branch-i
(`task/ACS-P0-003-localization`).

## BF-1 — malformed format template ruši `Translator.t()`

`translator.py` linija ~61-64: `template.format(**params)` hvata samo
`KeyError`/`IndexError`. Template kao `"Broken {"` baca `ValueError` koji
izlazi neuhvaćen.

Reprodukovano: `Translator(...).t('x')` sa katalog vrijednošću `"Broken {"`
→ `ValueError: Single '{' encountered in format string`.

**Fix:** dodati `ValueError` u postojeći `except (KeyError, IndexError):`
blok (postaje `except (KeyError, IndexError, ValueError):`), isto ponašanje
kao za ostale interpolation greške — log warning, vrati original template.

## BF-2 — non-string katalog vrijednost ruši `Translator.t()` sa `AttributeError`

`scripts/validate_resources.py` `validate_i18n()` provjerava da je katalog
`dict` i key-set, ali NE provjerava da su vrijednosti `str`. Ako je npr.
`"app.title": {"bad": "nested"}`, validator to prihvata, a
`Translator.t()` kasnije puca na `.format()` jer vrijednost nije string.

**Fix — oba mjesta:**

1. `validate_i18n()`: za svaki key/value par u en/bhs katalogu, ako
   `not isinstance(value, str)`, dodati readable error
   (`f"{path}: value for {key!r} must be a string, got {type(value).__name__}"`).
2. `Translator._load()` ili `Translator.t()`: defanzivna provjera tipa prije
   `.format()` — ako `template` nije `str`, tretirati kao missing/malformed
   (log warning, vratiti `[missing:{key}]` ili slično), ne osloniti se
   isključivo na eksterni validator da runtime bude siguran.

## BF-3 — invalid JSON ruši `validate_i18n()` prije čitljive greške

`_duplicate_keys(raw)` poziva `json.loads(raw, object_pairs_hook=hook)` PRIJE
kasnijeg `try: json.loads(raw) except JSONDecodeError`. Za nevalidan JSON,
`_duplicate_keys()` sam baca `JSONDecodeError` neuhvaćen, prije nego što
kod stigne do postojećeg readable-error handling-a.

**Fix:** obuhvatiti `_duplicate_keys(raw)` poziv u `try`/`except
json.JSONDecodeError` (isti obrazac kao postojeći blok ispod), dodati
readable error umjesto propuštanja exception-a dalje. Redoslijed treba biti:
pokušaj parse (uhvati JSONDecodeError → error i prekini dalju obradu tog
fajla), tek onda duplicate-key i ostale provjere.

## Obavezno

- Tri nova regresiona testa (unit za translator BF-1/BF-2, unit ili
  integration za validator BF-2/BF-3), svaki dokazano FAIL na trenutnom
  (`0c23bcf`) kodu prije fixa, PASS poslije — isti FAIL→PASS obrazac kao
  ranije adversarial dokazi.
- Zadržati svih 65 postojećih testova zelenih.
- I dalje SAMO fajlovi unutar ACS-P0-003 `allowed_paths`
  (`localization/translator.py`, `scripts/validate_resources.py`,
  `tests/unit/localization/`, `tests/integration/localization/`). Ne
  dirati ACS-P0-004 (channels registry — sada merged u main), Campaign/
  Content/Brand, bootstrap/main, UI framework, fact/provenance, regionalnu
  lingvističku bazu.

## Verification

```bash
cd "H:\ai-campaign-studio-worktrees\ACS-P0-003-localization"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy src
.\.venv\Scripts\python.exe scripts\validate_resources.py
git status --short
```

## Sljedeće

Koordinator provjerava novi delta protiv `0c23bcf` (ne cijeli task ponovo),
zatim fresh Codex re-review. Human Owner merge odluka čeka zatvorene nalaze.
