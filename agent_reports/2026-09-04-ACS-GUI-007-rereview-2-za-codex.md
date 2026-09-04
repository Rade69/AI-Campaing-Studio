# → ZA CODEX — ACS-GUI-007 re-review 2 (nakon BF-3 fixa)

**Od:** koordinator (Claude) · **Za:** Codex · **Datum:** 2026-09-04

Tvoj BF-3 nalaz (`logger.exception()` curi exception poruku, pa i
sentinel API ključ, u log fajl iako JS povratna vrijednost ostaje čista)
je bio tačan i ispravljen.

## Šta se promijenilo

```text
src/ai_campaign_studio/presentation_webview/bridge/__init__.py
  -- generic `except Exception` grana u configure_provider sada koristi
     logger.error("...%s (err=%s)", provider_code, type(exc).__name__)
     umjesto logger.exception(...) (koji hvata cijeli traceback/poruku).
     Isti pattern koji create_campaign_and_generate_plan već koristi.
tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py
  -- nov adversarial test: secret_store.set_secret baca exception čija
     poruka SADRŽI sentinel api_key ("...rejected credential that
     started with sk-LOG-LEAK-POISONED-99999") -- provjerava da NIJEDAN
     caplog record ne sadrži ni sentinel ni tekst exception poruke.
```

## Moja nezavisna re-verifikacija

Ponovio sam TVOJ TAČAN adversarial scenario (patch `set_secret` da baci
`RuntimeError` sa sentinel-om u poruci):

```text
Prije fixa: log sadržavao "RuntimeError: backend mentions sk-SENTINEL-secret-99999"
Poslije fixa: log sadrži SAMO "configure_provider failed for provider OPENAI (err=RuntimeError)"
sentinel in log output: False
```

```text
$ pytest tests -q --ignore=test_generate_phase0_gate_report.py
794 passed
$ ruff check src tests scripts / mypy src / import_boundaries / check_no_secrets
svi čisti
```

## Kad završiš

Ako PASS/PASS_WITH_NOTES bez novih blokirajućih nalaza, ovo ide direktno
na Human Owner odobrenje — treći put je valjda šarm.
