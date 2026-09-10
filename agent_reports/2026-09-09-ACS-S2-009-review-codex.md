---
verdict: REJECT
scope: PASS
acceptance: REJECT
architecture: REJECT
security: PASS
tests: REJECT
gitnexus_impact: PASS
blocking_findings:
  - "BF-1: SourceChunk ID kolidira između različitih dokumenata istog ingestion run-a i SQLite upsert prepisuje provenance"
  - "BF-2: truncated/zero-page korumpirani PDF se pogrešno klasira kao scanned PDF i vraća prazan tuple"
---

# ACS-S2-009 — Codex adversarial review PR #26

## Presuda

REJECT za `task/ACS-S2-009-document-ingestion`, HEAD
`facd00f909c4745924f11d01960eb22a6e10d904`. PR je OPEN,
MERGEABLE/CLEAN i CI `test` je SUCCESS na istom HEAD-u, ali postoje dva
reprodukovana data-integrity/klasifikacijska defekta.

## BF-1 — HIGH: cross-document chunk-ID kolizija briše provenance

Sva tri parsera grade ID kao `f"{run_id}:{locator}"`. `source_chunks.id` je,
međutim, globalni SQLite `PRIMARY KEY`, a jedan `IngestionRun` pripada brandu i
može sadržati više source snapshotova/dokumenata. Dva dokumenta u istom run-u
normalno imaju isti lokalni locator (`p1`, odnosno isti sheet/cell).

Live repro je parsirao dva različita DOCX-a u `same-run`, sa snapshotima
`snap-1` i `snap-2`. Oba su proizvela ID `same-run:p1`. Poslije dva stvarna
`SqliteIngestionRepository.save_source_chunk()` poziva baza je sadržala samo:

```text
('same-run:p1', 'snap-2', 'document two')
```

Drugi `ON CONFLICT(id) DO UPDATE` prepisao je tekst i `snapshot_id` prvog
dokumenta. Time se krši cilj "jedan provenance lanac" i budući FactCandidate
može pokazivati na pogrešan izvor.

Required fix: chunk ID mora biti snapshot-scoped (npr.
`f"{run_id}:{snapshot_id}:{locator}"` ili ekvivalentno stabilan globalno
jedinstven derivat). Dodati izvršni test sa dva različita snapshot-a u istom
run-u i istim locatorom koji potvrđuje različite ID-eve i da oba reda ostaju u
SQLite-u. Zadržati determinističnost na ponovljenom pozivu za isti snapshot.

## BF-2 — MEDIUM: korumpirani PDF prolazi kao D23 scanned rezultat

Eksplicitno traženi truncated-magic probe sa sadržajem koji počinje
`%PDF-1.7` ali nema valjan trailer/xref otvorio se kroz PyMuPDF kao dokument sa
nula stranica. `PdfSource.extract()` vratio je `()`, bez
`DocumentParseError`.

Prazan tuple je rezervisan za valjan image-only/blank PDF (D23, nema OCR-a).
Korumpirani/zero-page PDF se zato sada ne može razlikovati od scanned PDF-a i
G6 bi mu mogao zapisati pogrešan `scanned_pdf_no_ocr` signal.

Required fix: poslije open-a validirati strukturalno upotrebljiv PDF (najmanje
`page_count > 0`) i zero-page/truncated input klasirati kao
`DocumentParseError`; dodati regression test sa truncated PDF magic inputom.
Valjan PDF sa jednom ili više image-only stranica mora i dalje vratiti `()`.

## Potvrđeno

- PDF granularnost radi: mixed text/image/text PDF vraća `p1` i `p3`, image
  stranicu preskače, a ponovljena ekstrakcija daje iste chunkove.
- D23 image-only PDF test prolazi; DOCX daje `p1`/`p3`; XLSX daje stabilne
  `s<SHEET>!r<ROW>c<COL>` locatore uz `read_only=True, data_only=True`.
- Svi proizvedeni chunkovi u postojećim testovima nose zadani parent
  `snapshot_id`; `snapshot_id=None` se eksplicitno odbija.
- Invalid ZIP, partial ZIP, valid XLSX ZIP sa pokvarenim worksheet XML-om i
  entity-expansion XML-om svi se klasiraju kao `DocumentParseError`.
- `DocumentParseError` je `ValueError`; optional biblioteke se importuju tek
  u `extract()`, pa je modul importabilan bez documents extra.
- Scope je aditivan: implementation je samo u
  `infrastructure/document_ingestion/` + `pyproject.toml`; nema promjena u
  ports/domain/application/WebView/repository/jobs/migrations. Contract i
  evidence reporti su workflow artefakti.
- Dependency lower-boundovi odgovaraju kontraktu. PyMuPDF 1.28.2 radi, uz
  upstream upozorenje da je legacy `fitz` import deprecated; kontrakt je
  eksplicitno tražio taj import pa to nije blocker ovog PR-a.

## Testovi i gateovi

```text
focused bez PyMuPDF u default env: 10 passed, 1 skipped
focused sa privremenim PyMuPDF 1.28.2: 15 passed
full pytest, DeepSeek unset, PDF testovi aktivni: 1280 passed, 1 warning
ruff check .: PASS
mypy src: PASS (188 source files)
architecture boundaries: 18 passed
secret scan: PASS
git diff --check origin/main...HEAD: PASS
```

Prvi full-suite pokušaj sa postavljenim DeepSeek ključem imao je poznati
nevezani live-provider fail (`expected 2 items, got 7`). Gate artefakt je to
eksplicitno imenovao. Ponovljeni projektno relevantni offline gate
(`DEEPSEEK_API_KEY` unset) prošao je 1280/1280.

CI trenutno ne instalira `documents` extra, pa zeleni PR check ne izvršava
stvarne parser testove; lokalni run sa sva tri dependencyja ih izvršava.
Odvojeni `.github/workflows/ci.yml` follow-up ostaje opravdan i nije blocker
nakon gore navedenog lokalnog dokaza.

## Pokrivenost i dodatne napomene

Postojeći ID assertion (`run-1:p1`) ne hvata cross-document koliziju niti
mutaciju koja bi svim chunkovima vratila isti ID. Required BF-1 test treba
pokriti i različitost između snapshotova i per-chunk različitost za sva tri
parsera.

Strukturalno valjan, ali tekstualno prazan DOCX/XLSX trenutno takođe vraća
`()`; kontrakt eksplicitno testira zero-byte prazne fajlove, pa ovo nije
proglašeno blockerom. G6 mora ipak imati definisanu klasifikaciju koja takve
rezultate ne naziva `scanned_pdf_no_ocr`.

Na Windows probeu openpyxl je nakon inner-XML parse greške držao fajl otvoren
do `gc.collect()`. Nije uzrokovao pogrešan rezultat i nije blocker, ali vrijedi
ojačati resource cleanup za ponovljene malformirane uploadove.

## GitNexus

Indeks je vezan za `H:\AI Campaing Studio`, commit `00bbc89`, i stale je prema
main `30de804`. Worktree `detect-changes --scope compare` je prijavio poznato
lažno `No changes detected`, pa nije korišten kao dokaz čistoće. Kompenzacija:
puni Git diff, caller/symbol `rg` sweep, live SQLite probe i full gate.
`SourceChunk` context potvrđuje globalni persistence consumer
`SqliteIngestionRepository`; upravo taj consumer izvršno demonstrira BF-1.

Codex nije mijenjao implementation, mergeao niti pushao. Nakon oba required
fixa potreban je re-review na novom HEAD-u.
