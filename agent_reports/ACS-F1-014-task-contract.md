---
task_id: ACS-F1-014
phase: Faza-1
title: "A10 (plan-numeracija) — Plan editing/versioning/approval"
risk: MEDIUM
coordinator: claude
implementer: TBD (Human Owner assigns)
reviewers: [claude]
status: "OPEN — contract written before code"
created_at: 2026-09-02
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/application/campaigns/edit_campaign_plan.py
  - src/ai_campaign_studio/application/campaigns/reorder_campaign_item.py
  - src/ai_campaign_studio/application/campaigns/approve_campaign_plan.py
  - tests/unit/application/campaigns/test_edit_campaign_plan.py
  - tests/unit/application/campaigns/test_reorder_campaign_item.py
  - tests/unit/application/campaigns/test_approve_campaign_plan.py
  - tests/integration/application/campaigns/test_edit_campaign_plan_integration.py
  - tests/integration/application/campaigns/test_approve_campaign_plan_integration.py
forbidden_paths:
  - src/ai_campaign_studio/application/campaigns/create_campaign.py
  - src/ai_campaign_studio/application/campaigns/generate_campaign_plan.py
  - src/ai_campaign_studio/application/posts/
  - src/ai_campaign_studio/application/brands/
  - src/ai_campaign_studio/application/schemas/
  - src/ai_campaign_studio/application/mappers/
  - src/ai_campaign_studio/domain/
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
  head: d11aaec
  index_status: fresh (analyze re-run 2026-09-02 post ACS-F1-012 contract commit)
  targets:
    - symbol: "new application/campaigns/{edit_campaign_plan,reorder_campaign_item,approve_campaign_plan}.py"
      upstream_risk: NONE
      upstream_count: 0
      downstream_notes: "Brand-new files in the already-established application/campaigns/ package (ACS-F1-009). Reuse CampaignRepositoryPort.get_plan/save_plan/get_campaign/save_campaign (already exist, no port changes needed) and domain entities as-is. Does not touch create_campaign.py or generate_campaign_plan.py."
      affected_processes: []
  scope_fit: PASS
  unknowns:
    - "GenerateSocialPost (ACS-F1-011) currently does NOT check that a CampaignPlan is APPROVED
      before generating a post against it, even though plan section 32 says post generation must
      not start from a DRAFT plan. This is a real, known gap -- deliberately NOT closed by this
      task (touching generate_social_post.py here would collide with the concurrent ACS-F1-012
      task, which is also mid-flight on that same file). Left as an explicit open item for a
      future small task once ACS-F1-012 has merged."
---

# Kontekst

Task **A10 — Plan editing/versioning/approval** (plan sekcije 31 "Campaign plan manual edit" i 32
"Approve Campaign Plan"). **Task-ID je ACS-F1-014** — namjerno preskočeno ACS-F1-013, taj broj je
već rezervisan (u ACS-F1-012 kontraktu i brief-u) za budući "Content revisions" (plan sekcija 38)
task, da ne dođe do kolizije referenci.

Nastavlja ACS-F1-009 (`application/campaigns/create_campaign.py` + `generate_campaign_plan.py`,
mergovano) — treći i četvrti use-case u istom paketu, isti obrazac (Protocol portovi, atomic
persist preko `SqliteUnitOfWork`).

**Poznat, namjerno neriješen gap** (vidi `unknowns` u frontmatter-u): `GenerateSocialPost`
(ACS-F1-011, mergovano) trenutno NE provjerava da je plan `APPROVED` prije generisanja posta,
iako plan sekcija 32 eksplicitno kaže "Post generation ne smije krenuti sa DRAFT planom". Dodavanje
tog guard-a bi zahtijevalo dirati `generate_social_post.py`, isti fajl koji **paralelno** dira
ACS-F1-012 (claim linter rewiring) — namjerno OSTAVLJENO za poseban, mali budući task poslije
ACS-F1-012 merge-a, da se izbjegne konflikt na istom fajlu. Ne pokušavati "usput" riješiti ovaj gap
u ovom tasku.

