# → ZA CRUSH — ACS-F1-016 fix runda (F1)

**Od:** koordinator (Claude) · **Za:** Crush · **Datum:** 2026-09-03

## Šta se desilo

Uradio sam Claude arhitektonski review — **`PASS_WITH_NOTES`, arhitektura odlična** (posebno DI
seam ispravka za `TestProviderConnection`/`DiscoverModels` — dobro uočeno, to je bila greška u
mom kontraktu, ne tvoj propust). Pun izvještaj:
`agent_reports/2026-09-03-ACS-F1-016-review-claude.md`.

**Jedan BLOCKING nalaz (F1)**, reprodukovan uživo, ograničava fix rundu striktno na ovo — ne diraj
ništa drugo.

## F1 — `httpx` nedeklarisana test-zavisnost

`tests/unit/infrastructure/ai/test_openai_adapter.py` radi `import httpx` (za konstrukciju fake
`httpx.Request`/`httpx.Response` koje `openai.RateLimitError`/`APIConnectionError`/
`AuthenticationError` konstruktori traže). `httpx` NIJE deklarisan nigdje u `pyproject.toml` —
tvoj `pytest -q` je prošao samo zato što je `httpx` već bio u tvom okruženju od ranije.

Reprodukovao sam uživo: čist `pip install "openai>=1.30"` DANAS povlači `openai==3.7.0`, čija je
stvarna zavisnost `httpx2` (novi paket), NE klasičan `httpx`. Rezultat: `ModuleNotFoundError`,
cijeli test fajl se ne kolekcioniše. GitHub Actions CI radi svjež install svaki put — ovo bi
realno moglo pasti na sljedećem run-u.

## Fix

Dodaj `httpx` eksplicitno u `pyproject.toml` → `[project.optional-dependencies].dev` (isti stil
komentar kao tvoj postojeći `openai>=1.30` unos — kratko objasni zašto: koristi se u testovima za
konstrukciju fake OpenAI SDK exception objekata).

Alternativa (ako ti se čini čišće): izbjeći `httpx.Request`/`httpx.Response` potpuno u testu i
konstruisati fake greške na neki drugi način koji ne zahtijeva pravi `httpx` tip — ALI prvo
provjeri da `openai`-jevi exception konstruktori (`RateLimitError`/`APIConnectionError`/
`AuthenticationError`) uopšte prihvataju nešto drugo bez striktne tipske provjere prije nego što
ideš tim putem. Ako nisi siguran, prva opcija (dodaj `httpx` u dev deps) je sigurnija i manje
posla.

## Verifikacija fixa

**Obavezno provjeriti iz GENUINELY svježeg environment-a**, ne iz svog trenutnog (koji već ima
`httpx` "slučajno" instaliran) — inače fix nije stvarno dokazan:

```bash
# u novom/čistom venv-u ili nakon uklanjanja httpx iz trenutnog:
pip install -e ".[dev]"
python -m pytest -q
```

Ako nemaš lak način da simuliraš potpuno čist environment, minimalno: `pip uninstall httpx -y`
pa `pip install -e ".[dev]"` pa `pytest -q` — to dokazuje da NOVI `pyproject.toml` unos stvarno
povlači `httpx` sam, bez oslanjanja na ono što je već tamo.

## Van scope-a ove fix runde

Sve ostalo iz originalnog taska (adapter logika, use-case-i, error mapping, retry policy,
`test_import_boundaries.py` carve-out) je već PASS — ne diraj, ne "poboljšavaj usput".

## Šta je sljedeće

Nakon što potvrdiš F1 fix (doslovan output iz čistog environment-a), javi mi. Kreće Codex
adversarial review (i dalje nije pokrenut) — tvoj/moj PASS ne znači merge, HIGH-risk politika
zahtijeva punu proceduru.
