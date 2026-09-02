---
task_id: ACS-F1-011
phase: Faza-1
title: "A11 — Allowed Facts + Social Content Generation (GenerateSocialPost)"
risk: MEDIUM
coordinator: claude
implementer: pi
reviewers: [claude]
status: "BLOCKED — čeka ACS-F1-010 merge (payload persistence prerequisite)"
created_at: 2026-09-02
dependencies: [ACS-F1-010]
allowed_paths:
  - src/ai_campaign_studio/application/posts/__init__.py
  - src/ai_campaign_studio/application/posts/select_allowed_facts.py
  - src/ai_campaign_studio/application/posts/claim_validator.py
  - src/ai_campaign_studio/application/posts/generate_social_post.py
  - tests/unit/application/posts/
  - tests/integration/application/posts/
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/schemas/
  - src/ai_campaign_studio/application/mappers/
  - src/ai_campaign_studio/application/brands/
  - src/ai_campaign_studio/application/campaigns/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/infrastructure/
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
  head: 5603030
  index_status: fresh (analyze re-run 2026-09-02 post ACS-F1-009 merge; RE-CHECK required
    after ACS-F1-010 merges, since this task's base commit will move)
  targets:
    - symbol: "new application/posts/ package"
      upstream_risk: NONE
      upstream_count: 0
      downstream_notes: "Brand-new directory, zero existing importers. Orchestrates already-merged pieces: application/schemas/social_post_generation_output.py (ACS-F1-004), domain/facts/policies.py is_fact_usable (ACS-F1-001), ports/repositories.py + Sqlite adapters (ACS-F1-005/006 + ACS-F1-010's payload addition), ports/ai.py + ports/prompts.py + infrastructure/ai + infrastructure/prompts (ACS-F1-008). Does not modify any of them."
      affected_processes: []
  scope_fit: PASS
  unknowns:
    - "ACS-F1-010 nije još mergovan u trenutku pisanja ovog kontrakta — implementer MORA
      raditi na main-u NAKON ACS-F1-010 merge-a (rebase/re-branch ako je worktree kreiran
      ranije), ne na main @ 5603030 koji nema ContentPiece.payload polje."
---

# Kontekst

Task **A11 — Allowed Facts + Social Content Generation** (plan sekcije 33
"Allowed Fact Selection", 34 "Social Content generation pipeline", 35
"Fact-ID validator" — SAMO fact-id dio, ne linter; task-lista `## A11`).
Drugi generation use-case nakon ACS-F1-009 (campaign plan) — isti
arhitektonski obrazac (Protocol portovi, atomic persist, fake AI port u
testovima), sad za pojedinačan social post.

**Zavisi od ACS-F1-010** (`ContentPiece.payload: SocialPostPayload | None`)
— bez tog polja generisan post nema gdje da se perzistuje. Ako ACS-F1-010
još nije mergovan kad implementer krene, STOP i javi koordinatoru, ne
izmišljati privremeno mjesto za payload (npr. ne gurati ga u
`facts_allowed_json` ili slično zaobilazno rješenje).

**Namjerna scope granica prema A12** (plan task-lista `## A12 — Claim
validator + linter + revisions`, sekcije 36-38): A12 vlasnik je
`claim_linter.py` (rule-config-driven, `resources/claim_rules/
default_v1.yaml`, numeric pattern detekcija, prohibited/risky termini,
sekcija 36), finalne `ContentStatus` derivacije NAKON lintera (sekcija 37),
i `revise_content_piece.py` (sekcija 38). **Ovaj task NE implementira
nijedno od toga.** Ono što OVAJ task implementira iz sekcije 35 je SAMO
Fact-ID validator (provjera da claim tipa FACT stvarno referencira
postojeći, `APPROVED`, ne-superseded fact koji je bio u `AllowedFactSet`) —
to je dovoljno da svaki claim dobije REALAN, već-postojeći `ClaimStatus`
(nema potrebe za novim enum članom/domain izmjenom).

**Interim `ContentStatus` pravilo (dokumentovati u kodu, implementer
primjenjuje tačno ovo, ne izmišlja alternativu):**

```text
Ako BILO KOJI claim ima ClaimStatus.UNSUPPORTED (fact-id validator ga je
tako označio) → ContentPiece.status = ContentStatus.NEEDS_REVIEW
  (izvjestan problem, ne treba čekati A12-ov linter da to potvrdi)
Inače → ContentPiece.status = ContentStatus.GENERATING
  (fact-validiran, ali JOŠ NIJE prošao kroz A12-ov prohibited-term linter
  — ContentStatus.DRAFT je rezervisan za "nema UPOZORENJA" ISHOD sekcije 37,
  koji ovaj task ne može tvrditi bez lintera; GENERATING je most, A12 će
  ga finalizovati na DRAFT ili NEEDS_REVIEW)
```

**Namjerno van scope-a (ne graditi sad):**

- `ContentSlotContract` (sekcija 41 — pixel/layout slot pravila) — vizuelni/
  renderer koncept za A13/A14, ne za tekst generaciju. Prompt kontekst
  nosi samo `target.platform_code`/`target.format_code` kao plain string
  (isti nivo apstrakcije kao `CampaignTarget` domain entitet).
- `PlatformDefinition`/`FormatDefinition` registry lookup (`ai_registry`/
  `channels` paket) — `application/posts/` NE uvozi te pakete (isto pravilo
  kao `application/campaigns/` koji ih takođe ne uvozi).
- "Role rules" registry — `CampaignRole` enum + `CampaignItem.role/topic/
  goal` idu direktno u prompt kontekst, nema posebnog rules-lookup modula
  (ne postoji ni danas, ne graditi ga za jedan prompt).

**Risk**: MEDIUM — orchestration nad već review-ovanim slojevima (isti
klasa rizika kao ACS-F1-009), ne dira SecretStore/migracije/registry
contracts. §29: Claude-only review, PASS → odmah merge.

Prije koda pročitati:

```text
AGENTS.md
CLAUDE.md
docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md
.agent/CURRENT_STATE.md
AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md
  sekcija 33 "Allowed Fact Selection", 34 "Social Content generation
  pipeline", 35 "Fact-ID validator" (SAMO FACT/CTA/OPINION/CREATIVE default
  pravila — ne sekcije 36-38), task-lista "## A11" i "## A12" (da vidiš
  TAČNU granicu)
```

Pročitati postojeći kod koji se orkestrira:

```text
src/ai_campaign_studio/application/schemas/social_post_generation_output.py
src/ai_campaign_studio/application/campaigns/generate_campaign_plan.py
  (STIL primjer — isti _UnitOfWork Protocol pattern, isti AIRequest-building
  pattern, ne kopirati sadržaj)
src/ai_campaign_studio/domain/content/entities.py (ContentPiece, uključujući
  ACS-F1-010-ovo novo `payload` polje — PROČITATI NAKON tog mergea)
src/ai_campaign_studio/domain/content/claims.py (ContentClaim)
src/ai_campaign_studio/domain/content/enums.py (ClaimStatus, ClaimType, ContentStatus)
src/ai_campaign_studio/domain/facts/policies.py (is_fact_usable — koristiti, ne duplirati)
src/ai_campaign_studio/domain/facts/entities.py (ApprovedFact)
src/ai_campaign_studio/domain/campaign/entities.py (CampaignItem, Campaign)
src/ai_campaign_studio/ports/repositories.py (CampaignRepositoryPort.get_campaign/get_plan,
  BrandRepositoryPort.get_snapshot, FactRepositoryPort.list_snapshot_facts,
  ContentRepositoryPort.save_content_piece — sve već postoji, NE dodavati nove metode)
src/ai_campaign_studio/ports/ai.py, ports/prompts.py
resources/prompts/post_generation/v1.yaml
```

# Objective

1. `application/posts/select_allowed_facts.py` — `select_allowed_facts()`
   deterministička selekcija (bez AI, bez embeddings, bez vector DB).
2. `application/posts/claim_validator.py` — Fact-ID validator (sekcija 35,
   SAMO fact-id dio).
3. `application/posts/generate_social_post.py` — `GenerateSocialPost`
   use-case, orkestrira sve.
4. Testovi: unit (fake portovi) + integration (prava SQLite baza).

# Implementation steps

## `select_allowed_facts.py`

```python
@dataclass(frozen=True)
class AllowedFactSet:
    fact_ids: tuple[FactId, ...]
    selection_reasons: dict[FactId, str]

def select_allowed_facts(
    campaign_item: CampaignItem, snapshot_facts: tuple[ApprovedFact, ...]
) -> AllowedFactSet: ...
```

Algoritam (deterministički, bez LLM poziva):

1. Zadržati SAMO fact-ove za koje `is_fact_usable(fact)` vraća `True`
   (postojeća domain policy funkcija — ne duplirati status-provjeru
   ručno).
2. Za svaku frazu u `campaign_item.facts_needed`, jednostavan lexical
   matcher: case-insensitive substring provjera protiv `fact.content` i
   `fact.logical_fact_id` (dozvoljeno po planu — "Ako nema dovoljno
   metadata, dopušten je jednostavan lexical matcher").
3. `selection_reasons[fact.id]` = kratak string zašto je izabran (npr.
   koja `facts_needed` fraza je matchovala).
4. Prazan `campaign_item.facts_needed` ili nula poklapanja → prazan
   `AllowedFactSet` (NIJE greška — post može imati samo CTA/OPINION/
   CREATIVE claimove).

## `claim_validator.py`

Implementira TAČNO sekciju 35 (ne 36):

```python
def validate_claim(
    claim: ContentClaimOutput, allowed: AllowedFactSet, fact_repo: FactRepositoryPort
) -> ContentClaim: ...
```

- `type == FACT`: mora imati >=1 `fact_id`; svaki fact mora postojati
  (`fact_repo.get_fact`), biti `is_fact_usable` (APPROVED, pokriva i
  "nije superseded" i "nije soft-deleted" kroz postojeću policy funkciju),
  I biti u `allowed.fact_ids`. Sve prođe → `ClaimStatus.VERIFIED_BY_FACT`.
  Bilo šta ne prođe → `ClaimStatus.UNSUPPORTED` + `reason_codes` (npr.
  `"missing-fact-id"`, `"fact-not-approved"`, `"fact-not-offered"` — isti
  reason code stringovi kao plan sekcija 36 lista, i dalje validni ovdje
  iako je puni linter A12).
- `type in (CTA, OPINION, CREATIVE)`: default `ClaimStatus.NON_FACTUAL`
  (nema dodatnu term-listu provjeru — to je A12-ov linter).

## `generate_social_post.py`

```python
class GenerateSocialPost:
    def __init__(
        self, campaign_repo, brand_repo, fact_repo, content_repo,
        prompt_repo, ai_port, unit_of_work,
    ) -> None: ...
    def execute(
        self, campaign_id: CampaignId, plan_id: CampaignPlanId,
        campaign_item_id: CampaignItemId, target: CampaignTarget,
    ) -> ContentPiece: ...
```

Tok:

1. `campaign = campaign_repo.get_campaign(campaign_id)` — ako `None`,
   `EntityNotFound`.
2. `plan = campaign_repo.get_plan(plan_id)` — ako `None`, `EntityNotFound`.
3. Pronaći `campaign_item` u `plan.items` sa `id == campaign_item_id` —
   ako nema, `EntityNotFound` (NE dodavati novu repository metodu za
   direktan lookup po item id-u — plan već nosi sve iteme, ovo je čisto
   in-memory pretraga).
4. `snapshot = brand_repo.get_snapshot(campaign.brand_snapshot_id)` — ako
   `None`, `EntityNotFound`.
5. `snapshot_facts = fact_repo.list_snapshot_facts(snapshot.id)`.
6. `allowed = select_allowed_facts(campaign_item, snapshot_facts)`.
7. `prompt = prompt_repo.get("post_generation", "1")`.
8. Konstruisati `AIRequest`: `system_text=prompt.instructions`,
   `user_text` grade se od campaign_item (role/topic/goal), brand
   snapshot summary (voice/preferred_terms/forbidden_terms/
   regional_vocabulary/tone_examples/language/locale/script — isti obrazac
   kao ACS-F1-009), `allowed` fact-ova sadržaj (fact_id + content za svaki
   dozvoljen fact — model MORA vidjeti stvaran tekst fact-a da bi mogao
   citirati), `target` (channel/platform_code/format_code kao plain
   string), `json_schema = SocialPostGenerationOutput.model_json_schema()`.
9. `response = ai_port.generate(request)` — ako `structured_payload is
   None`, `InvariantViolation`.
10. `output = SocialPostGenerationOutput.model_validate(response.structured_payload)`
    (Pydantic — propagira `ValidationError` ako ne validira, NE gutati).
11. Za svaki `output.claims` item, `validate_claim(...)` → lista
    `ContentClaim` objekata (`id=new_id()`).
12. Odrediti `ContentPiece.status` po interim pravilu iz Konteksta iznad
    (bilo koji `UNSUPPORTED` claim → `NEEDS_REVIEW`, inače `GENERATING`).
13. Konstruisati `SocialPostPayload` iz `output` (headline/caption/hook/
    body/cta/hashtags; `visual_direction=None` — vizuelni sistem je A13+).
14. Konstruisati `ContentPiece` (`id=PostId(new_id())`,
    `payload_type=ContentPayloadType.SOCIAL_POST`, `payload=<gore>`,
    `facts_allowed=allowed.fact_ids`, `claims=<gore>`).
15. Perzistirati `content_repo.save_content_piece(content_piece)` unutar
    JEDNE `SqliteUnitOfWork` transakcije (isti atomicity pattern kao
    ACS-F1-007/009 — samo JEDAN repository poziv ovdje, ali i dalje kroz
    `with unit_of_work: ... uow.commit()` radi konzistentnosti sa ostatkom
    application sloja i da eventualni budući drugi poziv u istoj metodi
    ostane atomičan).
16. Vratiti `ContentPiece`.

# Acceptance

- [ ] `select_allowed_facts`: samo `APPROVED` fact-ovi ikad uđu u
      `AllowedFactSet` (test sa `SUPERSEDED`/`SOFT_DELETED` fact-om u
      snapshotu — mora biti isključen).
- [ ] `select_allowed_facts`: lexical matching test (fact čiji `content`
      sadrži frazu iz `facts_needed` je izabran; fact koji ne sadrži nije).
- [ ] `select_allowed_facts`: prazan `facts_needed` → prazan
      `AllowedFactSet`, NE greška (test dokazuje da use-case i dalje radi
      dalje, samo bez FACT claimova moguć).
- [ ] `claim_validator`: FACT claim sa fact_id koji NIJE u `AllowedFactSet`
      → `UNSUPPORTED` (čak i ako fact postoji i APPROVED je — mora biti u
      allowed setu, ne samo validan sam po sebi).
- [ ] `claim_validator`: FACT claim sa nepostojećim fact_id → `UNSUPPORTED`.
- [ ] `claim_validator`: FACT claim sa validnim, allowed, APPROVED fact_id
      → `VERIFIED_BY_FACT`.
- [ ] `claim_validator`: CTA/OPINION/CREATIVE claim → `NON_FACTUAL` uvijek
      (bez obzira na fact_ids sadržaj).
- [ ] `GenerateSocialPost`: happy path (fake `TextGenerationPort` sa
      validnim payload-om, sve claims VERIFIED_BY_FACT/NON_FACTUAL) →
      `ContentPiece.status == GENERATING`, `payload` popunjen, persistovan.
- [ ] `GenerateSocialPost`: bilo koji `UNSUPPORTED` claim →
      `ContentPiece.status == NEEDS_REVIEW` (test dokazuje).
- [ ] `GenerateSocialPost`: nevalidan AI output (fali obavezno polje) →
      jasna greška PRIJE perzistencije (repository netaknut — isti
      disciplina kao ACS-F1-007/009).
- [ ] `GenerateSocialPost`: nepostojeći `campaign_id`/`plan_id`/
      `campaign_item_id` → `EntityNotFound`, svaki test posebno.
- [ ] Use-case zavisi SAMO od portova (`CampaignRepositoryPort`,
      `BrandRepositoryPort`, `FactRepositoryPort`, `ContentRepositoryPort`,
      `PromptRepositoryPort`, `TextGenerationPort`) + lokalnog
      `_UnitOfWork` Protocol-a — provjeriti import-e, nema `channels`/
      `ai_registry` importa.
- [ ] Integration test koristi pravu SQLite bazu (isti obrazac kao
      ACS-F1-005..009 — `create_connection` + `run_migrations` na
      `tmp_path`), po mogućnosti lanči cijeli lanac (LoadBrandFixture →
      CreateCampaign → GenerateCampaignPlan → GenerateSocialPost) kao
      ACS-F1-009-ov `test_end_to_end_fixture_to_plan`, ako je to razumno
      bez prevelikog test setup-a.
- [ ] `python -m pytest -q`, `ruff check .`, `mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest -q
python -m pytest tests/architecture/test_import_boundaries.py -v
python -m pytest tests/unit/application/posts tests/integration/application/posts -v
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- fact-id validator implementira TAČNO sekciju 35 (FACT/CTA/OPINION/
  CREATIVE default pravila) — NE dodaje term-liste/numeric-pattern
  detekciju (to je A12);
- interim `ContentStatus` pravilo primijenjeno TAČNO kako je specificirano
  (UNSUPPORTED→NEEDS_REVIEW, inače GENERATING — NE DRAFT);
- `select_allowed_facts` samo zadržava `is_fact_usable` fact-ove (koristi
  postojeću policy funkciju, ne duplira logiku);
- `ContentSlotContract`/`channels`/`ai_registry` NISU importovani —
  scope discipline;
- atomicity/error-before-persist disciplina ista kao ACS-F1-007/009;
- `payload` polje se koristi ispravno (zavisi od ACS-F1-010 merge-a prije
  ovog review-a).

# Rollback

MEDIUM risk — nova, izolovana orchestration logika nad već review-ovanim
portovima (uključujući ACS-F1-010-ovo aditivno `payload` polje). Fix na
istoj branch bez proširenja scope-a. STOP i vrati na puni ciklus samo ako
se pokaže potreba da task dira `domain/`/`ports/`/migracije (to je već
HIGH teritorija, ACS-F1-010 ju je namjerno izolovao).

# Coordination

**BLOCKED dok ACS-F1-010 ne merguje.** Nakon merge-a, implementer mora
`git merge main` (ili re-branch) u svoj worktree PRIJE početka koda, da
dobije `ContentPiece.payload` polje. Nezavisan od svega ostalog trenutno
otvorenog.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-011-allowed-facts-post-generation
Branch:   task/ACS-F1-011-allowed-facts-post-generation
Base:     main @ 5603030 (implementer MORA merge-ovati main nakon ACS-F1-010 prije rada)
```
