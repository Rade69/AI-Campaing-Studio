---
task_id: ACS-GUI-011
title: "Brend GUI — unos URL-a pokreće IngestBrandSources (bridge + ekran)"
coordinator: claude
implementer: claude
reviewers: [claude (self-verify, HttpFetcher+DomainDiscovery+extraction live test already proven ranije u sesiji)]
status: "OPEN — contract pisan prije koda, na eksplicitan zahtjev korisnika ('Želim da sve napraviš kako bi i ja to mogao da testiram')"
created_at: 2026-09-11
risk: MEDIUM
gitnexus_required: false
adversarial_required: false
---

# Kontekst

Prethodna nezavisna provjera (ova sesija) je pokazala:
- `IngestBrandSources` (G6) sa PRAVOM infrastrukturom (HttpFetcher,
  DomainDiscovery, UrlClassifier, MainContentExtractor,
  BoilerplateFilter, Deduplicator, VisualIdentityAdapter) STVARNO radi
  end-to-end na živom URL-u (`https://example.com/` → 2 fetched, 6
  extracted, 6 candidates) — motor je potvrđeno ispravan.
- Ali `presentation_webview` GUI (pywebview + WebView2, stvarna desktop
  aplikacija) NEMA polje za unos URL-a. Brend ekran ima placeholder
  string "Kasnije: pokreni ingestion/review tok." `CampaignBridgeApi`
  ima metode za PREGLED/ODOBRAVANJE već-ingestovanih kandidata
  (`get_ingestion_review`, `approve_fact_candidate`,
  `reject_fact_candidate`), ali nijednu koja prima URL i pokreće
  ingestion. `IngestBrandSources` ima nula pozivalaca u produkcijskom
  kodu.

Korisnik traži da se ovo ožiči da MOŽE SAM testirati kroz pravu
aplikaciju, ne samo kroz moju skriptu.

# Cilj

Dodati minimalan, funkcionalan put: korisnik unese jedan ili više URL-a
na Brend ekranu, GUI pokrene `IngestBrandSources` kao pozadinski posao
(JobManager, isti obrazac kao `generate_campaign_content`), prikaže
progress, i po završetku prikaže rezultat (broj fetched/extracted/
candidates) — koristeći VEĆ POSTOJEĆI `get_ingestion_review` za prikaz
samih kandidata (ne dupliciati tu logiku).

# Scope (allowed_paths)

```yaml
allowed_paths:
  - src/ai_campaign_studio/presentation_webview/bridge/__init__.py       # nova metoda + wiring
  - src/ai_campaign_studio/presentation/ui_models.py                    # novi UI model (StartIngestionResultUiModel)
  - src/ai_campaign_studio/presentation_webview/screens/brend/__init__.py  # ukloniti placeholder, dodati URL input + dugme + status prikaz
  - src/ai_campaign_studio/presentation_webview/static/app.js           # JS handler: submit → poll job → prikaži rezultat
  - tests/unit/presentation_webview/bridge/test_start_brand_ingestion.py  # NOVI
  - agent_reports/ACS-GUI-011-task-contract.md
  - agent_reports/2026-09-11-ACS-GUI-011-claude.md                      # NOVI, evidence
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/ingestion/ingest_brand_sources.py  # NE DIRATI — već testiran i radi
  - src/ai_campaign_studio/infrastructure/web_ingestion/url_safety_policy.py  # NE DIRATI (G3 SSRF)
  - src/ai_campaign_studio/infrastructure/web_ingestion/http_fetcher.py      # NE DIRATI
  - src/ai_campaign_studio/subprocess_runtime/                              # G8, nepovezano
  - resources/migrations/                                                    # nema nove šeme
```

# Dizajn

## Bridge: `start_brand_ingestion(raw_payload: dict) -> dict`

- Payload: `{"brand_id": str | None, "urls": list[str]}`. `brand_id=None`
  → koristi `_ensure_brand()` isti obrazac kao `get_ingestion_review`.
