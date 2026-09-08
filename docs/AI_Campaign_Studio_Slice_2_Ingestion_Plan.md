# AI Campaign Studio — Slice 2 (Brand/Website Ingestion) — podjela na gate-ove

- **Status:** predlog za Human Owner — nije još aktivan implementation scope; po potvrđivanju koordinator pretvara gate-ove u Task Contract-e.
- **Datum:** 2026-09-08
- **Arhitektonska osnova:** `AI_Campaign_Studio_Faza_0_6_Channel_Model_LLM_Registry.md` §56 (Website Ingestion) + §19/§20 (Vertical Slice 2/3), `AI_Campaign_Studio_Faza_1_v1_5_Analytics_Ready_Implementation_Plan.md` §24
- **Namjera:** ne arhivirati cijeli website, nego izvući marketinški korisne informacije u kontrolisanom pipeline-u sa provenance-om i human-review tačkom.

---

# 1. Kontekst i cilj

Slice 2 zamjenjuje `Fixture Loader` sa `Brand Ingestion + Human Review`, **bez** promjene Campaign Engine-a. Inputi: website + PDF/DOCX/XLSX + ručne napomene → `SourceSnapshot`/`SourceChunk` → `FactCandidate` → Human Review → `ApprovedFact`/`BrandSnapshot`.

Ako Website Ingestion kasnije zahtijeva refaktor Campaign Engine-a, granica iz Faze 1 nije dobro napravljena (Faza 1 v1.4 §82).

---

# 2. DAG

```
S2-G1  Brand Ingestion Domain + Ports (contracts only)
        ↓
S2-G2  Ingestion Persistence (migracija 0009)
        ↓
  ┌──────────┬──────────┬──────────┬──────────┐
  ↓          ↓          ↓          ↓          ↓
S2-G3      S2-G4      S2-G5      S2-G9      (paralelno, disjunktni)
Fetch/     Content    Visual     Documents
Discovery  Extract    Extract    (PDF/DOCX/XLSX)
  └──────────┴──────────┴──────────┴──────────┘
        ↓
S2-G6  Ingestion Pipeline use-case + JobManager + checkpoint
        ↓
S2-G7a Approve/Reject FactCandidate use-case (provenance invariant)
        ↓
S2-G7b Brand Intelligence Review UI (bridge + ekran)
        ↓
S2-G8  Playwright fallback (SPIKE + gate, opcioni, tek nakon HTTP-only dokaza)
```

---

# 3. Zaključane granice (Human Owner potvrdio 2026-09-08)

- **D-G1:** `FactCandidate` + `FactStatus.PROPOSED` žive u `domain/facts/`; provenance objekti (`SourceSnapshot`/`SourceChunk`/`IngestionRun`/`IngestionCheckpoint`) u `domain/ingestion/`. Candidate je facts koncept (nepotvrđena činjenica), ne ingestion artefakt.
- **D-G2:** G1 definiše **sve portove** kao contracte. Adapter gate-ovi (G3/G4/G5/G9) diraju **samo svoje** `infrastructure/` fajlove — time su `allowed_paths` potpuno disjunktni (pravilo §10).
- **D-G3:** G7 je razdvojen na G7a (application approve use-case, MEDIUM) i G7b (bridge + ekran + Node/VM test, HIGH).
- **D-G4:** G1 je MEDIUM (aditivno: novi paket, novi članovi enuma, novi ID tipovi; nema migracije ni postojećih podataka). G2 je HIGH (migracija je uvijek HIGH, workflow §6).
- **D-G5:** G1 može krenuti odmah, paralelno sa završetkom Slice 1.5 (F1-051 / P1.5-G7/G8) — `allowed_paths` su disjunktni od `presentation_webview/`.

---

# 4. Nalazi istraživanja koji oblikuju podjelu

