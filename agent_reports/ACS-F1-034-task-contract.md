---
task_id: ACS-F1-034
phase: Faza-1 (post A14) — A15, ZIP EXPORT + TELEMETRY SUMMARY (plan sekcija 46)
title: "ExportCampaign: ZIP export (campaign.json + per-post PNG/caption/content.json + ai_summary.json)"
risk: MEDIUM
coordinator: claude
implementer: TBD
reviewers: [claude]
status: "OPEN — contract written before code, čeka implementera"
created_at: 2026-09-05
dependencies: [ACS-F1-033]
allowed_paths:
  - src/ai_campaign_studio/ports/export.py
  - src/ai_campaign_studio/infrastructure/export/__init__.py
  - src/ai_campaign_studio/infrastructure/export/zip_exporter.py
  - src/ai_campaign_studio/application/export/__init__.py
  - src/ai_campaign_studio/application/export/export_campaign.py
  - tests/unit/ports/test_export.py
  - tests/unit/infrastructure/export/test_zip_exporter.py
  - tests/unit/application/export/test_export_campaign.py
  - tests/integration/application/export/test_export_campaign_integration.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/ports/repositories.py
  - src/ai_campaign_studio/ports/rendering.py
  - src/ai_campaign_studio/application/schemas/
  - resources/migrations/
  - src/ai_campaign_studio/application/campaigns/
  - src/ai_campaign_studio/application/posts/
  - src/ai_campaign_studio/application/visual/
  - src/ai_campaign_studio/application/rendering/
  - src/ai_campaign_studio/application/evaluation/
  - src/ai_campaign_studio/infrastructure/rendering/
gitnexus_required: true
adversarial_required: false
gitnexus:
  required: true
  note: >
    Nov port (`ports/export.py`), prvi pozivalac koji KOMPONUJE
    `RenderPost` (ACS-F1-033) unutar drugog use-case-a (isti obrazac kao
    `run_system_b.py` koji interno konstruiše `GenerateCampaignPlan`/
    `ApproveCampaignPlan`/`GenerateSocialPost` iz sirovih portova — NE
    prima gotove use-case objekte kao konstruktorske zavisnosti).
    Koordinator pokreće detect-changes/impact prije merge-a (GitNexus MCP
    dostupan, indeks stale — re-index prije provjere).
  repository: "H:\\AI Campaing Studio"
  branch: main
  head: 9e693b0
  scope_fit: "PENDING — popuniti kad se GitNexus indeks osvježi prije merge-a."
---

# Kontekst

A14 je potpuno gotov (renderer stvarno piše PNG na disk). A15 je
POSLJEDNJI application-layer komad plan sekcije-po-sekciju prije nego
što G10 evaluacija (A19 puna vertical slice, A20 exit evaluation) uopšte
postane izvodljiva — export je ono što A16 (A/B harness) NIJE testirao
(A16 je namjerno stao na deterministic metrics + human-eval paket, bez
render/export prezentacije, per ACS-F1-026 scope odluka).

**Istraženo prije pisanja kontrakta** (isti disciplinovan pristup kao za
sve prethodne A13/A14 taskove):

1. **Nijedan port ne treba novu metodu.** `ContentRepositoryPort.list_campaign_content`,
   `CampaignRepositoryPort.get_campaign/get_brief/get_plan`,
   `VisualRepositoryPort.get_visual_system`,
   `RevisionRepositoryPort.list_entity_revisions` — SVE VEĆ POSTOJE i
   pokrivaju sve što ovaj task treba READ-ONLY. Zato `forbidden_paths`
   uključuje `ports/repositories.py` — ovaj task ga NE treba dirati.
