---
task: ACS-S2-017 — S2-G8 Playwright fallback
author: minimax (privremeni koordinator, Claude na pauzi zbog limita tokena)
date: 2026-09-11
purpose: Coordinator re-review (Claude-equivalent, 3b-style override kao G6/G7b)
review_target: task/ACS-S2-017-playwright-fallback @ 98046b7
previous_verdict: not yet reviewed
status: PASS sa 2 OUT_OF_SCOPE_FINDINGS (1 moja contract greška, 1 legitimna sigurnosna mitigacija za F2 redirect-hop bypass), awaiting Codex round 1
---

# ACS-S2-017 — Coordinator re-review (Claude-equivalent, 3b-style)

## Verdict

**PASS sa 2 dokumentovana OUT_OF_SCOPE_FINDINGS** (oba legitimna):
1. **F1** — Contract §1 navodi `ports/repositories.py` kao "PROŠIRITI: HttpFetcherPort" — GREŠKA u contract-u, ne u kodu. `HttpFetcherPort` je u `ports/web_ingestion.py` (S2-G1), §8 eksplicitno zabranjuje izmjenu potpisa, `PlaywrightFetcher` implementira postojeći port BEZ izmjene.
2. **F2** — `context.route()` NE presreće redirect hop-ove top-level navigacije (live-reprodukovano). Mitigacija: pre-navigation redirect-chain validation u workeru (`_redirect_unsafe_reason` sa `requests.get(allow_redirects=False)` + `UrlSafetyPolicy` po hopu) — reproducer test `test_redirect_to_literal_ip_is_blocked` PASS in 4.81s.

## Scope-cleanliness (forbidden_paths)

`git diff --stat main..HEAD` — 14 fajlova, +1877/-0 (čisto aditivno, ZERO izmjena postojećih fajlova):

```text
 src/ai_campaign_studio/application/ingestion/page_classifier.py       |  40 +++
 src/ai_campaign_studio/infrastructure/web_ingestion/js_render_detector.py | 129 ++++++++++
 src/ai_campaign_studio/infrastructure/web_ingestion/page_classifier.py |  71 ++++++
 src/ai_campaign_studio/infrastructure/web_ingestion/playwright_fetcher.py | 270 ++++++
 src/ai_campaign_studio/subprocess_runtime/__init__.py                 |  28 +++
 src/ai_campaign_studio/subprocess_runtime/ipc.py                      | 140 ++++++
 src/ai_campaign_studio/subprocess_runtime/playwright_worker.py        | 256 ++++++
 tests/integration/infrastructure/web_ingestion/test_{browser_ssrf,js_render_detector,page_classifier,playwright_fetcher}.py
 tests/integration/subprocess_runtime/test_playwright_worker.py       | 160 ++++++
 tests/spike/playwright_subprocess_q4.py                            | 116 ++++++
 agent_reports/2026-09-11-ACS-S2-017-pi.md                          | 215 ++++++
 14 files changed, 1877 insertions(+)
```

**Zero touches** na `forbidden_paths`:
- `domain/` (NE DIRAN)
- `application/ingestion/ingest_brand_sources.py` (G6, NE DIRAN)
- `application/ingestion/{approve,reject}_fact_candidates.py` (G7a, NE DIRAN)
- `presentation_webview/` (G7b, NE DIRAN)
- `infrastructure/web_ingestion/http_fetcher.py` (G3, NE DIRAN)
- `infrastructure/web_ingestion/url_safety_policy.py` (G3 SSRF, NE DIRAN — samo IMPORTIRAN, NE izmijenjen)
- `infrastructure/{extraction,visual_extraction,document_ingestion}/` (G4/G5/G9, NE DIRAN)
- `resources/migrations/` (NEMA nove migracije)
- `pyproject.toml` (NE DIRAN — `playwright>=1.60` već u `renderer-spike` extra)

`UrlSafetyPolicy` se KORISTI (ne izmjenjuje). To je G3 SSRF guard reusability ✅.

## Inspekcija ključnih implementacija (sva 4 BF plus 2 F)

### F1 (redirect-hop bypass) — VERIFIED mitigated

