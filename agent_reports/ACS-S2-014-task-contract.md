---
task_id: ACS-S2-014
phase: "S2-G6 — Ingestion Pipeline use-case + JobManager + Checkpoint"
title: "application/ingestion/ingest_brand_sources.py — DISCOVER→CLASSIFY→FETCH→EXTRACT→BUILD_FACTS→DONE orchestration"
coordinator: claude
implementer: TBD
reviewers: [claude, codex]
status: "OPEN -- contract written before code, čeka implementera"
created_at: 2026-09-10
dependencies: [ACS-S2-001, ACS-S2-002, ACS-S2-009, ACS-S2-010, ACS-S2-011, ACS-S2-012]
risk: HIGH
allowed_paths:
  - src/ai_campaign_studio/application/ingestion/
  - src/ai_campaign_studio/infrastructure/web_ingestion/url_classifier.py
  - src/ai_campaign_studio/infrastructure/web_ingestion/__init__.py
  - tests/unit/application/ingestion/
  - tests/unit/infrastructure/web_ingestion/test_url_classifier.py
  - tests/integration/application/ingestion/
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/infrastructure/database/
  - src/ai_campaign_studio/infrastructure/extraction/
  - src/ai_campaign_studio/infrastructure/visual_extraction/
  - src/ai_campaign_studio/infrastructure/document_ingestion/
  - src/ai_campaign_studio/infrastructure/web_ingestion/http_fetcher.py
  - src/ai_campaign_studio/infrastructure/web_ingestion/url_safety_policy.py
  - src/ai_campaign_studio/infrastructure/web_ingestion/robots_reader.py
  - src/ai_campaign_studio/infrastructure/web_ingestion/sitemap_reader.py
  - src/ai_campaign_studio/infrastructure/web_ingestion/domain_discovery.py
  - src/ai_campaign_studio/infrastructure/web_ingestion/crawl_budget.py
  - src/ai_campaign_studio/presentation_webview/
  - resources/migrations/
gitnexus_required: true
adversarial_required: true
---

# Kontekst

Šesti Slice 2 gate — **najveći i arhitektonski najrizičniji gate u
Slice 2 do sad**. Kanonski plan §10 "S2-G6": orkestrira
DISCOVER→CLASSIFY→FETCH→RENDER→EXTRACT→BUILD_FACTS→DONE, job-backed
preko `JobManager`, §7 lease-queue recovery, cooperative cancellation.
**Risk HIGH — ista klasa grešaka kao ACS-F1-047/ACS-HOTFIX-001**
(concurrency/lifecycle race conditions). Pun review ciklus: Claude →
Codex → Human Owner, NE §29.