**Risk**: MEDIUM — orchestration nad već review-ovanim slojevima (isti klasa kao ACS-F1-009), ne
dira SecretStore/migracije/registry contracts. §29: Claude-only review, PASS → odmah merge.

Prije koda pročitati:

```text
AGENTS.md
CLAUDE.md
docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md
.agent/CURRENT_STATE.md
AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md
  sekcija 31 "Campaign plan manual edit", sekcija 32 "Approve Campaign Plan"
```

Pročitati postojeći kod koji se orkestrira:

```text
src/ai_campaign_studio/application/campaigns/create_campaign.py (STIL primjer, ACS-F1-009)
src/ai_campaign_studio/application/campaigns/generate_campaign_plan.py (STIL primjer + domain
  validation pattern koji ćeš ponoviti — order uniqueness, non-empty topic)
src/ai_campaign_studio/domain/campaign/entities.py (Campaign, CampaignPlan, CampaignItem)
src/ai_campaign_studio/domain/campaign/enums.py (CampaignStatus, CampaignPlanStatus,
  CampaignItemStatus)
src/ai_campaign_studio/ports/repositories.py (CampaignRepositoryPort — get_plan/save_plan/
  get_campaign/save_campaign već postoje, NE dodavati nove metode)
```

# Objective

1. `application/campaigns/edit_campaign_plan.py` — `EditCampaignPlan` use-case.
2. `application/campaigns/reorder_campaign_item.py` — `ReorderCampaignItem` use-case (deleguje
   na `EditCampaignPlan` interno — ne duplirati versioning/persist logiku).
3. `application/campaigns/approve_campaign_plan.py` — `ApproveCampaignPlan` use-case.

# Implementation steps

## Zajednički versioning princip (obje edit-klase)

Svaka izmjena (edit ILI reorder) plana:

1. Učitati stari plan (`campaign_repo.get_plan(plan_id)`) — `None` → `EntityNotFound`.
2. **Mora biti `CampaignPlanStatus.DRAFT`** — "Ne mutirati odobreni plan" znači i APPROVED i
   SUPERSEDED planovi se NE mogu editovati. Bilo koji drugi status → `InvariantViolation`.
3. Konstruisati NOVI `CampaignPlan` (`id=new_id()`, `version=old.version + 1`, `status=DRAFT`,
   `items=<nova lista>`).
4. Stari plan → `dataclasses.replace(old, status=CampaignPlanStatus.SUPERSEDED)`.
5. Perzistirati OBA (`save_plan(old_superseded)`, `save_plan(new_plan)`) unutar JEDNE
   `SqliteUnitOfWork` transakcije.
6. Domain validacija na NOVOJ listi itema PRIJE perzistencije (isti obrazac kao
   `generate_campaign_plan.py`): `order` unique, svaki `topic` non-empty. Ne provjeravati item
   count protiv `brief.content_piece_count` — edit SMIJE mijenjati broj itema (dodaj/obriši).

## `EditCampaignPlan`

```python
class EditCampaignPlan:
    def __init__(self, campaign_repo: CampaignRepositoryPort,
                 unit_of_work: _UnitOfWork) -> None: ...
    def execute(self, plan_id: CampaignPlanId,
                updated_items: tuple[CampaignItem, ...]) -> CampaignPlan: ...
```

Namjerno JEDNOSTAVAN API: pozivalac šalje CIJELU novu listu itema kakvu novi plan treba imati —
"change topic/change goal/change role" znači pozivalac šalje izmijenjen `CampaignItem` na istom
mjestu; "delete item" znači pozivalac ga izostavi iz liste; "add item" znači pozivalac doda novi
`CampaignItem` (implementer/pozivalac konstruiše `id=new_id()`, `status=PLANNED`); "replace item"
znači pozivalac pošalje potpuno drugačiji item na istom `order`. **Use-case sam ne pravi command
API za svaki tip izmjene** — to bi bilo prerano uopštavanje za jedan poziv (AR3 disciplina).