1. **Donor `WebshopAudit` NE postoji na disku** — Faza 0.6 D36/D37 kažu "adaptirati donor kod", ali projekat nije dostupan. Fetch/sitemap/parser piše se **svježe iza portova**. D36/D37 treba ispraviti ili eksplicitno zabilježiti u G3 kontraktu.
2. **Provenance seam već postoji** — `SourceReference` (`domain/facts/entities.py`) već ima `snapshot_id`/`chunk_id` polja (neiskorištena). Slice 2 ih aktivira; eventualno dodati `page_title`/`retrieved_at`.
3. **`FactStatus` već rezerviše `PROPOSED`** — komentar u `domain/facts/enums.py`: *"Slice 1 has no PROPOSED status — that arrives with the Slice 2 FactCandidate workflow."*
4. **`VisualIdentity` VO postoji** — `logo_path`/`primary_colors`/`secondary_colors`/`font_families`/`image_style_notes` su tačan output za visual extraction.
5. **`JobState` spreman za checkpoint** — `progress_current`/`progress_total`/`phase`/`message` već postoje.
6. **Migracije su na `0008`** — sledeća je `0009_ingestion_foundation.sql`.

---

# 5. Gate-ovi

## S2-G1 — Brand Ingestion Domain + Ports (contracts only)

**Scope:**
- `domain/ingestion/` — `SourceSnapshot` (immutable, v1/v2, `snapshot_id` + `retrieved_at` + `content_hash`), `SourceChunk`, `IngestionRun`, `IngestionCheckpoint`, `StructuredDataRecord` (JSON-LD sirovi zapis).
- `domain/facts/` — `FactCandidate` + `FactStatus.PROPOSED`.
- `domain/common/ids.py` — novi ID tipovi (`SourceSnapshotId`, `SourceChunkId`, `FactCandidateId`, `IngestionRunId`).
- `ports/web_ingestion.py` — `HttpFetcherPort`, `SitemapReaderPort`, `UrlClassifierPort`, `MainContentExtractorPort`, `VisualIdentityExtractorPort`, `DocumentExtractorPort`.
- `ports/repositories.py` — `IngestionRepositoryPort`.

**Risk:** MEDIUM
**allowed_paths:** `domain/ingestion/`, `domain/facts/`, `domain/common/ids.py`, `ports/web_ingestion.py`, `ports/repositories.py`
**forbidden:** `infrastructure/`, `application/`, `presentation_webview/`, `jobs/`
**Acceptance:**
- svi entiteti frozen; `SourceSnapshot` se nikad ne mutira (nova verzija = nov objekat).
- `FactCandidate.status` životni ciklus `PROPOSED → APPROVED → REJECTED`.
- provenance obavezan na svakom chunk/candidate-u.
- portovi su Protocol-only, bez infrastrukture import-a.

---

## S2-G2 — Ingestion Persistence

**Scope:** migracija `0009_ingestion_foundation.sql` (`source_snapshots`, `source_chunks`, `fact_candidates`, `structured_data_records`, `ingestion_runs`, `ingestion_checkpoints`) + `infrastructure/database/repositories/sqlite_ingestion_repository.py`.

**Risk:** HIGH (migracija — uvijek HIGH po §6/§29)
**allowed_paths:** `resources/migrations/`, `infrastructure/database/migrations.py`, `infrastructure/database/repositories/sqlite_ingestion_repository.py`, `ports/repositories.py`
**forbidden:** sve ostalo
**Acceptance:** aditivna migracija (ne dira postojeće tabele), idempotentan runner, repo contract testi, bez `ON DELETE CASCADE` (postojeća konvencija).

---

## S2-G3 — HTTP Fetch + Discovery (paralelan)

**Scope:** `infrastructure/web_ingestion/` — `robots_reader`, `sitemap_reader`, `domain_discovery`, `link_discovery`, `url_normalizer`, `url_classifier`, `crawl_budget`, `http_fetcher`.

