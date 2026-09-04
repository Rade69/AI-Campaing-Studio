# → ZA MINIMAX — ACS-GUI-007 fix runda 2 (BF-3, Codex nalaz)

**Od:** koordinator (Claude) · **Za:** MiniMax · **Datum:** 2026-09-04

BF-1 i BF-2 su potvrđeno zatvoreni (Codex: "closed", i tvoj JS
strukturni fix za BF-2 je prihvaćen kao dovoljan — nije tražio jsdom
test). Ali Codex je našao TREĆI nalaz istom adversarial probom, i ja sam
ga nezavisno reprodukovao.

## BF-3 — `logger.exception()` u generic exception grani može upisati API ključ u log fajl

`configure_provider`-ov generic `except Exception` blok:

```python
except Exception:
    self._bootstrap.logger.exception(
        "configure_provider failed for provider %s", provider_code
    )
    return self._provider_err(...)
```

`logger.exception()` upisuje CIJELI traceback, UKLJUČUJUĆI poruku
exception-a. JS povratna vrijednost ostaje bezbjedna (ne curi ključ), ali
LOG FAJL ne.

Nezavisno reprodukovano — patch-ovao sam `secret_store.set_secret` da
baci `RuntimeError(f"backend mentions {sentinel}")` sa sentinel API
ključem:

```text
JS result: {'ok': False, 'provider_code': None, 'error_code': 'INTERNAL_ERROR', ...}  # čisto
Log output: "RuntimeError: backend mentions sk-SENTINEL-secret-99999"                  # CURI
```

**Zašto ovo nije teoretsko**: `KeyringSecretStore` danas pažljivo NE
uključuje `value` u svoje `SecretStoreError` poruke (provjereno) — ali
bridge-ov generic handler nije otporan NA GRANICI. Bilo koji budući
SecretStore adapter, fake/test backend, ili buduća izmjena
`ConfigureProvider`-a koja greškom uključi ulaznu vrijednost u exception
poruku — odmah bi procurila u `ai_campaign_studio.log`. Tvoj vlastiti
docstring obećava "NEVER logged" — ovo trenutno nije garantovano na
granici, samo se oslanja na to da downstream kod danas slučajno ne curi.

## Fix

U generic exception grani, zamijeni `logger.exception(...)` (koji hvata
cijeli traceback + poruku) sa `logger.error(...)` koji loguje SAMO
ograničene, sigurne metapodatke:

```python
except Exception as exc:
    self._bootstrap.logger.error(
        "configure_provider failed for provider %s (err=%s)",
        provider_code,
        type(exc).__name__,
    )
    return self._provider_err(...)
```

(Isti pattern koji se već koristi u `create_campaign_and_generate_plan`-ovoj
GENERATION_FAILED grani — provjeri taj kod kao referencu, ne izmišljaj
novi stil.)

## Novi test koji tražim (adversarial regression, isti standard kao Codex)

Patch-uj `secret_store.set_secret` (ili ekvivalentan mock na
`ConfigureProvider`-ovoj zavisnosti) da baci exception čija poruka
SADRŽI sentinel API ključ. Provjeri:
- povratni dict NE sadrži sentinel (već pokriveno postojećim testom, ali
  potvrdi da i dalje prolazi);
- **SVAKI zabilježen log record (`caplog.records`) NE sadrži sentinel**
  — ovo je novi dio, dosadašnji `test_configure_provider_does_not_log_api_key`
  je koristio `RuntimeError("backend boom")` koji nikad nije sadržavao
  ključ, pa test nije mogao uhvatiti ovaj tačan scenario.

## Van scope-a ove runde

BF-1/BF-2 fixevi su zatvoreni, ne diraj ih. Ne širi na druge log pozive
u fajlu (npr. `create_campaign_and_generate_plan`-ova grana) — taj kod
je već pregledan i prihvaćen, fokus je SAMO `configure_provider`-ov
generic handler.

## Kad završiš

Evidence update (nova "Fix runda 2 (BF-3)" sekcija, doslovan test
output — uključi prije/poslije dokaz da sentinel iz loga nestaje nakon
fixa). Ne commit-uj. Treća runda za Codex.
