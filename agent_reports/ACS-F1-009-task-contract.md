---
task_id: ACS-F1-009
phase: Faza-1
title: "A9 — CreateCampaign + GenerateCampaignPlan use-cases (mock-adapter pipeline)"
risk: MEDIUM
coordinator: claude
implementer: TBD (Human Owner assigns)
reviewers: [claude]
status: "OPEN — contract written before code"
created_at: 2026-09-02
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/application/campaigns/__init__.py
  - src/ai_campaign_studio/application/campaigns/create_campaign.py
  - src/ai_campaign_studio/application/campaigns/generate_campaign_plan.py
  - src/ai_campaign_studio/application/mappers/campaign_brief_mapper.py
  - src/ai_campaign_studio/ports/repositories.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_campaign_repository.py
  - tests/unit/application/campaigns/
  - tests/unit/application/mappers/test_campaign_brief_mapper.py
  - tests/integration/application/campaigns/
  - tests/integration/database/repositories/test_sqlite_campaign_repository.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/schemas/
  - src/ai_campaign_studio/application/mappers/brand_fixture_mapper.py
  - src/ai_campaign_studio/application/brands/
  - src/ai_campaign_studio/ports/ai.py
  - src/ai_campaign_studio/ports/prompts.py
  - src/ai_campaign_studio/infrastructure/prompts/
  - src/ai_campaign_studio/infrastructure/ai/
  - src/ai_campaign_studio/infrastructure/database/connection.py
  - src/ai_campaign_studio/infrastructure/database/migrations.py
  - src/ai_campaign_studio/infrastructure/database/unit_of_work.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_brand_repository.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_fact_repository.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_content_repository.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_visual_repository.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_revision_repository.py
  - src/ai_campaign_studio/presentation/
  - src/ai_campaign_studio/presentation_webview/
  - src/ai_campaign_studio/bootstrap.py
  - src/ai_campaign_studio/main.py
gitnexus_required: true
adversarial_required: false
gitnexus:
  required: true
  repository: "H:\\AI Campaing Studio"
  worktree: main (pre-branch pre-impact)
  branch: main
  head: e2a7e33
  index_status: fresh (analyze re-run 2026-09-02 post ACS-F1-007/008/GUI-002 merge)
  targets:
    - symbol: "CampaignRepositoryPort (ports/repositories.py) — ADDITIVE method get_brief"
      upstream_risk: LOW
      upstream_count: 1
      downstream_notes: "gitnexus impact (upstream, includeTests=true): only application/brands/load_brand_fixture.py imports the repositories module (unrelated to CampaignRepositoryPort itself — no existing caller uses any CampaignRepositoryPort method yet, since this is its first real consumer). Adding a NEW method does not change any existing method signature, so every already-merged caller/fake stays valid. tests/unit/ports/test_repositories.py's runtime_checkable isinstance check only exercises BrandRepositoryPort, not CampaignRepositoryPort — no existing test breaks."
      affected_processes: []
    - symbol: "new application/campaigns/ package"
      upstream_risk: NONE
      upstream_count: 0
      downstream_notes: "Brand-new directory, zero existing importers. Orchestrates already-merged, already-reviewed pieces: application/schemas/campaign_brief.py + campaign_plan_output.py (ACS-F1-004), ports/repositories.py + SqliteCampaignRepository (ACS-F1-005/006), ports/ai.py + ports/prompts.py + infrastructure/prompts + infrastructure/ai (ACS-F1-008). Does not modify any of those except the one additive method above."
      affected_processes: []
  scope_fit: PASS
  unknowns: []
---

# Kontekst

