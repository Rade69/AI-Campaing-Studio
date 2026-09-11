---
task_id: ACS-S2-017
phase: "S2-G8 — Playwright fallback (SPIKE + gate, opcioni)"
title: "playwright_worker.py (subprocess, persistent) + js_render_detector.py — JS-heavy fallback za HTTP fetch"
coordinator: minimax (privremeni, Claude na pauzi zbog limita tokena)
implementer: pi (ili opencode, ko je slobodan)
reviewers: [claude, codex, human_owner]
status: "OPEN -- contract written before code. S2-G8 je OPCIONI po Canonical plan §10, NE blokira 'unesi URL → vidi rezultat' petlju (zatvorena u S2-G7b merge)."
created_at: 2026-09-11
dependencies: [ACS-S2-001, ACS-S2-002, ACS-S2-014, ACS-S2-015, ACS-S2-016]  # svi MERGED
risk: HIGH
gitnexus_required: true
adversarial_required: true
opcionalno: true
---

# Kontekst

Deveti i **POSLJEDNjI** Slice 2 gate-ovi. Kanonski plan §10 S2-G8
specificira:

> "**Scope:** `playwright_worker.py` (subprocess-baziran persistent
> worker, §6.3 route-validacija), `js_render_detector.py`. Aktivira
> se SAMO kad HTTP fetch vrati JS-heavy stranicu (§8 klasifikacija
> ulaz)."

> "**Ključna odluka (Q4):** subprocess, NE thread (isti razlog kao
> F1-052 pytest izolacija — thread+Chromium dokazano rizičan).
> Default = HTTP-first."

> "**Risk:** HIGH (browser worker, packaging, Windows). Opcioni, ne
> blokira ništa drugo."

**Zašto je OPCIONI**: S2-G7b (Brand Intelligence Review UI) je
MERGED 2026-09-11 (commit `cc35f82`). "Unesi URL, vidi rezultat"
petlja je ZATVORENA sa HTTP-only G3+G4+G5 cijevima. S2-G8 je
**fallback** za JS-heavy sajtove (SPA, klijentski renderirane
stranice) koje HTTP fetch ne može parsirati. Ako aplikacija ne
treba pokrivati takve sajtove, G8 se može preskočiti.

**Kada se G8 aktivira**: SAMO kad `js_render_detector` klasificira
HTTP fetch response kao JS-heavy (po §8 PageClassifier, TODO u
planu). Za tipične marketing sajtove, blog-ove, e-commerce
listing-e, G3+G4 već rade.

# Ključna arhitektonska odluka (Q4 — subprocess, NE thread)

F1-052 (pytest izolacija) je dokazao da `thread + Chromium` pati
od flaky test izolacije (Chromium drži file lock-ove, port-ove,
profile state). U produkciji, thread-based Playwright bi:

1. Držao globalni Chromium lock — samo jedan crawl u isto vrijeme
2. Dijelio profile state između targeta — kontaminacija cookie-ja,
   localStorage
3. Diffikultno cleanup-ovati na cancel (kill thread vs. graceful
   shutdown)

**Q4 odluka**: subprocess-bazirani persistent worker.

```python
# playwright_worker.py (subprocess)
class PlaywrightWorker:
    """Long-lived subprocess; main process talks via stdin/stdout.
    Owns ONE Chromium instance, services MULTIPLE fetch requests
    serially (one page = one navigation, with full cleanup between)."""

    def __init__(self):
        self._proc = subprocess.Popen(
            ["python", "-m", "ai_campaign_studio.subprocess_runtime.playwright_worker"],
            stdin=PIPE, stdout=PIPE, stderr=PIPE,
        )

    def fetch(self, url: str, timeout: int) -> PlaywrightResult:
        """Send JSON request, get JSON response. Synchronous."""
        self._proc.stdin.write(json.dumps({"url": url, "timeout": timeout}).encode() + b"\n")
        self._proc.stdin.flush()
        line = self._proc.stdout.readline()
        return PlaywrightResult.from_json(line)
```

**Trade-off**:
- ✅ Jedan Chromium = cleanup determinističan (subprocess kill = full
  teardown, no thread zombie)
- ✅ Profile state izolacija (svaki request = nova context ili
  context-per-origin)
- ✅ Cancel jednostavan: `proc.terminate()` je blocking ali
  bounded (Chromium exit <5s)
