---
task_id: ACS-S2-009
phase: "S2-G9 — Documents PDF/DOCX/XLSX"
title: "Document source parsers (PyMuPDF/python-docx/openpyxl) → isti SourceChunk/FactCandidate model"
coordinator: MiniMax (privremeno, Claude na pauzi zbog limita tokena)
implementer: pi
reviewers: [claude, codex]
status: "OPEN -- contract written before code, čeka implementera"
created_at: 2026-09-09
dependencies: [ACS-S2-001, ACS-S2-002]
risk: MEDIUM
allowed_paths:
  - src/ai_campaign_studio/infrastructure/document_ingestion/
  - src/ai_campaign_studio/infrastructure/document_ingestion/__init__.py
  - pyproject.toml
  - tests/unit/infrastructure/document_ingestion/
  - tests/unit/infrastructure/document_ingestion/__init__.py
forbidden_paths:
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/presentation_webview/
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_ingestion_repository.py
  - src/ai_campaign_studio/jobs/
  - resources/migrations/
gitnexus_required: true
adversarial_required: false
---

# Kontekst

Četvrti Slice 2 gate (nakon S2-G1 domain/ports i S2-G2 persistence merge-ovanih;
S2-G3/G4/G5/G9 paralelni). Kanonski plan §10 "S2-G9": dokument source
parsers za PDF/DOCX/XLSX koji proizvode **isti `SourceChunk` /
`FactCandidate` model** kao web ingestion (jedan provenance lanac).
D23: nema OCR-a (deep-research odluka).

Reference dokumenti:
- Kanonski plan: [`docs/AI_Campaign_Studio_Slice_2_Canonical_Plan.md`](../../../../docs/AI_Campaign_Studio_Slice_2_Canonical_Plan.md)
  (DAG §3, sync/async odluka §5 — Fiksirana u ACS-S2-001, *ne
  preispitivati*, security/ssrf §6, durability §7, page-classification
  §8, reuse §9, S2-G9 specifikacija §10, hard gates §11).
- Three archive documents — `AI_Campaign_Studio_Slice_2_Ingestion_Plan.md`,
  `ACS_Website_Ingestion_WebshopAudit_Donor_Analysis.md`,
  `docs/deep-research-report.md` — SAMO ako kanonski plan eksplicitno
  uputi na detalj koji ne sažima (§10 + §11 hard gates su dovoljni za
  G9 scope).
- `domain/ingestion/entities.py` (`SourceChunk`, `FactCandidate`,
  `CrawlTarget`, enum-i) — iz ACS-S2-001 + S2-002.
- `.agent/GITNEXUS_PROTOCOL.md` (obavezan za MEDIUM risk prema §13-§15).

**S2-G9 arhitektonska namjena** (sa §10): dokument (PDF/DOCX/XLSX) je
**jedan od više izvora** ingestion-a. Svaki source (web, dokumenti,
budući izvori) treba da se svede na isti `SourceSnapshot → SourceChunk →
FactCandidate` lanac, tako da G6 orkestracija (JobManager + checkpoint
recovery + cooperative cancellation) može tretirati sve izvore
uniformno. G9 NE dodaje novi port — koristi `IngestionRepositoryPort`
koji je već definisan u [`src/ai_campaign_studio/ports/repositories.py`](../../../../src/ai_campaign_studio/ports/repositories.py)
(S2-G1 contracts + S2-G2 lease queue). Adapter za dokumente je
implementation detalj ovog gate-a; G6 će ga pozvati kao
`InfrastructureDocumentSource` funkciju koja proizvodi `SourceChunk` +
`FactCandidate` direktno i registruje ih kroz `IngestionRepositoryPort`.

# Objective

Implementirati `DocumentSourceParsers` (PyMuPDF za PDF, python-docx za
DOCX, openpyxl za XLSX) u
`src/ai_campaign_studio/infrastructure/document_ingestion/`. Svaki
parser:

1. Prima putanju do lokalnog dokumenta (ili `bytes` + mime hint) +
   `IngestionRunId` + opcionalni `SourceSnapshotId` (za nastavak na
   postojeći snapshot ako extractor failuje u sredini).
2. Čita dokument u chunk-ove (granularnost per-parser, vidjeti
   Implementation details dolje).
3. Vraća `tuple[SourceChunk, ...]` (svaki chunk ima `SourceSnapshotId`
   parent reference, `chunk_id | None` se određuje nakon upisa).
4. NE pravi `FactCandidate` (to je G4/G5 step — dokumenti daju
   chunks; fact extraction iz chunks je extractor's posao, ne
   source-ov). Eventualni `last_error` se vraća na `CrawlTarget`
   analogno web-u, ako applicable.

`SourceChunk` (iz S2-G1/S2-G2) već ima:
`id: SourceChunkId`, `snapshot_id: SourceSnapshotId`, `locator_type:
str` (`"pdf_page"`, `"docx_para"`, `"xlsx_sheet_cell"`), `locator: str`
(sekvencijalni identifikator unutar dokumenta), `text: str`. Adapter
treba da popuni SVE četiri kolone smisleno.

D23 (nema OCR-a): skenirani PDF-ovi (slike umjesto teksta) ne spadaju
u scope; parser MORA vratiti `tuple[()]`` (prazan tuple) sa
`last_error="scanned_pdf_no_ocr"` na `CrawlTarget`, dokumentovano u
implementaciji. ACS nema plan za OCR (deep-research §10 D23).

# Implementation details (preporuka, ne obaveza — Pi odlučuje)

1. **`PdfSource`** (PyMuPDF): jedan `SourceChunk` po stranici
   (`locator_type="pdf_page"`, `locator="p{N}"`, `text=page.get_text()`).
   `pymupdf.open()` context manager. Ako `page.get_text().strip() == ""`,
   skip-page + log (vjerovatno scanned PDF).

2. **`DocxSource`** (python-docx): jedan `SourceChunk` po paragrafu
   (`locator_type="docx_para"`, `locator="p{N}"`, `text="\\n".join(p.runs)`
   ili samo `p.text`). Iteracija kroz `doc.paragraphs`. Tabele u
   DOCX-u (izvan `doc.paragraphs`) se MOGU izostaviti u ovoj rundi —
   označiti kao `OUT_OF_SCOPE` ako se pojavi potreba, jer zahtijeva
   iteraciju kroz `doc.tables` koja nije trivijalna. Ili uključiti
   ako Pi odluči (pišem `OUT_OF_SCOPE` u evidence ako je izostavljeno).

3. **`XlsxSource`** (openpyxl): jedan `SourceChunk` po sheet-u
   (`locator_type="xlsx_sheet_cell"`, `locator="s{SHEET}!c{R}{C}"`,
   `text=str(cell.value)`). Iteracija kroz `wb.sheetnames`. Prazne
   ćelije se izostavljaju; numeričke se konvertuju u `str()`. Formule
   (`cell.data_type == 'f'`) se uzimaju sa `cell.value` kao string
   formula (ne evaluiraju se).

4. **`__init__.py`**: izvesti sve tri klase + opcionalni
   `register_document_chunks(session, repo, run_id, source_path) ->
   int` helper koji poziva sve tri po MIME tipu. Helper NIJE port
   layer (G6 će ga zvati direktno ili kroz registry).

# Acceptance

- [ ] Tri nova dependency-ja u `pyproject.toml`. Preporuka:
      `[project.optional-dependencies] documents = ["PyMuPDF>=1.24",
      "python-docx>=1.1", "openpyxl>=3.1"]` (opciona extra jer
      dokument ingestion nije uvijek potreban; CI install sa
      `pip install -e ".[dev,documents]"`). Ako Pi odluči staviti u
      `[project.dependencies]` (core), obrazložiti u evidence.
- [ ] `PdfSource`, `DocxSource`, `XlsxSource` klase sa `extract(path,
      run_id, snapshot_id | None) -> tuple[SourceChunk, ...]` (ili
      sličan API).
- [ ] Unit testovi za svaki format sa SmallFile fixture-ima
      (minimalan PDF u `tests/_fixtures/documents/` sa 2 stranice
      teksta + 1 praznom/skenniranom stranicom, isti pattern za DOCX
      i XLSX).
- [ ] Svaki parser test:
    - otvori valid fajl → chunks ima očekivani `len`, tačan
      `locator_type`, tačne `locator` vrijednosti;
    - corrupted fajl (`bytes` od nevažećeg headera) → exception
      klasiran specifično (npr. `DocumentParseError` ValueError
      subclass) NE širi `Exception` generički;
    - prazan fajl (`bytes("")`) → exception istog tipa.
- [ ] Scanned PDF (image-only) test: parser VRAĆA prazan tuple +
      `last_error="scanned_pdf_no_ocr"` (ili sličan signal), NE
      raise. Implementer odlučuje signature.
- [ ] `IngestionRepositoryPort` runtime-checkable test se NE
      mijenja (ovo NIJE port change).
- [ ] NEMA izmjena u `ports/repositories.py` / `domain/*` /
      `application/*` / `infrastructure/database/repositories/*`
      (GitNexus `detect_changes` potvrda).
- [ ] `python -m pytest tests/unit/infrastructure/document_ingestion/ -v` prolazi.
- [ ] `python -m pytest tests/unit -q` (bez dokument integration
      testova, samo unit) prolazi. Poznati flaky
      `test_gate_report_against_current_repo_passes` MOŽE se pojaviti
      nezavisno — `stdout_tail=` u
      `artifacts/phase0_foundation_gate.json` treba pokazati koji
      test (ACS-MAINT-001).
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Scope čist: ništa van `allowed_paths`. Ako Pi treba izmijeniti
      `IngestionRepositoryPort` ili dodati novi port — eskalacija
      prema koordinatoru (MiniMax privremeno), proširenje
      `allowed_paths`, follow-up task.

# Implementation steps

1. Pročitati: kanonski plan §10 S2-G9, §11 hard gates, §6 SSRF
   (čak i za dokumente — extract-from-local-file je file IO
   sigurnosni aspekt), `domain/ingestion/entities.py` (SourceChunk
   shape), `ports/repositories.py` (IngestionRepositoryPort signatura
   za `register_source_snapshot` + `register_source_chunks`).
2. Provjeriti stvarnu verziju PyMuPDF / python-docx / openpyxl u dev
   okruženju (ako već instalirani — ne ponovo instalirati).
3. Napisati `PdfSource` + test SmallFile fixture + 3 test slučaja.
4. Napisati `DocxSource` + test SmallFile fixture + 3 test slučaja.
5. Napisati `XlsxSource` + test SmallFile fixture + 3 test slučaja.
6. Ažurirati `pyproject.toml` (`[project.optional-dependencies]
   documents` extra).
7. `npx gitnexus detect_changes` prije commit-a (GitNexus
   `gitnexus_required: true`).
8. CI mora biti zeleno sa `pip install -e ".[dev,documents]"`
   (update CI install liniju ako je potrebno — `allowed_paths`
   NE uključuje `.github/`, pa ako treba update CI-ja, eskalacija).

# Review focus — Claude PRVO, PA Codex (MEDIUM, ali NOVI adapter)

- **Chunk granularnost per format**: PDF per-page, DOCX per-paragraph
  (ili per-section ako Pi odluči), XLSX per-sheet-cell. Locator
  vrijednost mora biti STABILNA — isti chunk treba imati isti
  locator na dva poziva parsera.
- **D23 honor**: scanned PDF ne smije raiseati; mora vratiti
  prazan rezultat sa signalom. Cross-check evidence.
- **Exception klasiranje**: corrupted file MORA imati specifičan
  exception tip (NE `Exception`), tako da G6 orkestracija može
  uhvatiti i ažurirati `CrawlTarget.last_error`.
- **Source ID consistency**: svaki chunk `snapshot_id` mora biti
  isti kao parent `SourceSnapshot.id` (foreign key u S2-G2
  migraciji).
- **GitNexus aditivnost**: `gitnexus_detect_changes` PRIJE review-a
  MORA pokazati SAMO nove simbole (3 source klase, helper,
  fixture fajlovi, testovi) + `pyproject.toml` documents extra.
  NULA izmjena u port/domain/application/repository.

**Codex adversarial fokus**: ZIP bomb u XLSX-u (`xl/sharedStrings.xml`
sa milionima redova), PDF sa circular references (PyMuPDF
historically), DOCX sa ekstremno dubokim XML nestingom (`O(n²)`
`document.xml` parsing) — pokušati napraviti SmallFile fixture koji
simulira svaki od ovih i provjeriti da parser NE hang-uje (ili
ima timeout escape).

# Rollback

MEDIUM (implementacija, ne migracija). Nema `ALTER TABLE` u
aplikaciji, parseri su čist kod. Rollback: revert commit + (opciono)
`pip uninstall PyMuPDF python-docx openpyxl`. Migration-shema
(`source_chunks`, `source_snapshots` u S2-G2) ostaje netaknuta i
neovisna o G9.

# Coordination

**Disjunktni paralelni kandidati** (provjeriti `allowed_paths`
presjek prije nego se puste paralelno):

| Kandidat | allowed_paths |
|---|---|
| ACS-S2-010+ (S2-G3 — HTTP Fetch) | `infrastructure/web_ingestion/` (nema overlap sa `document_ingestion/`) |
| ACS-S2-011+ (S2-G4 — Content Extract) | `domain/extraction/` (ili slično, još nije decidirano) |
| ACS-S2-012+ (S2-G5 — Visual Extract) | `infrastructure/visual_extraction/` (nema overlap) |
| ACS-S2-013+ (S2-G6 — Pipeline use-case) | `application/ingestion/` (zavisi od svih G3/G4/G5/G9) |

S2-G3/G4/G5/G9 su u principu paralelni po kanonskom plan §3, ALI:

- G3, G4, G5 ne zavise od G9 (koriste isti SourceChunk/FactCandidate
  model, ali extractoru od WEB-a, ne dokumenta).
- G9 **ne zavisi** od G3/G4/G5 (parser dokumenta nezavisan od
  web portova).
- **G6 zavisi od SVIH** (G2 + G3 + G4 + G5 + G9).

Trenutno nema drugog S2-G* contract-a otvorenog. Kad se otvore,
potvrditi disjunktnost `allowed_paths` + GitNexus shared-caller
prije nego oba idu paralelno.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-S2-009-document-ingestion
Branch:   task/ACS-S2-009-document-ingestion
Base:     main @ 30de804
```

# Napomena za implementera (Pi)

- `domain/ingestion/entities.py` već ima `SourceChunk` (frozen
  dataclass, S2-G1) i `SourceChunkId` (NewType, S2-G1). Koristiti
  njih. NE kreirati nove entitete.
- Ako `SourceChunk` polja nisu dovoljna za dokumente (npr. treba
  `pdf_metadata` sa author/title), **NE dodavati nova polja u
  ovom tasku** — to je risk scope proširenje, eskalacija. Ili
  koristiti `locator` slobodno (npr. `locator="p1:author=John"`) i
  parsirati u G4/G5.
- PyMuPDF je `import fitz` (legacy import name), NE `pymupdf`.
- openpyxl je `import openpyxl`, ali Workbook klasa je
  `openpyxl.load_workbook(path, read_only=True, data_only=True)` za
  sigurno read-only mod.
- `bytes` vs `path` API: implementacija treba primati PUTANJU.
  G6 će otvoriti fajl preko standardnog `with open() as f:` i
  proslijediti putanju. (Alternative: primati `bytes` + mime hint —
  ako Pi odluči, prihvatljivo, ali path-based je default.)
