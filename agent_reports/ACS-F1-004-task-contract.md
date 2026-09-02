---
task_id: ACS-F1-004
phase: Faza-1
title: "Campaign/Content/Visual boundary schemas (A4, dio 2)"
risk: MEDIUM
coordinator: claude
implementer: crush
reviewers: [claude]
status: "OPEN — contract written before code"
created_at: 2026-09-02
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/application/schemas/campaign_brief.py
  - src/ai_campaign_studio/application/schemas/campaign_plan_output.py
  - src/ai_campaign_studio/application/schemas/social_post_generation_output.py
  - src/ai_campaign_studio/application/schemas/revision_output.py
  - src/ai_campaign_studio/application/schemas/visual_direction_output.py
  - src/ai_campaign_studio/application/schemas/__init__.py
  - src/ai_campaign_studio/domain/visual/enums.py
  - tests/unit/application/schemas/
forbidden_paths:
  - src/ai_campaign_studio/domain/common/
  - src/ai_campaign_studio/domain/brand/
  - src/ai_campaign_studio/domain/facts/
  - src/ai_campaign_studio/domain/campaign/
  - src/ai_campaign_studio/domain/content/
  - src/ai_campaign_studio/domain/visual/entities.py
  - src/ai_campaign_studio/domain/visual/layout.py
  - src/ai_campaign_studio/domain/visual/slots.py
  - src/ai_campaign_studio/application/schemas/brand_fixture.py
  - src/ai_campaign_studio/application/mappers/
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
  head: 0edae77
  index_status: fresh (analyze re-run 2026-09-02 post ACS-F1-002 + docs/gui-v3 work)
  targets:
    - symbol: "new files under application/schemas/, extension of domain/visual/enums.py"
      upstream_risk: LOW
      upstream_count: "domain/visual/enums.py already has existing importers (domain/visual/entities.py, domain/visual/layout.py) — this task only ADDS new enum members/classes for image_treatment/logo_rule/cta_rule typing, does not change existing enum values (LayoutPrimitive, Alignment, HeadlineScale, etc.) used by ACS-F1-002's merged code."
      downstream_notes: "application/schemas/ has zero existing importers (verified). Pure additive."
      affected_processes: []
  scope_fit: PASS
  unknowns: []
---

# Kontekst

Task **A4 — Pydantic boundary schemas**, sekcija 15, drugi dio. Paralelno
sa **ACS-F1-003** (Pi) — `brand_fixture.py`. Nema zavisnosti između ova
dva taska. Domain sloj (A3, ACS-F1-001 + ACS-F1-002) je potpuno gotov i
merged — svi entiteti koje ovi schema-i mapiraju već postoje kao plain
frozen dataclasses.

**Rule 0A.5**: `application/schemas/` ne postoji (samo `__init__.py`) —
čista implementacija.

**Poznata napomena iz A3** (docstring `domain/visual/entities.py`
`CampaignVisualSystem`): "`image_treatment`/`logo_rule`/`cta_rule` are left
as plain strings for A3 (their full enum taxonomy is not specified); the
A4 boundary schema will type them." Ovaj task je taj trenutak — ako
`visual_direction_output.py` treba tipizirane vrijednosti za ta tri polja,
dozvoljeno je dodati nove enume u `domain/visual/enums.py` (ne mijenjati
postojeće enume, samo dodati nove). `CampaignVisualSystem`/`LayoutSpec`
dataclass-ovi u `entities.py`/`layout.py` se NE mijenjaju u ovom tasku —
ako se pokaže da baš to polje (tip `str` -> tip `Enum`) mora promijeniti
na samom entitetu, javiti koordinatoru prije nego se to uradi (to bi bio
dodir van `allowed_paths`, potencijalno zahtijeva redefinisanje
kontrakta), ne raditi to tiho.

**Risk**: MEDIUM — boundary/validation kod, ne infrastructure. §29
politika: Claude-only review, PASS -> odmah commit/push/merge.

Prije koda pročitati:

```text
AGENTS.md
CLAUDE.md
docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md
.agent/CURRENT_STATE.md
AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md
  sekcije 0A (cijela), 8 (domain model princip), 12 (Campaign domain),
  13 (Content domain), 14 (Visual domain), 15 (Pydantic boundary
  schemas — svih 5 fajlova ovog taska)
```