2. **AI telemetry je STVARNO ograničena na ono što je perzistovano.**
   `AIResponse`/`AITelemetry` (ports/ai.py) nose `input_tokens`/
   `output_tokens`/`latency_ms`, ALI **samo `generate_social_post.py` i
   `revise_content_piece.py` ikad snime `Revision` red sa
   `provider`/`model`** (grep potvrđen) — `GenerateCampaignPlan` i
   `GenerateVisualSystem`/`PlanPostLayout` NE perzistuju NIŠTA
   telemetrijsko. `Revision` tabela SAMA nema `input_tokens`/
   `output_tokens`/`latency_ms` kolone uopšte (samo `provider`/`model`/
   `prompt_version`/`instruction`). **Zaključak**: `telemetry/ai_summary.json`
   za ovaj task MOŽE SAMO agregirati provider/model brojeve po
   `ContentPiece` revizijama (koliko AI poziva, koji provideri/modeli) —
   NE token/cost/latency brojke (te NE POSTOJE nigdje u bazi). Ovo je
   POŠTENO ograničenje, ne propust — izmišljanje token brojki koje
   sistem nikad nije zabilježio bilo bi suprotno cijelom "fact-first/
   provenance" principu ovog projekta. Postoji i `TelemetryRepositoryPort`
   ("Future analytics telemetry sink (Slice 1.5)") — EKSPLICITNO
   označen za budućnost, NE dirati ga ovdje.
3. **Nema "trenutni plan/visual_system za kampanju" lookup-a.** Isti
   obrazac kao `PlanPostLayout`/`RenderPost` (ACS-F1-031/033) —
   `plan_id`/`visual_system_id` idu kao EKSPLICITNI parametri
   `execute()`-u, ne izmišljati novi port metod.
4. **`export_campaign.py` NE smije direktno importovati
   `infrastructure/export/`** (AR1: application → infrastructure je
   pogrešan smjer). Zato nov, minimalan `ports/export.py`
   (`ExportWriterPort` sa JEDNOM metodom) — čak i kad postoji samo JEDAN
   implementator (stdlib `zipfile`), isti obrazac kao SVAKA druga
   infrastruktura u ovom projektu (AI/prompts/rendering/repositories —
   sve ide kroz port, bez izuzetka).
5. **`ExportCampaign` interno konstruiše `RenderPost`** iz sirovih
   portova (`content_repo`, `campaign_repo`, `visual_repo`, `renderer`),
   isti obrazac kao `run_system_b.py` (koji interno konstruiše
   `GenerateCampaignPlan`/`ApproveCampaignPlan`/`GenerateSocialPost`) —
   NE prima gotov `RenderPost` objekat kao konstruktorsku zavisnost.

# Objective

## 1. `ports/export.py`

```python
class ExportWriterPort(Protocol):
    def write_zip(self, output_path: str, files: dict[str, bytes]) -> None: ...
```

`files` ključ = arcname unutar ZIP-a (npr. `"campaign.json"`,
`"content-01/feed.png"`), vrijednost = sirovi bajtovi. Namjerno JEDNA,
minimalna metoda — nema potrebe za bogatijim interfejsom dok se ne
pokaže potreba.

## 2. `infrastructure/export/zip_exporter.py` — `ZipExportWriter`

Implementira `ExportWriterPort` preko stdlib `zipfile.ZipFile` (mode
`"w"`, `ZIP_DEFLATED`). Kreira roditeljski direktorijum ako ne postoji.

## 3. `application/export/export_campaign.py` — `ExportCampaign`

```python
class ExportCampaign:
    def __init__(
        self,
        campaign_repo: CampaignRepositoryPort,
        content_repo: ContentRepositoryPort,
        visual_repo: VisualRepositoryPort,
        revision_repo: RevisionRepositoryPort,
        renderer: RendererPort,
        export_writer: ExportWriterPort,
    ) -> None: ...

    def execute(
        self,
        campaign_id: CampaignId,
        plan_id: CampaignPlanId,
        visual_system_id: VisualSystemId,
        output_zip_path: str,
    ) -> ExportResult: ...
```

`ExportResult` (lokalan dataclass u istom fajlu, ne u portu):
```python
@dataclass(frozen=True)
class ExportResult:
    zip_path: str
    exported_content_piece_ids: tuple[PostId, ...]
    skipped_content_piece_ids: tuple[PostId, ...]
```