- ⚠️ IPC overhead: stdin/stdout JSON po zahtjevu (~5-20ms)
- ⚠️ Subprocess startup: ~1-2s prvi put (Chromium launch), poslije
  reuseable

**Alternative (NE radimo)**: thread-based Playwright (single
Chromium, multiple page contexts). Odbaceno zbog F1-052.

# §1 — Scope (allowed_paths, sve su ADITIVNE izmjene)

```yaml
allowed_paths:
  # Subprocess worker (production code)
  - src/ai_campaign_studio/subprocess_runtime/__init__.py  # NOVI
  - src/ai_campaign_studio/subprocess_runtime/playwright_worker.py  # NOVI
  - src/ai_campaign_studio/subprocess_runtime/ipc.py  # NOVI (JSON-RPC helpers)
  - src/ai_campaign_studio/infrastructure/web_ingestion/playwright_fetcher.py  # NOVI (HttpFetcherPort impl)
  - src/ai_campaign_studio/infrastructure/web_ingestion/js_render_detector.py  # NOVI
  - src/ai_campaign_studio/infrastructure/web_ingestion/page_classifier.py  # NOVI (§8)
  - src/ai_campaign_studio/application/ingestion/page_classifier.py  # NOVI (use-case wrapper)
  - src/ai_campaign_studio/ports/repositories.py  # PROŠIRITI: HttpFetcherPort za Playwright (BEZ izmjene postojećih)
  # Testovi
  - tests/integration/infrastructure/web_ingestion/test_playwright_fetcher.py  # NOVI
  - tests/integration/infrastructure/web_ingestion/test_js_render_detector.py  # NOVI
  - tests/integration/infrastructure/web_ingestion/test_browser_ssrf.py  # NOVI
  - tests/spike/playwright_subprocess_q4.py  # NOVI (Q4 spike reproducer)
  - tests/integration/subprocess_runtime/test_playwright_worker.py  # NOVI
  - agent_reports/2026-09-11-ACS-S2-017-pi.md
  - agent_reports/2026-09-11-ACS-S2-017-fix-round*-brief.md
forbidden_paths:
  - src/ai_campaign_studio/domain/  # NE DIRATI
  - src/ai_campaign_studio/application/ingestion/ingest_brand_sources.py  # NE DIRATI (G6)
  - src/ai_campaign_studio/application/ingestion/approve_fact_candidates.py  # NE DIRATI (G7a)
  - src/ai_campaign_studio/application/ingestion/reject_fact_candidates.py  # NE DIRATI (G7a)
  - src/ai_campaign_studio/presentation_webview/  # NE DIRATI (G7b)
  - src/ai_campaign_studio/infrastructure/web_ingestion/http_fetcher.py  # NE DIRATI (G3, koristimo kao referenca)
  - src/ai_campaign_studio/infrastructure/web_ingestion/url_safety_policy.py  # NE DIRATI (G3 SSRF)
  - src/ai_campaign_studio/infrastructure/web_ingestion/robots_reader.py  # NE DIRATI (G3)
  - src/ai_campaign_studio/infrastructure/web_ingestion/sitemap_reader.py  # NE DIRATI (G3)
  - src/ai_campaign_studio/infrastructure/web_ingestion/url_normalizer.py  # NE DIRATI (G3)
  - src/ai_campaign_studio/infrastructure/web_ingestion/domain_discovery.py  # NE DIRATI (G3)
  - src/ai_campaign_studio/infrastructure/web_ingestion/crawl_budget.py  # NE DIRATI (G3)
  - src/ai_campaign_studio/infrastructure/extraction/  # NE DIRATI (G4)
  - src/ai_campaign_studio/infrastructure/visual_extraction/  # NE DIRATI (G5)
  - src/ai_campaign_studio/infrastructure/document_ingestion/  # NE DIRATI (G9)
  - resources/migrations/  # NEMA NOVE MIGRACIJE
  - pyproject.toml  # NE DIRATI (playwright>=1.60 već u renderer-spike extra)
```

**pyproject.toml napomena**: `renderer-spike = ["playwright>=1.60"]` već postoji (linija 102). Canonical install koristi `.[dev]` ALI NE `.[renderer-spike]`. Playwright NE SMIJE biti u `[project.dependencies]` (zbog Windows install ovisnosti). CI install mora ostati `pip install -e ".[dev]"` (NE dodavati `[renderer-spike]` jer CI ne treba pokretati Playwright u testu — to je G3-G7 worker samo, ne CI infrastruktura).

