---
task_id: ACS-F1-026
phase: Faza-1 (G10 — A/B evaluation harness, A16)
title: "A/B evaluation harness: Control A baseline + System B wrapper + determinističke metrike"
risk: MEDIUM
coordinator: claude
implementer: crush
reviewers: [claude]
status: "OPEN — contract written before code"
created_at: 2026-09-04
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/application/evaluation/__init__.py
  - src/ai_campaign_studio/application/evaluation/evaluation_post.py
  - src/ai_campaign_studio/application/evaluation/run_control_a.py
  - src/ai_campaign_studio/application/evaluation/run_system_b.py
  - src/ai_campaign_studio/application/evaluation/deterministic_metrics.py
  - src/ai_campaign_studio/application/schemas/ab_control_output.py
  - tests/unit/application/evaluation/
  - tests/integration/application/evaluation/
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/campaigns/
  - src/ai_campaign_studio/application/posts/
  - src/ai_campaign_studio/application/brands/
  - src/ai_campaign_studio/application/ai_provider/
  - src/ai_campaign_studio/infrastructure/
  - src/ai_campaign_studio/ports/
  - resources/prompts/
  - resources/claim_rules/
  - resources/migrations/
gitnexus_required: true
adversarial_required: false
gitnexus:
  required: true
  note: >
    GitNexus MCP nedostupan u trenutku pisanja. Koordinator će pokrenuti
    detect-changes/impact prije merge-a. Novi `application/evaluation/`
    paket nema postojećih pozivalaca (potpuno nov modul); poziva postojeće
    use-case-e (`CreateCampaign`, `GenerateCampaignPlan`,
    `ApproveCampaignPlan`, `GenerateSocialPost`) i postojeći
    `content_similarity.jaccard_similarity` (ACS-F1-025) BEZ izmjene
    njihovih potpisa.
  repository: "H:\\AI Campaing Studio"
  branch: main
  head: 99b1449
  scope_fit: "PENDING — popuniti kad GitNexus MCP bude dostupan."
---

# Kontekst

Human Owner je 2026-09-04 odobrio G10 (A/B evaluation harness) kao
sljedeći prioritet nakon ACS-GUI-007 — krajnji dokaz Faze 1 da je
Campaign Engine ("System B", puni strukturisani pipeline) stvarno
mjerljivo bolji od golog single-prompt pristupa ("Control A"), ne samo
pretpostavka.

Specifikacija VEĆ POSTOJI u detalju —
`AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md` §47-50 —
**ne izmišljati nove kriterijume, ovaj kontrakt samo operacionalizuje već
napisanu specifikaciju.**

**Obim ovog taska (A16 iz plana)**: Control A + System B + determinističke
metrike. Human eval paket (§49, `human_eval.py`) je ZASEBAN, budući task
(ACS-F1-027) — depends on ovom tasku, ne diraj ga ovdje. Puni "vertical
slice" kroz render+export (A19) i finalna Kill/Pivot odluka nakon
višestrukih runova (A20) su TAKOĐE van scope-a — render/export moduli ne
postoje uopšte u kodu danas (provjereno: nema `application/render/`,
`application/export/`), a R1 pitanje (da li je struktura vrijedna) ne
zavisi od toga — render/export su prezentacija, ne utiču na kvalitet
generisanog teksta.

**Obavezno pročitati prije koda**:

```text
AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md
  §47 (A/B kontrola), §48 (determinističke metrike), §50 (Kill/Pivot —
  KONTEKST samo, ovaj task ne implementira samu odluku)
resources/prompts/ab_control/v1.yaml (VEĆ POSTOJI — koristi ga, ne piši
  novi prompt)
src/ai_campaign_studio/application/schemas/social_post_generation_output.py
  (VEĆ POSTOJI — SocialPostGenerationOutput + ContentClaimOutput, Control A
  output se gradi NA OVOME, ne izmišljaj paralelnu šemu)
src/ai_campaign_studio/application/posts/claim_linter.py (VEĆ POSTOJI —
  ponovo iskoristiti za claim-bazirane metrike, ne pisati novu logiku)
src/ai_campaign_studio/application/posts/claim_validator.py (VEĆ POSTOJI)
src/ai_campaign_studio/application/posts/content_similarity.py (VEĆ
  POSTOJI, ACS-F1-025 — `jaccard_similarity`/`SIMILARITY_THRESHOLD` —
  plan eksplicitno traži "jednostavna lexical/Jaccard metrika... heuristic
  only" za tekst-sličnost, OVO JE TA FUNKCIJA, ne piši novu)
src/ai_campaign_studio/application/campaigns/create_campaign.py,
  generate_campaign_plan.py, approve_campaign_plan.py (VEĆ POSTOJE —
  System B JE ovaj postojeći pipeline, samo se orkestrira redom)
src/ai_campaign_studio/application/posts/generate_social_post.py (VEĆ
  POSTOJI — System B poziva ovo po stavci plana)
resources/platforms/*.yaml (`text_constraints.max_chars` — za
  headline_overflow_count)
tests/integration/application/campaigns/test_generate_campaign_plan_integration.py
  (TAČAN pattern za real-repo wiring — repliciraj, ne izmišljaj novi)
```

# Objective

Tri nove, nezavisno testabilne komponente u `application/evaluation/`:

1. **`run_control_a.py`** — naivan single-call baseline (§47).
2. **`run_system_b.py`** — tanak orkestracioni wrapper oko VEĆ POSTOJEĆEG
   pravog pipeline-a (§47 "System B koristi puni pipeline" — ne
   reimplementirati, samo pozvati redom).
3. **`deterministic_metrics.py`** — 11 metrika (§48), primijenjene
   JEDNAKO na A i B izlaz (fer poređenje).

Plus **`evaluation_post.py`** — zajednička, normalizovana struktura koju
i A i B mapiraju u sebe, da metrike ne moraju znati odakle podaci dolaze.

# Implementation steps

## 1. `evaluation_post.py` — normalizovana struktura

```python
@dataclass(frozen=True)
class EvaluationPost:
    """One generated post, normalized so deterministic_metrics.py can
    treat Control A and System B output identically."""
    role: str | None          # None za Control A (nema role koncept)
    topic: str | None         # None za Control A
    headline: str
    caption: str
    hook: str
    body: str
    cta: str
    hashtags: tuple[str, ...]
    platform_code: str | None  # None za Control A (nema per-post target)
    format_code: str | None
    claims: tuple[ContentClaim, ...]  # VEĆ LINTOVANE (isti claim_linter
                                       # poziv za oba, vidi korak 2/3)
```

(`ContentClaim` je postojeći domain tip iz `domain/content/claims.py` —
uvezi ga, ne izmišljaj paralelan.)

## 2. `run_control_a.py`

```python
def run_control_a(
    brand_snapshot: BrandSnapshot,
    snapshot_facts: tuple[ApprovedFact, ...],
    brief: CampaignBrief,
    prompt_repo: PromptRepositoryPort,
    ai_port: TextGenerationPort,
    claim_rules: ClaimRules,
) -> tuple[EvaluationPost, ...]:
```

