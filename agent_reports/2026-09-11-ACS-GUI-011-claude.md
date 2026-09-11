# ACS-GUI-011 — Brend GUI: unos URL-a pokreće IngestBrandSources

**Datum:** 2026-09-11
**Agent:** Claude
**Scope:** vidi `ACS-GUI-011-task-contract.md`

## Šta je urađeno

1. **Bridge** (`presentation_webview/bridge/__init__.py`): nova metoda
   `start_brand_ingestion(raw_payload)`. Validira `{brand_id, urls}`,
   submituje pozadinski posao preko `JobManager` (isti obrazac kao
   `generate_campaign_content`), vraća `job_id` odmah. Closure na
   worker thread-u gradi FRESH `IngestBrandSources` sa PRAVOM
   infrastrukturom (`HttpFetcher`, `DomainDiscovery`, `UrlClassifier`,
   `MainContentExtractor`, `BoilerplateFilter`, `Deduplicator`,
   `VisualIdentityAdapter`) — identično onome što je ranije u sesiji
   ručno dokazano da radi na `https://example.com/`. Na kraju upisuje
   finalne brojke (`fetched/extracted/candidates/failed`) u `JobState.message`
   preko postojećeg `job_manager.update_progress()` — nema novih
   privatnih hakova na `JobManager`.
2. **UI model**: `StartIngestionResultUiModel` u `presentation/ui_models.py`.
3. **Brend ekran**: uklonjen placeholder ("Kasnije: pokreni ingestion/review
   tok.") u panelu "Pregled činjenica" — zamijenjen poljem za URL +
   dugmetom "Pokreni ingestion".
4. **app.js**: `startIngestion()` — submit, poll `get_job_status` (isti
   `POLL_INTERVAL_MS`), na `SUCCEEDED` poziva postojeći `loadFactReview()`
   (već postoji za review listu) tako da se novi kandidati odmah vide.

## Šta NIJE dirano (namjerno, iz contract-a)

- `IngestBrandSources`, `HttpFetcher`, `UrlSafetyPolicy` — nepromijenjeni.
- `document_extractors={}` — PDF/DOCX/XLSX URL-ovi trenutno daju 0 chunk-ova
  (ne pucaju, samo se ništa ne izvuče). Follow-up ako zatreba.
- "Osvježi podatke" dugme i "Dodaj resurs" (Brend resursi panel) i dalje
  imaju svoje stare toast poruke — različita funkcija (status-check /
  file-upload), nisu preklapali sa ovim zadatkom.
- Brand-picker UI — koristi se postojeći `_ensure_brand()` default/seed
  brend (isti obrazac kao `get_ingestion_review`).

## Verifikacija

```
Live end-to-end (bridge → job → real fetch → review), https://example.com/:
  start_brand_ingestion → ok=True, job_id vraćen odmah
  get_job_status poll:  RUNNING → phase=FETCH → SUCCEEDED
                         message='fetched=2 extracted=6 candidates=6 failed=0'
  get_ingestion_review → 6 candidates, sa stvarnim tekstom i snapshot_url

python -m ruff check .   : All checks passed
python -m mypy src       : Success, 218 source files, 0 errors
node --check app.js      : OK (sintaksa validna)
pytest test_start_brand_ingestion.py : 7/7 PASS (validacija, bez mreže)
pytest tests/unit/presentation_webview/ : 329/329 PASS (nema regresije)
pytest (puna regresija)  : 1541 passed, 0 failed, 413.83s
```

## Kako TI (korisnik) možeš testirati kroz pravu aplikaciju

1. Otvori terminal u `H:\AI Campaing Studio` (main, poslije merge-a).
2. Prvi put (ako nisi ranije): `playwright install chromium` NIJE
   potreban za ovo (to je G8, nepovezano). Provjeri da je WebView2
   Runtime instaliran (Windows obično već ima, GUI će jasno reći ako ne).
3. Pokreni GUI:
   ```
   .venv\Scripts\python.exe -m ai_campaign_studio.presentation_webview
   ```
4. U prozoru: klikni **Brend** u navigaciji.
5. Klikni tab **"Pregled činjenica"** (peti tab).
6. U polje "URL za preuzimanje sadržaja" unesi npr. `https://example.com/`
   (ili bilo koji pravi javni sajt) i klikni **"Pokreni ingestion"**.
7. Vidjet ćeš status "U toku — FETCH…" dok se posao izvršava (par
   sekundi do desetak sekundi, zavisno od sajta), pa poruku sa brojkama
   (fetched/extracted/candidates/failed).
8. Lista kandidata ispod (odobri/odbij) će se sama osvježiti sa
   stvarnim tekstom preuzetim sa tog sajta.

## Rizici / ograničenja

- SSRF zaštita je ISTA kao svugdje (`UrlSafetyPolicy`, provjereno u ranijim
  rundama ove sesije) — literal privatni/loopback IP i redirect ka njemu
  bivaju odbijeni sa `unsafe:...` u `get_job_status().message` posredno
  (candidate lista ostaje prazna, run status SUCCEEDED sa failed_pages>0).
- Jedan URL po pokretanju u ovoj verziji (v1, namjerno — vidi contract).
- Nema cancel dugmeta za ovaj posao (postoji za `generate_campaign_content`,
  ovdje namjerno izostavljeno radi jednostavnosti prve verzije — job je
  obično brz za par stranica).

## Sljedeće

Ako testiranje otkrije da treba: multi-URL unos (textarea), cancel dugme,
brand-picker, ili G9 document_extractors wiring — javi, to su odvojeni
mali follow-up taskovi, ne mijenjaju ovaj.
