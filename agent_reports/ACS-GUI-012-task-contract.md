---
task_id: ACS-GUI-012
title: "Pregled činjenica — grupisanje po izvornoj stranici (accordion)"
coordinator: claude
implementer: claude
status: "OPEN — kontrakt pisan prije koda, korisnički zahtjev nakon testiranja ACS-GUI-011"
created_at: 2026-09-11
risk: LOW
gitnexus_required: false
adversarial_required: false
---

# Kontekst

Korisnik je testirao ACS-GUI-011 (unos URL-a → ingestion) i prijavio da je
prikaz preuzetih kandidata nepregledan: svaki pasus je poseban red sa
ponovljenim URL-om i sopstvenim dugmićima, BEZ ikakvog CSS stilizovanja
(`fact-review-row` klasa nije imala nijedno pravilo u `app.css` — potvrđeno
grep-om prije izmjene). Korisnik je izabrao "Grupisano po stranici
(accordion)" kao pravac (AskUserQuestion, 3 opcije ponuđene).

# Cilj

Grupisati fact-review kandidate po `snapshot_url` u collapsible sekcije
(accordion), sa čistim redovima unutra (bez ponavljanja URL-a po stavci).
Zadržati POSTOJEĆU semantiku (raw provenance-backed citati za human review —
NE dirati BUILD_FACTS/no-LLM arhitekturu, samo prezentaciju).

# Scope

```yaml
allowed_paths:
  - src/ai_campaign_studio/presentation_webview/static/app.js   # renderRows/bindRowButtons prepravka
  - src/ai_campaign_studio/presentation_webview/static/app.css  # nove .fact-group* klase
  - tests/unit/presentation_webview/screens/test_brend_review_ui.py  # novi test za grupisanje
  - agent_reports/ACS-GUI-012-task-contract.md
forbidden_paths:
  - src/ai_campaign_studio/presentation_webview/bridge/           # get_ingestion_review se ne mijenja, isti shape
  - src/ai_campaign_studio/application/                            # nema logičke izmjene, samo prikaz
```

# Šta NE SMIJE

- Ne dodavati LLM sažimanje/sintezu sadržaja — ostaje raw citat po stavci,
  samo grupisan.
- Ne mijenjati `get_ingestion_review` DTO shape (frontend-only izmjena).
- Ne dirati approve/reject/assemble logiku — samo vizuelni kontejner oko
  postojećih dugmića.

# Acceptance

1. Kandidati sa istim `snapshot_url` se prikazuju pod JEDNIM header-om sa
   brojem stavki; URL se NE ponavlja po stavci.
2. Klik na header sekcije skladi/otvara sadržaj (collapsed stanje se
   pamti po URL-u dok je stranica otvorena, ne resetuje se poslije
   approve/reject reload-a iste liste).
3. Postojeći `test_brend_review_ui.py` testovi (XSS escaping, counts,
   approve-click→reload) i dalje PASS bez izmjene (markup restrukturiran,
   ali `escapeHtml` i selektori ostaju isti).
4. Novi test: 2 kandidata sa istim URL-om + 1 sa drugim → 2 grupe, prva
   sa "2 stavke", druga sa "1 stavka"; URL se pojavljuje TAČNO jednom po
   grupi (u header-u), ne po stavci.
5. `node --check app.js`, ciljani testovi PASS.
