---
task_id: ACS-S2-011
phase: "S2-G4 â€” Content Extraction + Boilerplate"
title: "main_content_extractor + boilerplate_filter + deduplicator (Q12 spike: Trafilatura vs readability-lxml)"
coordinator: MiniMax (privremeno, Claude na pauzi)
implementer: opencode
reviewers: [claude, codex]
status: "OPEN -- contract written before code, Äeka implementera"
created_at: 2026-09-10
dependencies: [ACS-S2-001, ACS-S2-002, ACS-S2-009, ACS-S2-010]
risk: MEDIUM
allowed_paths:
  - src/ai_campaign_studio/infrastructure/extraction/
  - src/ai_campaign_studio/infrastructure/extraction/__init__.py
  - pyproject.toml
  - tests/unit/infrastructure/extraction/
  - tests/unit/infrastructure/extraction/__init__.py
  - tests/integration/extraction/
  - tests/integration/extraction/__init__.py
  - spikes/extraction-benchmark/  # privremeni benchmark za Q12 spike
forbidden_paths:
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/presentation_webview/
  - src/ai_campaign_studio/jobs/
  - src/ai_campaign_studio/infrastructure/web_ingestion/  # G3 scope, NE G4
  - src/ai_campaign_studio/infrastructure/visual_extraction/  # G5 scope, NE G4
  - src/ai_campaign_studio/infrastructure/database/
  - resources/migrations/
gitnexus_required: true
adversarial_required: false
---

# Kontekst

Å esti Slice 2 gate (S2-G1/G2/G9 merged, S2-G3 u toku, S2-G4 paralelan
sa G3/G5). Kanonski plan Â§10 "S2-G4 â€” Content Extraction + Boilerplate":
`main_content_extractor`, `boilerplate_filter`, `deduplicator`. **Q12
spike**: Trafilatura vs readability-lxml na 3-5 stvarnih BHS sajtova
**PRIJE** konaÄne odluke â€” ne pretpostaviti pobjednika.

**Plan Â§10 naglaÅ¡ava MEDIUM risk** (NE HIGH): nema nove migracije
(`structured_data_records` eksplicitno odloÅ¾ena u S2-002 contract Â§1
i ostaje follow-up zaseban task, NE G4).

Reference dokumenti (po `.agent/TASK_ROUTING.md` "Website Ingestion task"):
- [Kanonski plan `docs/AI_Campaign_Studio_Slice_2_Canonical_Plan.md`](../../docs/AI_Campaign_Studio_Slice_2_Canonical_Plan.md):
  Â§3 DAG, Â§5 sync/async (fiksirana, NE preispitivati), Â§6 SSRF (NE
  G4 scope, ALI koriste isti `requests` flow), Â§7 durability, **Q12
  spike** naziv, Â§10 S2-G4 specifikacija, Â§11 hard gates.
- `domain/ingestion/entities.py` (SourceSnapshot, SourceChunk) + `ports/
  repositories.py` (IngestionRepositoryPort, `register_source_chunk`).
- `.agent/GITNEXUS_PROTOCOL.md` (obavezan za MEDIUM).

# Å ta

Implementirati `infrastructure/extraction/` module (lokacija je
koordinatorska odluka â€” alternative: `content_extraction/`, G4-spec
kaÅ¾e "samo extraction fajlovi"):