`order` polje na novim itemima: implementer bira da li ih pozivalac eksplicitno numeriše, ili
`EditCampaignPlan` normalizuje redoslijed liste u `1..N` sam — dokumentovati izbor. Preporučeno:
pozivalac šalje items u željenom redoslijedu, use-case dodijeli `order = 1..N` po poziciji u listi
(jednostavnije, manje prostora za grešku pozivaoca), ALI onda mora vratiti items sa PRAVILNO
postavljenim `order` (ne vjerovati ulaznom `order` polju uopšte za ovaj use-case).

## `ReorderCampaignItem`

```python
class ReorderCampaignItem:
    def __init__(self, campaign_repo: CampaignRepositoryPort,
                 unit_of_work: _UnitOfWork) -> None: ...
    def execute(self, plan_id: CampaignPlanId,
                ordered_item_ids: tuple[CampaignItemId, ...]) -> CampaignPlan: ...
```

Učitava stari plan, provjerava da `ordered_item_ids` je permutacija POSTOJEĆIH item id-jeva u
planu (isti skup, drugi redoslijed — ako fali id ili ima nepoznat id, `InvariantViolation` PRIJE
bilo kakve izmjene), gradi novu `tuple[CampaignItem, ...]` u tom redoslijedu sa `order`
prepostavljenim `1..N`, pa **delegira na `EditCampaignPlan.execute(plan_id, reordered_items)`**
(kompozicija — reorder NE duplira versioning/persist/validation logiku, samo priprema listu i
zove edit).

## `ApproveCampaignPlan`

```python
class ApproveCampaignPlan:
    def __init__(self, campaign_repo: CampaignRepositoryPort,
                 unit_of_work: _UnitOfWork) -> None: ...
    def execute(self, plan_id: CampaignPlanId) -> CampaignPlan: ...
```

1. Učitati plan — `None` → `EntityNotFound`.
2. Mora biti `CampaignPlanStatus.DRAFT` (ne SUPERSEDED, ne već APPROVED) — inače
   `InvariantViolation`.
3. Provjere PRIJE odobrenja (plan sekcija 32): broj itema > 0; nema duplicate `order`; svaki item
   ima non-empty `role`/`topic`/`goal` (role je već enum-garantovan strukturno; topic/goal
   string-provjera).
4. `dataclasses.replace(plan, status=CampaignPlanStatus.APPROVED)`.
5. Učitati vlasnički `Campaign` (`campaign_repo.get_campaign(plan.campaign_id)`) — `None` →
   `EntityNotFound` (ne bi trebalo biti moguće u praksi, ali provjeriti).
   `dataclasses.replace(campaign, status=CampaignStatus.PLAN_APPROVED)`.
6. Perzistirati OBA (`save_plan`, `save_campaign`) atomično.
7. Vratiti odobreni `CampaignPlan`.

"Ne auto-approve post" — ovaj use-case NE dira `ContentPiece`/postove, samo `CampaignPlan`/
`Campaign` status.

# Acceptance

- [ ] `EditCampaignPlan`: uspješna izmjena kreira NOVI `CampaignPlan` (novi `id`,
      `version = old.version + 1`, `status=DRAFT`); stari plan postaje `SUPERSEDED` — OBA
      perzistovana (test čita nazad oba kroz `get_plan`).
- [ ] `EditCampaignPlan`: pokušaj editovanja NE-DRAFT plana (APPROVED ili SUPERSEDED) →
      `InvariantViolation`, ništa novo nije perzistovano (test za oba statusa).
