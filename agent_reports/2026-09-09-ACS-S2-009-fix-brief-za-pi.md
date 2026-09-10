---
task_id: ACS-S2-009
phase: "fix-brief za Codex REJECT #2: BF-1 + BF-2"
title: "chunk ID kolizija (BF-1) + truncated-PDF D23 klasifikacija (BF-2)"
to_implementer: pi
from_coordinator: MiniMax (koordinator)
created_at: 2026-09-09
---

# Kontekst

Codex adversarial review [#26](https://github.com/Rade69/AI-Campaing-Studio/pull/26) REJECT.
Dva blocking nalaza na HEAD-u `facd00f`:

- **BF-1 (HIGH)** — cross-document chunk-ID kolizija, SQLite
  `ON CONFLICT(id) DO UPDATE` prepisuje provenance
- **BF-2 (MEDIUM)** — truncated/zero-page korumpirani PDF se
  pogrešno klasira kao D23 scanned, vraća prazan tuple umjesto
  `DocumentParseError`

Nepromijenjeno od prethodnog review-a: scope (PASS), security (PASS),
gitnexus_impact (PASS). Scope čist (nema novih izmjena van
allowed_paths).

# BF-1 — HIGH: chunk ID mora biti snapshot-scoped

## Reprodukcija (Codex-ov live repro)

Parsirati dva različita DOCX-a u istom `IngestionRunId`, sa snapshotima
`snap-1` i `snap-2`. Trenutni kod pravi:
```python
id = SourceChunkId(f"{run_id}:{locator}")  # oba → "same-run:p1"
```
SQLite `source_chunks.id PRIMARY KEY` + `ON CONFLICT(id) DO UPDATE` —
drugi `save_source_chunk()` prepisuje red prvog dokumenta:
```text
('same-run:p1', 'snap-2', 'document two')   # ← samo ovo ostaje
```
Time se krši "jedan provenance lanac" — `FactCandidate` koja se
kasnije veže na `(same-run:p1, snap-1)` više ne postoji.

## Required fix

`SourceChunk.id` mora biti **globalno jedinstven** u SQLite shemi
(S2-G2 migracija, `0009_ingestion_foundation.sql`):
```sql
source_chunks.id TEXT PRIMARY KEY
```
Trenutni `f"{run_id}:{locator}"` to NE garantira (isti locator u
dva snapshot-a istog run-a → kolizija).

**Ispravan obrazac**: `f"{run_id}:{snapshot_id}:{locator}"` —
snapshot-scoped, deterministički, idempotentan za isti
`(run_id, snapshot_id, locator)`. Primjeri:

```python
# pdf_source.py, docx_source.py, xlsx_source.py — SVA TRI
id = SourceChunkId(f"{run_id}:{snapshot_id}:{locator}")
```

VAŽNO: `snapshot_id` je već na ruci u `extract(self, path,
run_id, snapshot_id)` signature (S2-G1/S2-G2 entitet). NEMA
potrebe za novim parametrom — samo proslijedi u ID format.

## Required regression test

Novi test u `tests/unit/infrastructure/document_ingestion/`
(test_pdf_source.py ili novi test_chunk_id_collision.py):

```python
def test_extract_two_documents_in_same_run_produce_distinct_ids(
    tmp_path: Path
) -> None:
    """BF-1: chunk ID collision across snapshots in the same run."""
    path_a = tmp_path / "doc_a.docx"
    path_b = tmp_path / "doc_b.docx"
    _make_docx(path_a, ["First only"])
    _make_docx(path_b, ["Second only"])

    src_a = DocxSource().extract(
        str(path_a), IngestionRunId("run-1"), SourceSnapshotId("snap-1")
    )
    src_b = DocxSource().extract(
        str(path_b), IngestionRunId("run-1"), SourceSnapshotId("snap-2")
    )

    ids_a = [c.id for c in src_a]
    ids_b = [c.id for c in src_b]
    assert ids_a != ids_b, (
        f"BF-1 collision: ids_a={ids_a}, ids_b={ids_b}"
    )
    # Idempotency: ponovljeni poziv za isti snapshot daje iste ID-eve.
    src_a_again = DocxSource().extract(
        str(path_a), IngestionRunId("run-1"), SourceSnapshotId("snap-1")
    )
    assert [c.id for c in src_a_again] == ids_a
```

Test mora pokrivati:
- 2 različita snapshot-a u istom run-u → distinct ID
- isti snapshot ponovljen → isti ID (determinističnost)

**Opciono proširenje (preporučeno)**: isti test za `PdfSource` i
`XlsxSource` (sva tri parsera). Ili parametrizirani test sa
`@pytest.mark.parametrize("source_cls", [PdfSource, DocxSource,
XlsxSource])`.

**Ažuriraj postojeći test `test_extract_valid_pdf_*`**: assertion
`chunks[0].id == "run-1:p1"` postaje `chunks[0].id ==
"run-1:snap-1:p1"` (snapshot_id ulazi u ID). Tako i ostali
postojeći testovi koji koriste `assert chunks[X].id == "run-1:p1"`
pattern.

## Scope

**Samo**: `src/ai_campaign_studio/infrastructure/document_ingestion/{pdf,docx,xlsx}_source.py`
+ test fajlovi u `tests/unit/infrastructure/document_ingestion/`.
NEMA izmjena u SQLite shemi (S2-G2 vec definirao PRIMARY KEY),
portovima, domeni, repo-u. **NEMA nove migracije** — BF-1 se rješava
u Python-u jer je problem u ID formatu, ne u shemi.

# BF-2 — MEDIUM: truncated/zero-page PDF mora biti DocumentParseError, NE D23 ()

## Reprodukcija (Codex-ov live repro)

PDF sa magic headerom `%PDF-1.7` ali bez valjanog trailer/xref
(truncated korumpirani fajl): PyMuPDF ga otvori kao dokument sa
`page_count = 0`. `PdfSource.extract()` loop je `for page_index in
range(doc.page_count)` — sa 0 stranica, nijedan chunk se appenda,
return `()`.

Posljedica: G6 orkestracija vidi prazan tuple i zapisuje
`last_error="scanned_pdf_no_ocr"` na `CrawlTarget` — što je
pogrešno za korumpirani fajl (trebao bi `last_error="corrupted_pdf"` ili
sl., NE scanned).

D23 PRAZAN tuple je isključivo za **valjdan image-only PDF** (PDF
koji se uspješno otvori, ima stranice, ALI nema tekstualni sadržaj
jer je skeniran). Korumpirani/zero-page PDF nema nikakvu validnu
strukturu — ne može se razlikovati od praznog dokumenta u D23
kontekstu.

## Required fix

U `pdf_source.py`, POSLIJE `doc = fitz.open(path)`, dodati
strukturalnu provjeru:

```python
# pdf_source.py, nakon otvaranja fajla
if doc.page_count == 0:  # type: ignore[union-attr]
    doc.close()
    raise DocumentParseError(
        "PDF has zero pages (truncated or corrupted); "
        "cannot extract."
    )
```

Ili, dublje (opciono, ako Codex preferira): validacija broja
> 0 stranica + barem jedna stranica sa `get_text()` koja nije
potpuno prazna whitespace (za razlikovanje od image-only). ALI
minimalna verzija (page_count > 0) je dovoljna za BF-2.

`try/finally` oko `doc.close()` je opcioni cleanup hardening
(release fajl handle). Originalna Codex napomena: "openpyxl drži
fajl otvoren do `gc.collect()`". Za PyMuPDF, `doc.close()` je
jednostavan za dodati u `try/finally`.

## Required regression test

U `tests/unit/infrastructure/document_ingestion/test_pdf_source.py`:

```python
def test_extract_truncated_pdf_raises_document_parse_error(
    tmp_path: Path,
) -> None:
    """BF-2: a truncated/zero-page PDF (valid magic but no trailer)
    must raise DocumentParseError, NOT return empty tuple (which
    is reserved for valid D23 image-only PDFs)."""
    path = tmp_path / "truncated.pdf"
    # Valid %PDF-1.7 magic, then deliberately truncated garbage
    # (no xref, no trailer). PyMuPDF accepts this as 0-page doc.
    path.write_bytes(b"%PDF-1.7\n" + b"\x00" * 200)

    with pytest.raises(DocumentParseError):
        PdfSource().extract(
            str(path), IngestionRunId("run-1"), SourceSnapshotId("snap-1")
        )
```

Također: **zadržati** `test_extract_scanned_pdf_returns_empty_tuple`
ali pojačati — napraviti PDF sa `text_pages=0, blank_pages=2`
(trenutno) I novi test `text_pages=0, blank_pages=1` da se razlikuje
"validan PDF sa samo image-only stranicama" od "korumpiran/zero-page".

Ako je PyMuPDF teško natjerati da kreira 0-page PDF sintetički, može
se koristiti opcioni test pattern sa `path.write_bytes(b"%PDF-1.7\n"
+ corrupted trailer)` kao u reprodukciji Codex-a.

# Acceptance (za ponovni Claude review)

- [ ] `id` u sva tri parsera postao `f"{run_id}:{snapshot_id}:{locator}"`
      (ili ekvivalentno globalno jedinstven, dokumentuj zašto)
- [ ] Novi test `test_extract_two_documents_in_same_run_produce_distinct_ids`
      (ili parametrizirani) PROLAZI za sva tri parsera
- [ ] Postojeći testovi sa `chunks[X].id == "run-1:p1"` AŽURIRANI
      na novi ID format (sa snapshot_id)
- [ ] PdfSource: `page_count == 0` → `raise DocumentParseError` (POSLIJE open)
- [ ] Novi test `test_extract_truncated_pdf_raises_document_parse_error`
      PROLAZI (sa `%PDF-1.7` + korumpirani trailer, NE sa `%PDF-1.7`
      + valid trailer + 0 stranica jer to ne postoji kao "0-page PDF")
- [ ] `test_extract_scanned_pdf_returns_empty_tuple` I DALJE PROLAZI
      (image-only PDF sa VALID strukturom + tekst-stranice bez teksta
      → `()`)
- [ ] Opciono: `try/finally: doc.close()` za cleanup hardening
- [ ] Opciono: parametrizirani test cross-document collision za sva tri parsera
- [ ] Pytest focused (sa documents extra) PROLAZI
- [ ] `python -m pytest tests/unit -q` PROLAZI (DeepSeek unset, kako stoji
      u lekciji iz handoff-a)
- [ ] `python -m ruff check .` i `python -m mypy src` PROLAZE
- [ ] NEMA izmjena van `allowed_paths`

# Implementation steps (redoslijed)

1. Pročitaj Codex review (ovo je fix-brief na osnovu toga):
   `agent_reports/2026-09-09-ACS-S2-009-review-codex.md`
2. **BF-1 prvo**: `id` format u `pdf_source.py`, `docx_source.py`,
   `xlsx_source.py` — sva tri u jednoj sesiji. Ažuriraj postojeće
   testove sa novim ID patternom.
3. **BF-1 test**: dodaj cross-document collision test (preporučeno
   parametrizirani za sva tri parsera).
4. **BF-2**: u `pdf_source.py` dodaj `if doc.page_count == 0: raise
   DocumentParseError(...)` POSLIJE `fitz.open(path)`.
5. **BF-2 test**: dodaj `test_extract_truncated_pdf_raises_document_parse_error`
   sa truncated magic inputom.
6. Pokreni `python -m pytest tests/unit/infrastructure/document_ingestion/ -v`
   sa documents extra instaliranim — svi PASS.
7. Pokreni `python -m pytest -q` (DeepSeek unset) — PASS.
8. `ruff`, `mypy` — PASS.
9. Commit + push branch (kao i prethodni put).
10. Pošalji reply sa "→ ZA CODEX" markerom (nakon što ja
    uradim Claude re-review + mutation test).

# Verifikacija

Codex je prethodno potvrdio:
- PDF mješoviti text/image/text PDF: `p1` i `p3`, image preskače.
- D23 image-only test.
- DOCX `p1`/`p3`, XLSX stabilni lokatori.
- snapshot_id se provjerava; None se odbija.
- Invalid ZIP, partial ZIP, XLSX corrupted, XML entity-expansion
  → `DocumentParseError`.
- `DocumentParseError` je `ValueError`.
- Scope aditivan.
- Dependency lower-bound OK.

Dakle FIX NE SMIJE dirati ove potvrđene aspekte.

# Rollback

MEDIUM (nema migracije, nema GUI). Rollback: revert commit.

# Worktree

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-S2-009-document-ingestion
Branch:   task/ACS-S2-009-document-ingestion
Base:     main @ 30de804
```

Čekam tvoj evidence sa verification outputom + commit hash, pa
radim Claude re-review (mutation-test) i šaljem nazad Codex-u na
re-review.

**Workflow napomena**: mutation-test ću pokrenuti na BF-1 i BF-2 —
privremeno mutirati ID format na `f"{run_id}:{locator}"` (stari) i
provjeriti da collision test FAIL-uje. Vraćanje na ispravan format
treba ponovo proći, čist `git diff --stat`. Isto za BF-2 —
mutirati `if doc.page_count == 0: raise` natrag na samo-skip i
provjeriti da truncated-PDF test FAIL-uje.