1. **`main_content_extractor`** â€” prima HTML (ili markdown/tekst ako
   upstream pipeline veÄ‡ konvertuje), vraÄ‡a `str` sa main article
   text-om. **Q12 spike obavezan** PRIJE izbora biblioteke:
   - **Trafilatura** (Python wrapper, `pip install trafilatura`,
     koristi `lxml` ispod haube, dobra na vijesti/blogovima, F1
     score tipiÄno 0.85-0.95 na clean HTML)
   - **readability-lxml** (port Mozilla Readability, najÄeÅ¡Ä‡e
     koriÅ¡ten u web scraping ekosistemima, robustan na layout
     promjene)
   - **BENCHMARK na 3-5 BHS sajtova** (npr. klix.ba, nezavisne.com,
     bhtourism.ba, akta.ba, faktor.ba â€” NE nuÅ¾no, ALI trebaju
     realni bosansko-srpsko-hrvatski sajtovi sa raznolikom strukturom
     â€” vijesti, blog, tourism, ecommerce landing page)
   - **NE odluÄivati bez benchmarka** â€” Äak i ako Pi/OpenCode preferira
     jednu biblioteku, benchmark oba i odluÄi na osnovu mjerenja
   - Benchmark output: `spikes/extraction-benchmark/result.md` (NE u
     `infrastructure/extraction/` â€” spike folder je uvijek
     privremen, vidjeti `pyproject.toml` ruff exclude za `spikes/`)

2. **`boilerplate_filter`** â€” uklanja navigacione elemente, footere,
   aside, cookie banner, social-share widgete. ALI: `main_content_extractor`
   veÄ‡ radi dosta toga (Trafilatura ima `include_comments=False`,
   `include_tables=False`, `favor_precision=True`). Provjeriti da se
   NE duplira posao. Ako je boilerplate_filter zaseban korak,
   implementirati kao post-processing pass.

3. **`deduplicator`** â€” ulaz: `tuple[SourceChunk, ...]`. Izlaz:
   `tuple[SourceChunk, ...]` sa uklonjenim duplikatima. Definicija
   "duplikata" za acceptance:
   - **TaÄan tekst match** (case-normalized, whitespace-normalized):
     dva chunka sa istim tekstom â†’ zadrÅ¾i prvi, ukloni drugi.
   - **Heuristic near-duplicate** (opciono, ako se pokaÅ¾e korisno):
     Jaccard similarity > 0.9 na whitespace-tokeniziranim chunkovima.
     ALI: ovo zahtijeva threshold tuning â€” za S2-G4 je dovoljan taÄan
     match.
   - PonaÅ¡anje: input order je preservation order (deterministiÄki
     output za isti input).
   - Edge case: prazan input â†’ prazan output. Jedan chunk â†’ jedan
     chunk. Svi duplikati â†’ jedan chunk.

4. **`__init__.py` exports** â€” `MainContentExtractor`, `BoilerplateFilter`,
   `Deduplicator` klase (ili funkcije â€” koordinatorska odluka).

# Q12 Spike detalji

`spikes/extraction-benchmark/` (privremeni direktorij, **NE commit-ovan
u production** â€” vidjeti workflow pattern za spike vs production):

```text
spikes/extraction-benchmark/
â”œâ”€â”€ README.md             # Å¡ta testiramo, kako pokrenuti
â”œâ”€â”€ corpus/               # 3-5 stvarnih HTML fajlova (BHS sajtovi)
â”‚   â”œâ”€â”€ klix.ba-article.html
â”‚   â”œâ”€â”€ nezavisne.com-article.html
â”‚   â”œâ”€â”€ ...
â”œâ”€â”€ benchmark.py          # pokreÄ‡e oba library-ja, mjeri F1 / precision / recall
â”‚                           (sa ground truth manualno oznaÄenim main content-om)
â”œâ”€â”€ result.md             # output benchmarka: koja biblioteka pobjeÄ‘uje, zaÅ¡to
â””â”€â”€ chosen.md             # finalna odluka + obrazloÅ¾enje
```

**Ground truth pristup**: za svaki HTML fajl, ruÄno oznaÄiti "main
content" (kopija paste u `ground-truth/` subfolder, ili inline u
`benchmark.py`). Benchmark mjeri:
- **Precision**: koliko ekstrahiranog teksta je main content (false
  positives = nav, footer, aside, cookie banner).
- **Recall**: koliko main content-a je ekstrahirano (false negatives =
  paragrafi koji pripadaju artikli ali nedostaju).
- **F1**: harmonijska sredina.
- **Speed**: sekunde po HTML fajl (prosjek).