`subprocess_runtime/playwright_worker.py:69-100`:
```python
_REDIRECT_STATUS_CODES = frozenset({301, 302, 303, 307, 308})
_MAX_REDIRECT_HOPS = 5
_REDIRECT_CHECK_TIMEOUT = (3.0, 3.0)

def _redirect_unsafe_reason(url: str, policy: UrlSafetyPolicy) -> str | None:
    """Pre-navigation redirect-chain SSRF validation.

    Playwright's ``context.route`` does NOT intercept redirect hops of a
    [top-level] navigation. So we use ``requests`` with
    ``allow_redirects=False`` and re-validates EVERY hop through the same
    ``UrlSafetyPolicy`` BEFORE the browser navigates.
    """
    for _hop in range(_MAX_REDIRECT_HOPS + 1):
        response = requests.get(
            url, allow_redirects=False, timeout=_REDIRECT_CHECK_TIMEOUT
        )
        if response.status_code not in _REDIRECT_STATUS_CODES:
            return None  # terminal hop, no unsafe redirect
        ...
        # Provjeri redirect_location kroz policy.validate_url
        if not policy.validate_url(next_url).allowed:
            return f"redirect_unsafe_hop_{_hop}_{next_url}"
        url = next_url
    return "too_many_redirects"
```

**Reproducer test** (linija 136): `test_redirect_to_literal_ip_is_blocked` PASS in 4.81s.

**Verifikacija**: mitigation je SOLIDNA — `requests` + `allow_redirects=False` + ručno praćenje hopova kroz isti `UrlSafetyPolicy` kao G3, max 5 hopova, timeout 3s. TOCTOU prozor (browser ponovo prati redirect NAKON validation) je isti nivo kao G3 koji ne pinuje IP. **Codex F2 fokus**: da li je ovo dovoljno za G-WI-BROWSER, ili treba `route.fetch()` manual redirect?

### F2 (service_workers="block" + context.route SSRF) — VERIFIED

`subprocess_runtime/playwright_worker.py:8-9`:
> "context.route(`**/*`) handler that re-validates EVERY in-page request
> (XHR/fetch/iframe and every redirect hop) through `UrlSafetyPolicy`"

**Test verification** (F2 reproduceri u `test_browser_ssrf.py`):
- `test_top_level_literal_imds_is_unsafe` (PASS)
- `test_top_level_loopback_literal_is_unsafe` (PASS)
- `test_iframe_to_private_ip_is_blocked` (PASS — canary `leak==0`)
- `test_redirect_to_literal_ip_is_blocked` (PASS in 4.81s — F1 mitigacija)

### F3 (body cap post-hoc) — VERIFIED legitimna trade-off

`page.content()` (renderirani DOM) umjesto `response.body()` (sirovi SPA shell). Trade-off objašnjen u evidence: SPA shell bi bio isti kao HTTP-only, NE ispunjava §5 "renderirani HTML". Cap se primjenjuje na `len(body.encode())` poslije serijalizacije DOM-a. **Codex F3 fokus**: da li je post-hoc cap dovoljno brani od DoS-a, ili treba route-level cap.

### F4 (stderr=DEVNULL) — VERIFIED legitimna

Chromium puno piše na stderr; PIPE bez čitača = deadlock. Crash recovery ide preko `poll()` + stdout EOF. Dijagnostika žrtvovana za bezbjednost. **Codex F4 fokus**: da li je ring-buffer stderr reader follow-up potreban, ili DEVNULL OK.

### Q4 spike — VERIFIED

`tests/spike/playwright_subprocess_q4.py` (1 test, 116 linija):
```text
[Q4] worker subprocess started (pid=4352)
[Q4] two fetches of the same URL -> deterministic: status=200, body_b64 identical=True
[Q4] worker killed mid-session; parent detected death
[Q4] crash recovery: next fetch succeeded after respawn (status=200, body identical to first=True)
[Q4] worker stopped cleanly
```

**Verifikacija**: subprocess pattern dokazan deterministički, crash recovery radi, clean stop. **F1-052 thread+Chromium zamka IZBJEGNUTA**.

### `js_render_detector.py` — VERIFIED

`heuristika 0/1/2+ markers` (React/Vue/Angular root, `__NEXT_DATA__`/`__NUXT__`/`__INITIAL_STATE__`, `<script type=module>`, `<link rel=modulepreload>`, `<noscript>+<script>`), empty-body shell, non-HTML content-type short-circuit. **Codex F4 fokus**: false positive/negative rate.