**Risk:** MEDIUM
**allowed_paths:** `infrastructure/web_ingestion/` (samo fetch/discovery fajlovi)
**forbidden:** `domain/`, `application/`, `presentation_webview/`, `jobs/`, `ports/`
**Ključna odluka (Q11):** URL ranking = determinističke path-segment heuristike (HIGH/MEDIUM/LOW/IGNORE lista iz Faza 0.6); klasifikator/LLM tek ako heuristika ne bude dovoljna. Default: `same_domain_only: true`, `max_pages: 20`, `max_depth: 2`.
**Acceptance:** robots.txt/sitemap parsing na fixture HTML-ima; crawl budget strogo ograničava broj fetch-eva; URL dedup po canonical formi.

---

## S2-G4 — Content Extraction + Boilerplate (paralelan)

**Scope:** `infrastructure/web_ingestion/` — `main_content_extractor`, `boilerplate_filter`, `deduplicator`.

**Risk:** MEDIUM
**allowed_paths:** `infrastructure/web_ingestion/` (samo extraction fajlovi)
**forbidden:** `domain/`, `application/`, `presentation_webview/`, `jobs/`, `ports/`
**Ključna odluka (Q12):** **ne pisati boilerplate ručno.** `trafilatura` (primarni) + `readability-lxml` (alternativa), oba iza porta. Custom heuristika tek kao treći sloj ako se dokaže da ne pokrivaju tipične BHS sajtove (spike na 3–5 stvarnih sajtova).
**Acceptance:** na fixture HTML-ovima izlaz sadrži samo glavni sadržaj (bez nav/footer/cookie/CTA); cross-page dedup po normalized hashu + fuzzy similarity.

---

## S2-G5 — Visual Identity Extraction (paralelan)

**Scope:** `infrastructure/web_ingestion/` — `asset_extractor`, `visual_identity_extractor`. Output u postojeći `VisualIdentity` VO.

**Risk:** MEDIUM
**allowed_paths:** `infrastructure/web_ingestion/` (samo visual fajlovi)
**forbidden:** `domain/`, `application/`, `presentation_webview/`, `jobs/`, `ports/`
**Ključna odluka:** jeftini signali — CSS custom properties (`--primary`/`--accent`), `font-family`, favicon, OpenGraph image, logo kandidati. **Ne** raditi tešku image analizu (kasniji slice).
**Acceptance:** iz fixture HTML-a izvlači boje/fontove/logo; neizvučeno → `VisualIdentity` sa `None`/praznim, nikad crash.

---

## S2-G9 — Documents (PDF/DOCX/XLSX) (paralelan)

**Scope:** `infrastructure/document_ingestion/` — `pdf_extractor` (PyMuPDF), `docx_extractor` (python-docx), `xlsx_extractor` (openpyxl). Output: isti `SourceChunk`/`FactCandidate` model kao web (jedan provenance lanac).

**Risk:** MEDIUM
**allowed_paths:** `infrastructure/document_ingestion/`
**forbidden:** `domain/`, `application/`, `presentation_webview/`, `jobs/`, `ports/`
**Acceptance:** PDF/DOCX/XLSX → chunk-ovi sa provenance (`source_type="pdf"` itd.); D23 — **nema OCR-a**.

---

## S2-G6 — Ingestion Pipeline use-case + JobManager + Checkpoint

**Scope:** `application/ingestion/ingest_brand_sources.py` — orkestrira 22 koraka (Faza 0.6 §56), job-backed preko postojećeg `JobManager`-a, sa `IngestionCheckpoint` save/resume i cooperative cancellation.

**Risk:** HIGH (concurrency/lifecycle, JobManager — klasa grešaka iz F1-047)
**zavisi od:** G2, G3, G4, G5, G9
**allowed_paths:** `application/ingestion/`, `jobs/`, `domain/ingestion/`, `ports/`
**forbidden:** `presentation_webview/`
**Ključne odluke:** checkpoint se čuva **poslije svake faze** (resume ne ponavlja fetch); reentrancy guard isti obrazac kao F1-047 (`try/finally`, jedan terminal-state call-site); `JobState.progress_total` = broj selektovanih stranica.
**Acceptance:** full run → found/analyzed/skipped outcome; cancel mid-run → checkpoint sačuvan, resume nastavlja bez duplog fetch-a; 2 konkurentna ingestion joba za različite brendove ne dijele stanje.