**Rezultat mora sadrÅ¾avati**: ime pobjednika, F1 score, decision
rationale. Ako je razlika < 5% F1, tie-breaker je bundle size
(manji library = bolji).

# Acceptance

- [ ] `main_content_extractor` proizvodi NON-EMPTY output za svaki
      HTML u benchmark korpusu (graceful fallback na raw text ako
      extractor failuje, sa `last_error` log)
- [ ] `boilerplate_filter` NE smanjuje F1 score (sanity: filter ne
      oduzima legitiman main content)
- [ ] `deduplicator` taÄan match: 5 ulaz chunks sa 3 unique + 2 duplikata
      â†’ 3 output chunks
- [ ] `deduplicator` deterministiÄki: isti input â†’ isti output (redoslijed
      oÄuvan)
- [ ] `deduplicator` edge cases: prazan input â†’ prazan; 1 chunk â†’ 1; svi
      duplikati â†’ 1
- [ ] `spikes/extraction-benchmark/result.md` postoji sa jasnom
      odlukom (Trafilatura vs readability-lxml)
- [ ] `spikes/extraction-benchmark/chosen.md` obrazlaÅ¾e odluku
- [ ] NEMA novog porta u `ports/` (isti obrazac kao S2-G9 â€” koristi
      `IngestionRepositoryPort` iz S2-G1)
- [ ] NEMA izmjena u `domain/`, `application/`, `presentation_webview/`,
      `jobs/`, `infrastructure/web_ingestion/`,
      `infrastructure/visual_extraction/`, `infrastructure/database/`,
      `resources/migrations/`
- [ ] `python -m pytest tests/unit/infrastructure/extraction/ -v` PROLAZI
- [ ] `python -m pytest -q` (DeepSeek unset) PROLAZI
- [ ] `python -m ruff check .` i `python -m mypy src` PROLAZE
- [ ] GitNexus `detect_changes` pokazuje SAMO nove simbole +
      `pyproject.toml` izmjene (ako ima novih dependency-ja)
- [ ] Mutation-test demonstriran (min 1 mutacija â†’ FAIL â†’ restore â†’
      PASS)

# Implementation steps (redoslijed, Q12 spike PRVO)

1. ProÄitati kanonski plan Â§10 S2-G4 + Â§11 hard gates + Q12 spike
   naziv u planu.
2. **Q12 spike PRVO** (PRIJE production koda):
   - Kreirati `spikes/extraction-benchmark/` (lokacija privremena, NE
     production).
   - Skinuti 3-5 HTML fajlova sa BHS sajtova (curl/wget; ALI
     poÅ¡tivati robots.txt i rate limit â€” 1 req/sec).
   - RuÄno ground-truth anotirati main content (paste u
     `corpus/ground-truth/`).
   - Pokrenuti oba library-ja, mjeriti P/R/F1 + speed.
   - OdluÄiti na osnovu benchmarka. Ako se odluka mijenja od
     oÄekivanja (npr. preferirao Trafilaturu, ali readability
     pobjeÄ‘uje), obrazloÅ¾i.
3. Implementirati `main_content_extractor` sa odabranom bibliotekom.
4. `boilerplate_filter` (opcioni post-pass, NE ako extractor to veÄ‡
   radi).
5. `deduplicator` (Äist Python, bez dependency-ja).
6. `__init__.py` exports.
7. `pyproject.toml` dependency management (vidi ispod).
8. `npx gitnexus detect_changes` PRIJE commit-a.
9. Mutation-test discipline.

# Dependency management

Preporuka za `pyproject.toml [project.optional-dependencies]`:
```toml
[project.optional-dependencies]
extraction = ["trafilatura>=1.6", "readability-lxml>=0.8"]
```
ili samo pobjednik (ovisno o Q12 spike):
```toml
extraction = ["trafilatura>=1.6"]  # ako Trafilatura pobijedi
```

ALTERNATIVNO: staviti u `[project.dependencies]` ako je G4 feature
koji se oÄekuje uvek (NE samo opcionalno). Koordinatorska odluka.

# Acceptance (za review)

