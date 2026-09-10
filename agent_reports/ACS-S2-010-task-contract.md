---
task_id: ACS-S2-010
phase: "S2-G3 â€” HTTP Fetch + Discovery"
title: "Web fetch portovi + SSRF guard + robots/sitemap/crawl-budget (paralelan sa G4/G5)"
coordinator: MiniMax (privremeno, Claude na pauzi)
implementer: pi
reviewers: [claude, codex]
status: "OPEN -- contract written before code, Äeka implementera"
created_at: 2026-09-10
dependencies: [ACS-S2-001, ACS-S2-002, ACS-S2-009]
risk: MEDIUM
allowed_paths:
  - src/ai_campaign_studio/infrastructure/web_ingestion/
  - src/ai_campaign_studio/infrastructure/web_ingestion/__init__.py
  - pyproject.toml
  - tests/unit/infrastructure/web_ingestion/
  - tests/unit/infrastructure/web_ingestion/__init__.py
  - tests/infrastructure/web_ingestion/
  - tests/infrastructure/web_ingestion/__init__.py
forbidden_paths:
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/presentation_webview/
  - src/ai_campaign_studio/jobs/
  - src/ai_campaign_studio/infrastructure/database/
  - resources/migrations/
gitnexus_required: true
adversarial_required: false
---

# Kontekst

Peti Slice 2 gate (S2-G1/G2/G9 merged, S2-G3 paralelan sa G4/G5). Kanonski
plan Â§10 "S2-G3 â€” HTTP Fetch + Discovery": `infrastructure/web_ingestion/`
(robots_reader, sitemap_reader, url_safety_policy, domain_discovery,
url_normalizer, crawl_budget, http_fetcher). **Bez novog porta** â€”
koristi `IngestionRepositoryPort` iz S2-G1 (isti obrazac kao S2-G9 za
dokument ingestion). Sync/async odluka fiksirana u S2-G1
(`requests` + custom `HTTPAdapter` za SSRF, NE aiohttp/asyncio).

Reference dokumenti (po `.agent/TASK_ROUTING.md` "Website Ingestion task"):
- [Kanonski plan `docs/AI_Campaign_Studio_Slice_2_Canonical_Plan.md`](../../docs/AI_Campaign_Studio_Slice_2_Canonical_Plan.md):
  DAG Â§3, sync/async Â§5 (fiksirana), **SSRF Â§6** (detaljno), durability
  Â§7, hard gates Â§11, S2-G3 specifikacija Â§10.
- `domain/ingestion/entities.py` + `ports/repositories.py` (S2-G1 contract + S2-G2 lease queue).
- `.agent/GITNEXUS_PROTOCOL.md` (obavezan za MEDIUM).

# Å ta

Implementirati `infrastructure/web_ingestion/` module:

1. **`robots_reader`** (Protego â‰¥ 0.6.2): RFC 9309 robots.txt parser
   (cache â‰¤ 24h, unreachable â†’ disallow, unavailable â†’ allow).
2. **`sitemap_reader`**: `sitemap.xml` parser, izvlaÄi `<loc>` URL-ove
   (sa `<lastmod>` ako postoji). Validira XML strukturu.
3. **`url_safety_policy`** (Â§6 SSRF): **NAJBITNIJI DIO** â€” resolver
   koji ODBIJA:
   - `127.0.0.0/8` (loopback)
   - `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` (privatni opsezi)
   - `169.254.0.0/16` (link-local)
   - IPv6 `::1`, `fc00::/7`, `fe80::/10`
   - `0.0.0.0/8`, `255.255.255.255` (broadcast)
   - **literalna IP u URL-u ILI redirectu** (Â§6.2 strogo â€” ne samo DNS
     lookup na original URL, nego na SVAKI redirect target)
   - `userinfo@` u URL-u (`http://user:pass@host/` â€” credentials leak)
   - neodobreni portovi (default allow 80/443, opcionalno allow
     8080/8443 za dev samo, REJECT 22/23/25/3306/5432/6379/27017 i
     ostali privileged)
   - `hostname â†’ private A/AAAA` rezolucija (DOHVAT preko DNS prije
     konekcije)
