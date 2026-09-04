# → ZA MINIMAX — ACS-GUI-005 fix runda 2 (BF-2, Codex nalaz)

**Od:** koordinator (Claude) · **Za:** MiniMax · **Datum:** 2026-09-04

Codex je vratio **FAIL** (1 blocking nalaz) na adversarial review. BF-1
(Google model_id) fix je potvrđen dobar — Codex ga nije reotvorio. Novi
nalaz je vezan za tvoju `__main__.py` izmjenu.

## BF-2 — `_open_window()` sada gradi pravi `CampaignBridgeApi()`, ali stari
## unit test to ne mock-uje

`test_pywebview_start_uses_explicit_edgechromium_and_debug_false`
(`tests/unit/presentation_webview/test_webview2_fail_loud.py:86`) je
PRIJE ACS-GUI-005 bio čist, izolovan unit test: mock-uje `webview` modul i
`_probe_webview2`, poziva `_open_window(...)`, provjerava da je
`webview.start` pozvan sa `gui="edgechromium", debug=False`. Ništa više.

Tvoja izmjena je dodala `bridge = CampaignBridgeApi()` unutar
`_open_window()`, PRIJE `webview.create_window(...)` poziva. To znači da
ovaj test sada TIHO zavisi od punog `create_bootstrap()` uspjeha (DB
konekcija, migracije, logging setup, paths) — test više nije hermetičan.

Kod mene taj test i dalje prolazi (5/5 u `test_webview2_fail_loud.py`),
ali kod Codex-a je pukao sa `PermissionError` na log fajlu (sandbox razlika
u file permissions). **Poenta nije da li puca kod mene ili kod Codex-a —
poenta je da unit test koji je trebao biti čist sada zavisi od
filesystem/DB/logging side effect-a koje ne treba da testira.** To je
krhko preko različitih okruženja (CI, druge mašine), tačno onako kako
je Codex predvidio.

## Šta uraditi

Codex predlaže dvije opcije, biraj koja ti više odgovara arhitektonski:

**Opcija A** — mock `CampaignBridgeApi` u testu:
```python
with patch.dict(sys.modules, {"webview": fake_webview}), patch(
    "ai_campaign_studio.presentation_webview.__main__._probe_webview2"
), patch(
    "ai_campaign_studio.presentation_webview.__main__.CampaignBridgeApi"
) as fake_bridge_cls:
    ...
    _open_window(...)
```
(zahtijeva da `CampaignBridgeApi` bude importovan na module-level u
`__main__.py`, ne lokalno unutar `_open_window` — provjeri da li tvoj
trenutni lazy `from .bridge import CampaignBridgeApi` unutar funkcije to
dozvoljava za patch-ovanje; ako ne, prebaci import na module-level, to je
sitna izmjena unutar tvog već dozvoljenog `allowed_paths` fajla).

**Opcija B** (Codex-ov drugi prijedlog) — mali `_build_bridge()` helper u
`__main__.py` koji samo poziva `CampaignBridgeApi()`, i test patch-uje
`_build_bridge` umjesto konstruktora direktno. Malo čistije za buduće
testove (jedan seam za sve).

Ja preferiram **Opciju B** (eksplicitan seam je lakše održavati), ali
prepuštam tebi finalnu odluku — obje su prihvatljive.

## Dozvola za `test_webview2_fail_loud.py`

Ovaj fajl NIJE bio u tvom originalnom `allowed_paths`, ali je pokvaren
TVOJOM izmjenom u `__main__.py` (koji jeste u allowed_paths) — isti
obrazac kao `test_import_boundaries.py` ranije. **Eksplicitno te
ovlašćujem, ovdje, pismeno, da izmijeniš TAČNO
`tests/unit/presentation_webview/test_webview2_fail_loud.py`** — samo
`test_pywebview_start_uses_explicit_edgechromium_and_debug_false`, ništa
drugo u tom fajlu. Nema potrebe da opet pitaš preko ask_user — ovo je
već koordinirano.

## Nakon fixa, ponovo pokreni CIJELI gate

```bash
python -m pytest tests/unit/presentation_webview/test_webview2_fail_loud.py -v
python -m pytest tests -q
python -m ruff check .
python -m mypy src
python -m pytest tests/architecture/test_import_boundaries.py -v
```

## Van scope-a ove runde

BF-1 (Google model_id) je zatvoren, ne diraj. Codex-ove N1/N2 napomene
(error mapping, factory empty-key) su non-blocking, ne trebaju izmjenu.

## Kad završiš

Evidence update (nova "Fix runda 2 (BF-2)" sekcija, doslovan test output).
Ne commit-uj. Ide nazad Codex-u na re-review.