- Validacija: `urls` mora biti neprazna lista nepraznih stringova. SSRF
  provjera se NE radi ovdje — `HttpFetcher`/`UrlSafetyPolicy` je već
  provjeren guard unutar `IngestBrandSources._fetch`, bridge mu ne
  duplira logiku.
- Posao ide na `JobManager` (isti obrazac kao `generate_campaign_content`
  §ACS-F1-047/ACS-GUI-008): sync dio samo validira i submituje,
  closure otvara SVOJ `_resource_scope()` na worker thread-u (SQLite
  connection se ne dijeli preko thread granice — HOTFIX-002 pravilo)
  i tamo gradi FRESH `IngestBrandSources` sa PRAVOM infrastrukturom
  (identično onome što je dokazano da radi u ovoj sesiji).
  `document_extractors={}` — namjerno prazno u v1 (PDF/DOCX/XLSX G9
  extractors nisu ožičeni ovdje, poznato ograničenje, follow-up).
- Vraća odmah `{ok, brand_id, job_id, error_code, error_message}` —
  JS poll-uje kroz VEĆ POSTOJEĆI `get_job_status(job_id)`.

## Brend ekran + app.js

- Zamijeniti placeholder tekst jednim `<input type="text">` (URL) +
  dugme "Pokreni ingestion" (BHS latinica).
- Klik → `pywebview.api.start_brand_ingestion({urls: [val]})` → poll
  `get_job_status` (isti poll pattern kao za `generate_campaign_content`
  u postojećem `app.js`, reuse-ovati tu funkciju ako je generička) →
  na `SUCCEEDED` pozvati `get_ingestion_review` i prikazati broj
  kandidata + link "Idi na pregled" (ako review UI već postoji na
  drugom ekranu) ili inline listu prvih par kandidata.

# Šta NE SMIJE (out of scope)

- Ne dirati `IngestBrandSources`, `HttpFetcher`, `UrlSafetyPolicy` —
  već testirano, radi.
- Ne graditi UI za brand-picker (koristi postojeći default/seed brand).
- Ne dodavati document_extractors (G9) u ovoj rundi.
- Ne dodavati multi-URL batch textarea UI polish — jedan URL po pokretanju
  je dovoljno za v1 (korisnik traži da MOŽE TESTIRATI, ne finalni UX).
- Ne mijenjati `get_ingestion_review`/`approve_fact_candidate`/
  `reject_fact_candidate` — koriste se as-is.

# Acceptance

1. Novi unit test `test_start_brand_ingestion.py`: validacija (prazan
   payload, prazna lista URL-ova → VALIDATION_ERROR), uspješan submit
   vraća `job_id`, `get_job_status(job_id)` na kraju pokazuje
   `SUCCEEDED` sa `fetched_pages > 0` (koristi lokalni HTTP test server
   iz `tests/integration/infrastructure/web_ingestion` obrasca, NE
   pravi internet — determinism u CI).
2. Ručna live provjera (ja, bez klikanja miša — direktan Python poziv
   `CampaignBridgeApi().start_brand_ingestion(...)` + polling) na
   PRAVOM URL-u (`https://example.com/`), potvrđuje isti rezultat kao
   ranija skripta.
3. `python -m ruff check`, `python -m mypy src`, ciljani pytest testovi
   PASS.
4. Korisnička instrukcija za ručno GUI testiranje (pokreni GUI, unesi
   URL, klikni dugme, vidi rezultat) — napisana u finalnom izvještaju.

# Rizik

MEDIUM: nova GUI→backend putanja, ali NE dira SSRF/security kod (samo
ga poziva, isto kao što G6 testovi već rade), NE dira domain/persistence
šemu, prati POSTOJEĆI, već-revidirani JobManager obrazac
(`generate_campaign_content`) 1:1. Nema potrebe za posebnom adversarial
rundom — glavni rizik (SSRF) je već zatvoren u G3/G8 fix rundama ranije
u ovoj sesiji.
