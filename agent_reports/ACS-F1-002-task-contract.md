---
task_id: ACS-F1-002
phase: Faza-1
title: "Campaign domain + Content domain + Visual domain (A3, dio 2)"
risk: MEDIUM
coordinator: claude
implementer: crush
reviewers: [claude]
status: "OPEN — contract written before code"
created_at: 2026-09-02
dependencies: [ACS-F1-001]
allowed_paths:
  - src/ai_campaign_studio/domain/campaign/
  - src/ai_campaign_studio/domain/content/
  - src/ai_campaign_studio/domain/visual/
  - resources/campaign_templates/
  - tests/unit/domain/campaign/
  - tests/unit/domain/content/
  - tests/unit/domain/visual/
forbidden_paths:
  - src/ai_campaign_studio/domain/common/
  - src/ai_campaign_studio/domain/brand/
  - src/ai_campaign_studio/domain/facts/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/channels/
  - src/ai_campaign_studio/localization/
  - src/ai_campaign_studio/ai_registry/
  - src/ai_campaign_studio/infrastructure/
  - src/ai_campaign_studio/jobs/
  - src/ai_campaign_studio/presentation/
  - src/ai_campaign_studio/bootstrap.py
  - src/ai_campaign_studio/main.py
gitnexus_required: true
adversarial_required: false
gitnexus:
  required: true
  repository: "H:\\AI Campaing Studio"
  worktree: main (pre-branch pre-impact)
  branch: main
  head: 215d528
  index_status: stale — analyze re-run recommended before this task's merge, not blocking for pre-impact
  targets:
    - symbol: "new directories domain/campaign, domain/content, domain/visual"
      upstream_risk: NONE
      upstream_count: 0
      downstream_notes: "Brand-new directories, zero existing importers. Depends on domain/common/ids.py type aliases from ACS-F1-001 for entities.py files specifically — see Coordination section for sequencing."
      affected_processes: []
  scope_fit: PASS
  unknowns: []
---

# Kontekst

Drugi dio taska **A3 — Common + Domain enums/entities** iz
`AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md`, paralelno sa
ACS-F1-001 (Pi) koji radi `domain/common` extension + Brand + Facts. Ovaj
task pokriva Campaign, Content i Visual domene.

**Rule 0A.5 (protiv dupliranja)**: nijedan od ovih direktorijuma trenutno
ne postoji u repo-u — čista implementacija, nema šta da se dupira.

**Risk**: MEDIUM, ne HIGH — isti obrazloženje kao ACS-F1-001 (čist domain
sloj, postojeći `test_import_boundaries.py` je safety net). §29 politika:
Claude-only review, PASS → odmah commit/push/merge.

**VAŽNA ZAVISNOST**: `domain/campaign/entities.py` i `domain/content/entities.py`
koriste typed ID aliase (`BrandSnapshotId`, `FactId`, itd.) koje definiše
ACS-F1-001 u `domain/common/ids.py`. Vidi sekciju "Redoslijed rada" ispod
za tačno šta raditi prije/poslije toga.

Prije koda pročitati:

```text
AGENTS.md
CLAUDE.md
docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md
.agent/CURRENT_STATE.md
AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md
  sekcije 0A (cijela), 8 (domain model princip), 12 (Campaign domain),
  13 (Content domain), 14 (Visual domain)
```

# Objective

1. `domain/campaign/` — enums, roles, templates, entities.
2. `domain/content/` — enums, claims, revisions, entities.
3. `domain/visual/` — enums, entities, layout, slots.

# Redoslijed rada (zbog zavisnosti na ACS-F1-001)

**Odmah, bez čekanja** (nema zavisnosti na `domain/common`):

- `campaign/enums.py`, `campaign/roles.py`, `campaign/templates.py`
- `content/enums.py`
- `visual/enums.py`, `visual/slots.py` (ContentSlotContract ne referencira
  typed ID-jeve iz common-a)

**Tek kad koordinator potvrdi da je ACS-F1-001 merged** (ili barem da
`domain/common/ids.py` sadrži typed ID aliase na disku):

- `campaign/entities.py`, `content/entities.py`, `content/claims.py`,
  `content/revisions.py`, `visual/entities.py`, `visual/layout.py`