- [ ] Svi gore navedeni acceptance PROLAZE
- [ ] `spikes/extraction-benchmark/result.md` + `chosen.md` postoje
- [ ] Scope Äist: `git diff --stat` ne sadrÅ¾i `ports/`, `domain/`,
      `application/`, `infrastructure/web_ingestion/`,
      `infrastructure/visual_extraction/`, `infrastructure/database/`,
      `resources/migrations/`
- [ ] Determinizam: isti input â†’ isti output za sva tri modula

# Review focus â€” Claude PRVO, PA Codex (MEDIUM, NOVI adapter)

- **Q12 spike** mora biti ODLUÄŒEN benchmarkom, ne preferencijom.
  Codex Ä‡e traÅ¾iti `result.md` sa stvarnim mjerenjima.
- **`deduplicator` taÄan match** â€” primarni acceptance test.
  Codex Ä‡e traÅ¾iti determinizam (isti input â†’ isti output).
- **`main_content_extractor` graceful fallback** â€” ako extractor
  failuje (mali HTML, neobiÄan markup), vraÄ‡a non-empty output sa
  log warning. NE throw exception (G6 orkestracija ne Å¾eli exception
  svaki put kad extractor ne uspije savrÅ¡eno).
- **Scope** â€” `gitnexus_detect_changes` potvrda.
- **Boilerplate filter** â€” ne oduzimati legitiman main content
  (sanity test).

**Codex adversarial fokus**: probati BHS-sajtove sa specifiÄnim
izazovima (paywall, infinite scroll, cookie consent overlay, mixed
BHS+English content, latinica+Ä‡irilica). PokuÅ¡ati dataset gdje
je main content ispod fold-a (ne u viewport-u).

# Rollback

MEDIUM (nema migracije, nema GUI). Rollback: revert commit +
opciono `pip uninstall trafilatura readability-lxml` ako u
`[project.dependencies]`. Ako u optional extra, samo revert.
`spikes/extraction-benchmark/` je veÄ‡ privremen (NE production
artifact), njegov rollback je samo brisanje spike foldera.

# Coordination

- **Paralelan sa S2-G3 (Pi, `infrastructure/web_ingestion/`)** i
  **S2-G5 (Pi ili drugi, `infrastructure/visual_extraction/`)** â€”
  disjunktni scope, razliÄite biblioteke. Workflow Â§10 provjera
  `allowed_paths(A) âˆ© allowed_paths(B) = âˆ…`:
    - G3 âŠ¥ G4: `web_ingestion/` vs `extraction/`
    - G4 âŠ¥ G5: `extraction/` vs `visual_extraction/`
    - G3 âŠ¥ G5: `web_ingestion/` vs `visual_extraction/`
- **Zavisi od S2-G3** (G3 fetch â†’ G4 extraction) za E2E smoke test,
  ALI NE za unit testove G4 (G4 radi nad HTML stringom, NE treba
  HTTP).
- **G6 (orkestracija) zavisi od G3+G4+G5+G9** â€” poslije G4.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-S2-011-content-extract
Branch:   task/ACS-S2-011-content-extract
Base:     main @ d13ad18
```

# Napomena za OpenCode agenta

- **Q12 spike je OBAVEZAN** prije production koda. Nije "opcioni
  benchmark" â€” to je dio acceptance-a. Ako nema benchmarka, G4 NE
  prolazi review.
- Koristi `spikes/extraction-benchmark/` za spike, NE kreiraj
  test_html_fixture u `tests/_fixtures/` (van `allowed_paths`).
- Ako extractor biblioteka zahtijeva nativnu dependency (npr.
  lxml C extension), testiraj sa mockom za unit testove, pravi
  HTML za integration.
- `deduplicator` NE treba dependency-ja â€” Äist Python (funkcija ili
  klasa, koordinatorska odluka).
- Koristiti `requests` NE `aiohttp` (sync/async fiksirana u S2-G1).
  Ako extractor interno koristi async (Trafilatura moÅ¾e), wrap u
  sync wrapper.