### Tok

1. `campaign_repo.get_campaign(campaign_id)` → `EntityNotFound` ako `None`.
2. `campaign_repo.get_brief(campaign.brief_id)` → `EntityNotFound` ako `None`.
3. `campaign_repo.get_plan(plan_id)` → `EntityNotFound` ako `None`;
   `plan.campaign_id != campaign_id` → `InvariantViolation` (plan mora
   pripadati ovoj kampanji).
4. `visual_repo.get_visual_system(visual_system_id)` → `EntityNotFound`
   ako `None`.
5. `content_repo.list_campaign_content(campaign_id)` — svi ContentPiece
   za kampanju.
6. Sortirati pieces po `order` NJIHOVOG `CampaignItem`-a (lookup preko
   `plan.items`, mapirano po `id`) — NE po arbitrarnom redoslijedu
   povratne vrijednosti repozitorijuma.
7. Za svaki piece REDOM:
   - Ako `piece.payload is None` → dodati u `skipped_content_piece_ids`,
     PRESKOČITI (nema teksta za export).
   - Konstruisati interni `RenderPost(content_repo, campaign_repo,
     visual_repo, renderer)`, pozvati `.execute(piece.id,
     visual_system_id, <temp PNG putanja preko `tempfile`>)`.
     - Ako `RenderPost` baci `EntityNotFound` (nema `LayoutSpec` za taj
       piece — nikad nije prošao kroz `PlanPostLayout`) → uhvatiti
       SPECIFIČNO taj izuzetak, dodati piece u
       `skipped_content_piece_ids`, PRESKOČITI (post nije spreman za
       export). NE hvatati generičan `Exception` — samo
       `EntityNotFound`.
   - Pročitati PNG bajtove sa temp putanje.
   - Dodijeliti folder ime `content-{NN}` (NN = dvocifren redni broj
     PO REDOSLIJEDU IZ KORAKA 6, počevši od `01`, RAČUNAJUĆI SAMO
     eksportovane — ne preskočene — piece-ove).
   - Sastaviti `content-{NN}/content.json` (id, campaign_item_id,
     target(channel/platform_code/format_code), payload
     (headline/caption/hook/body/cta/hashtags), status, claims
     (id/text/type/status/reason_codes/fact_ids), render_status
     (`RenderResult.status.value`), render_warnings
     (`RenderResult.warnings`), created_at/updated_at).
   - Sastaviti `content-{NN}/caption.txt` (plain tekst,
     `piece.payload.caption`).
   - `content-{NN}/feed.png` = pročitani PNG bajtovi.
8. Agregirati telemetriju: za SVAKI eksportovani (ne preskočen) piece,
   `revision_repo.list_entity_revisions("ContentPiece", piece.id)`,
   prikupiti `(provider, model)` parove. `telemetry/ai_summary.json`:
   ```json
   {
     "content_piece_count": <broj eksportovanih>,
     "ai_call_count": <ukupan broj revizija sa provider+model>,
     "providers_used": ["google", "openai", ...],
     "models_used": ["gemini-2.5-flash", ...],
     "note": "Token/cost/latency metrike nisu dostupne — trenutno se ne
              perzistuju nigdje u sistemu (vidi Revision šemu). Ovo NIJE
              propust ovog exporta, nego postojeće ograničenje sistema."
   }
   ```
9. Sastaviti `campaign.json` (campaign_id, brand_snapshot_id, brief
   [offer/goal/audience_text/content_piece_count/content_language_context],
   plan_version=`plan.version`, visual_system_id,
   content_piece_ids=[SAMO eksportovani, ISTIM redoslijedom kao folderi],
   created_at=`campaign.created_at`, exported_at=`utc_now()`). **Nema
   API ključeva niti bilo kakvog secret-a nigdje u ovom objektu** (plan
   doslovno: "Ne uključivati API ključeve" — trivijalno zadovoljeno jer
   ništa ovdje ne dotiče `SecretStore`/keyring).