Pročitati i postojeći merged kod (ne pogađati polja):

```text
src/ai_campaign_studio/domain/campaign/entities.py
src/ai_campaign_studio/domain/campaign/roles.py
src/ai_campaign_studio/domain/content/entities.py
src/ai_campaign_studio/domain/content/claims.py
src/ai_campaign_studio/domain/content/revisions.py
src/ai_campaign_studio/domain/visual/entities.py
src/ai_campaign_studio/domain/visual/layout.py
src/ai_campaign_studio/domain/visual/enums.py
```

# Objective

1. `application/schemas/campaign_brief.py` — validacija GUI/CLI ulaza za
   `CampaignBrief`.
2. `application/schemas/campaign_plan_output.py` — validacija LLM output-a
   za `CampaignPlan`/`CampaignItem`.
3. `application/schemas/social_post_generation_output.py` — validacija LLM
   output-a za `SocialPostPayload` + `ContentClaim`.
4. `application/schemas/revision_output.py` — validacija partial-field
   revizije.
5. `application/schemas/visual_direction_output.py` — validacija LLM
   output-a za `CampaignVisualSystem` kandidat + `LayoutSpec` kandidat.

# Implementation steps

## `campaign_brief.py`

Pydantic model koji validira input prije mapiranja u domain `CampaignBrief`
(`offer`, `goal`, `audience_text`, `targets`, `content_piece_count`,
`content_language_context`, `special_instructions`). `targets` polje mora
validirati kao lista `CampaignTarget`-kompatibilnih objekata
(`channel`/`platform_code`/`format_code` stringovi — ne validirati protiv
`channels` registry ovdje, to je van scope-a, samo strukturna validacija).
`content_piece_count` mora biti pozitivan integer.

## `campaign_plan_output.py`

LLM output shape (tačno iz plana):

```json
{
  "campaign_theme": "...",
  "items": [
    {"order": 1, "role": "PROBLEM", "topic": "...", "goal": "...",
     "facts_needed": ["..."]}
  ]
}
```

Mora:

- imati tačno `content_piece_count` itema (broj se prosljeđuje kao
  validacioni kontekst/parametar, ne hardkodirati);
- `order` unique i sekvencijalan;
- `role` mora biti validan `CampaignRole` enum vrijednost (import iz
  `domain.campaign.roles`, ne dupliran string enum);
- `topic` ne smije biti prazan string.

## `social_post_generation_output.py`

LLM output shape (tačno iz plana):

```json
{
  "headline": "...", "caption": "...", "hook": "...", "body": "...",
  "cta": "...", "hashtags": ["..."],
  "claims": [{"text": "...", "type": "FACT", "fact_ids": ["fact_..."]}]
}
```

`claims[].type` mora biti validan `ClaimType` enum (import iz
`domain.content.enums`). Mapira se ka `SocialPostPayload` + tuple od
`ContentClaim` (mapiranje samo strukturno validira ovdje — stvarno
kreiranje `ContentClaim.id`/`status` je use-case posao, van ovog taska;
schema samo garantuje da su ulazni podaci ispravnog oblika).

## `revision_output.py`

Samo polja koja se MIJENJAJU (partial update shape) — eksplicitno NE
dozvoliti da npr. samo `headline` promjena slučajno "povuče" i promijeni
`caption` ako `caption` nije poslan. Koristiti Pydantic `Optional`/
"unset vs None" razliku (npr. `model_fields_set` ili eksplicitni sentinel)
tako da schema razlikuje "polje nije poslano" od "polje je eksplicitno
postavljeno na prazan string" — dokumentovati odabrani pristup u
docstring-u, ovo je namjerno suptilna tačka koju review provjerava.

## `visual_direction_output.py`

Sadrži:

```text
CampaignVisualSystem candidate
LayoutSpec candidate
```