4. **`domain_discovery`**: robots.txt + sitemap.xml + (opciono) `<a>`
   linkovi na startnom URL-u do max `crawl_budget`. VraÄ‡a `tuple[str, ...]`
   URL-ova za crawl queue. Poziva `url_safety_policy` na svaki kandidat
   PRIJE dodavanja u listu.
5. **`url_normalizer`**: scheme (https samo za externi), host
   (lowercase, IDNâ†’Punycode), path (percent-encoding, fragment
   strip), query (sort kljuÄeva za dedup).
6. **`crawl_budget`**: max N URL-ova po domeni (default 1000), politeness
   (min 1 sekunda izmeÄ‘u requesta istog hosta).
7. **`http_fetcher`**: `requests` + custom `HTTPAdapter` koji PRESREÄ†E
   `socket.create_connection` za SSRF enforcement na DNS + IP nivou.
   Response-size streaming limit (default 5 MB), timeout (connect 5s,
   read 10s), retry sa exponential backoff (max 3 pokuÅ¡aja).

# Acceptance (SSRF test matrica â€” Â§6, NE SMIJE proÄ‡i bez svega)

```python
# Minimalna matrica (proÅ¡irena verzija u fix-brief ako treba):
SSRF_TEST_CASES = [
    # Direktna blokada
    ("http://127.0.0.1/", reject, "loopback IPv4"),
    ("http://localhost/", reject, "DNS loopback"),
    ("http://10.0.0.1/", reject, "private 10/8"),
    ("http://192.168.1.1/", reject, "private 192.168/16"),
    ("http://172.16.0.1/", reject, "private 172.16/12"),
    ("http://169.254.169.254/latest/meta-data/", reject, "link-local AWS IMDS"),
    ("http://[::1]/", reject, "loopback IPv6"),
    ("http://[fc00::1]/", reject, "private IPv6"),
    ("http://[fe80::1]/", reject, "link-local IPv6"),
    ("http://0.0.0.0/", reject, "wildcard IPv4"),
    ("http://255.255.255.255/", reject, "broadcast IPv4"),
    ("http://user:pass@example.com/", reject, "userinfo"),
    ("http://example.com:22/", reject, "SSH port"),
    ("http://example.com:3306/", reject, "MySQL port"),
    ("http://2130706433/", reject, "decimal literal IP = 127.0.0.1"),
    ("http://0x7f000001/", reject, "hex literal IP = 127.0.0.1"),
    ("http://0177.0.0.1/", reject, "octal literal IP = 127.0.0.1"),
    # DNS rebinding
    ("http://localtest.me/", reject, "DNS resolves to 127.0.0.1"),
    ("http://127-0-0-1.nip.io/", reject, "DNS wildcard nip.io"),
    # Redirect
    ("http://example.com/redirect-to-localhost", reject, "redirect â†’ private"),
    ("http://example.com/redirect-to-imds", reject, "redirect â†’ 169.254"),
    # Public allowed
    ("http://example.com/", allow, "public"),
    ("https://example.com/", allow, "public HTTPS"),
]
```

**Test fajlovi** (obavezno):
- `tests/unit/infrastructure/web_ingestion/test_url_safety_policy.py`:
  cijela matrica, parametrizirana, sa oÄekivanim allow/reject.
- `tests/infrastructure/web_ingestion/test_ssrf_e2e.py`: live
  `http_fetcher` probe sa `requests-mock` ili lokalni HTTP server
  (binds to 127.0.0.1, fake redirect chain) â€” testira da SSRF
  enforcement radi u celom fetch lancu, ne samo u resolveru.
- `tests/unit/infrastructure/web_ingestion/test_robots_reader.py`:
  RFC 9309 (cache, unreachable, unavailable), 200/4xx/5xx, malformirani
  robots.txt.
- `tests/unit/infrastructure/web_ingestion/test_sitemap_reader.py`:
  Validan sitemap, prazan sitemap, malformirani XML, URL-ovi sa
  razliÄitim `<lastmod>`.
- `tests/unit/infrastructure/web_ingestion/test_url_normalizer.py`:
  IDN, percent-encoding, fragment strip, query sort.