- [ ] `EditCampaignPlan`: duplicate `order` u novoj listi itema → `InvariantViolation` PRIJE
      perzistencije (stari plan ostaje netaknut — test dokazuje).
- [ ] `EditCampaignPlan`: prazan `topic` → `InvariantViolation` (isti obrazac kao
      `generate_campaign_plan.py`-ova domain validacija).
- [ ] `EditCampaignPlan`: add/delete/replace item scenariji testirani (bar po jedan test za svaki
      od tri).
- [ ] `EditCampaignPlan`: atomicity test (mid-persist failure — npr. `save_plan` na novom planu
      failuje nakon uspješnog `save_plan` na starom — stari plan OSTAJE DRAFT, ne SUPERSEDED; na
      pravoj SQLite bazi).
- [ ] `ReorderCampaignItem`: novi redoslijed → nova plan verzija, `order` polja tačno `1..N` po
      novom redoslijedu (test).
- [ ] `ReorderCampaignItem`: `ordered_item_ids` koji ne odgovara skupu postojećih item id-jeva
      (fali jedan, ili ima nepoznat) → `InvariantViolation` PRIJE bilo kakve izmjene (test za oba
      slučaja).
- [ ] `ApproveCampaignPlan`: uspješno odobrenje → `CampaignPlan.status == APPROVED` I
      `Campaign.status == PLAN_APPROVED`, oba perzistovana atomično (test).
- [ ] `ApproveCampaignPlan`: pokušaj odobrenja NE-DRAFT plana → `InvariantViolation` (test za
      APPROVED i za SUPERSEDED polazni status).
- [ ] `ApproveCampaignPlan`: plan sa duplicate `order` ili praznim `topic`/`goal` → odbijen PRIJE
      promjene statusa (test).
- [ ] Svi use-case-i zavise SAMO od `CampaignRepositoryPort` + lokalnog `_UnitOfWork` Protocol-a
      (isti obrazac kao ACS-F1-009) — provjeriti import-e.
- [ ] Integration testovi na pravoj SQLite bazi (isti obrazac kao ACS-F1-005..011).
- [ ] `python -m pytest -q`, `ruff check .`, `mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths` — POSEBNO ne `generate_social_post.py` (poznat gap, vidi
      Kontekst, namjerno van scope-a).

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest -q
python -m pytest tests/architecture/test_import_boundaries.py -v
python -m pytest tests/unit/application/campaigns tests/integration/application/campaigns -v
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- versioning invariant je STVARNO atomičan (stari SUPERSEDED + novi DRAFT persistuju zajedno ili
  nijedan — testirano na pravoj bazi, ne samo tvrđeno);
- editovanje NE-DRAFT plana je nemoguće (APPROVED i SUPERSEDED oba blokirana, ne samo jedan);
- `ReorderCampaignItem` stvarno deleguje na `EditCampaignPlan` (nema duplirane persist/validation
  logike — DRY provjera diff-om);
- `ApproveCampaignPlan` ažurira OBA (`CampaignPlan` i `Campaign`) atomično;
- `generate_social_post.py` NIJE diran (poznat gap ostaje dokumentovan, ne "usput riješen" na
  pola posla koji bi mogao konfliktovati sa paralelnim ACS-F1-012);
- scope discipline — nema dirania `create_campaign.py`/`generate_campaign_plan.py`.

# Rollback

MEDIUM risk — nova, izolovana orchestration logika u već-postojećem paketu. Fix na istoj branch
bez proširenja scope-a.

# Coordination

Nezavisan od ACS-F1-012 (claim linter — različit paket, `application/posts/` vs
`application/campaigns/`), može ići paralelno. **NE dirati `generate_social_post.py`** (vidi
Kontekst) da se izbjegne konflikt sa ACS-F1-012 koji je trenutno u toku na tom fajlu.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-014-campaign-plan-editing
Branch:   task/ACS-F1-014-campaign-plan-editing
Base:     main @ d11aaec
```