**Sve zavisnosti su MERGED**: S2-G1 (domain/ports, PR #23), S2-G2
(persistence + lease queue, PR #25), S2-G3 (HTTP fetch + SSRF + robots
+ sitemap + discovery + budget, PR #27), S2-G4 (content extraction,
PR #28), S2-G5 (visual identity, PR #30), S2-G9 (document parsers,
PR #26).

**Nezavisno verifikovani konkretni building blockovi** (pročitani
liniju-po-liniju prije pisanja ovog kontrakta, NE pretpostavljeni):

```text
G3  infrastructure/web_ingestion/
    HttpFetcher().fetch(url) -> FetchResult (url, final_url, status_code,
        content: bytes|None, content_type, error)
    DomainDiscovery(...).discover(start_url) -> tuple[str, ...]
    SitemapReader().<pogledati metodu> -> tuple[SitemapEntry, ...]
    RobotsReader().can_fetch(url) -> bool, .sitemaps(url) -> tuple[str,...]
    CrawlBudget().can_crawl(domain) -> bool,
        .wait_politeness(domain) -> float, .record_fetch(domain) -> None
    normalize_url(url) -> str
    UrlSafetyPolicy (već primijenjen UNUTAR HttpFetcher/SafeHttpAdapter
        -- G6 NE treba ponovo validirati URL prije fetch-a, HttpFetcher
        to već radi na SVAKOM hop-u)

G4  infrastructure/extraction/
    MainContentExtractor().extract(html: str) -> str (NE
        ContentExtractionResult -- G4 evidence eksplicitna odluka,
        chunking je G6 posao)
    BoilerplateFilter().<pogledati metodu>(text: str) -> str
    Deduplicator().<pogledati metodu>(chunks) -> dedup chunks

G5  infrastructure/visual_extraction/
    VisualIdentityAdapter().extract(html: str, base_url: str)
        -> VisualIdentity (postojeći domain VO, NE SourceChunk)

G9  infrastructure/document_ingestion/
    PdfSource/DocxSource/XlsxSource: SVA TRI dijele identičan potpis
    .extract(path: str, run_id: IngestionRunId,
        snapshot_id: SourceSnapshotId | None = None)
        -> tuple[SourceChunk, ...]
    (raise DocumentParseError ako snapshot_id nije proslijeđen)

    NAPOMENA: ovaj potpis NE ODGOVARA `DocumentExtractorPort.extract(
    file_path: str) -> ContentExtractionResult` iz S2-G1
    (`ports/web_ingestion.py:111`) -- G9 implementer je namjerno birao
    drugačiji, direktniji shape (dokumenti već proizvode gotove
    SourceChunk-ove sa dodijeljenim snapshot_id, jer za lokalni fajl
    "fetch" i "extract" su prirodno jedan korak). `DocumentExtractorPort`
    je efektivno OSIROČEN -- nijedan adapter ga ne implementira. G6
    MORA pozivati PdfSource/DocxSource/XlsxSource DIREKTNO (konkretne
    klase), NE preko tog porta. Ne "popravljati" ovo u ovom tasku
    (van allowed_paths, van scope-a) -- samo dokumentovano da
    implementer ne gubi vrijeme tražeći adapter koji ne postoji.

G2  IngestionRepositoryPort (SqliteIngestionRepository) -- svih 19
    metoda, uključujući lease queue:
    register_crawl_targets(targets) -> int (idempotentno,
        ON CONFLICT DO NOTHING na (run_id, normalized_url))
    claim_next_crawl_target(run_id, lease_duration_seconds)
        -> CrawlTarget | None (ATOMSKI, BEGIN IMMEDIATE, lease_until
        računat NAKON sticanja write locka -- ACS-S2-002 BF-1 lekcija)
    update_crawl_target_state(target_id, state, *, last_error=None)
        -- NEMA snapshot_id parametra (G2 nije imao razlog da ga doda;
        G6 mora sam pratiti koji snapshot ide uz koji target, npr.
        preko svog internog mapping-a ili čitanjem `SourceSnapshot.url
        == crawl_target.normalized_url` -- DOKUMENTOVATI odabrani
        pristup u evidence-u)
    recover_expired_leases(run_id) -> int
    save_source_snapshot/save_source_chunk/save_fact_candidate/
        save_ingestion_run/save_ingestion_checkpoint (svi ON CONFLICT
        DO UPDATE upsert)
    list_source_snapshots_by_run(run_id) -- radi preko
        crawl_targets.snapshot_id FK (ACS-S2-002 cross-run-leak fix)
```

# §1 — CLASSIFY faza nema adapter (gap, ispunjava se OVDJE)

`UrlClassifierPort` (S2-G1, `ports/web_ingestion.py`) NEMA nijednu
implementaciju u `src/` (nezavisno potvrđeno grep-om prije pisanja
ovog kontrakta). Nijedan G3/G4/G5/G9 gate ga nije eksplicitno dobio u
scope — kanonski plan §8 kaže samo "Pripada S2-G3/S2-G4", nedovoljno
precizno, pa je propušten.

**Ovaj task ispunjava taj gap** (isti obrazac kao ACS-S2-002 koje je
dobilo `CrawlTarget` lease-queue metode koje S2-G1 nije definisao —
mali, dobro-definisan prerequisite unutar većeg gate-a, ne zaseban
task, jer je CLASSIFY doslovno G6-ova faza po DAG-u).

`infrastructure/web_ingestion/url_classifier.py` (nov fajl,
`allowed_paths` iznad):

```python
class UrlClassifier:
    """Deterministic URL-signal classification (canonical plan §8).

    URL-ONLY signals (path segments, query-free basename) -- CLASSIFY
    happens BEFORE FETCH in the pipeline (canonical plan §10 S2-G6), so
    content signals (title/H1/breadcrumb/schema.org) are NOT available
    here; those belong to a future content-signal refinement pass, NOT
    this port (UrlClassifierPort docstring, S2-G1).
    """

    def classify(self, url: str) -> PageType: ...
```

Implementacija: path-segment pattern matching (npr. `/about`,
`/o-nama` → `ABOUT`; `/contact`, `/kontakt` → `CONTACT`;
`/blog/`, `/vijesti/`, `/news/` → `BLOG`; `/proizvod`, `/product`,
`/shop/`, `/prodavnica` → `PRODUCT`; itd. — implementer bira tačan
pattern-set, mora pokriti BAR EN i BHS_LATIN varijante URL segmenata
jer je ovo isti trg kao BHS lokalizacija cijelog projekta). Root
path (`/`) → `HOME`. Nepoznat → `OTHER`. NIKAD LLM poziv (§8 princip,
non-negotiable). Unit testovi sa realnim URL uzorcima (koristiti isti
6-sajtova Q12 spike korpus iz G4 ako pomaže kalibraciji pattern-a —
`spikes/extraction-benchmark/`).

# Objective — orkestracija

## 1. `IngestBrandSources` use-case (`application/ingestion/ingest_brand_sources.py`)

Job-backed preko `JobManager.submit(job_type, func)` gdje `func`
prihvata `token: CancellationToken` parametar (JobManager ga
automatski injektuje ako potpis ima `token` argument — pogledati
`jobs/manager.py::_accepts_token` prije pisanja, NE pretpostaviti).

**Faze** (svaka faza: rad → `token.raise_if_cancelled()` → upiši
`IngestionCheckpoint` → `job_manager.update_progress(job_id, current,
total, phase=IngestionPhase.X.value)` — checkpoint SE UPISUJE POSLIJE
svake faze, "honest cancellation" princip: ako se cancel desi USRED
faze, ta faza se NE broji kao završena, posljednji upisani checkpoint
ostaje ono što je STVARNO završeno):

1. **DISCOVER**: `DomainDiscovery.discover(start_url)` +
   `SitemapReader`/`RobotsReader.sitemaps()` → skup kandidat URL-ova.
   `normalize_url()` na svaki. `register_crawl_targets()` (idempotentno
   — safe za restart/recrawl, `ON CONFLICT DO NOTHING`).
2. **CLASSIFY**: `UrlClassifier.classify(url)` po URL-u (§1 gore) →
   `page_type_hint` na `CrawlTarget` (NAPOMENA: `register_crawl_targets`
   iz G2 prima `CrawlTarget` objekte već sa `page_type_hint` popunjenim
   — CLASSIFY se logički može spojiti u DISCOVER korak PRIJE
   `register_crawl_targets` poziva, budući da G2 nema odvojenu
   "update classify" metodu; DOKUMENTOVATI ovu kombinaciju u evidence-u,
   NIJE odstupanje od plana, samo implementaciona posljedica postojeće
   G2 API površine).
3. **FETCH**: petlja `claim_next_crawl_target(run_id, lease_duration)`
   dok ne vrati `None` (queue prazan). Za svaki claimovan target:
   `CrawlBudget.can_crawl(domain)` provjera + `wait_politeness(domain)`
   PRIJE fetch-a, `HttpFetcher.fetch(url)`, `record_fetch(domain)`
   poslije. Uspješan fetch → `save_source_snapshot()` (SourceSnapshot
   sa `content_hash` — implementer bira hash algoritam, dokumentovati),
   → `update_crawl_target_state(target_id, FETCHED)`. Neuspješan
   (transport error) → `update_crawl_target_state(target_id,
   FAILED_RETRYABLE, last_error=...)` (NE `FAILED` odmah — retry
   accounting, `attempts` polje, implementer dizajnira threshold prije
   trajnog `FAILED`). SSRF-rejected (HttpFetcher interno vraća
   `FetchResult.error` sa `"unsafe:"` prefiksom) → `SKIPPED_UNSAFE`
   terminal, NE retryable.
4. **RENDER**: **NO-OP u v1** — Playwright fallback je S2-G8 (opcioni,
   ne postoji još). Content-only HTTP fetch je "Default = HTTP-first"
   (kanonski plan §10 S2-G8) — G6 v1 preskače ovu fazu potpuno (samo
   upiše `IngestionCheckpoint(phase=RENDER)` odmah nakon FETCH da
   state-mašina ostane kompletna za kasniji S2-G8 dodatak, BEZ
   stvarnog browser poziva).
5. **EXTRACT**: za svaki `FETCHED` snapshot: ako je HTML
   (`content_type` sadrži `text/html`) →
   `MainContentExtractor.extract(html)` → `BoilerplateFilter` →
   `Deduplicator` (implementer MORA pročitati stvarne G4 metod-signature
   prije koda, kontrakt ih namjerno ne izmišlja). Rezultat → materijalizovati
   `SourceChunk` entitete (dodijeliti `id`/`snapshot_id` OVDJE — S2-G1
   port docstring eksplicitno kaže da je ovo G6-ov posao) →
   `save_source_chunk()`. AKO je dokument (PDF/DOCX/XLSX, detektovano
   preko file extension/content-type iz discovery faze ILI
   Content-Type header-a) → `PdfSource`/`DocxSource`/`XlsxSource`.extract(
   path, run_id, snapshot_id) DIREKTNO (§ konteksta napomena) — VEĆ
   vraća gotove `SourceChunk`-ove, samo `save_source_chunk()` svaki.
   Visual identity: `VisualIdentityAdapter.extract(html, base_url)` po
   HOME/ABOUT stranicama (implementer bira koje stranice — nema smisla
   pozivati na SVAKOJ stranici, HOME je minimum) — rezultat NIJE
   `SourceChunk`, nego `VisualIdentity` VO; ČUVANJE tog VO nije G6 posao
   u v1 (nema `save_visual_identity` na `IngestionRepositoryPort` —
   ako treba, to je follow-up task koji dodaje port metodu, VAN scope-a
   OVOG kontrakta — DOKUMENTOVATI kao OUT_OF_SCOPE_FINDING, ne
   improvizovati novu port metodu bez kontrakta). `update_crawl_target_state(
   target_id, EXTRACTED)`.
6. **BUILD_FACTS**: **DETERMINISTIČKI u v1, NEMA LLM** (koordinatorova
   odluka — vidi §2 ispod). Svaki preživjeli, ne-prazan `SourceChunk`
   → JEDAN `FactCandidate(snapshot_id=chunk.snapshot_id,
   chunk_id=chunk.id, content=chunk.text, status=PROPOSED)` →
   `save_fact_candidate()`. `update_crawl_target_state(target_id, DONE)`.
7. **DONE**: `save_ingestion_run(run.status=SUCCEEDED,
   finished_at=..., stats=IngestionRunStats(...))` sa finalnim
   brojevima.

## 2. BUILD_FACTS je deterministički, NE LLM (odluka, koordinator, 2026-09-10)

Kanonski plan §2 pominje "budući LLM candidate builder unutar S2-G6"
kao MOGUĆNOST, ne obavezu — i eksplicitno zahtijeva da TAJ builder bude
tool-less + evidence-validiran (indirect prompt injection odbrana) ako
se ikad implementira. Za v1 G6, koordinator odlučuje: **BEZ LLM-a**.

Razlozi:
1. Svaki `SourceChunk` → 1:1 `FactCandidate` je jednostavno, testabilno,
   nula nove AI-provider površine (nijedan novi `AIRequest.purpose`,
   nula prompt injection rizika jer nema LLM-a koji čita website
   sadržaj u ovoj fazi).
2. G-WI-FACT-FIRST hard gate (kanonski plan §11) traži samo da
   "Website → FactCandidate → Human Review → ApprovedFact, NEMA
   alternativnog automatskog puta" — deterministički 1:1 mapping
   ISPUNJAVA ovo bez ikakvog LLM-a.
3. Smarter LLM-bazirani candidate builder (grupisanje više chunk-ova u
   jedan semantički fact, deduplikacija preko sličnog značenja, itd.)
   je STVARNA buduća poboljšica, ali ZASEBAN task sa svojim tool-less
   dizajnom — ne miješati u već veliki HIGH-risk G6 scope.

Implementer NE SMIJE dodati LLM poziv u ovaj task bez eskalacije
koordinatoru.

# §3 — Cooperative cancellation i checkpoint recovery (glavni review fokus)

- **Startup recovery**: PRIJE pokretanja FETCH petlje (ili na startu
  `IngestBrandSources.execute()` za resume slučaj), pozvati
  `recover_expired_leases(run_id)` — vraća `LEASED` sa isteklim
  `lease_until` nazad na `PENDING` (§7 kanonskog plana, G-WI-RECOVER
  hard gate). Ovo MORA biti testirano: simulacija "proces ubijen usred
  FETCH-a" (target ostaje `LEASED` sa isteklim lease-om u bazi) →
  novi `IngestBrandSources` poziv na ISTI `run_id` → target se vraća u
  petlju, NULA duplog rada (provjeriti da `save_source_snapshot` upsert
  ponašanje sprječava duplikat ako je fetch već jednom uspio prije
  kill-a — edge case: target je bio `FETCHED` ALI checkpoint nije
  stigao da se upiše prije kill-a → mora se ponovo obraditi ISPRAVNO,
  ne duplo brojati u `IngestionRunStats`).
- **`token.raise_if_cancelled()`** poziva se BAR jednom po iteraciji
  FETCH petlje (ne samo jednom na početku cijelog use-case-a — inače
  cancel ne bi imao efekta dok se cijeli queue ne isprazni). Isti
  princip za EXTRACT/BUILD_FACTS petlje.
- **`JobManager.update_progress`** pozvati sa smislenim `current/total`
  (npr. broj obrađenih crawl_targets / ukupan broj) i `phase=` — ovo
  je već postojeći GUI-facing mehanizam (koristi ga
  `generate_campaign_content`, ACS-F1-047 referenca), G6 MORA slijediti
  isti obrazac, ne izmišljati novi.
- **F1-047/HOTFIX-001 lekcija** (pročitati
  `agent_reports/2026-09-01-ACS-HOTFIX-001-*.md` prije koda ako
  implementer nije upoznat): `JobManager` je već `RLock`-baziran i
  event-ordering-safe (CREATED prije STARTED garantovano) — G6 se NE
  treba brinuti o toj klasom grešaka UNUTAR `JobManager`-a samog, ALI
  MORA biti pažljiv na SVOJU vlastitu concurrency unutar
  `claim_next_crawl_target` petlje ako implementer odluči da FETCH fazu
  paralelizuje preko `ThreadPoolExecutor`-a (VIŠE claim-ova
  istovremeno) — ako se to radi, MORA imati isti stil concurrent-claim
  test kao ACS-S2-002 (2+ threads, `threading.Barrier`, potvrda nula
  duplog claim-a). **Sekvencijalni FETCH (jedan claim odjednom u
  worker thread-u) je JEDNOSTAVNIJI i DOVOLJAN za v1** — paralelizacija
  petlje je OPCIONA optimizacija koju implementer NE MORA raditi;
  ako je izbjegne, ovaj concurrency test nije potreban (dokumentovati
  odluku).

# Acceptance

- [ ] `url_classifier.py`: deterministički, URL-only, nikad LLM, pokriva
      EN + BHS_LATIN URL segmente, unit testovi sa realnim uzorcima.
- [ ] `IngestBrandSources.execute(brand_id, source_scope, ...)
      -> IngestionRun` (ili slično — implementer finalizuje potpis),
      job-backed preko `JobManager.submit`.
- [ ] Sve faze checkpoint-uju NAKON završetka (ne prije), "honest
      cancellation" dokazano testom (cancel usred FETCH petlje → resume
      → tačno onoliko rada koliko NIJE bilo završeno prije cancel-a,
      NIJE duplo, NIJE izgubljeno).
- [ ] **G-WI-RECOVER dokazano**: kill/prekid usred crawl-a (simulacija
      — LEASED target sa isteklim lease-om u bazi) → resume →
      `recover_expired_leases` ga vraća u petlju → nula duplog/izgubljenog
      rada. NAJVAŽNIJI test u ovom tasku.
- [ ] **G-WI-EVIDENCE dokazano**: svaki `FactCandidate` traceable do
      `SourceSnapshot` (kroz `snapshot_id`, provjereno u integration
      testu, ne samo tip-nivo kao u S2-G1).
- [ ] SSRF-rejected URL nikad ne dobija `SourceSnapshot` (HttpFetcher
      već blokira, G6 samo mora ispravno mapirati `FetchResult.error`
      na `SKIPPED_UNSAFE` state, ne pokušavati "fix-ovati" SSRF logiku
      ovdje — VAN `allowed_paths`).
- [ ] BUILD_FACTS je 100% deterministički, NULA LLM poziva (grep
      dokaz — `AIRequest`/`TextGenerationPort` se NIGDJE ne pojavljuje
      u `application/ingestion/`).
- [ ] Cooperative cancellation: `token.raise_if_cancelled()` provjeren
      unutar SVAKE petlje faze (ne samo jednom).
- [ ] Integration test: pun DISCOVER→DONE tok na realnom malom
      fixture-sajtu (`tmp_path` HTTP server ili slično — isti stil kao
      G3/G9 testova, provjeriti postojeći obrazac prije izmišljanja
      novog), sa STVARNIM `SourceSnapshot`/`SourceChunk`/`FactCandidate`
      brojevima na kraju (ne samo "ne baca grešku").
- [ ] `python -m pytest -q` (DeepSeek unset) pun suite prolazi, 0
      regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths` — POSEBNO nula izmjena u
      `http_fetcher.py`/`url_safety_policy.py` (SSRF logika je VEĆ
      pregledana i sigurna, G6 je SAMO caller).
- [ ] GitNexus pre-change context + `detect_changes` evidence.
- [ ] **CI provjeren preko PR-a.**

# Implementation steps

1. Pročitati SVE konkretne G2-G5/G9 module navedene u Kontekstu iznad
   (fajl-po-fajl, ne oslanjati se na ovaj kontrakt kao source of truth
   za tačne signature — potvrditi grep-om, API se mogao promijeniti
   od pisanja ovog kontrakta).
2. Pročitati `jobs/manager.py` i `jobs/cancellation.py` u cjelini.
3. Pročitati `agent_reports/2026-09-01-ACS-HOTFIX-001-*.md` (RLock
   lekcija) i bar jedan postojeći `JobManager`-baziran use-case
   (`generate_campaign_content` ili slično) kao stil-referenca.
4. Implementirati `url_classifier.py` (§1) prvo, izolovano, sa
   testovima.
5. Implementirati `IngestBrandSources` fazu-po-fazu, testirajući svaku
   izolovano prije nego se spoje u pun tok.
6. Implementirati G-WI-RECOVER test PRIJE nego se task smatra gotovim
   — ovo je najvažniji test, ne ostavljati za kraj.
7. GitNexus `detect_changes` prije commit-a.

# Review focus — Claude PRVO, PA Codex (HIGH, pun ciklus)

- **G-WI-RECOVER test je stvaran, ne kozmetički** — mora simulirati
  STVARAN kill (ne samo pozvati `recover_expired_leases` direktno bez
  konteksta), pa dokazati da resume ispravno nastavlja.
- **Checkpoint-poslije-faze, ne prije** — pažljivo pročitati redoslijed
  operacija u svakoj fazi.
- **Nula LLM poziva u BUILD_FACTS** (grep dokaz).
- **`claim_next_crawl_target` korišten ISPRAVNO** — jedan claim po
  worker-u u petlji, ne re-implementirati atomicity logiku iznova
  (već postoji u G2, G6 je samo caller).
- **SSRF granica poštovana** — G6 nikad ne zaobilazi `HttpFetcher`
  da bi sam radio HTTP pozive.

**Codex adversarial fokus**: cancel-usred-faze race conditions
(pokušati smisliti scenario gdje checkpoint i cancel race-uju na način
koji bi kontraktov "honest cancellation" test propustio), kill-usred-
FETCH-a sa DJELOMIČNO upisanim `SourceSnapshot` (fetch uspio, ali
crash prije `update_crawl_target_state(FETCHED)` — da li resume
ispravno detektuje da je snapshot već tu i ne duplira ga, ili barem ne
kvari statistiku).

# Rollback

HIGH risk (concurrency/lifecycle, F1-047 klasa) — PUN ciklus: Claude
review → Codex adversarial review → Human Owner eksplicitno odobrenje
PRIJE merge-a.

# Coordination

Zadnji blokirajući gate za S2-G7a (Approve/Reject FactCandidate).
Nema poznatih nezavisnih paralelnih kandidata trenutno otvorenih —
provjeriti `allowed_paths` presjek prije bilo kog paralelnog rada
(workflow §10).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-S2-014-ingestion-pipeline
Branch:   task/ACS-S2-014-ingestion-pipeline
Base:     main @ 0672df7
```
