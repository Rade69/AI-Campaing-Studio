---
task_id: FLOW-1000
title: "Plan-approved guard u GenerateSocialPost"
phase: Faza-1
risk: MEDIUM
coordinator: claude
implementer: TBD (Human Owner assigns)
reviewers: [claude]
status: "OPEN — contract written before code"
created_at: 2026-09-02
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/application/posts/generate_social_post.py
  - tests/unit/application/posts/test_generate_social_post.py
  - tests/integration/application/posts/test_generate_social_post_integration.py
forbidden_paths:
  - src/ai_campaign_studio/application/posts/select_allowed_facts.py
  - src/ai_campaign_studio/application/posts/claim_validator.py
  - src/ai_campaign_studio/application/posts/claim_linter.py
  - src/ai_campaign_studio/application/posts/derive_content_status.py
  - src/ai_campaign_studio/application/campaigns/
  - src/ai_campaign_studio/application/brands/
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
  head: 52e2638
  index_status: fresh (analyze re-run 2026-09-02 post ACS-F1-014 merge)
  targets:
    - symbol: "GenerateSocialPost (application/posts/generate_social_post.py) — adding a guard clause"
      upstream_risk: LOW
      upstream_count: 0
      downstream_notes: "Zero upstream importers besides its own test files (still not wired into bootstrap/GUI/CLI). Public execute() signature does not change — only a new early-exit check inside it."
      affected_processes: []
  scope_fit: PASS
  unknowns: []
---

# Kontekst

**Prvi task pod novom `FLOW-NNNN` šemom** (`docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md` §31) —
naslov ide UZ broj svaki put kad se pominje, nikad "FLOW-1000" golo.

Poznat, dokumentovan gap iz ACS-F1-014 (Plan editing/versioning/approval, mergovano): plan
sekcija 32 eksplicitno kaže "Post generation ne smije krenuti sa DRAFT planom", ali
`GenerateSocialPost` (ACS-F1-011, mergovano, prežicano u ACS-F1-012) trenutno UOPŠTE ne provjerava
`plan.status` prije generisanja posta — može se pozvati nad `DRAFT`, čak i `SUPERSEDED` planom.
Namjerno nije popravljeno u ACS-F1-014 da se izbjegne fajl-konflikt sa paralelnim ACS-F1-012 (oba
su tada dirala `generate_social_post.py`). Oba taska su sada mergovana — put je čist.

**Risk**: MEDIUM — jedna guard klauzula u već-postojećem, izolovanom use-case-u (isti klasa rizika
kao ostali `application/posts/` taskovi). §29: Claude-only review, PASS → odmah merge.

Prije koda pročitati:

```text
AGENTS.md
CLAUDE.md
docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md
.agent/CURRENT_STATE.md
AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md
  sekcija 32 "Approve Campaign Plan" (rečenica "Post generation ne smije krenuti sa DRAFT planom")
```

Pročitati postojeći kod:

```text
src/ai_campaign_studio/application/posts/generate_social_post.py (execute() metoda — tačno mjesto
  gdje se plan učitava, prije bilo kakvog AI poziva)
src/ai_campaign_studio/domain/campaign/enums.py (CampaignPlanStatus — DRAFT/APPROVED/SUPERSEDED)
src/ai_campaign_studio/application/campaigns/approve_campaign_plan.py (ACS-F1-014 — stil primjer
  kako se `InvariantViolation` baca za pogrešan plan status)
```

# Objective

Dodati provjeru: `GenerateSocialPost.execute()` odbija generisanje posta ako plan nije
`CampaignPlanStatus.APPROVED`.

# Implementation steps

U `execute()`, ODMAH nakon `plan = self._campaign_repo.get_plan(plan_id)` i `None`-provjere
(prije pretrage `campaign_item`-a u `plan.items`, prije bilo kakvog AI poziva):

```python
if plan.status is not CampaignPlanStatus.APPROVED:
    raise InvariantViolation(
        f"campaign plan {plan_id} is {plan.status.value}; only an APPROVED "
        "plan can be used to generate posts"
    )
```

Dodati `CampaignPlanStatus` u postojeći import iz `domain.campaign.enums` (fajl trenutno uvozi
samo iz `domain.content.enums`/drugih — provjeriti tačan postojeći import blok, dodati novi ako
ne postoji).

**Ažurirati postojeće fixture-e u oba test fajla** (`test_generate_social_post.py`,
`test_generate_social_post_integration.py`): `_plan()` helper trenutno konstruiše plan sa
`status=CampaignPlanStatus.DRAFT` — svi POSTOJEĆI happy-path testovi će sad pasti ako se ne
promijeni na `CampaignPlanStatus.APPROVED` (plan mora biti odobren da bi post generacija uopšte
prošla). Ovo NIJE oslabljivanje testa — happy path sad ispravno zahtijeva odobren plan, isto kao
što je ACS-F1-012 morao ažurirati `GENERATING`→`DRAFT` assertions.

# Acceptance

- [ ] Generisanje posta nad `DRAFT` planom → `InvariantViolation`, PRIJE bilo kakvog AI poziva
      (fake AI port dokazuje da `generate()` nije pozvan — provjeri `call_count`/`requests` na
      fake portu, ne samo da exception postoji) i prije bilo kakve perzistencije.
- [ ] Generisanje posta nad `SUPERSEDED` planom → isto (`InvariantViolation`, bez AI poziva/
      perzistencije).
- [ ] Generisanje posta nad `APPROVED` planom i dalje radi (happy path, postojeći testovi
      ažurirani da koriste `APPROVED` fixture, NE obrisani).
- [ ] Integration test: isti scenario (DRAFT plan → odbijen) na pravoj SQLite bazi, koristeći
      ACS-F1-014-ov `ApproveCampaignPlan` da dobiješ pravi `APPROVED` plan za happy-path
      integration test (ili ručno konstruisan `APPROVED` plan — implementer bira, dokumentuje).
- [ ] `python -m pytest -q`, `ruff check .`, `mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest -q
python -m pytest tests/architecture/test_import_boundaries.py -v
python -m pytest tests/unit/application/posts/test_generate_social_post.py tests/integration/application/posts/test_generate_social_post_integration.py -v
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- guard je STVARNO prije AI poziva (provjeriti da fake AI port `call_count`/`requests` ostaje 0 u
  negative testovima, ne samo da exception postoji negdje u toku);
- SVI postojeći happy-path testovi su ažurirani na `APPROVED` fixture, nijedan obrisan/oslabljen;
- nema dirania `select_allowed_facts.py`/`claim_validator.py`/`claim_linter.py`/
  `derive_content_status.py`/`application/campaigns/` — samo guard u `generate_social_post.py`.

# Rollback

MEDIUM risk — jedna guard klauzula. Fix na istoj branch bez proširenja scope-a.

# Coordination

Nezavisan od svega trenutno otvorenog (trenutno nema drugih OPEN taskova).

```text
Worktree: ../ai-campaign-studio-worktrees/FLOW-1000-plan-approved-guard
Branch:   task/FLOW-1000-plan-approved-guard
Base:     main @ 52e2638
```