# §2 — `playwright_worker.py` (subprocess)

**Proces komunikacija** (JSON-RPC, line-delimited):
- Request: `{"request_id": "uuid", "url": "...", "timeout": 20, "max_bytes": 5_000_000, "browser": "chromium"}`
- Response: `{"request_id": "uuid", "ok": true, "status_code": 200, "content_type": "text/html", "body_b64": "...", "headers": {...}}` ili `{"request_id": "uuid", "ok": false, "error_code": "...", "error_message": "..."}`

**Browser hardening (G-WI-BROWSER + §6.3)**:
- `service_workers="block"` na context — Playwright ne presreće
  Service Worker zahtjeve inače
- `context.route(handler)` — svaki in-page XHR/fetch/iframe request
  prolazi kroz `UrlSafetyPolicy.validate_url` (isti kao G3 SSRF)
- `context.set_extra_http_headers` — NE (Bez tajnih headera;
  Playwright context ne smije imati API ključeve)
- Per-request `BrowserContext` (NE globalni) — svaki fetch = novi
  context, full cleanup
- `await context.close()` poslije svakog fetch — obavezno čak i
  na greške

**Timeout + body limit**:
- `page.set_default_timeout(timeout_seconds)` (default 20s)
- `page.goto(url, timeout=timeout_seconds, wait_until="networkidle")`
- `response.body()` cap na `max_bytes` (5 MB default) — ako
  prelazi, abort + error `body_too_large`

**Subprocess lifecycle**:
- Parent (`infrastructure/web_ingestion/playwright_fetcher.py`) drži
  worker process. `start()` pokreće subprocess, `stop()` terminira.
- Idempotent: višestruki `start()`-ovi ne smiju kreirati
  višestruke procese
- Crash recovery: ako subprocess dies, parent detektuje kroz
  `proc.poll()` i rekreira
- Timeout: ako request traje > timeout, parent terminira subprocess
  i rekreira (ČISTO STANJE, F1-052 reason)

# §3 — `js_render_detector.py`

**Input**: HTTP fetch response (status_code, content_type, body preview)
**Output**: `(bool, str)` — `(is_js_heavy, reason)`

**Heuristika** (po Canonical plan §8):
1. **Content-Type**:
   - Ako `text/html` BEZ `text/plain`: nastavi heuristiku
   - Ako `application/json`, `application/xml`, `text/plain`, slika,
     PDF, DOCX, XLSX: `is_js_heavy=False` (HTTP-only je dovoljno)
2. **HTML markers** (regex na body preview, prvih 50KB):
   - `<script type="module">` + `<link rel="modulepreload">` → SPA
   - `<div id="root">` (React) / `<div id="app">` (Vue) / `<app-root>` (Angular) → SPA
   - `__NEXT_DATA__`, `__NUXT__`, `window.__INITIAL_STATE__` →
     SSR/CSR framework
   - `<noscript>` u kombinaciji sa `<script>` (graceful degradation
     pattern)
3. **Empty body** (HTML sa `<head>` ali `<body>` skoro prazan):
   - Ako body ima <100 chars nakon `<body>` otvaranja tag-a →
     `is_js_heavy=True` (sadržaj se dodaje JS-om)
4. **Confidence threshold**:
   - 0 markers → `False, "no_js_markers"`
   - 1 marker → `False, "weak_signal_<marker>"` (NE aktiviraj G8)
   - 2+ markers → `True, "js_heavy_<markers>"` (aktiviraj G8)

**Trade-off**: false positives (G8 aktiviran za statičan sajt)
koštaju 1-2s po URL-u (subprocess IPC). False negatives (G8 NE
aktiviran za JS-heavy sajt) koštaju loš extraction (prazan
content). Prag od 2+ markers je balans.

# §4 — `page_classifier.py` (§8)

**PageClassifier port** (port metoda):
```python
def classify(url: str, content_type: str, body_preview: str) -> PageType:
    """Determine page type from URL + content signals.

    Used by IngestBrandSources (G6) to choose page-specific extractors
    (e.g. PRODUCT-page gets different chunking than BLOG-page).
    """
```

**Signal priority**:
1. **URL path**: `/products/<slug>` → PRODUCT, `/blog/<slug>` →
   BLOG, `/about` → ABOUT, `/contact` → CONTACT, root → HOME
2. **Content-Type + Content-Language headers** (NE body parsing —
   preširoko, scope-creep)
