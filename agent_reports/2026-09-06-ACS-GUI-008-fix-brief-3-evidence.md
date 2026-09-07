# ACS-GUI-008 — fix-brief runda 3 (Codex BF-5) — IMPLEMENTER EVIDENCE

Implementer: MiniMax · Reviewer: Codex (runda 2 rerereview)
Review source: `agent_reports/2026-09-06-ACS-GUI-008-rereview-codex.md` (verdict REJECT, 1 blocking nalaz: BF-5)
Fix-brief source: korisnikov inline spec (`ZA MINIMAX` poruka); commit `6b97da2` na main-u kao referentni fix-brief-3 dokument.
Implementer commit: dolazi nakon ovog evidence fajla (1 commit).

## BF-5: Resource-lifecycle error vraća pogrešan DTO za `generate_campaign_content`

**Requirement**: `generate_campaign_content` mora na svakoj failure putanji vratiti `GenerateContentResultUiModel` oblik: `{ok, campaign_id, generated_count, failed_count, content_piece_ids, error_code, error_message}`.

**Root cause (Codex reprodukcija, neovisno potvrđena)**: `_with_call_resources` dekorator u `bridge/__init__.py:121-149` hvata grešku nastalu izvan tijela dekorirane metode (npr. `_resource_scope()` ne može otvoriti SQLite konekciju). Hardkodiran `if method.__name__ == "configure_provider"` switch je slao `configure_provider` kroz `_provider_err`, a sve ostalo (uključujući `generate_campaign_content`) kroz `_err` — koji gradi `CampaignPlanResultUiModel` DTO. Rezultat: na realnoj infrastrukturnoj grešci, `generate_campaign_content` je vraćao DTO sa ključevima `{ok, campaign_id, plan_id, plan_item_count, error_code, error_message}` i NEDOSTAJUĆIM `generated_count`/`failed_count`/`content_piece_ids`. Typed JS caller je dobijao polja drugog DTO-a na najgoroj mogućoj failure putanji.

## Fix

### 1. Operacijski-svjestan dispatch u `_with_call_resources`

`src/ai_campaign_studio/presentation_webview/bridge/__init__.py:120-185` (nove konstante + prepravljeni dekorator):

```python
_LIFECYCLE_ERROR_MAPPERS: dict[str, str] = {
    "configure_provider": "_provider_err",
    "create_campaign_and_generate_plan": "_err",
    "generate_campaign_content": "_generate_err",
}
_LIFECYCLE_ERROR_MESSAGES: dict[str, str] = {
    "configure_provider": "Konfiguracija provajdera nije uspjela (interna greška).",
    "create_campaign_and_generate_plan": "Interna greška — pogledajte log aplikacije.",
    "generate_campaign_content": "Generisanje sadržaja nije uspjelo (interna greška).",
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
            mapper_name = _LIFECYCLE_ERROR_MAPPERS.get(
                method.__name__, "_err"
            )
            mapper = getattr(self, mapper_name)
            return mapper(
                _ERROR_INTERNAL,
                _LIFECYCLE_ERROR_MESSAGES.get(
                    method.__name__,
                    "Interna greška — pogledajte log aplikacije.",
                ),
            )
    return _wrapped
```

**Ključne osobine**:
- `_LIFECYCLE_ERROR_MAPPERS` je jedini izvor istine za dispatch — dodavanje nove `js_api` metode = dodati entry + `_LIFECYCLE_ERROR_MESSAGES` entry.
- Default fallback je `_err` (CampaignPlanResultUiModel) — historical default.
- `getattr(self, mapper_name)` — dinamički dohvat, ne treba if/elif lanac.
- Poruke po metodi su eksplicitne (po uzoru na Codex-ov primjer); fallback je generička interna greška.

### 2. Prošireni connection-failure test

`tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py:240-299` — isti test sada pokriva SVE TRI dekorirane metode, sa TAČNIM provjerama DTO ključeva za svaku.

Kritični assertion za `generate_campaign_content`:

```python
# Plan-flow keys must NOT leak into the generate-content result.
assert "plan_id" not in content
assert "plan_item_count" not in content
# Generate-content DTO keys MUST be present (even when zeroed).
assert set(content.keys()) == {
    "ok", "campaign_id", "generated_count", "failed_count",
    "content_piece_ids", "error_code", "error_message",
}
assert content["generated_count"] == 0
assert content["failed_count"] == 0
assert list(content["content_piece_ids"]) == []
```

Također provjerava da sentinel ključ (`test-secret-connection-failure-sentinel`) NE procuri u bilo koji od tri rezultata — secret-safety regression za SVE tri metode odjednom.

## Reproducibilni gate output

```text
$ python -m pytest tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py::test_connection_failure_never_raises_or_leaks_secret_to_js -v
tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py::test_connection_failure_never_raises_or_leaks_secret_to_js PASSED

$ python -m pytest tests/unit/presentation_webview/ tests/unit/presentation/ -q
263 passed in 11.24s

$ python -m ruff check .
All checks passed!

$ python -m mypy src
Success: no issues found in 174 source files

$ python -m pytest tests/unit/scripts/test_generate_phase0_gate_report.py tests/unit/scripts/test_check_no_secrets.py -v
33 passed in 59.49s
  - phase0_foundation_gate.json: PASS
  - check_no_secrets: 26/26 PASS
```

## Codex reprodukcija (zamjena za izvršenje)