Ako ACS-F1-001 još nije spreman kad implementer stigne do entities.py
fajlova — javiti koordinatoru, ne izmišljati privremene lokalne ID tipove
(to bi bilo dupliranje koje 0A.5 zabranjuje).

# Implementation steps

## `domain/campaign/enums.py`

```text
CampaignStatus: DRAFT, PLAN_GENERATED, PLAN_APPROVED, GENERATING_POSTS,
                IN_REVIEW, APPROVED, EXPORTED
CampaignPlanStatus: DRAFT, APPROVED, SUPERSEDED
CampaignItemStatus: PLANNED, APPROVED, GENERATED, REJECTED
```

## `domain/campaign/roles.py`

```text
CampaignRole enum: PROBLEM, EDUCATION, INSIGHT, BENEFIT, PROOF, TRUST,
OBJECTION, MYTH_BUSTING, COMPARISON, BEHIND_THE_SCENES, PRODUCT, OFFER,
URGENCY, ACTION, COMMUNITY, STORY, FAQ
```

## `domain/campaign/templates.py`

```text
CampaignTemplate (id, name, role_sequence[])
```

Početni resource template `lead_generation_v1`, sekvenca: PROBLEM,
EDUCATION, PROOF, OBJECTION, BENEFIT, OFFER, ACTION. Domain-level
predstavljanje ovdje; ako se odluči da template živi kao resource fajl
(YAML/JSON), staviti pod `resources/campaign_templates/` — konzistentno
sa data-driven obrascem koji `channels/`/`ai_registry/` već koriste u P0
(ne hardcoded Python literal ako P0 obrazac sugeriše resource fajl —
implementer odlučuje na osnovu čitljivosti, ali dokumentovati izbor).

## `domain/campaign/entities.py` (nakon ACS-F1-001)

```text
CampaignBrief (id, offer, goal, audience_text, targets[], content_piece_count,
               content_language_context, special_instructions[], created_at)
Campaign (id, brand_id, brand_snapshot_id, brief_id, status, created_at)
CampaignPlan (id, campaign_id, version, status, items[], created_at)
CampaignItem (id, order, role, topic, goal, target_audience_id?,
              facts_needed[], status)
```

`facts_needed` je semantička potreba (string/opis), ne nužno stvaran fact
ID — actual fact selection radi kasniji use-case (van ovog taska).

## `domain/content/enums.py`

```text
ContentStatus: PLANNED, GENERATING, DRAFT, NEEDS_REVIEW, APPROVED,
               REJECTED, EXPORTED
ContentPayloadType: SOCIAL_POST  (samo ovo za Fazu 1)
ClaimType: FACT, CTA, OPINION, CREATIVE
ClaimStatus: VERIFIED_BY_FACT, UNSUPPORTED, USER_APPROVED, PROHIBITED,
             NON_FACTUAL
```

## `domain/content/claims.py`

```text
ContentClaim (id, text, type, fact_ids[], status, reason_codes[])
```

## `domain/content/revisions.py`

```text
Revision (id, entity_type, entity_id, version, timestamp, origin,
          provider?, model?, prompt_version?, previous_value, new_value,
          instruction?)
origin: MANUAL | AI | SYSTEM
```

**Napomena (analytics-ready)**: `Revision.id` je ono što
`AI_Campaign_Studio_Faza_0_7_Performance_Analytics_Architecture.md`
naziva `content_revision_id` — dozvoljeno i traženo prije G10 po
`.agent/TASK_ROUTING.md` "Performance / Analytics task" sekciji A. Nema
dodatnih polja potrebnih van onoga što je već navedeno ovdje.

## `domain/content/entities.py` (nakon ACS-F1-001)

```text
CampaignTarget (channel, platform_code, format_code)
ContentPiece (id, campaign_item_id, target, payload_type, status,
              brand_snapshot_id, facts_allowed[], claims[], revision_ids[],
              created_at, updated_at)
SocialPostPayload (headline, caption, hook, body, cta, hashtags[],
                    visual_direction?)
```