Task **A9 — Campaign Brief + Campaign Planning** (plan sekcije 29 "Campaign
Brief use-case" i 30 "Campaign Plan generation", task-lista `## A9`). Prvi
task koji stvarno **spaja** dva prethodno izolovano izgrađena i mergovana
toka:

```text
ACS-F1-007 (LoadBrandFixture) → daje persistovan BrandSnapshot
ACS-F1-008 (Prompt repo + AI port + mock adapter) → daje PromptRepositoryPort
                                                       + TextGenerationPort
```

u prvi pravi **application-layer generation pipeline**:

```text
CreateCampaign:
  CampaignBriefInput (raw dict) → validacija → domain CampaignBrief
    → domain Campaign (DRAFT) → persist (atomic)

GenerateCampaignPlan:
  Campaign (persisted) → BrandSnapshot (persisted) → CampaignBrief (persisted)
    → CampaignRole definicije + CampaignTemplate kandidat (LEAD_GENERATION_V1,
      jedini postojeći template — ne graditi selection engine za jedan
      template, AR3)
    → PromptRepositoryPort.get("campaign_plan", "1")
    → AIRequest (system/user text iz prompt instructions + brief + brand
      snapshot + language context; json_schema = CampaignPlanOutput.model_json_schema())
    → TextGenerationPort.generate(request)
    → CampaignPlanOutput (Pydantic validacija + item-count/order provjera,
      ACS-F1-004 već postoji, NE duplirati)
    → domain validacija (role diversity, no duplicate topics)
    → CampaignPlan DRAFT + CampaignItem-i
    → persist (atomic) + Campaign.status → PLAN_GENERATED
```

**A8 (pravi live provider adapter — OpenAI/Anthropic/itd.) je EKSPLICITNO
odgođen** (Human Owner odluka, 2026-09-02) — ovaj task NE čeka na A8.
`TextGenerationPort` je Protocol; use-case zavisi samo od njega, ne od
konkretnog adaptera. Testovi koriste lokalne test-double implementacije
`TextGenerationPort` (fake, definisan u test fajlu) koje vraćaju
`CampaignPlanOutput`-šejp strukturu — **ne mijenjati
`infrastructure/ai/mock_adapter.py`** (već review-ovan/mergovan u
ACS-F1-008, njegov `DETERMINISTIC` mod namjerno vraća generički
`{"result": "ok"}` payload koji NE odgovara `CampaignPlanOutput` šemi; to
nije bug, mock adapter nije specifičan za jedan use-case).

**Zašto se `ports/repositories.py` i `sqlite_campaign_repository.py` diraju
u ovom tasku** (oba su inače van tipičnog `application/` scope-a): `Campaign
→ BrandSnapshot → CampaignBrief` pipeline korak zahtijeva čitanje
persistovanog brief-a nazad po `brief_id`, a `CampaignRepositoryPort` trenutno
ima `save_brief()` ali **nema `get_brief()`** — čista rupa, ne
implementer-ova greška. `campaign_briefs` tabela i sve kolone već postoje
(ACS-F1-006 migracija), samo read metoda fali. Dozvoljena izmjena je
**striktno aditivna**: DODATI `get_brief(brief_id: str) -> CampaignBrief |
None` na Protocol i njegovu SQLite implementaciju. NE mijenjati
potpis/ponašanje nijedne postojeće metode na tim fajlovima — koordinator će
to line-by-line diff-ovati pri review-u (`ports/repositories.py` je
shared-contract teritorija, ACS-F1-005). GitNexus upstream-impact potvrđuje
LOW rizik (vidi frontmatter) — dodavanje metode ne kvari nijednog postojećeg
callera.

Prije koda pročitati:

```text
AGENTS.md
CLAUDE.md
docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md
.agent/CURRENT_STATE.md
AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md
  sekcija 29 "Campaign Brief use-case", sekcija 30 "Campaign Plan
  generation" (uključujući "Domain validation" pod-sekciju), task-lista
  stavka "## A9", AR3 (nema services/ kante za sve)
```

Pročitati postojeći kod koji se orkestrira (ne pogađati potpise):

```text
src/ai_campaign_studio/application/schemas/campaign_brief.py
src/ai_campaign_studio/application/schemas/campaign_plan_output.py
src/ai_campaign_studio/application/mappers/brand_fixture_mapper.py
  (STIL primjer za novi campaign_brief_mapper.py, ne kopirati sadržaj)
src/ai_campaign_studio/application/brands/load_brand_fixture.py
  (STIL primjer za use-case orkestraciju + UnitOfWork atomicity pattern,
  ne kopirati sadržaj)
src/ai_campaign_studio/domain/campaign/entities.py
src/ai_campaign_studio/domain/campaign/enums.py
src/ai_campaign_studio/domain/campaign/roles.py
src/ai_campaign_studio/domain/campaign/templates.py
src/ai_campaign_studio/domain/content/entities.py (CampaignTarget)
src/ai_campaign_studio/domain/brand/entities.py (BrandSnapshot)
src/ai_campaign_studio/ports/repositories.py
src/ai_campaign_studio/ports/ai.py
src/ai_campaign_studio/ports/prompts.py
src/ai_campaign_studio/infrastructure/database/repositories/sqlite_campaign_repository.py
src/ai_campaign_studio/infrastructure/database/unit_of_work.py
resources/prompts/campaign_plan/v1.yaml
```

# Objective

1. `application/mappers/campaign_brief_mapper.py` — mapira validiran
   `CampaignBriefInput` u domain `CampaignBrief` (novi fajl, isti stil kao
   `brand_fixture_mapper.py`: pure in-memory transformacija, `new_id()`,
   `utc_now()`).
2. `application/campaigns/create_campaign.py` — `CreateCampaign` use-case.
3. `application/campaigns/generate_campaign_plan.py` — `GenerateCampaignPlan`
   use-case.
4. `CampaignRepositoryPort.get_brief()` (aditivno) + SQLite implementacija.
5. Testovi: unit (fake portovi) + integration (prava SQLite baza).

# Implementation steps

## `campaign_brief_mapper.py`

```text
map_campaign_brief(input: CampaignBriefInput) -> CampaignBrief
```

Konstruiše `CampaignTarget` objekte iz `input.targets`, `id=new_id()`,
`created_at=utc_now()`. Čisto mapiranje, bez validacije (validacija se
dešava u Pydantic sloju PRIJE poziva mappera — isti disciplina kao brand
fixture mapper).

## `CampaignRepositoryPort.get_brief()` + adapter

```text
def get_brief(self, brief_id: str) -> CampaignBrief | None: ...
```

SQLite implementacija čita `campaign_briefs` red po `id`, deserijalizuje
`targets_json` nazad u `tuple[CampaignTarget, ...]` i
`special_instructions_json` u `tuple[str, ...]` (isti obrazac kao postojeći
`_campaign_from_row`/`_item_from_row` helper funkcije u istom fajlu — dodati
analogni `_brief_from_row`).

## `CreateCampaign`

```text
class CreateCampaign:
    def __init__(self, campaign_repo: CampaignRepositoryPort,
                 unit_of_work: _UnitOfWork) -> None: ...
    def execute(self, brand_id: BrandId, brand_snapshot_id: BrandSnapshotId,
                raw_brief: dict) -> Campaign: ...
```

(implementer bira tačan potpis — dokumentovati izbor, isto pravilo kao
ACS-F1-007's `_UnitOfWork` Protocol.)

Tok:

1. Validirati `raw_brief` kroz `CampaignBriefInput.model_validate(raw_brief)`
   — ako ne validira, propagirati grešku, ništa nije perzistirano (isti
   disciplina kao `LoadBrandFixture`).
2. Mapirati kroz `map_campaign_brief(...)`.
3. Konstruisati domain `Campaign` (status=`DRAFT`, `id=new_id()`,
   `brief_id=brief.id`).
4. Perzistirati brief + campaign unutar JEDNE `SqliteUnitOfWork` transakcije
   (isti atomicity pattern kao ACS-F1-007 — `uow.commit()` samo ako oba
   poziva uspiju).
5. Vratiti `Campaign`.

Ne generiše plan (to radi `GenerateCampaignPlan`, odvojen poziv).

## `GenerateCampaignPlan`

```text
class GenerateCampaignPlan:
    def __init__(self, campaign_repo: CampaignRepositoryPort,
                 brand_repo: BrandRepositoryPort,
                 prompt_repo: PromptRepositoryPort,
                 ai_port: TextGenerationPort,
                 unit_of_work: _UnitOfWork) -> None: ...
    def execute(self, campaign_id: CampaignId) -> CampaignPlan: ...
```

Tok:

1. Učitati `Campaign` (`campaign_repo.get_campaign(campaign_id)`) — ako ne
   postoji, jasna greška.
2. Učitati `BrandSnapshot` (`brand_repo.get_snapshot(campaign.brand_snapshot_id)`).
3. Učitati `CampaignBrief` (`campaign_repo.get_brief(campaign.brief_id)`).
4. Izabrati template kandidat: `LEAD_GENERATION_V1` (jedini postojeći —
   ne graditi selection logiku za jedan template).
5. Učitati prompt: `prompt_repo.get("campaign_plan", "1")`.
6. Konstruisati `AIRequest`:
   - `system_text`/`user_text` grade se od `prompt.instructions` + brief
     (offer/goal/audience/content_piece_count) + brand snapshot summary
     (voice/preferred_terms/forbidden_terms/regional_vocabulary/
     tone_examples/language/locale/script) + `CampaignRole` lista + template
     `role_sequence` — implementer bira tačan tekstualni format,
     dokumentovati izbor;
   - `json_schema = CampaignPlanOutput.model_json_schema()`;
   - `prompt_name="campaign_plan"`, `prompt_version="1"`.
7. `response = ai_port.generate(request)`.
8. Validirati `response.structured_payload` kroz
   `validate_campaign_plan_output(payload, brief.content_piece_count)`
   (ACS-F1-004, već postoji — NE duplirati order/count validaciju).
9. **Domain validacija** (ono što `CampaignPlanOutput`-ov Pydantic validator
   NE provjerava):
   - role diversity >= razuman prag (plan ne precizira tačan broj —
     implementer bira i DOKUMENTUJE, npr. minimalno 2 distinktne role kad
     `content_piece_count >= 2`);
   - nema identičnih `topic` stringova među itemima.
   - "Ne koristiti LLM da validira svoj output" — sve provjere su
     deterministički Python kod, ne dodatni AI poziv.
10. Mapirati validirane iteme u domain `CampaignItem` objekte
    (`id=new_id()`, `status=PLANNED`).
11. Konstruisati `CampaignPlan` (status=`DRAFT`, `version=1`).
12. Perzistirati plan (`campaign_repo.save_plan`) I ažurirani `Campaign`
    (status → `PLAN_GENERATED`, `dataclasses.replace(campaign, status=...)`,
    `campaign_repo.save_campaign`) unutar JEDNE `SqliteUnitOfWork`
    transakcije — ako bilo šta faila (uključujući AI poziv ili domain
    validaciju), NIŠTA se ne perzistira/mijenja (Campaign ostaje u
    prethodnom statusu).
13. Vratiti `CampaignPlan`.

# Acceptance

- [ ] `CreateCampaign`: validacija PRIJE perzistencije (invalid `raw_brief`
      ne ostavlja trag u bazi — test dokazuje, isti obrazac kao ACS-F1-007).
- [ ] `CreateCampaign`: atomicity test (mid-persist failure ostavlja i
      `campaigns` i `campaign_briefs` prazne).
- [ ] `GenerateCampaignPlan`: happy-path test sa fake `TextGenerationPort`
      koji vraća validan `CampaignPlanOutput`-šejp payload — plan
      persistovan, `Campaign.status == PLAN_GENERATED`, item count ==
      `brief.content_piece_count`.
- [ ] `GenerateCampaignPlan`: invalid-schema test — fake port vraća payload
      koji NE prolazi `CampaignPlanOutput` validaciju (npr. pogrešan broj
      itema ili nepoznat role) → jasna greška, `Campaign.status` OSTAJE
      nepromijenjen, ništa novo nije perzistirano.
- [ ] `GenerateCampaignPlan`: role-diversity i duplicate-topic domain
      provjere imaju SVOJ test (ne samo Pydantic schema test).
- [ ] `GenerateCampaignPlan`: atomicity test (mid-persist failure — npr.
      `save_plan` uspije, `save_campaign` failuje — ostavlja `Campaign`
      status nepromijenjen I `campaign_plans`/`campaign_items` prazne za taj
      poziv).
- [ ] Oba use-case-a zavise SAMO od portova (`CampaignRepositoryPort`,
      `BrandRepositoryPort`, `PromptRepositoryPort`, `TextGenerationPort`) +
      lokalnog `_UnitOfWork` Protocol-a — provjeriti import-e, nema SQLite/
      YAML/network importa u `application/campaigns/`.
- [ ] `get_brief()` je JEDINA nova metoda na `CampaignRepositoryPort` —
      koordinator diff-uje `ports/repositories.py` da nijedna postojeća
      metoda (bilo kojeg od 7 portova) nije promijenjena.
- [ ] Integration testovi koriste pravu SQLite bazu (kao ACS-F1-005/006/007
      — `create_connection` + `run_migrations` na `tmp_path`) i
      `SqliteCampaignRepository` uključujući novi `get_brief()`.
- [ ] `python -m pytest -q`, `ruff check .`, `mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest -q
python -m pytest tests/architecture/test_import_boundaries.py -v
python -m pytest tests/unit/application/campaigns tests/unit/application/mappers/test_campaign_brief_mapper.py tests/integration/application/campaigns tests/integration/database/repositories/test_sqlite_campaign_repository.py -v
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- `ports/repositories.py` diff je STRIKTNO aditivan (samo `get_brief`
  dodat, ništa drugo promijenjeno) — pročitati cijeli diff, ne samo novi
  kod;
- atomicity je STVARNO testirana za oba use-case-a (mid-failure rollback na
  pravoj SQLite bazi), ne samo tvrđena;
- `GenerateCampaignPlan` NE zove pravi provider (test double/fake u
  test-ovima, `infrastructure/ai/mock_adapter.py` netaknut);
- role-diversity i duplicate-topic provjere postoje kao EKSPLICITNA domain
  logika u use-case-u (ne implicitno "valjda Pydantic to hvata" — Pydantic
  validator hvata samo order-uniqueness i item-count, ne role diversity ni
  duplicate topics);
- use-case-i zavise od portova (Protocol), ne konkretnih SQLite/YAML/mock
  klasa;
- scope discipline — nema dirania `application/schemas/`,
  `application/mappers/brand_fixture_mapper.py`, `ports/ai.py`,
  `ports/prompts.py`, `infrastructure/ai/`, `infrastructure/prompts/`,
  ijedne druge SQLite repository implementacije osim
  `sqlite_campaign_repository.py`.

# Rollback

MEDIUM risk — nova, izolovana orchestration logika + jedna aditivna
Protocol metoda sa potvrđenim LOW upstream impact-om (GitNexus). Fix na
istoj branch bez proširenja scope-a. STOP i vrati na puni ciklus SAMO ako
se pokaže da `ports/repositories.py` izmjena zahtijeva više od dodavanja
`get_brief` (npr. ako implementer zaključi da treba mijenjati postojeći
potpis) — to je HIGH-liste teritorija (shared-contract refactor), ne
nastavljati tiho olakšanim putem.

# Coordination

Nezavisan od bilo kojeg trenutno otvorenog taska. Zavisi (already-merged,
ne aktivna zavisnost) od ACS-F1-004 (schemas), ACS-F1-005/006
(persistence), ACS-F1-007 (LoadBrandFixture — nije runtime zavisnost, ali
integration testovi mogu koristiti isti `brightsmile.json` fixture +
`LoadBrandFixture` da dobiju pravi `BrandSnapshot` za end-to-end test), i
ACS-F1-008 (AI port/prompts — runtime zavisnost preko Protocol-a, ne preko
mock adaptera).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-009-campaign-brief-plan-generation
Branch:   task/ACS-F1-009-campaign-brief-plan-generation
Base:     main @ e2a7e33
```
