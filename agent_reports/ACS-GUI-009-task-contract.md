---
task_id: ACS-GUI-009
phase: Faza-1 (post ACS-GUI-007 / post G10 PASS)
title: "Pregled i izvoz: stvaran vizuelni sistem + layout + render + ZIP export preko postojećeg pipeline-a"
risk: HIGH
coordinator: claude
implementer: TBD
reviewers: [claude, codex]
status: "OPEN -- contract written before code, čeka implementera"
created_at: 2026-09-06
dependencies:
  - ACS-GUI-005/006/007 (merged) -- bridge composition pattern
  - ACS-GUI-008 (paralelno, ne blokira -- vidi Coordination)
allowed_paths:
  - src/ai_campaign_studio/presentation_webview/bridge/__init__.py
  - src/ai_campaign_studio/presentation_webview/screens/pregled_izvoz/__init__.py
  - src/ai_campaign_studio/presentation_webview/static/app.js
  - src/ai_campaign_studio/presentation/contracts.py
  - src/ai_campaign_studio/presentation/ui_models.py
  - tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py
  - tests/unit/presentation_webview/test_pregled_izvoz_ssr.py
  - tests/unit/presentation/test_contracts.py
  - tests/unit/presentation/test_ui_models.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/infrastructure/
  - resources/migrations/
  - src/ai_campaign_studio/presentation_webview/screens/studio_sadrzaja/
gitnexus_required: true
adversarial_required: true
gitnexus:
  required: true
  note: >
    Koordinator MORA pokrenuti impact provjeru na
    `GenerateVisualSystem`, `PlanPostLayout` i `ExportCampaign` prije
    merge-a -- ovaj task ih PRVI PUT poziva iz GUI konteksta.
    `ExportCampaign` posebno: već je mijenjan 3x (ACS-F1-034/036/039),
    treći put dobio OBAVEZAN `performance_repo` parametar -- provjeriti
    da bridge poziva TAČAN, TRENUTNI 7-parametarski konstruktor, ne
    stariju verziju iz sjećanja/dokumentacije.
---

# Kontekst