3. **HTML markers** (već u `js_render_detector`): ako
   `__NEXT_DATA__` ili React/Vue/Angular root → SPApp, NE klasificiraj
   kao BLOG (SPA homepage je HOME, NE BLOG)

**Output**: `PageType` enum (HOME, ABOUT, PRODUCT, BLOG, ARTICLE, CONTACT, OTHER)

**Integration**: `IngestBrandSources._classify_target(target, snapshot) → PageType`
poziva classifier, koristi result za page-specific extraction logic.

**Risk**: classifier scope-creep — implementer treba paziti da NE
uvodi deep HTML parsing (kao F1-053 query-param pattern, reuse
postojeći).

# §5 — Acceptance (G-WI-BROWSER, opcioni)

### Obavezno

1. **Q4 spike reproducer** (`tests/spike/playwright_subprocess_q4.py`):
   - Subprocess worker pokrenut, 2 fetch requesta (isti URL)
   - Rezultat: deterministički, oba response-a sa istim
     `status_code`, `body_b64` hash
   - Subprocess kill poslije 1 fetch → rekreacija → 2. fetch OK
   - Crash recovery: `proc.terminate()` u sredini → parent
     detektuje, rekreira
2. **Browser SSRF test** (`test_browser_ssrf.py`):
   - Playwright context.route() blokira `<iframe src="http://169.254.169.254/">`
     (literal AWS metadata IP)
   - URL sa literal IP-om → subprocess vraća `error_code="unsafe_url"`
   - Redirect chain ka literal IP-u → blocked
3. **JS detection reproducer** (`test_js_render_detector.py`):
   - `text/html` sa `<div id="root">` + `<script type="module">` →
     `(True, "js_heavy_react_root+module")`
   - `text/html` sa statičkim `<p>Hello world</p>` →
     `(False, "no_js_markers")`
   - `text/html` sa 1 markerom →
     `(False, "weak_signal_<marker>")`
4. **PageClassifier reproducer** (`test_page_classifier.py` — u
   `infrastructure/web_ingestion/`):
   - URL `/products/foo` → PRODUCT
   - URL `/blog/2024/why-x` → BLOG
   - URL `/` + React marker → HOME (NE BLOG)
5. **Subprocess integration** (`test_playwright_worker.py`):
   - End-to-end: `PlaywrightFetcher.fetch(url)` poziva subprocess,
     čeka response, parsira body
   - Timeout: 25s, response_timeout 20s — ako subprocess ne
     odgovori, parent terminira i rekreira

### Standardna verifikacija

```text
python -m ruff check .: All checks passed
python -m mypy src: 211 source files, 0 errors
python -m pytest -q: 1488+ passed (G7b regression), 1 skipped, 0 failed
python -m pytest -q tests/integration/infrastructure/web_ingestion/test_playwright_fetcher.py \
  tests/integration/infrastructure/web_ingestion/test_js_render_detector.py \
  tests/integration/infrastructure/web_ingestion/test_browser_ssrf.py \
  tests/integration/subprocess_runtime/test_playwright_worker.py \
  tests/spike/playwright_subprocess_q4.py: 6/6 PASS
git diff --check origin/main...HEAD: clean
GitNexus pre-change impact: prove NO new HIGH-risk blast radius
  (SubprocessWorker = new module, isolated; PageClassifier = new
  port method, additive)
```

### Materialno bolji rezultat (G-WI-BROWSER)

Test sa PRAVIM JS-heavy sajtom (npr. `react.dev`, `vuejs.org`,
`angular.io`):
1. HTTP fetch → body: `<div id="root"></div>` (prazan)
2. HTTP-only extraction: 0 chunks (ContentExtractor ne nalazi
   tekst)
3. Playwright fallback activation (js_heavy=True)
4. Playwright fetch → body: cijeli renderirani HTML, 5-50KB
5. Extraction: 10-30 chunks
6. **Dokazivo materijalno bolji**: chunks Playwright > chunks
   HTTP-only by 5x (iliti barem > 1 chunk)

# §6 — Workflow (HIGH, pun ciklus, opcioni)

1. **Pi implementer**: piše kod po contract-u, pokreće pytest,
   ruff, mypy. Otvara PR.
2. **Coordinator re-review (Claude-equivalent ili Claude kad se
   vrati)**: scope-cleanliness, forbidden_paths, contract
   compliance, integration testovi.