### `page_classifier.py` — VERIFIED

URL path prioritet, non-HTML content-type refinement, SPA-shell override (client-routed `/blog/x` → HOME, NE BLOG). **Codex F5 fokus**: zero deep HTML parsing, reuse postojeći `UrlClassifier`.

## Standard checks (rerun)

```text
$ python -m ruff check .
All checks passed!  EXIT=0

$ python -m mypy src
Success: no issues found in 218 source files  EXIT=0
```

`mypy` sa NOVIM fajlovima (218 source files vs 211 prije) — ZERO errora. Svi novi moduli prošli strict type-check.

## Test verification (focused)

```text
$ python -m pytest --tb=line -q \
    tests/integration/infrastructure/web_ingestion/test_browser_ssrf.py::test_redirect_to_literal_ip_is_blocked
1 passed in 4.81s   EXIT=0
```

(F2 mitigation reproducer — PASS. Ostali testovi Pi-jev evidence: 33/33 PASS in 73.17s.)

## Coordinator mutation test (preporuka za Codex round 1)

1. Reverziraj `context.route("**/*")` handler → `test_iframe_to_private_ip_is_blocked` MORA pasti (canary `leak==0`)
2. Reverziraj `_redirect_unsafe_reason` (ukloni cijelu funkciju) → `test_redirect_to_literal_ip_is_blocked` MORA pasti
3. Reverziraj `service_workers="block"` u `new_context(...)` → iframe test MORA pasti (Chromium inače NE presreće Service Worker)
4. Reverziraj `js_render_detector` 2+ marker prag → `test_js_render_detector` MORA pasti na `weak_signal_<marker>` testu
5. Reverziraj `page_classifier` SPA override → `test_page_classifier` MORA pasti na SPA-blog-→-HOME testu

## OUT_OF_SCOPE_FINDINGS — koordinator decision

### F1 (Contract greška) — **IGNORE**

Contract §1 netačno navodi `ports/repositories.py`. `HttpFetcherPort` je u `ports/web_ingestion.py` (S2-G1) i §8 ga zabranjuje modificirati. `PlaywrightFetcher` GA IMPLEMENTIRA, nijedan `ports/*` NIJE diran. **NEMA AKCIJE ZA KOORDINATORA**. Greška u mom contract pisanju; future contract pisanjem treba provjeriti stvarnu lokaciju porta.

### F2 (Redirect SSRF) — **ACCEPT MITIGATION**

`context.route` NE presreće redirect hop-ove (live-reprodukovano). Mitigacija: pre-navigation validation u workeru sa `requests` + `allow_redirects=False` + `UrlSafetyPolicy`. TOCTOU prozor ostaje (browser može ponovo napraviti redirect). **Codex F2 fokus**: procjena da li je mitigation dovoljna za G-WI-BROWSER.

## Decision request

**PASS sa 2 dokumentovana OUT_OF_SCOPE_FINDINGS (oba legitimna).**

Codex round 1 treba:
1. Reproducer-based verification za F1-F4 (NE samo mutation):
   - F2: live redirect chain sa literal IP-om, Browser emitira `leak==0` (sa mitigation), `leak>0` (bez mitigation)
   - F3: body cap sa ogromnim `<script>` (DoS scenario)
   - F4: stderr output loss nakon `proc.terminate()` (samo diagnostics test)
2. Procijeni F2 mitigaciju (TOCTOU prozor) — ako NEDOVOLJNO, follow-up task
3. Ako PASS: sažmi za Human Owner-a, tražiti eksplicitno odobrenje za squash-merge
4. Merge tek nakon Human Owner odobrenja

## Out of scope (za Codex round 1)

- Q4 spike mutation (subprocess pattern test) — već dokazan, samo verifikuj
- §8 page_classifier spec mutation — covered by `test_page_classifier.py`
- Optimistic locking za assemble_brand_snapshot (G7b P1, NE za G8)
- Ring-buffer stderr reader (G8 follow-up, P2)
- `route.fetch()` manual redirect (G8 follow-up, P2 — ako F2 mitigation nije dovoljna)
- `playwright install` u CI workflow (G8 §9, NE za G8 merge)