10. `export_writer.write_zip(output_zip_path, files)` gdje `files` ima
    SVE gore sastavljene unose (`campaign.json`, `content-{NN}/*` za
    svaki eksportovan piece, `telemetry/ai_summary.json`).
11. Vratiti `ExportResult`.

# Implementation steps

1. `ports/export.py` po Objective #1.
2. `infrastructure/export/zip_exporter.py` po Objective #2 — testirati
   IZOLOVANO prvo (pravi `zipfile`, tmp_path, provjeriti round-trip).
3. `application/export/export_campaign.py` po Objective #3 — NAJVEĆI
   dio posla.
4. Testovi:
   - `test_export.py` (unit, port shape — isti stil kao `test_rendering.py`).
   - `test_zip_exporter.py` (unit, pravi `zipfile`): `write_zip` sa 2-3
     unosa → otvoriti nazad preko `zipfile.ZipFile`, potvrditi imena i
     sadržaj bajt-za-bajt identični ulazu; prazan `files` dict → validan
     prazan ZIP (ne izuzetak); roditeljski direktorijum se kreira ako ne
     postoji.
   - `test_export_campaign.py` (unit, fake portovi + fake renderer +
     fake export_writer): happy path 2 pieces → `write_zip` pozvan sa
     `campaign.json` + `content-01/*` + `content-02/*` +
     `telemetry/ai_summary.json` (provjeriti TAČNE ključeve, ne samo
     broj), redoslijed foldera prati `CampaignItem.order` (test sa
     pieces ubačenim NASUMIČNIM redoslijedom u fake repo, provjeriti da
     su foldiri IPAK ispravno numerisani po order-u); piece bez
     `payload` → preskočen, NIJE u ZIP-u, JESTE u
     `skipped_content_piece_ids`; piece čiji `RenderPost` baci
     `EntityNotFound` (nema layout spec) → preskočen isto; `plan.campaign_id`
     ne odgovara `campaign_id` → `InvariantViolation`; 4 GENUINE odvojena
     "entity not found" scenarija (campaign/brief/plan/visual_system —
     isti standard kao ACS-F1-029/031, ne spajati grane).
   - `test_export_campaign_integration.py` (integration, prava SQLite +
     stvaran `PillowRenderer` + stvaran `ZipExportWriter`): PUN lanac
     fixture→brief→plan→approve→`GenerateSocialPost`×2→`GenerateVisualSystem`→
     `PlanPostLayout`×2→`ExportCampaign` → OTVORITI stvaran ZIP preko
     `zipfile.ZipFile`, potvrditi: `campaign.json` postoji i parsira se,
     SADRŽI `content_piece_ids` sa tačno 2 unosa, `content-01/feed.png`
     postoji i > 0 bajtova (pravi PNG, ne prazan fajl), `content-01/caption.txt`
     sadrži tačan tekst, `content-01/content.json` parsira se,
     `telemetry/ai_summary.json` parsira se i sadrži `provider`/`model`
     iz stvarnog fake AI porta korištenog u lancu.

# Acceptance

- [ ] `ExportWriterPort` postoji sa jednom metodom (`write_zip`).
- [ ] `ZipExportWriter` piše STVARAN, validan ZIP (round-trip test).
- [ ] `ExportCampaign` NE dira `ports/repositories.py` (git diff dokaz —
      sve postojeće read metode su dovoljne).
- [ ] Folder numeracija (`content-01`, `content-02`, ...) prati
      `CampaignItem.order`, NE arbitraran redoslijed iz repozitorijuma.
- [ ] Piece bez `payload` → preskočen (ne u ZIP-u), zabilježen u
      `skipped_content_piece_ids`.
- [ ] Piece bez `LayoutSpec` (RenderPost `EntityNotFound`) → preskočen
      isto, uhvaćen SPECIFIČNO (ne generičan `except Exception`).