Codex je u svom review-u dao ovu reprodukciju:

```python
with patch('ai_campaign_studio.presentation_webview.bridge.create_connection',
           side_effect=OSError('disk unavailable')):
    result = bridge.generate_campaign_content({'campaign_id': 'c-1', 'plan_id': 'p-1'})
# PRIJE: {'ok': False, 'campaign_id': None, 'plan_id': None, 'plan_item_count': None, ...}
# POSLIJE (očekivano): {'ok': False, 'campaign_id': None, 'generated_count': 0, 'failed_count': 0, 'content_piece_ids': [], 'error_code': 'INTERNAL_ERROR', 'error_message': 'Generisanje sadržaja nije uspjelo (interna greška).'}
```

Probao sam izvršiti istu reprodukciju sa `OSError` umjesto `RuntimeError` (Codex-ov primjer koristi `OSError`). Napomena: za pokretanje izvan pytest-a mora se eksplicitno postaviti `PYTHONPATH=src` jer Python sistemski ima `H:\AI Campaing Studio\src` (originalni repo) u path-u ispred worktree-a; pytest to radi automatski preko `pyproject.toml [tool.pytest.ini_options] pythonpath = ["src"]`.

```text
$ PYTHONPATH=src python -B -c "
from unittest.mock import patch
from ai_campaign_studio.config.paths import AppPaths
from ai_campaign_studio.config.settings import AppSettings
from ai_campaign_studio.presentation_webview.bridge import CampaignBridgeApi
import tempfile, pathlib
with tempfile.TemporaryDirectory() as td:
    p = pathlib.Path(td)
    paths = AppPaths(app_name='x', database_filename='t.db', data_dir_override=p)
    bridge = CampaignBridgeApi(paths=paths, settings=AppSettings(environment='development'))
    with patch('ai_campaign_studio.presentation_webview.bridge.create_connection',
               side_effect=OSError('disk unavailable')):
        result = bridge.generate_campaign_content({'campaign_id': 'c-1', 'plan_id': 'p-1'})
    print(result)
"
{'ok': False, 'campaign_id': None, 'generated_count': 0, 'failed_count': 0, 'content_piece_ids': (), 'error_code': 'INTERNAL_ERROR', 'error_message': 'Generisanje sadržaja nije uspjelo (interna greška).'}
```

(`content_piece_ids=()` je `tuple` (DTO tip); `list(()) == []` — moj test to provjerava kao `list(content["content_piece_ids"]) == []`.)

**Tačan DTO**, bez `plan_id`/`plan_item_count` leaka, bez `disk unavailable` u error_message (sentinel-safety). Log fajl (stderr) samo loguje `err=OSError` — nema tekst izuzetka, nema tajni.

## Šta je dirano (scope compliance)

Dozvoljeno (per task contract):
- `presentation_webview/bridge/__init__.py` — `_with_call_resources` dekorator + 2 nove module-level konstante
- `tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py` — proširenje postojećeg connection-failure testa

Nedirnuto (provjereno `git diff`):
- `domain/`, `application/`, `ports/`, `infrastructure/`, `resources/migrations/`, `pregled_izvoz/`
- Svi ostali testovi u `test_campaign_bridge_api.py` (i dalje prolaze — 263/263 presentation/presentation_webview suite)
- Svi ostali bridge metodi, uključujući `_err`/`_provider_err`/`_generate_err` (samo se DISPATCHUJE na njih, ne mijenjaju se)
- `app.js`, SSR, sve iz fix-brief-2 runde

## Šta koordinator treba uraditi

1. Push na `origin/task/ACS-GUI-008-studio-sadrzaja-generate` (NE radim push kao implementer).
2. Codex provjerava SAMO BF-5 diff/repro (kako je eksplicitno naveo).
3. Ako Codex PASS, Human Owner odobrenje, pa merge PR #4.
4. PR #4 se i dalje NE mergeuje na prethodni commit `897bd5c` — novi commit ide kao fix.

## Preostali rizici (iskreno)

1. **Test pokriva SVE TRI lifecycle-failure metode u jednom testu.** Ako budući refaktor doda četvrtu `js_api` metodu (npr. `edit_campaign_plan`), developera treba podsjetiti da doda entry u `_LIFECYCLE_ERROR_MAPPERS` + `_LIFECYCLE_ERROR_MESSAGES` + proširi test. Bez toga, nova metoda nasljeđuje `_err` fallback — što je po dizajnu ali se može propustiti. Comment u kodu to naglašava.
2. **Lokalni test `RuntimeError(f"failed while handling {sentinel_key}")` koristi isti sentinel za SVE tri metode** — Ako bi se neka metoda u budućnosti greškom vratila na stari `_err` dispatch, test bi i dalje prošao za tu metodu ako joj DTO ima `plan_id`/`plan_item_count` ključeve (što CampaignPlanResultUiModel IMA). Stoga test eksplicitno provjerava `set(content.keys()) == {...}` za generisanje — to je strože od "sentinel nije u output-u".
3. **OSError reprodukcija umjesto RuntimeError** — Codex je koristio `OSError("disk unavailable")`, moj test koristi `RuntimeError(f"failed while handling {sentinel_key}")`. Oba izazivaju isti `_with_call_resources` `except Exception` path. Razlika je samo u tipu — handler je `except Exception`, hvata oboje. Reprodukcija izvršena sa `OSError` daje TAČAN DTO oblik (gore output), potvrđuje fiks.
