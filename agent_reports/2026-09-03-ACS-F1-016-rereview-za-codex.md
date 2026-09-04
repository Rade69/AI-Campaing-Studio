# → ZA CODEX — ACS-F1-016 re-review (BF-1, BF-2 fix runda)

**Od:** koordinator (Claude) · **Za:** Codex · **Datum:** 2026-09-03

Crush je popravio oba nalaza iz tvog REJECT-a. Evidence: `agent_reports/2026-09-03-ACS-F1-016-crush.md`
("Fix runda 2" sekcija). Ja sam nezavisno pregledao i verifikovao prije nego što sam te zvao nazad:

## BF-1 — potvrđen fix

`openai_adapter.py`: `choice = completion.choices[0]` zadržan, `finish_reason=getattr(choice,
"finish_reason", None)` (bilo `getattr(message, ...)`). Test fixture (`_completion` helper u
`test_openai_adapter.py`) prepravljen na realan shape — `finish_reason` na `choice`, komentar
eksplicitno kaže zašto. `test_generate_returns_structured_payload` sad asertuje
`response.finish_reason == "stop"`.

## BF-2 — potvrđen fix

`configure_provider.py`: guard dodan odmah poslije `get_provider()`, PRIJE
`set_secret`/`save_provider_config`:

```python
if not provider.requires_api_key:
    raise InvariantViolation(f"provider {provider.provider_code} does not require an API key")
```

`InvariantViolation` je pre-postojeći domain error (`domain/common/errors.py`, netaknut diff-om —
provjerio). Regresioni test `test_provider_without_api_key_rejected`: fake provider sa
`requires_api_key=False` → `pytest.raises(InvariantViolation)` → i eksplicitno dokazuje
`secret_store.secrets == {}` i `config_repo.saved is None` (guard je pravi early-return, ne samo
throw poslije side-effect-a).

## Moja nezavisna verifikacija (ne samo pročitao evidence)

```text
python -m pytest -q                                        → 644 passed
python -m ruff check .                                      → All checks passed
python -m mypy src                                           → Success, 134 files
python -m pytest tests/architecture/test_import_boundaries.py -q  → 18 passed
python scripts/check_no_secrets.py                          → NO CONFIRMED SECRET
git status --short                                           → isti fajl-set kao prošla runda,
                                                                 ništa van BF-1/BF-2 scope-a dirano
```

## Za tebe

Provjeri da li se slažeš da su BF-1/BF-2 stvarno zatvoreni, i da fix nije uveo novi problem (npr.
da `InvariantViolation` na ovom mjestu ne krši neki drugi ugovoreni tok, ili da regression test za
BF-1 stvarno testira ono što misli da testira). Ako imaš dodatne adversarial probe koje želiš da
pokreneš (kao ranije za retry/error-mapping/secret-leak), slobodno. Ako PASS — sljedeći korak je
Human Owner eksplicitno odobrenje, ne merge sam po sebi.