- `tests/unit/infrastructure/web_ingestion/test_crawl_budget.py`:
  politeness timing (interval â‰¥ 1s), max N limit, reset po domeni.

# Å ta NE raditi

- **NE dodavati novi port u `ports/`** â€” koristi `IngestionRepositoryPort`
  iz S2-G1 (sliÄan obrazac kao S2-G9 dokumenti).
- **NE uvoditi novu shemu** (`structured_data_records` migracija je
  eksplicitno odloÅ¾ena u S2-002 contract Â§1, ostaje follow-up zaseban
  task, NE G3).
- **NE koristiti aiohttp/asyncio** â€” sync/async fiksirana u S2-G1
  (`requests` + custom `HTTPAdapter`).
- **NE raditi faktiÄki HTTP poziv u testovima** (live `requests` na
  realne domene) â€” `requests-mock` ili lokalni HTTP server binding
  na 127.0.0.1 (koji MORA biti blokiran od SSRF-a).
- **NE ignorisati `Content-Length` header** â€” streaming limit MORA biti
  provjeren PRIJE buffering-a.
- **NE cache-ovati robots.txt duÅ¾e od 24h** (RFC 9309).

# Implementation steps (redoslijed, SSRF-first)

1. ProÄitati kanonski plan Â§6 SSRF (cijela sekcija), Â§7 durability
   (crawl budget, politeness), Â§10 S2-G3 specifikacija, Â§11 hard gates.
2. ProÄitati `domain/ingestion/entities.py` (SourceSnapshot,
   IngestionRun, CrawlTarget), `ports/repositories.py`
   (IngestionRepositoryPort signatura za `register_crawl_targets`).
3. **Implementirati `url_safety_policy` PRVO** (SSRF enforcement) â€”
   sa test matricom kao prvim testom. Ovo je NAJVAÅ½NIJI dio,
   bug ovdje je bezbjednosni issue.
4. `http_fetcher` sa `HTTPAdapter` koji PRESREÄ†E DNS lookup
   (`socket.getaddrinfo`) i provjerava `url_safety_policy` na
   svakom hop-u (ukljuÄujuÄ‡i redirect chain).
5. `robots_reader`, `sitemap_reader`, `url_normalizer`,
   `domain_discovery`, `crawl_budget` â€” logika oko fetchera.
6. `__init__.py` exports + `pyproject.toml` documents extra ili
   requests/Protego u `[project.dependencies]` (vidi G3 prijedlog
   ispod).
7. `npx gitnexus detect_changes` PRIJE commit-a (GitNexus required).
8. Mutation-testing discipline: minimalno jedan mutation na
   `url_safety_policy` (npr. invertuj jedan SSRF check â†’ test FAIL,
   vrati â†’ PASS, `git diff --stat` Äist).

# Dependency management

Preporuka: u `[project.optional-dependencies]` (NE `[project.dependencies]`):
```toml
[project.optional-dependencies]
web-discovery = ["Protego>=0.6.2"]
```
sa `requests>=2.31` (veÄ‡ u `[project.dependencies]` preko `openai` i
sl., ALI treba provjeriti â€” ako ne, dodati u `[project.dependencies]`).
Ako Pi odluÄi staviti Protego u `[project.dependencies]` (core),
obrazloÅ¾iti u evidence.

# Acceptance (za review)

- [ ] Svi test fajlovi u `tests/unit/infrastructure/web_ingestion/` PROLAZE
- [ ] SSRF test matrica (svi 22+ sluÄajeva iznad) PROLAZE
- [ ] `tests/infrastructure/web_ingestion/test_ssrf_e2e.py` PROLAZI
      (live fetch sa mock/local server, redirect chain)
- [ ] `crawl_budget` politeness timing PROLAZI (interval â‰¥ 1s â€” koristiti
      `monkeypatch.setattr` na `time.sleep` ili sl.)
- [ ] `http_fetcher` sa redirect-om na privatni IP â†’ reject (NE prati redirect)
- [ ] `http_fetcher` sa `Content-Length > limit` â†’ reject PRIJE buffering
- [ ] NEMA novog porta u `ports/`
- [ ] NEMA izmjena u `domain/`, `application/`, `presentation_webview/`,
      `jobs/`, `infrastructure/database/`, `resources/migrations/`