Svaka vrijednost schema-validirana — svi enum-tipizirani atributi
(`primary_layout_family`, `headline_scale`, `alignment`, `image_position`,
`headline_position`, `overlay`, `logo_position`, `cta_style`) validiraju
protiv postojećih enuma u `domain/visual/enums.py`. Ako
`image_treatment`/`logo_rule`/`cta_rule` trebaju enum tipizaciju (vidi
napomena u Kontekst sekciji), dodati te enume u `domain/visual/enums.py`
kao NOVE klase (ne mijenjati postojeće `LayoutPrimitive`/`Alignment`/
`HeadlineScale`/itd.) i koristiti ih u ovom schema fajlu — sama
`CampaignVisualSystem` dataclass ostaje `str` za ta polja u ovom tasku
(schema samo dodatno validira da string vrijednost odgovara jednom od
dozvoljenih enum članova prije nego što uopšte stigne do mapera).

# Acceptance

- [ ] Svi schema fajlovi su Pydantic `BaseModel`, ne dataclass.
- [ ] `campaign_plan_output.py` odbija plan sa duplim `order` vrijednostima
      (test dokazuje).
- [ ] `campaign_plan_output.py` odbija nevalidan `role` string koji nije
      `CampaignRole` član (test dokazuje).
- [ ] `campaign_plan_output.py` odbija plan čiji broj itema ne odgovara
      očekivanom `content_piece_count`.
- [ ] `social_post_generation_output.py` odbija `claims[].type` koji nije
      validan `ClaimType`.
- [ ] `revision_output.py` ispravno razlikuje "polje nije poslano" od
      "polje je eksplicitno prazno" (test dokazuje na konkretnom primjeru:
      revizija koja mijenja samo `headline` ne dira `caption`).
- [ ] `visual_direction_output.py` odbija bilo koji od enum-tipiziranih
      atributa ako vrijednost nije član odgovarajućeg domain enuma —
      dokazuje da proizvoljan LLM string ("SOMETHING_WEIRD") ne prolazi
      (ovo je namjerno adversarial-style test iako `adversarial_required`
      nije formalno true za cijeli task — ovaj specifičan test JE
      obavezan jer direktno štiti od klase bugova navedene u A3 review
      focusu).
- [ ] Ako je `domain/visual/enums.py` proširen: postojeći enumi
      (`LayoutPrimitive`, `Alignment`, `HeadlineScale`, itd.) nisu
      izmijenjeni, samo dodati novi. `python -m pytest -q` i dalje
      prolazi u cijelosti (uključujući ACS-F1-002 testove).
- [ ] Nema infrastructure importa — potvrđeno kroz
      `tests/architecture/test_import_boundaries.py`.
- [ ] `python -m pytest -q`, `ruff check .`, `mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest -q
python -m pytest tests/architecture/test_import_boundaries.py -v
python -m pytest tests/unit/application -v
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- Pydantic tačno na granici, ne procurio u domain;
- svi enum-tipizirani LLM output-i STVARNO odbijaju proizvoljan string
  (ne samo type hint bez runtime validacije — Pydantic ovo radi
  automatski za `Enum` polja, ali provjeriti da schema koristi stvarni
  domain enum tip, ne `str` sa naknadnom ručnom provjerom koja se može
  zaboraviti);
- `revision_output.py` partial-update semantika je stvarno testirana, ne
  samo tvrđena;
- ako `domain/visual/enums.py` proširen — provjeriti da je čisto
  additivno, ACS-F1-002 kod i testovi netaknuti;
- scope discipline — `brand_fixture.py`/`application/mappers/` nisu
  dirani (ACS-F1-003 teritorija).

# Rollback

MEDIUM risk. Fix na istoj branch bez proširenja scope-a. STOP i vrati na
puni ciklus samo ako task pokaže potrebu da mijenja postojeće domain
entitete (`entities.py`/`layout.py`) van dozvoljenog enum-dodavanja — to
zahtijeva redefinisan kontrakt, ne tihu odluku implementera.

# Coordination

Paralelno sa **ACS-F1-003** (Pi) — `brand_fixture.py` +
`application/mappers/`. `allowed_paths` disjoint. Oba taska mogu dodavati
u `application/schemas/__init__.py` — koordinator rješava trivijalni
merge ako se preklope, nije blokator za bilo koji task pojedinačno.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-004-campaign-content-visual-schemas
Branch:   task/ACS-F1-004-campaign-content-visual-schemas
Base:     main @ 0edae77
```
