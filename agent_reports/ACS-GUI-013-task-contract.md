---
task_id: ACS-GUI-013
title: "Brend GUI — dugme za brisanje preuzetih podataka (reset za testiranje)"
coordinator: claude
implementer: claude
status: "OPEN — kontrakt pisan prije koda, korisnički zahtjev nakon testiranja ACS-GUI-011/012"
created_at: 2026-09-11
risk: MEDIUM
gitnexus_required: false
adversarial_required: false
---

# Kontekst

Korisnik testira ponavljanjem: unese URL, vidi rezultat, želi da unese
DRUGI URL bez da mu se stari kandidati miješaju sa novim. Trenutno
`get_ingestion_review` vraća SVE kandidate ikad ingestovane za brend —
nema načina da se lista isprazni iz GUI-ja.

# Cilj

Dugme "Obriši sve" u istom panelu ("Pregled činjenica") koje briše sve
ingestion podatke (runs/snapshots/chunks/candidates/crawl_targets/
checkpoints) za trenutni brend, uz potvrdu (confirm dialog — nepovratna
akcija).

# Ključna bezbjednosna odluka

`approved_facts` tabela se NE dira — već odobrena činjenica ima svoju
KOPIJU teksta (`content` kolona), nezavisnu od sirovih izvornih podataka.
Brisanje sirovih podataka gubi samo duboku provenance vezu (link nazad na
originalni snapshot), ne i sam odobreni tekst koji već može biti u
brand snapshot-u za generisanje kampanje. Ovo je namjeran, dokumentovan
trade-off (vidi docstring `delete_ingestion_data_for_brand`), ne previd.

# Scope

```yaml
allowed_paths:
  - src/ai_campaign_studio/ports/repositories.py                    # nova Protocol metoda
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_ingestion_repository.py  # implementacija
  - src/ai_campaign_studio/presentation/ui_models.py                 # ClearIngestionResultUiModel
  - src/ai_campaign_studio/presentation_webview/bridge/__init__.py   # clear_brand_ingestion
  - src/ai_campaign_studio/presentation_webview/screens/brend/__init__.py  # dugme
  - src/ai_campaign_studio/presentation_webview/static/app.js        # handler + confirm()
  - tests/unit/presentation_webview/bridge/test_clear_brand_ingestion.py  # NOVI
  - agent_reports/ACS-GUI-013-task-contract.md
forbidden_paths:
  - resources/migrations/  # nema nove šeme, samo DELETE nad postojećim tabelama
  - approved_facts tabela (nijedan DELETE ne smije je dirati)
```

# FK-safe redoslijed brisanja (foreign_keys=ON, connection.py)

```
1. capture: SELECT run_id-ove za brand, pa DISTINCT snapshot_id iz
   crawl_targets za te run_id-ove (PRIJE bilo kakvog DELETE-a)
2. DELETE fact_candidates WHERE snapshot_id IN (...)
3. DELETE source_chunks WHERE snapshot_id IN (...)
4. DELETE crawl_targets WHERE run_id IN (...)
5. DELETE source_snapshots WHERE id IN (...)
6. DELETE ingestion_checkpoints WHERE run_id IN (...)
7. DELETE ingestion_runs WHERE brand_id = ?
```

# Acceptance

1. Live provjera (ne samo unit test): ingest pravi URL → candidates>0 →
   clear → candidates==0 → clear ponovo (idempotentno, deleted_run_count=0,
   ne baca grešku) → ingest ponovo → candidates>0 opet.
2. Unit test: validacija (non-dict, nepostojeći brand) vraća
   VALIDATION_ERROR; potvrđeno da `approved_facts` ostaje netaknut kad
   postoji odobrena činjenica.
3. ruff/mypy čisto, node --check čisto.
4. Puna regresija bez novih padova (van poznatog nepovezanog flaky DeepSeek
   testa iz ACS-GUI-012 runde).
