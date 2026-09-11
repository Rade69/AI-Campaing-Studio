# ACS-GUI-013 — dugme za brisanje preuzetih podataka (reset za testiranje)

**Datum:** 2026-09-11
**Agent:** Claude
**Scope:** vidi `ACS-GUI-013-task-contract.md`

## Šta je urađeno

1. **Port** (`ports/repositories.py`): nova `IngestionRepositoryPort.delete_ingestion_data_for_brand(brand_id) -> int`.
2. **SQLite implementacija**: FK-safe redoslijed brisanja (fact_candidates →
   source_chunks → crawl_targets → source_snapshots → ingestion_checkpoints
   → ingestion_runs) — snapshot ID-ovi se hvataju PRIJE bilo kakvog DELETE-a
   jer `foreign_keys=ON` znači da redoslijed mora biti djeca-prije-roditelja.
   `approved_facts` tabela se NIKAD ne dira.
3. **Bridge**: `clear_brand_ingestion(raw_payload)` — ista validacija kao
   `start_brand_ingestion` (resolve brand, provjeri postoji), poziva repo
   metodu, vraća `deleted_run_count`.
4. **Brend ekran**: novo crveno dugme "Obriši sve" pored "Pokreni ingestion".
5. **app.js**: `clearIngestion()` — `window.confirm()` prije brisanja
   (nepovratna akcija), zatim poziv bridge-a, pa `loadFactReview()` da se
   lista odmah osvježi (prazna).

## Zašto `approved_facts` ostaje netaknut (namjerna odluka)

Kad se kandidat odobri, tekst se KOPIRA u `approved_facts.content` — ne
čuva se kao referenca na sirovi snapshot. Brisanje sirovih ingestion
podataka gubi samo duboku provenance vezu (link ka originalnoj stranici),
NE i sam odobreni tekst koji možda već ulazi u brand snapshot za generisanje
kampanje. Ovo je dokumentovano u docstring-u metode, provjereno testom.

## Verifikacija

```
Live end-to-end (bridge, pravi https://example.com/):
  1) ingest → 6 candidates
  2) clear_brand_ingestion → ok=True, deleted_run_count=1
  3) get_ingestion_review → 0 candidates (potvrđeno prazno)
  4) clear ponovo na već praznom brendu → ok=True, deleted_run_count=0 (idempotentno)

Integration test (test_clear_brand_ingestion_flow.py, seed pattern isti kao
postojeći test_ingestion_review_flow.py):
  - 2 kandidata seedovana, 1 odobren (approve_fact_candidate)
  - clear_brand_ingestion → sve ingestion tabele prazne (provjereno SQL COUNT)
  - approved_facts red za odobreni kandidat I DALJE POSTOJI sa ispravnim
    content-om — potvrđeno direktnim upitom nad bazom
  - idempotentno ponovno brisanje potvrđeno

python -m ruff check . : All checks passed
python -m mypy src     : Success, 218 fajlova, 0 grešaka
node --check app.js    : OK
pytest (ciljano)       : 3/3 novi testovi PASS, 338/339 presentation_webview
                          (1 nepovezan flaky DeepSeek test, poznat od prije)
pytest (puna regresija): 1545 passed, 0 failed, 381.48s
```

## Kako testirati u pravoj aplikaciji

1. Zatvori postojeći prozor aplikacije (ako je otvoren) i pokreni ponovo:
   ```
   cd "H:\AI Campaing Studio"
   $env:PYTHONPATH = "H:\AI Campaing Studio\src"
   .venv\Scripts\python.exe -m ai_campaign_studio.presentation_webview
   ```
2. Brend → "Pregled činjenica" → unesi URL → "Pokreni ingestion" → sačekaj
   rezultat.
3. Klikni crveno dugme **"Obriši sve"** → potvrdi u dijalogu → lista se
   isprazni.
4. Unesi novi URL → "Pokreni ingestion" ponovo — kreće se od čistog stanja.

## Rizici / ograničenja

- Brisanje je TRAJNO i bez undo-a u GUI-ju (otud confirm dijalog).
- Ako je korisnik već "Napravio snimak brenda" (assemble) sa odobrenim
  činjenicama prije brisanja, snimak ostaje ispravan (approved_facts
  netaknut) — ali ako PLANIRA da doda još izvora za ISTI snapshot kasnije,
  gubi mogućnost da vidi/reference-uje STARE sirove stranice (samo tekst
  ostaje, ne i "otvori originalnu stranicu" link). Prihvaćen trade-off za
  brzinu testiranja.
