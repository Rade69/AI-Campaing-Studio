# ACS-GUI-008 — fix-brief runda 3 (BF-5, Codex rereview nalaz)

Implementer: MiniMax · Reviewer: Claude + Codex (HIGH risk, pun ciklus)
Codex rereview: `agent_reports/2026-09-06-ACS-GUI-008-rereview-codex.md`
(verdict REJECT, samo BF-5 -- originalna 4 nalaza potvrđena zatvorena).

Koordinator je nezavisno reprodukovao BF-5 sam (isti repro kao Codex --
`create_connection` baca `OSError`, `generate_campaign_content` vraća
pogrešan DTO oblik).

## BF-5 — resource-lifecycle greška vraća pogrešan DTO za `generate_campaign_content`

`_with_call_resources`-ov `except Exception` blok (linija ~137-146)
hvata greške koje se dese U `_resource_scope()` samom (npr. konekcija
ne može da se otvori) -- ovo je IZVAN metode-specifičnog try/except-a
unutar `generate_campaign_content`. Dekorator trenutno provjerava SAMO
`method.__name__ == "configure_provider"` -> `self._provider_err(...)`;
SVE OSTALO (uključujući `generate_campaign_content`) ide kroz
`self._err(...)`, koji vraća `CampaignPlanResultUiModel` oblik
(`campaign_id`/`plan_id`/`plan_item_count`/`error_code`/`error_message`)
-- NE `GenerateContentResultUiModel` oblik
(`generated_count`/`failed_count`/`content_piece_ids` nedostaju).

**Reprodukovano i od koordinatora, identično Codex-u:**

```python
with patch('...create_connection', side_effect=OSError('disk unavailable')):
    result = bridge.generate_campaign_content({'campaign_id': 'c-1', 'plan_id': 'p-1'})
# {'ok': False, 'campaign_id': None, 'plan_id': None, 'plan_item_count': None,
#  'error_code': 'INTERNAL_ERROR', 'error_message': '...'}
# NEDOSTAJU: generated_count, failed_count, content_piece_ids
```

## Tražena izmjena

Učiniti `_with_call_resources`-ov error-mapping OPERACIJSKI SVJESTAN,
umjesto jednog hardkodiranog imena. Prijedlog (implementer bira tačan
oblik, ovo je jedan validan pristup):

```python
_LIFECYCLE_ERROR_MAPPERS: dict[str, str] = {
    "configure_provider": "_provider_err",
    "generate_campaign_content": "_generate_err",
}

def _with_call_resources(method: Callable[..., dict]) -> Callable[..., dict]:
    @wraps(method)
    def _wrapped(self: CampaignBridgeApi, *args: Any, **kwargs: Any) -> dict:
        try:
            with self._resource_scope():
                return method(self, *args, **kwargs)
        except Exception as exc:
            self._bootstrap.logger.error(
                "bridge resource lifecycle failed for %s (err=%s)",
                method.__name__, type(exc).__name__,
            )
            mapper_name = _LIFECYCLE_ERROR_MAPPERS.get(method.__name__, "_err")
            mapper = getattr(self, mapper_name)
            return mapper(
                _ERROR_INTERNAL,
                "Interna greška — pogledajte log aplikacije."
                if mapper_name == "_err" else
                "Konfiguracija provajdera nije uspjela (interna greška)."
                if mapper_name == "_provider_err" else
                "Generisanje sadržaja nije uspjelo (interna greška).",
            )
    return _wrapped
```

(Poruke po mapper-u mogu ostati kao odvojen mali if/elif ako je čitljivije
-- bitno je da `create_campaign_and_generate_plan` i dalje ide kroz
`_err`, `configure_provider` kroz `_provider_err`, `generate_campaign_content`
kroz `_generate_err`, SVAKI put sa TAČNIM poljima za svoj DTO.)

## Test koji MORA postojati (Codex-ov zahtjev)

Proširiti POSTOJEĆI connection-failure test (`test_campaign_bridge_api.py:240-258`,
koji trenutno pokriva SAMO `configure_provider`+`create_campaign_and_generate_plan`)
sa TREĆIM slučajem za `generate_campaign_content`:

```python
def test_generate_content_connection_failure_returns_correct_dto_shape(...):
    with patch('...create_connection', side_effect=OSError('disk unavailable')):
        result = bridge.generate_campaign_content({...})
    assert set(result.keys()) == {
        "ok", "campaign_id", "generated_count", "failed_count",
        "content_piece_ids", "error_code", "error_message",
    }
    assert result["ok"] is False
    assert result["error_code"] == "INTERNAL_ERROR"
    # secret-safety: exception text ne curi
    assert "disk unavailable" not in result["error_message"]
```

## Nakon fixa

Regression: connection-failure testovi (sva 3 slučaja), pun
`presentation`/`presentation_webview` suite, pun suite, ruff, mypy,
secret scan. Novo evidence -> nazad Codex-u SAMO za BF-5 diff/repro
(Codex je eksplicitno rekao "provjerava samo BF-5 diff/repro" -- ne
mora ponavljati cijeli review). Nakon Codex PASS, Human Owner
odobrenje. **PR #4 se NE merguje na `897bd5c`.**