- Učitaj `prompt_repo.get("ab_control", "1")`.
- Izgradi `AIRequest` — `user_text` sadrži brand snapshot summary (isti
  stil kao `_build_user_text` u `generate_campaign_plan.py`/
  `generate_social_post.py`, ali BEZ role/template/facts_needed
  strukture — samo "evo brenda, evo brief-a, napiši N postova"), SVE
  `snapshot_facts` kao običan kontekst (§47: "Može dobiti sve Approved
  Facts kao obični brand context jer cilj nije sabotirati kontrolu").
  `json_schema` = nova `ControlAOutput` (korak 4).
- Pozovi `ai_port.generate(request)`, validiraj `structured_payload`
  protiv `ControlAOutput`.
- Za SVAKI post u odgovoru: pretvori u `ContentClaim` domain objekte
  (isti pattern kao `validate_claim` poziv u `generate_social_post.py`),
  pa **primijeni ISTI `lint_claim`** (iz `claim_linter.py`) sa istim
  `claim_rules` — fer, jednaka provjera kao System B dobija.
- Vrati `tuple[EvaluationPost, ...]`, `role=None`, `topic=None`,
  `platform_code=None`, `format_code=None` za svaki (Control A nema te
  koncepte).
- **NE PERZISTUJE ništa u bazu** — ovo je čisto evaluacioni poziv, bez
  DB pisanja (nema Campaign/ContentPiece redova za Control A).

## 3. `run_system_b.py`

```python
def run_system_b(
    brand_id: BrandId,
    brand_snapshot_id: BrandSnapshotId,
    raw_brief: dict,
    campaign_repo: CampaignRepositoryPort,
    brand_repo: BrandRepositoryPort,
    fact_repo: FactRepositoryPort,
    content_repo: ContentRepositoryPort,
    revision_repo: RevisionRepositoryPort,
    prompt_repo: PromptRepositoryPort,
    ai_port: TextGenerationPort,
    unit_of_work: ...,
) -> tuple[EvaluationPost, ...]:
```

Orkestrira REDOM (ništa novo, samo poziva postojeće use-case-e tačno
kako GUI bridge to već radi za prva dva koraka):

1. `CreateCampaign(...).execute(brand_id, brand_snapshot_id, raw_brief)`
2. `GenerateCampaignPlan(...).execute(campaign.id)`
3. `ApproveCampaignPlan(...).execute(plan.id)` (VEĆ POSTOJI, provjeri
   tačan potpis prije koda — ovo bridge trenutno NE poziva, ali System B
   MORA proći kroz ovaj korak jer `GenerateSocialPost` zahtijeva
   `CampaignPlanStatus.APPROVED`)
4. Za SVAKU stavku odobrenog plana: `GenerateSocialPost(...).execute(
   campaign.id, plan.id, item.id, target)` (jedan `CampaignTarget` po
   stavci — iz brief-ovih `targets`, isti kao brief prosljeđen u
   `CreateCampaign`)
5. Mapiraj svaki rezultujući `ContentPiece` u `EvaluationPost`
   (`role=item.role.value`, `topic=item.topic`, `claims=piece.claims` —
   VEĆ lintovane od strane `GenerateSocialPost` samog, ne re-lintuj).

Ovo STVARNO PERZISTUJE u bazu (isti way kao bridge) — to je namjerno,
System B JE pravi pipeline.

## 4. `application/schemas/ab_control_output.py`

```python
class ControlAOutput(BaseModel):
    model_config = ConfigDict(frozen=True)
    posts: list[SocialPostGenerationOutput]
```

(Reuse postojeći `SocialPostGenerationOutput`/`ContentClaimOutput` —
ne dupliraj polja.)

## 5. `deterministic_metrics.py`

```python
@dataclass(frozen=True)
class DeterministicMetrics:
    unique_role_count: int | None       # None za Control A (nema role)
    duplicate_topic_count: int | None   # None za Control A (nema topic)
    exact_duplicate_caption_count: int
    unsupported_fact_claim_count: int
    forbidden_phrase_hits: int
    numeric_claim_violations: int
    missing_fact_ids: int
    schema_failure_count: int
    layout_failure_count: None          # UVIJEK None -- vizuelni sistem
                                          # ne postoji, ne izmišljaj broj
    headline_overflow_count: int
    cta_unique_count: int
    heuristic_near_duplicate_count: int  # BONUS, ne u originalnoj listi
                                          # od 11 ali eksplicitno traženo
                                          # u §48 ("Jaccard kao pomoćna,
                                          # uz oznaku heuristic only") —
                                          # koristi content_similarity.
                                          # jaccard_similarity preko SVIH
                                          # parova headline+caption,
                                          # prag SIMILARITY_THRESHOLD iz
                                          # istog modula (ne izmišljaj
                                          # nov prag)

def compute_metrics(posts: tuple[EvaluationPost, ...]) -> DeterministicMetrics: ...
```

Napomene po metrici:
- `unique_role_count`/`duplicate_topic_count`: `None` ako BILO KOJI post
  ima `role`/`topic` == `None` (Control A slučaj) — ne pretvaraj `None`
  u `0`, to bi lagalo da je "nula duplikata" umjesto "nije mjereno".
- `exact_duplicate_caption_count`: tačno string poređenje (`caption`
  polje), broj PARA koji su identični (ili broj postova preko prvog
  duplikata — tvoj izbor, dokumentuj).
- `unsupported_fact_claim_count`/`forbidden_phrase_hits`/
  `numeric_claim_violations`: iz `claims` polja (VEĆ lintovanih) —
  brojanje po `ClaimStatus`/`reason_codes`, ne re-implementiraj
  claim_linter logiku ovdje.
- `missing_fact_ids`: broj `ContentClaim` sa `type=FACT` i praznim
  `fact_ids`.
- `schema_failure_count`: broj postova gdje AI odgovor NIJE prošao
  Pydantic validaciju (0 ako su svi prošli — ovo JE mjerljivo, ne None).
- `headline_overflow_count`: koristi `platform_code`/`format_code` (kad
  postoje, tj. za System B) da nađeš `text_constraints.max_chars` iz
  `resources/platforms/*.yaml` (možeš importovati `PlatformRegistry`
  iz `channels/registry.py`, VEĆ POSTOJI, samo pozovi
  `.from_bundled_resources()`); za Control A (`platform_code=None`)
  preskoči tu provjeru (ne broji, ne pretpostavljaj platformu).
- `cta_unique_count`: broj DISTINCT `cta` stringova (casefold-normalizovan).

# Acceptance

- [ ] `run_control_a` poziva pravi `TextGenerationPort` adapter (fake u
      testovima, ali potpis prihvata pravi port), koristi POSTOJEĆI
      `ab_control` prompt, NE piše u bazu.
- [ ] `run_system_b` orkestrira SVE 4 postojeća use-case-a redom
      (Create → Generate plan → Approve → Generate post × N), STVARNO
      piše u bazu (isti kao pravi GUI tok).
- [ ] `compute_metrics` vraća sve navedene metrike; `layout_failure_count`
      je UVIJEK `None`; `unique_role_count`/`duplicate_topic_count` su
      `None` kad ulaz nema role/topic.
- [ ] `heuristic_near_duplicate_count` koristi POSTOJEĆI
      `content_similarity.jaccard_similarity`/`SIMILARITY_THRESHOLD`
      (ACS-F1-025) — ne novu implementaciju.
- [ ] Claim-bazirane metrike (`unsupported_fact_claim_count` itd.)
      koriste POSTOJEĆI `claim_linter`/`claim_validator` — ne novu logiku.
- [ ] Integration test: pokreni I Control A I System B protiv ISTOG
      `brightsmile.json` fixture-a i ISTOG brief-a (fake AI port sa
      deterministic/scripted odgovorima za oba), potvrdi da
      `compute_metrics` radi na oba izlaza bez greške.
- [ ] `domain/`, `application/campaigns/`, `application/posts/`,
      `application/brands/`, `application/ai_provider/`,
      `infrastructure/`, `ports/`, `resources/prompts/`,
      `resources/claim_rules/`, `resources/migrations/` NISU DIRANI.
- [ ] `python -m pytest tests/unit/application/evaluation/
      tests/integration/application/evaluation/ -v` prolazi.
- [ ] `python -m pytest tests -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest tests/unit/application/evaluation/ tests/integration/application/evaluation/ -v
python -m pytest tests -q
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- Control A stvarno ne piše u bazu (čist evaluacioni poziv);
- System B stvarno prolazi kroz `ApproveCampaignPlan` (bridge to danas
  NE radi — provjeri da si to dodao, ne preskočio jer "bridge to ne
  radi pa ni ovdje ne treba");
- `None` vs `0` razlika za ne-mjerljive metrike je dosljedno primijenjena
  (nikad lažni "nula" za nešto što nije mjereno);
- claim-bazirane metrike stvarno pozivaju postojeći `claim_linter`, ne
  duplirati regex/logiku;
- `heuristic_near_duplicate_count` stvarno uvozi `content_similarity`,
  ne kopira Jaccard formulu.

# Rollback

MEDIUM risk — potpuno nov, izolovan paket koji poziva postojeće
use-case-e bez izmjene njihovih potpisa. Fix na istoj branch bez
proširenja scope-a. §29: Claude-only review, PASS -> odmah merge.

# Coordination

ACS-F1-027 (human_eval.py, budući task) zavisi od `EvaluationPost` oblika
definisanog ovdje — koordinator će pisati taj kontrakt tek nakon što ovaj
merguje, da se oblik ne mijenja ispod njega.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-026-ab-eval-harness
Branch:   task/ACS-F1-026-ab-eval-harness
Base:     main @ 99b1449
```
