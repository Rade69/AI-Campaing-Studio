# → ZA CRUSH — ACS-F1-016 fix runda 2 (BF-1, BF-2)

**Od:** koordinator (Claude) · **Za:** Crush · **Datum:** 2026-09-03

Codex je uradio adversarial review: `agent_reports/2026-09-03-ACS-F1-016-review-codex.md` —
**REJECT**, dva nalaza. Nezavisno sam provjerio oba (stvaran OpenAI SDK model + stvaran domain
kod) — oba su realni bugovi, ne lažna uzbuna. F1 (httpx) ostaje zatvoren, ne diraj to.

## BF-1 — `finish_reason` se čita sa pogrešnog objekta

`infrastructure/ai/openai_adapter.py` (`generate()`, oko linije 115):

```python
message = completion.choices[0].message
...
finish_reason=getattr(message, "finish_reason", None)
```

Provjerio sam stvaran OpenAI SDK model: `finish_reason` je polje na `Choice`
(`completion.choices[0].finish_reason`), NE na `message`
(`ChatCompletionMessage` polja: `content`, `refusal`, `role`, `annotations`, `audio`,
`function_call`, `tool_calls` — nema `finish_reason`). Sa pravim OpenAI response-om, trenutni kod
UVIJEK vraća `None`. Test fixture je slučajno maskirao ovo stavljajući `finish_reason` na fake
`message` objekat umjesto na `choice`.

**Fix**: zadrži `choice = completion.choices[0]`, čitaj `message = choice.message`,
`finish_reason=getattr(choice, "finish_reason", None)`. Dodaj regresioni test sa fake response-om
oblikovanim kao stvaran OpenAI shape (`finish_reason` na `choice`, ne na `message`) — Codex-ov
review sadrži tačan primjer fixture-a.

## BF-2 — `ConfigureProvider` ne provjerava `requires_api_key`

`application/ai_provider/configure_provider.py` — `execute()` odmah upisuje secret i snima config,
bez provjere `provider.requires_api_key`. Potvrdio sam da je `requires_api_key: bool = True`
stvarno polje na `AIProviderDefinition` (`ai_registry/provider_models.py`).

**Fix**: poslije `provider = self._provider_registry.get_provider(provider_code)`, dodaj eksplicitan
guard — ako `not provider.requires_api_key`, podigni odgovarajuću domain grešku (npr.
`InvariantViolation`, isti obrazac kao ostatak projekta) PRIJE `set_secret`/`save_provider_config`.
Dodaj regresioni test: fake provider sa `requires_api_key=False` → dokaži da `secret_store.set_secret`
i `provider_config_repo.save_provider_config` NISU pozvani.

## Van scope-a ove runde

Sve ostalo (retry policy, error mapping, DI seam, httpx fix iz prošle runde) je već PASS kod
Codex-a i mene — ne diraj, ne "poboljšavaj usput".

## Verifikacija

```bash
pytest tests/unit/infrastructure/ai/test_openai_adapter.py tests/unit/application/ai_provider tests/integration/application/ai_provider -v
pytest -q
ruff check .
mypy src
pytest tests/architecture/test_import_boundaries.py -v
python scripts/check_no_secrets.py
```

## Kad završiš

Evidence update (novi "Fix runda 2" odjeljak u postojećem evidence fajlu, ili novi fajl). Ne
commit-uj. Ide nazad Codex-u na re-review prije Human Owner odobrenja — treća runda ako i tu nešto
iskrsne.