- [ ] `python -m ruff check .` i `python -m mypy src` PROLAZE
- [ ] `python -m pytest -q` (DeepSeek unset) PROLAZI
- [ ] GitNexus `detect_changes` pokazuje SAMO nove simbole + `pyproject.toml`
- [ ] Mutation-test demonstriran (min 1 mutacija â†’ FAIL â†’ restore â†’ PASS)

# Review focus â€” Claude PRVO, PA Codex (MEDIUM, NOVI adapter)

- **SSRF enforcement je #1 prioritet**. Svaki test case u matrici MORA
  proÄ‡i. Codex Ä‡e posebno testirati edge cases: octal/hex/decimal
  literal IP, IDN homograph, DNS rebinding preko `nip.io` /
  `localtest.me`, redirect chain na `127.0.0.1`, IP-only host bez DNS-a.
- **`crawl_budget` politeness** â€” `time.sleep(â‰¥1)` izmeÄ‘u requesta istog
  hosta. Testirati sa `monkeypatch.setattr` na `time.sleep` da ne Äeka
  stvarno.
- **RFC 9309 robots** â€” cache invalidation 24h, malformed robots
  (allow vs disallow po RFC-u), unreachable host (disallow fallback
  po RFC-u).
- **Streaming response limit** â€” `Content-Length` header, ALI i
  streaming chunk limit (defense-in-depth ako header laÅ¾e).
- **`url_normalizer` deterministiÄnost** â€” isti URL daje isti
  normalized formu (za dedup u `crawl_budget`).
- **Scope Äist** â€” `gitnexus_detect_changes` (ili ruÄni diff) MORA
  pokazati 0 promjena u `ports/`, `domain/`, `application/`,
  `repository/`.

**Codex adversarial fokus**: probati zaobiÄ‡i SSRF sa neobiÄnim
encodingima (`http://â‘ â‘¡â‘¦.â“ª.â“ª.â‘ /`, URL sa Unicode whitespace, IDN
homograph, redirect sa `Refresh` header-om umjesto `Location`,
chain od 5+ redirecta sa razliÄitim privatnim IP-ima na svakom).

# Rollback

MEDIUM (nema migracije, nema GUI). Rollback: revert commit + `pip
uninstall Protego` ako je u `[project.dependencies]`. Ako je u
optional extra, samo revert.

# Coordination

- **Disjunktan sa S2-G4** (OpenCode, `infrastructure/extraction/` â€”
  koordinatorska odluka za ime dir-a, ALI scope je extraction) i
  S2-G5 (`infrastructure/visual_extraction/`, vizuelna analiza).
- **NE MORA Äekati S2-G4/G5** â€” paralelan po kanonskom plan Â§3.
- **G6 zavisi od G3+G4+G5+G9** â€” ne dirati G6 scope.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-S2-010-http-fetch
Branch:   task/ACS-S2-010-http-fetch
Base:     main @ d13ad18
```

# Napomena za implementera (Pi)

- **SSRF enforcement je SAFETY-CRITICAL**. Ako misliÅ¡ da SSRF
  enforcement "previÅ¡e" blokira legitimne sajtove, obrazloÅ¾i u
  evidence â€” default je STRICT.
- `Protego` API: `Protego.parse(robots_txt_content)` vraÄ‡a objekt sa
  `can_fetch(url, user_agent)` metodom. Cache sa TTL.
- `requests` + `HTTPAdapter`: custom adapter dobija `getaddrinfo`
  callback, provjerava `url_safety_policy` PRIJE konekcije.
- `Content-Length` header provjera na `response.headers['Content-Length']`
  PRIJE `response.content` accessor-a. Za streaming, Äitati u chunks
  i abort ako ukupan bytes > limit.
- Redirect chain: `requests.Session` sa `max_redirects=10`, ALI
  PRESREÄ†I svaki redirect i provjeri `url_safety_policy` na target
  URL-u. `allow_redirects=False` za default safety.
- Ako treba novi dependency (Protego), dodaj u
  `pyproject.toml [project.optional-dependencies] web-discovery` (ili
  prema koordinatorskoj odluci).

