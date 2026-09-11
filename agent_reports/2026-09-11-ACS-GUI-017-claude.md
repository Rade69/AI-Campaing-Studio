# ACS-GUI-017 — masovne akcije (bulk odobri/odbij) za pregled činjenica

**Datum:** 2026-09-11
**Agent:** Claude
**Povod:** korisnik prijavio da je pregled od 210 kandidata (104+104+2 po
stranici, sitni bullet-fragmenti) neupotrebljiv — nemoguće ručno kliknuti
"Odobri"/"Odbij" 100+ puta. AskUserQuestion → korisnik izabrao "Masovne
akcije" kao prioritet (nad spajanjem fragmenata ili potpunim redizajnom).

## Šta je urađeno

1. **Backend** (`bulk_review_fact_candidates`, novi bridge metod):
   `{candidate_ids: [...], action: "approve"|"reject"}` — petlja postojeće
   `ApproveFactCandidate`/`RejectFactCandidate` use-case-ove (NEMA nove
   domain logike). Svaki id je nezavisan — jedan već-odlučen ili nepostojeći
   kandidat ne prekida ostatak batch-a; vraća `succeeded_count`/
   `failed_count`, ne all-or-nothing.
2. **Frontend**: checkbox po PROPOSED stavci, "select all" checkbox po
   grupi (samo ako grupa ima PROPOSED stavki), sticky traka na vrhu koja se
   pojavljuje čim je bar jedna stavka označena — "Odobri označeno" /
   "Odbij označeno" sa live brojačem.

## Verifikacija

```
Live end-to-end na PRAVIM podacima (kingdomdoo.com/en/, 210 kandidata):
  bulk approve 105 → succeeded=105 failed=0
  bulk reject  105 → succeeded=105 failed=0
  review poslije: approved_count=105, rejected_count=105
  ponovni bulk approve ISTIH 105 (idempotencija/partial-failure provjera):
    → succeeded=0 failed=105, ok=True (ne puca, ne prekida batch)

Integration test (test_bulk_review_fact_candidates_flow.py, seed pattern
isti kao test_clear_brand_ingestion_flow.py): 5/5 PASS
  - validacija (non-dict, nepoznat action, prazna lista)
  - approve 3 + reject 2 od 5 → tačni counts u get_ingestion_review
  - re-approve već odlučenih → svih 5 failed, ok=True
  - nepoznat candidate_id u batch-u → broji se kao failed, ne ruši batch

Node-VM markup test (test_bulk_checkboxes_render_for_proposed_only):
  2 PROPOSED (ista grupa) → 2 checkbox-a, 1 select-all
  1 APPROVED → bez checkbox-a
  (napomena: fake DOM ne parsira innerHTML u živo stablo, pa je
  interaktivni tok — klik→selekcija→bulk poziv — pokriven integration
  testom protiv prave baze, ne ovim markup testom)

ruff/mypy: čisto, node --check: čisto
pytest (presentation_webview + ingestion): 382/382 PASS
pytest (puna regresija): 1554 passed, 0 failed, 462.88s
```

## Kako testirati

Zatvori stari prozor i pokreni ponovo:
```
cd "H:\AI Campaing Studio"
$env:PYTHONPATH = "H:\AI Campaing Studio\src"
.venv\Scripts\python.exe -m ai_campaign_studio.presentation_webview
```
Brend → Pregled činjenica → ingestuj `https://kingdomdoo.com/en/` (ili bilo
šta drugo) → klikni "select all" checkbox na vrhu grupe → pojavljuje se
traka "N označeno" → "Odobri označeno" bulk-odobrava sve odjednom.

## Šta NIJE urađeno (druge dvije opcije iz AskUserQuestion)

- **Spajanje sitnih fragmenata** (104 bullet-a → par smislenih cjelina) —
  NIJE urađeno, korisnik je izabrao masovne akcije kao prioritet. I dalje
  dostupno kao follow-up ako se ispostavi da je i dalje potrebno.
- Sadržaj kandidata (npr. "- Recommendation systems...") ostaje sirov citat
  1:1 iz stranice — namjerno, fact-first/no-LLM princip nije diran.