---

## S2-G7a — Approve/Reject FactCandidate use-case

**Scope:** `application/ingestion/approve_fact_candidates.py` — approval pravi novi `ApprovedFact` (preko postojećeg APPROVED obrasca), nikad ne mutira candidate; reject označava candidate.

**Risk:** MEDIUM (provenance invariant)
**zavisi od:** G6
**allowed_paths:** `application/ingestion/`, `domain/facts/`, `domain/ingestion/`, `ports/repositories.py`
**forbidden:** `presentation_webview/`
**Acceptance:** idempotentan approve/reject; snapshot ostaje vezan za tačnu verziju; approved fact nosi `SourceReference` sa `snapshot_id`/`chunk_id`.

---

## S2-G7b — Brand Intelligence Review UI

**Scope:** read-path ekran u `presentation_webview/screens/brend/` (proširenje postojećeg Brend ekrana) + `bridge/__init__.py` read/write metode (`get_ingestion_review`, `approve_fact_candidate`, `reject_fact_candidate`, `assemble_brand_snapshot`).

**Risk:** HIGH (GUI lifecycle + human-in-loop)
**zavisi od:** G7a
**allowed_paths:** `presentation_webview/screens/brend/`, `bridge/__init__.py`
**forbidden:** `domain/`, `application/`, `ports/`, `infrastructure/`
**Ključna odluka:** izvršni Node/VM test OD PRVE VERZIJE (F1-046/049/051 obrazac), ne string-assertion.
**Acceptance:** transparentan prikaz (ne "Brand Brain") — koliko stranica, koliko činjenica, svaka sa source linkom; pywebview lifecycle exactly-once test; approve/reject idempotentan.

---

## S2-G8 — Playwright fallback (SPIKE + gate, opcioni)

**Scope:** `infrastructure/web_ingestion/playwright_worker.py`, `js_render_detector.py` — subprocess-bazirani persistent worker, aktivira se samo kad HTTP-fetch vrati JS-heavy stranicu.

**Risk:** HIGH (browser worker, packaging, Windows)
**Ključna odluka (Q4):** spike prije zaključavanja — **subprocess**, ne thread (thread+Chromium je već dokazano rizičan; isti razlog kao F1-052 pytest izolacija). Default = HTTP-first.
**Acceptance:** neaktiviran ako HTTP daje sadržaj; radi na JS-heavy sajtu; timeout, ne visi vječno.

---

# 6. Paralelizacija

- G3/G4/G5/G9 su **4 paralelna MEDIUM taska** (potpuno disjunktni `allowed_paths` — svaki dira samo svoje `infrastructure/` fajlove; portovi su definisani unaprijed u G1). Svi zavise samo od G1.
- G6 je HIGH (pun ciklus: Claude + Codex + Human Owner), čeka G2+G3+G4+G5+G9.
- G7a (MEDIUM) → G7b (HIGH) sekvencijalno.
- G8 opcioni, ne blokira ništa.

---

# 7. Otvorena pitanja za spike (ne blokiraju početak)

1. **Q12** — trafilatura vs readability-lxml na 3–5 stvarnih BHS sajtova (spike unutar G4).
2. **Q4** — Playwright subprocess dokaz (spike unutar G8).
3. **D36/D37** — donor `WebshopAudit` ne postoji; ažurirati Faza 0.6 ili zabilježiti u G3 kontraktu.

---

# 8. Preporučeni redoslijed u odnosu na Slice 1.5

G1 je disjunktan od `presentation_webview/` pa može krenuti paralelno sa F1-051 (Početna) i P1.5-G7/G8 (Performance UI). Preporučeno: G1 odmah u prazan slot, ostatak Slice 2 tek kad Slice 1.5 bude zatvoren i Human Owner potvrdi ovaj plan.