- [ ] `campaign.json` NE sadrži nijedno polje sa API ključem/secret-om
      (trivijalno — provjeriti da se ni `SecretStore` ni keyring
      import ne pojavljuju nigdje u ovom tasku).
- [ ] `telemetry/ai_summary.json` sadrži SAMO provider/model agregaciju
      (broj poziva, distinct provideri/modeli) + eksplicitnu napomenu
      da token/cost/latency NISU dostupni — NE izmišljene brojke.
- [ ] 4 GENUINE odvojena "entity not found" scenarija (campaign/brief/
      plan/visual_system) — isti standard kao ranije, ne spajati grane.
- [ ] Integration test STVARNO otvara pravi ZIP preko `zipfile.ZipFile`
      i provjerava stvaran sadržaj (ne samo da `execute()` ne baca
      izuzetak).
- [ ] `domain/`, `ports/repositories.py`, `ports/rendering.py`,
      `application/schemas/`, `resources/migrations/`,
      `application/campaigns/`, `application/posts/`,
      `application/visual/`, `application/rendering/`,
      `application/evaluation/`, `infrastructure/rendering/` NISU DIRANI.
- [ ] `python -m pytest tests/unit/ports/test_export.py tests/unit/infrastructure/export/ tests/unit/application/export/ tests/integration/application/export/ -v`
      prolazi.
- [ ] `python -m pytest tests -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema nove eksterne zavisnosti (stdlib `zipfile`/`tempfile`/`json`
      su dovoljni).
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest tests/unit/ports/test_export.py -v
python -m pytest tests/unit/infrastructure/export/ -v
python -m pytest tests/unit/application/export/ -v
python -m pytest tests/integration/application/export/ -v
python -m pytest tests -q
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- OTVORITI stvaran ZIP iz integration testa ručno (`zipfile.ZipFile`,
  `.namelist()`, pročitati par unosa) — ne vjerovati "export uspio" bez
  stvarnog pregleda sadržaja;
- folder-numeracija STVARNO prati `CampaignItem.order`, ne slučajno
  ispravna zbog test-podataka koji se poklapaju sa oba redoslijeda
  (test MORA namjerno pomiješati redoslijed da ovo dokaže);
- `telemetry/ai_summary.json` STVARNO ne izmišlja token/cost brojke —
  provjeriti da nema fabrikovanih polja;
- skip-logika (payload=None, LayoutSpec nedostaje) hvata SPECIFIČNE
  izuzetke, ne generičan `except Exception` koji bi sakrio prave bug-ove;
- `ports/repositories.py` STVARNO nedirnut (ovaj task ne treba nove
  read metode — ako implementer doda jednu, pitati ZAŠTO postojeće nisu
  dovoljne prije prihvatanja);
- `export_campaign.py` NE importuje `infrastructure/export/` direktno
  (AR1 provjera — mora ići kroz `ExportWriterPort`).

# Rollback

MEDIUM risk — nov port + nova infrastructure adapter + nov use-case koji
KOMPONUJE postojeći `RenderPost`, nema domain/postojeći-port izmjene,
nema nove zavisnosti. Fix na istoj branch bez proširenja scope-a. §29:
Claude-only review, PASS → odmah merge.

# Coordination

Zavisi od ACS-F1-033 (mergovano) — UNBLOCKED. Nakon ovog taska, plan
sekcije 39-46 (A13-A15) su POTPUNO gotove u kodu. Sljedeći korak ka
`G10 Vertical Slice PASS`: **A19** (puna vertical slice integracija —
fixture→brief→plan→approval→posts→validation→render→export, sve u JEDNOM
toku, dokaz da nema ručnog DB editovanja/hidden CLI bypass-a) i **A20**
(exit evaluation — više A16 runova, Kill/Pivot/Proceed odluka) — ovo
NIJE novi kod nego koordinatorova live end-to-end provjera + Human Owner
odluka, isti obrazac kao live A16 poređenje ranije ovog session-a.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-034-export-campaign
Branch:   task/ACS-F1-034-export-campaign
Base:     main @ 9e693b0
```