Pravilo: Approved `ContentPiece` se ne mijenja tiho — revizija Approved
sadržaja mora kreirati novi revision zapis i vratiti status u
`NEEDS_REVIEW`. Ovo je PRAVILO za kasniji use-case sloj (ne nužno
enforced unutar same dataclass ovdje, pošto su domain modeli plain
dataclasses bez use-case logike) — dokumentovati pravilo jasno u
docstring-u `ContentPiece`-a kao ugovor koji application sloj mora
poštovati.

## `domain/visual/enums.py`

```text
LayoutPrimitive (Slice 1 minimalno): HERO, SPLIT
```

Arhitektura mora dozvoliti kasnije: FAQ, QUOTE, PRODUCT, CTA, STAT,
COMPARISON, TESTIMONIAL, FEATURE — ne implementirati te sada, samo ne
zatvarati enum na način koji bi to onemogućio (npr. ne raditi closed
match-statement negdje koji bi pukao na dodatak).

## `domain/visual/entities.py` (nakon ACS-F1-001)

```text
CampaignVisualSystem (id, campaign_id, style[], primary_layout_family,
                       secondary_layout_family?, headline_scale,
                       image_treatment, logo_rule, cta_rule, alignment,
                       created_at)
```

## `domain/visual/layout.py` (nakon ACS-F1-001, ako referencira campaign_id tipove — provjeriti)

```text
LayoutSpec (primitive, image_position, headline_position, headline_scale,
            overlay, logo_position, cta_style, alignment, format)
```

Dozvoljene vrijednosti su enum/value object, NE slobodni stringovi iz
LLM-a — ovo je bezbjednosno/kvalitetno bitno pravilo, ne stilska
preferenca.

## `domain/visual/slots.py`

```text
ContentSlotContract (slot_name, target_chars, max_chars, max_lines,
                      preferred_case, allow_wrap, font_family,
                      min_font_size, max_font_size, bounding_box,
                      line_height, alignment, overflow_policy)
```

Za Slice 1 minimalno: `headline`, `cta`. Caption nije dio raster layouta
u prvom rendereru — ne dodavati caption slot sada.

# Acceptance

- [ ] Svi novi moduli su plain dataclasses/enums (Pydantic NIJE korišten).
- [ ] `LayoutSpec` polja su enum/value object tipovi, ne goli `str` koji bi
      dozvolio proizvoljan LLM output da prođe netestiran.
- [ ] `CampaignTemplate.lead_generation_v1` sekvenca ima tačno 7 uloga
      navedenih redom, bez duplikata.
- [ ] Nema infrastructure importa — potvrđeno kroz
      `tests/architecture/test_import_boundaries.py`.
- [ ] `python -m pytest -q`, `ruff check .`, `mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.
- [ ] `entities.py` fajlovi ne pišu privremene lokalne ID tipove umjesto
      čekanja na ACS-F1-001 (provjeriti da import dolazi iz
      `domain.common.ids`, ne iz lokalno definisanog aliasa).

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest -q
python -m pytest tests/architecture/test_import_boundaries.py -v
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- domain modeli su plain dataclasses, ne Pydantic;
- `tuple[str, ...]` za immutable kolekcije;
- `LayoutSpec`/`ContentSlotContract` vrijednosti su tipizirane, ne goli
  string passthrough iz potencijalnog LLM outputa (ovo je stvarna zaštita
  protiv kasnijeg "LLM je vratilo nešto čudno pa je layout eksplodirao"
  klase bugova);
- `entities.py` fajlovi stvarno importuju typed ID-jeve iz
  `domain.common.ids` (ACS-F1-001), ne dupliraju ih lokalno;
- scope discipline — nema dirania `common/`, `brand/`, `facts/`
  (ACS-F1-001 teritorija).

# Rollback

MEDIUM risk, isto obrazloženje kao ACS-F1-001. Fix na istoj branch bez
proširenja scope-a. STOP i vrati na puni ciklus ako se otkrije da task
dira nešto sa HIGH liste.

# Coordination

Paralelno sa **ACS-F1-001** (Pi). `allowed_paths` disjoint (provjereno,
uključujući package `__init__.py` fajlove — nijedan nije eksplicitno
naveden u oba kontrakta, tvoriće se prirodno u svakom novom paketu bez
konflikta jer su direktorijumi potpuno odvojeni).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-002-domain-campaign-content-visual
Branch:   task/ACS-F1-002-domain-campaign-content-visual
Base:     main @ 215d528
```