3. **Codex adversarial re-review**: reproducer-based + mutation-based.
   Posebno:
   - Service Worker bypass attempt (`service_workers="block"`
     effective?)
   - `context.route()` SSRF bypass (in-page XHR ka literal IP)
   - Subprocess crash recovery (kill, restart, idempotency)
   - `js_render_detector` false positive/negative rate
4. **Coordinator mutation-test**: reverziranje fallback-a,
   reverziranje SSRF guard-a, reverziranje timeout-a — sve
   MORAJU pasti.
5. **Human Owner**: eksplicitno odobrenje za squash-merge
   (NE §29, NE koordinator-override).
6. **Coordinator**: squash-merge, post-merge ciklus.

# §7 — Workflow odstupanja (ako Claude ostane na pauzi)

Isti pattern kao G6/G7b: Human Owner može odobriti 3b override
(Codex PASS + koordinator PASS + Human Owner odobrenje).
**Bez presedana za buduće HIGH taskove**; Claude PASS i dalje
standard kad Claude bude dostupan.

# §8 — Šta NE SMIJE (out of scope)

- Nema izmjene `HttpFetcherPort` potpisa (G3) — Playwright fetcher
  IMPLEMENTIRA postojeći port
- Nema izmjene `UrlSafetyPolicy` (G3 SSRF) — Playwright context.route()
  KORISTI isti policy kao G3
- Nema izmjene HTTP fetch (G3) — G8 je fallback, NE zamjena
- Nema izmjene Extraction (G4) — Playwright HTML se šalje kroz
  isti `MainContentExtractor` kao HTTP body
- Nema izmjene Visual Identity (G5) — vizuelni extraction se
  NE ponavlja u Playwright (HTTP body + isti Visual extractor)
- Nema izmjene G6 pipeline orchestrator — `js_render_detector`
  je SAMO heuristika, NE pipeline mutacija
- Nema izmjene G7b (Brand Review UI) — ne dodavati JS-heavy
  kontrole u GUI
- Nema izmjene `pyproject.toml` dependencies — `playwright>=1.60`
  već u `renderer-spike` extra, NE u `[project.dependencies]`
- Nema nove migracije (PageClassifier je in-memory)
- Nema S2-G9 — S2-G9 je S2-G7b
- Nema uvodjenja page-redirect automatskog re-crawl-a (G-WI-RECRAWL
  je već u G6 acceptance, NE za G8)
- Nema uvodjenja WebSocket transporta (G3 je HTTP, G8 je HTTP
  fallback, NE WebSocket)
- Nema "offline mode" (G3 je offline-tolerant već)
- Nema testova na PRAVIM vanjskim sajtovima (sa interneta) u CI
  (Q4 spike testira LOKALNI HTML, NE online)

# §9 — Posebna ograničenja

### Windows kompatibilnost

Playwright + Chromium na Windows:
- Chromium instalacija zahtijeva `playwright install chromium` (NE u
  `pip install` workflow)
- CI NE SMIJE pokretati Playwright (zbog Windows install ovisnosti)
- CI: `pytest -q --ignore=tests/spike --ignore=tests/integration/subprocess_runtime`
  (preskoči Playwright-specific testove)
- Lokalno (developer machine): pokrenuti `playwright install chromium`
  ručno prije pokretanja Playwright testova

### Pakovanje

`pyproject.toml:102` već ima `renderer-spike = ["playwright>=1.60"]`.
G8 NE SMIJE dodati `playwright` u `[project.dependencies]` (jer
Windows install zahtijeva `playwright install`, NE radi kroz
`pip install -e .`).

CI workflow: `pip install -e ".[dev]"` (BEZ `.[renderer-spike]`).
`tests/integration/subprocess_runtime/` i `tests/spike/` će
biti preskočeni u CI (`--ignore` flag), ali PROLAZE lokalno.

### Threading

G3 već koristi `_resource_scope` (ContextVar pattern) za
thread-safe resurse. G8 NE SMIJE uvoditi novi thread safety
pattern — subprocess je JEDINI process, single-threaded.

# §10 — Open question (za spike output)

Ako Q4 spike pokaže da subprocess pattern NE RADI (npr. Chromium
crash na Windows, IPC overhead preveliki, memory leak u
subprocess), koordinator piše follow-up task contract za
THREAD-BASED pattern (suprotno §2 odluka) sa eksplicitnim
upozorenjem "F1-052 precedent" u contract-u. NE raditi
thread-based bez eksplicitnog novog task contract-a.