Isti stub-status kao ACS-GUI-008, ali za `pregled_izvoz` ekran:
"Odobri kampanju" i "Izvezi ZIP paket" su `data-action="toast"`
stubovi (`presentation_webview/screens/pregled_izvoz/__init__.py`,
doslovni komentar u kodu: "real approve/export pipeline is G10+
scope"). G10 je sada PASS (2026-09-05) -- ovaj task je taj odgođeni
"G10+ scope" posao.

**Pun lanac koji već postoji i radi** (svaki dio testiran,
korišten u `ExportCampaign`-ovim integration testovima), ali NIKAD
pozvan iz GUI-ja:

```text
GenerateVisualSystem.execute(plan_id) -> (CampaignVisualSystem, LayoutSpec)
    (zahtijeva APPROVED plan -- već tačno stanje nakon ACS-GUI-008)
PlanPostLayout.execute(content_piece_id, visual_system_id, plan_id) -> LayoutSpec
    (jednom PO content piece-u koji još nema layout)
ExportCampaign(...7 portova uključujući performance_repo...)
    .execute(campaign_id, plan_id, visual_system_id, output_zip_path) -> ExportResult
    (interno zove RenderPost po piece-u, piše manifest.json,
    SADA i snima DistributionInstance po piece-u -- ACS-F1-039/041)
```

`GenerateVisualSystem` i `PlanPostLayout` OBA zahtijevaju `ai_port`
(stvaran AI poziv) -- isti provider-resolution obrazac kao postojeće
bridge metode. `ExportCampaign` NE zahtijeva AI (čist orkestrator nad
već postojećim podacima).

**"Odobri kampanju" dugme -- redefinicija, review MORA potvrditi.**
ACS-GUI-008 čini plan-approval TRANSPARENTNIM (dešava se automatski
kad se sadržaj generiše, korisnik ga ne vidi kao poseban klik). Do
trenutka kad korisnik stigne na "Pregled i izvoz", plan je VEĆ
APPROVED. Ovaj task stoga NE zove `ApproveCampaignPlan` ponovo (već je
odrađeno) -- "Odobri kampanju" dugme se preimenuje/repurpose-uje kao
korisnikova POTVRDA da je pregledao sadržaj PRIJE nego što se pokrene
export (npr. omogućava "Izvezi" dugme tek nakon klika na "Odobri", bez
ikakvog backend poziva -- čisto UI gating). Implementer dokumentuje
tačnu odluku u kodu; reviewer provjerava da nije slučajno pokušano
pozvati nepostojeći/pogrešan use-case pod tim dugmetom.

# Objective

## 1. Nova `js_api` metoda: `export_campaign_package(raw_payload: dict) -> dict`

- Ulaz: `{"campaign_id": "<str>"}`.
- Koraci (isti try/except-po-koraku, nikad ne puca u JS):
  1. Učitati kampanju + APPROVED plan. Ako plan nije APPROVED
     (korisnik nekako stigao ovdje bez ACS-GUI-008 koraka) ->
     `VALIDATION_ERROR` sa jasnom porukom ("Sadržaj još nije
     generisan.").
  2. Provjeriti da li `CampaignVisualSystem` već postoji za ovaj plan
     (`visual_repo.get_visual_system_by_plan` ili ekvivalent -- provjeri
     tačnu postojeću metodu u `VisualRepositoryPort`). Ako NE postoji,
     provajder resolution (PONOVO ISKORISTITI
     `self._resolve_provider()`) + `GenerateVisualSystem.execute(
     plan_id)`. Ako VEĆ postoji, preskoči (idempotentno -- drugi klik
     ne pravi drugi vizuelni sistem).
  3. Za SVAKI `ContentPiece` u kampanji BEZ postojećeg `LayoutSpec-a`
     (provjeri `visual_repo.get_layout_spec_by_content_piece`), pozvati
     `PlanPostLayout.execute(piece.id, visual_system.id, plan_id)`.
     Isti djelimičan-neuspjeh princip kao ACS-GUI-008 (jedan AI poziv
     ne smije srušiti cijelu petlju) -- ALI `ExportCampaign` već ima
     SVOJ skip-mehanizam za piece-ove bez layout-a
     (`RenderPost`/`_render_one_piece` hvata `EntityNotFound` i
     preskače), pa provjeri da li je JEDNOSTAVNIJE pustiti
     `ExportCampaign` da sam preskoči nedostajuće layout-e nego
     unaprijed ih svе generisati ovdje -- IMPLEMENTER ODLUČUJE i
     DOKUMENTUJE, oba pristupa su legitimna, ali VOLIMO manje koda ako
     `ExportCampaign` već rješava slučaj.
  4. `ExportCampaign(...).execute(campaign_id, plan_id,
     visual_system.id, output_zip_path)` -- `output_zip_path` ide u
     predvidljivu lokaciju: `AppPaths().data_dir / "exports" /
     f"{campaign_id}.zip"` (kreirati `exports/` direktorij ako ne
     postoji). Ne otvarati file-picker dijalog u ovom tasku (deferred
     polish) -- korisnik dobija APSOLUTNU putanju u rezultatu.
  5. Konstruisati SVE portove koje `ExportCampaign` traži -- provjeri
     TRENUTAN konstruktor u `application/export/export_campaign.py`
     (7 parametara, uključujući `performance_repo:
     PerformanceRepositoryPort`, dodat u ACS-F1-039) prije pisanja
     koda, NE osloniti se na stariji broj parametara.
- Povratna vrijednost: nov `ExportCampaignResultUiModel` -- `ok`,
  `campaign_id`, `zip_path`, `exported_count`, `skipped_count`,
  `error_code`, `error_message`.

## 2. `pregled_izvoz/__init__.py` -- stvarno povezivanje

- "Izvezi ZIP paket" dugme poziva `export_campaign_package`, prikazuje
  STVARAN `zip_path`/`exported_count` (ne fixture).
- "Odobri kampanju" dugme -- UI-only gating (Kontekst sekcija), bez
  backend poziva. Ne uklanjati dugme, samo mu promijeniti ulogu +
  toast tekst da odražava novu semantiku.
- Content-card grid (postojeći `ContentPreviewItem` fixture prikaz)
  po želji može ostati fixture-based u ovom tasku AKO povezivanje
  stvarnog sadržaja tu zahtijeva prevelik dodatan scope -- implementer
  dokumentuje odluku; PRIORITET je da "Izvezi" STVARNO radi, ne da
  svaki vizuelni detalj postane live.

## 3. `presentation/contracts.py` + `ui_models.py`

Isti obrazac kao ACS-GUI-008 Objective #3, za
`export_campaign_package`.

# Implementation steps

1. Bridge metoda (Objective #1) + jedinični testovi: happy path (2+
   piece-a, svi imaju layout i renderuju), djelimičan skip (1 piece
   bez payload-a -- `skipped_count=1`), vizuelni sistem već postoji
   (drugi klik ne duplira), plan nije APPROVED (`VALIDATION_ERROR`),
   nijedan provajder (`NO_PROVIDER_CONFIGURED`).
2. `contracts.py`/`ui_models.py` dopuna + testovi.
3. `pregled_izvoz/__init__.py` + `app.js` povezivanje + SSR test
   dopuna.
4. Integration test: STVARNA SQLite baza + `FakeAiPort`/deterministic
   test double (NE pravi provider poziv) + `PillowRenderer` (pravi,
   deterministički, brz) -- pun `export_campaign_package` lanac,
   potvrditi ZIP STVARNO postoji na disku, sadrži očekivane fajlove
   (`manifest.json`, `content-01/feed.png`, itd.), i
   `DistributionInstance` redovi STVARNO snimljeni (round-trip preko
   `performance_repo` -- isti standard kao ACS-F1-039/041 review).

# Acceptance

- [ ] `export_campaign_package` postoji, poziva
      `GenerateVisualSystem` (idempotentno) + `PlanPostLayout` (po
      potrebi) + `ExportCampaign` sa TAČNIM trenutnim potpisom (7
      portova).
- [ ] ZIP se STVARNO piše na disk, na predvidljivu putanju, putanja se
      vraća korisniku.
- [ ] Duplo pozivanje NE pravi duplikat `CampaignVisualSystem`.
- [ ] Plan-nije-APPROVED slučaj daje jasnu poruku, ne pucanje.
- [ ] Nijedan izuzetak ne izlazi u JS.
- [ ] `domain/`, `application/`, `ports/`, `infrastructure/`,
      `resources/migrations/`, `studio_sadrzaja/` NISU DIRANI.
- [ ] `python -m pytest tests/unit/presentation_webview/ tests/unit/presentation/ -v` prolazi.
- [ ] `python -m pytest -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.
- [ ] **CI provjeren preko PR-a.**

# Verification

```bash
python -m pytest tests/unit/presentation_webview/ tests/unit/presentation/ -v
python -m pytest -q
python -m ruff check .
python -m mypy src

git push -u origin task/ACS-GUI-009-pregled-izvoz-export
gh pr create --base main --title "ACS-GUI-009: Pregled i izvoz -- stvaran export"
gh pr checks
```

# Review focus -- Claude + Codex (adversarial)

- GitNexus impact na `GenerateVisualSystem`/`PlanPostLayout`/
  `ExportCampaign` STVARNO pokrenut prije merge-a.
- `ExportCampaign` konstruktor STVARNO ima svih 7 trenutnih parametara
  (uključujući `performance_repo`) -- najlakše mjesto da implementer
  greškom koristi stariji, memorisan potpis.
- ZIP fajl STVARNO otvoren i provjeren (integration test, ne samo
  "poziv nije pukao").
- `DistributionInstance` redovi STVARNO snimljeni preko GUI-poziva
  (round-trip test) -- ovo je PRVI put da export ide preko GUI-ja,
  treba isti standard provjere kao ACS-F1-039.
- Idempotentnost vizuelnog sistema STVARNO testirana.
- Codex adversarial runda po HIGH-risk standardu.

# Rollback

HIGH risk -- prvi put da GUI poziva `GenerateVisualSystem`/
`PlanPostLayout`/`ExportCampaign` (stvaran AI poziv + stvaran fajl na
disku + stvaran DB write), plus dijeli `bridge/__init__.py` sa
paralelnim ACS-GUI-008 taskom (vidi Coordination). Pun review ciklus
prije merge-a.

# Coordination

Zavisi od ACS-GUI-005/006/007 (mergovano). **Radi se PARALELNO sa
ACS-GUI-008** -- oba diraju `bridge/__init__.py`/`contracts.py`/
`ui_models.py`. Prvi koji završi merguje se prvo; drugi implementer
rebase-uje na svježi main prije otvaranja PR-a (koordinator
eksplicitno upozorava implementera na ovo pri predaji kontrakta).
FUNKCIONALNO, ACS-GUI-009 pretpostavlja da je sadržaj VEĆ generisan
(ACS-GUI-008 uradio svoj dio) -- ako se testira END-TO-END prije nego
oba mergovana, implementer može ručno generisati sadržaj preko
postojećih integration-test helper-a (isti obrazac kao
`test_export_campaign_integration.py`) da ne čeka na ACS-GUI-008.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-GUI-009-pregled-izvoz-export
Branch:   task/ACS-GUI-009-pregled-izvoz-export
Base:     main @ 0595912
```
