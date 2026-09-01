# ACS-P0-005 — fix round brief (BF-1, BF-2, BF-3)

Za: Pi (isti branch)
Od: Claude (koordinator), poslije Codex REJECT-a
Datum: 2026-09-01

## Status

Codex review: `agent_reports/2026-09-01-ACS-P0-005-review-codex.md` —
`verdict: REJECT`, tri blocking findings, `security: REJECT`. Koordinator
je sva tri nezavisno reprodukovao. HIGH/bezbjednosno-kritičan task (po
novoj review politici, `docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md` §29,
SecretStore i AI Provider/Model Registry ostaju na punom Codex+Claude+Human
Owner ciklusu).

**Task se NE spaja.** Fix runda na istoj branch-i
(`task/ACS-P0-005-ai-registry-secrets`).

## BF-1 — `KeyringSecretStore` čuva secret u exception `__cause__`

`raise SecretStoreError(...) from exc` postavlja originalni backend
exception kao `__cause__`. Ako backend exception message sadrži secret
value (realno za neke keyring backend implementacije koje echo-uju input u
grešci), `exc.__cause__`/traceback može otkriti value čak i kad
`str(SecretStoreError)` to ne sadrži.

Reprodukovano: backend čiji exception message sadrži secret →
`wrapped_exc.__cause__` sadrži secret value.

**Fix:** prekinuti exception chain sa `from None` umjesto `from exc`, tako
da originalni (potencijalno leaky) backend exception nikad ne postane dio
javno dostupnog `__cause__`/traceback lanca. Ako je debug informacija
potrebna, koristiti SAMO `type(exc).__name__` (ime klase, ne poruku/args)
kao safe technical context — nikad sirov `str(exc)` od backend-a.

## BF-2 — `secret_to_env_var()` dopušta alias/collision za nekanonska imena

Funkcija ne validira da `name` prati kontraktom zaključanu konvenciju
`provider/<PROVIDER_CODE>/api_key`. Zbog toga `"OPENAI/api_key"` (bez
`provider/` prefiksa) mapira na ISTI env var kao kanonski
`"provider/OPENAI/api_key"` — dva različita naziva čitaju isti secret.

Reprodukovano: `secret_to_env_var("OPENAI/api_key")` ==
`secret_to_env_var("provider/OPENAI/api_key")`.

**Fix:** dodati eksplicitnu validaciju secret name-a prije mapiranja —
prihvatiti SAMO oblik `provider/<CODE>/api_key` (regex ili strukturirani
split-check: tačno 3 segmenta, prvi mora biti doslovno `"provider"`, drugi
(provider code) nesmije biti prazan i mora sadržati samo
alfanumeričke/underscore karaktere, treći mora biti doslovno `"api_key"`).
Odbiti (raise `ValueError` ili `SecretStoreError`, implementer bira, ali
mora biti dokumentovano) prazan string, prazan provider segment, alias bez
`provider/` prefiksa, dupli slash, i bilo koji drugi oblik van konvencije —
NE tiho mapirati na isti env var kao nešto drugo.

## BF-3 — registry prihvata modele za nepoznatog providera

`register_manual_model()` ne provjerava da `model.provider_code` postoji u
`_providers`. `register_discovered_models(provider_code, models)` provjerava
samo da se `model.provider_code` slaže sa parametrom `provider_code`, ne da
taj `provider_code` uopšte postoji u registrovanim providerima.

Reprodukovano: `register_manual_model(ModelProfile(provider_code="UNKNOWN",
...))` je prihvaćen bez greške.

**Fix:** prije registracije (u oba metoda) potvrditi da `provider_code`
postoji u `self._providers` (koristiti postojeći `get_provider()` — on već
baca `RegistryError` za nepoznat provider, tako da poziv
`self.get_provider(model.provider_code)` prije `self._register(model)` je
dovoljan za obje putanje).

## Obavezno

- Tri nova regresiona testa, svaki dokazano FAIL na trenutnom (`5517c8b`)
  kodu prije fixa, PASS poslije:
  1. Backend exception sa secret-om u poruci → `SecretStoreError.__cause__`
     NE smije sadržati secret (ni `str(cause)` ni bilo šta u traceback
     lancu).
  2. `secret_to_env_var`/`get_secret` alias oblik (`"OPENAI/api_key"` bez
     `provider/` prefiksa) mora biti odbijen, ne tiho mapiran na isti env
     var kao kanonski oblik.
  3. `register_manual_model`/`register_discovered_models` sa nepoznatim
     `provider_code` → `RegistryError`.
- Zadržati svih 111 postojećih testova zelenih.
- I dalje SAMO fajlovi unutar ACS-P0-005 `allowed_paths`
  (`ai_registry/registry.py`,
  `infrastructure/secrets/{environment_secret_store,keyring_secret_store}.py`,
  i pripadajući test fajlovi). Ne dirati provider YAML oblik, `ports/`
  contracts, ACS-P0-006 scope.
- Ne-blocking opservacija iz Codex reviewa (prazan env var value vraća `""`
  ne `None`) — NE rješavati u ovoj rundi, van scope-a.

## Verification

```bash
cd "H:\ai-campaign-studio-worktrees\ACS-P0-005-ai-registry-secrets"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy src
git status --short
```

## Sljedeće

Koordinator provjerava novi delta protiv `5517c8b` (ne cijeli task ponovo),
zatim fresh Codex re-review (HIGH/security task, ostaje na punom ciklusu).
Human Owner merge odluka čeka zatvorene nalaze.
