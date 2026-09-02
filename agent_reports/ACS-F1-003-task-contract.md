---
task_id: ACS-F1-003
phase: Faza-1
title: "Brand fixture boundary schema + mapper (A4, dio 1)"
risk: MEDIUM
coordinator: claude
implementer: pi
reviewers: [claude]
status: "OPEN — contract written before code"
created_at: 2026-09-02
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/application/schemas/brand_fixture.py
  - src/ai_campaign_studio/application/schemas/__init__.py
  - src/ai_campaign_studio/application/mappers/brand_fixture_mapper.py
  - src/ai_campaign_studio/application/mappers/__init__.py
  - src/ai_campaign_studio/domain/brand/value_objects.py
  - resources/fixtures/
  - tests/unit/application/schemas/
  - tests/unit/application/mappers/
forbidden_paths:
  - src/ai_campaign_studio/domain/common/
  - src/ai_campaign_studio/domain/brand/entities.py
  - src/ai_campaign_studio/domain/facts/
  - src/ai_campaign_studio/domain/campaign/
  - src/ai_campaign_studio/domain/content/
  - src/ai_campaign_studio/domain/visual/
  - src/ai_campaign_studio/application/schemas/campaign_brief.py
  - src/ai_campaign_studio/application/schemas/campaign_plan_output.py
  - src/ai_campaign_studio/application/schemas/social_post_generation_output.py
  - src/ai_campaign_studio/application/schemas/revision_output.py
  - src/ai_campaign_studio/application/schemas/visual_direction_output.py
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
    - symbol: "new package application/schemas/, application/mappers/"
      upstream_risk: NONE
      upstream_count: 0
      downstream_notes: "application/ package currently has only __init__.py, zero existing importers (verified: grep for 'from ai_campaign_studio.application' across src/ returns nothing). Pure additive — imports FROM domain/brand, domain/facts, domain/common (all merged, stable), nothing imports INTO this task's new files yet."
      affected_processes: []
  scope_fit: PASS
  unknowns: []
---

# Kontekst

Task **A4 — Pydantic boundary schemas**, sekcija 15 iz
`AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md`, prvi dio.
Domain sloj (A3) je potpuno gotov i merged (`domain/common`, `brand`,
`facts`, `campaign`, `content`, `visual`) — svi entiteti postoje kao plain
frozen dataclasses. A4 dodaje granicu: Pydantic modele koji validiraju
spoljni ulaz (fixture JSON) i mapiraju ga u te postojeće immutable domain
objekte. **Ovaj task ne dira domain entitete** (osim jednog eksplicitno
dozvoljenog proširenja — vidi ispod), samo čita i konvertuje.

Paralelno ide **ACS-F1-004** (Crush) — `campaign_brief.py` +
`campaign_plan_output.py` + `social_post_generation_output.py` +
`revision_output.py` + `visual_direction_output.py`. `allowed_paths` su
disjoint (svaki task pokriva različite fajlove unutar
`application/schemas/`), nema zavisnosti između ova dva taska — mogu ići
potpuno paralelno bez čekanja.

**Rule 0A.5 (protiv dupliranja)**: `application/schemas/` i
`application/mappers/` trenutno ne postoje (samo `application/__init__.py`)
— čista implementacija.

**Poznata napomena iz A3** (vidi docstring `domain/brand/value_objects.py`
`Restriction`): "Minimal A3 shape: the full schema (category/severity/scope)
is defined with the A4 fixture boundary schema, not guessed here." Ovaj
task je taj trenutak — ako fixture format zahtijeva `category`/`severity`/
`scope` na `Restriction`, dozvoljeno je proširiti taj ONAJ dataclass (ne
praviti paralelnu verziju) u `domain/brand/value_objects.py`, koji je zato
eksplicitno u `allowed_paths`. Ako fixture ne zahtijeva ta polja, ne dirati
fajl uopšte — ne dodavati polja "za svaki slučaj".

**Risk**: MEDIUM. Ovo je boundary/validation kod (Pydantic), ne
infrastructure (SecretStore/SQLite/migrations/bootstrap nisu dirani) — nije
na HIGH listi. §29 politika: Claude-only review, PASS → odmah
commit/push/merge, bez Codex runde i bez posebnog Human Owner odobrenja.

Prije koda pročitati:

```text
AGENTS.md
CLAUDE.md
docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md
.agent/CURRENT_STATE.md
AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md
  sekcije 0A (cijela), 8 (domain model princip — Pydantic SAMO na
  granicama, ovo JE ta granica), 10 (Brand domain), 11 (Facts domain),
  15 (Pydantic boundary schemas — brand_fixture.py dio)
```

Pročitati i postojeći merged kod (ne pogađati polja):

```text
src/ai_campaign_studio/domain/brand/entities.py
src/ai_campaign_studio/domain/brand/value_objects.py
src/ai_campaign_studio/domain/facts/entities.py
src/ai_campaign_studio/domain/facts/enums.py
src/ai_campaign_studio/domain/common/ids.py
src/ai_campaign_studio/localization/enums.py
src/ai_campaign_studio/localization/language_context.py
```

# Objective

1. `application/schemas/brand_fixture.py` — Pydantic model(i) koji validiraju
   fixture JSON za brend.
2. `application/mappers/brand_fixture_mapper.py` — funkcija koja konvertuje
   validirani fixture u `Brand` + `BrandSnapshot` + `tuple[ApprovedFact, ...]`
   (postojeći immutable domain objekti, ne novi paralelni tipovi).
3. Jedan konkretan fixture primjer u `resources/fixtures/` (demo brend,
   npr. isti "BrightSmile" koji već postoji u `docs/gui-v3` mokapu — nije
   obavezno da bude isti sadržaj, ali korisno je za vizuelnu koherentnost
   kasnije; implementer bira ime/sadržaj, mora biti realan i kompletan
   primjer koji prolazi vlastitu validaciju).

# Implementation steps

## `application/schemas/brand_fixture.py`

Pydantic model za fixture JSON, tačno polja iz plana sekcija 15:

```text
brand.name
default_content_language_context   -> mapira na postojeći
                                       localization.language_context.ContentLanguageContext
voice
audiences
services
facts
restrictions
visual_identity
```

Svaki fixture fact:

```text
logical_fact_id
version
content
source_ref
```

Koristiti postojeći `ContentLanguageContext` (Pydantic, već postoji u
`localization/language_context.py`) za `default_content_language_context` —
NE praviti novi paralelni language schema. Struktura `voice`/`audiences`/
`services`/`restrictions`/`visual_identity` u Pydantic modelu mora
sadržavati SVA polja koja odgovarajući domain value object očekuje
(`BrandVoice`, `Audience`, `ServiceDefinition`, `Restriction`,
`VisualIdentity` iz `domain/brand/value_objects.py`) — pogledati tačna
imena polja u tom fajlu, ne pogađati.

Validacija:

- `facts` lista ne smije biti prazna (barem jedan approved fact potreban
  da fixture bude koristan).
- `logical_fact_id` unique unutar fixture-a (dva facta ne dijele isti
  logical id u istom fixture-u).
- `source_ref` obavezan po factu (fixture provenance — čak i "fixture"
  source_type mora biti eksplicitan, ne implicitan/prazan).

## `application/mappers/brand_fixture_mapper.py`

Funkcija (npr. `map_brand_fixture(fixture: BrandFixtureSchema) -> tuple[Brand, BrandSnapshot, tuple[ApprovedFact, ...]]`
— implementer bira tačan potpis, dokumentovati u docstring-u):

- Kreira `Brand` (novi `id` preko `domain.common.ids.new_id()`,
  `created_at` preko `domain.common.timestamps.utc_now()`).
- Za svaki fixture fact kreira `ApprovedFact` sa: novi `id`
  (`new_id()`), `logical_fact_id`/`version`/`content`/`source_ref` iz
  fixture-a, `status=FactStatus.APPROVED`, `created_at=utc_now()`,
  `superseded_by=None`, `deleted_at=None`.
- Kreira `BrandSnapshot` (`version=1`, `approved_fact_ids` = tuple ID-jeva
  novokreiranih facts, `language`/`locale`/`script` kao plain string-ovi
  izvedeni iz `ContentLanguageContext` — vidi docstring
  `BrandSnapshot` u `domain/brand/entities.py`: "callers map them to the
  existing ContentLanguageFamily/Script enum values at the boundary" —
  ovaj mapper JE taj caller).
- Ne perzistira ništa (nema SQLite poziva) — čista in-memory transformacija.
  Persistencija je A5, van ovog taska.

## `resources/fixtures/` — primjer

Jedan kompletan, validan JSON fixture fajl koji prolazi
`BrandFixtureSchema` validaciju i uspješno mapira kroz
`map_brand_fixture`. Mora imati barem 3 approved facts, barem 1 audience,
barem 1 service, barem 1 restriction, kompletan visual_identity.

# Acceptance

- [ ] `BrandFixtureSchema` (ili ekvivalentno imenovan Pydantic model) je
      Pydantic `BaseModel`, ne dataclass — ovo JE granica, Pydantic je
      ovdje ispravan izbor (za razliku od domain sloja).
- [ ] `default_content_language_context` koristi postojeći
      `ContentLanguageContext`, ne novi paralelni model.
- [ ] Mapper vraća postojeće domain tipove (`Brand`, `BrandSnapshot`,
      `ApprovedFact`) — provjereno importom iz `domain.brand.entities` /
      `domain.facts.entities`, ne lokalno definisanih duplikata.
- [ ] Mapper NE mutira ništa, NE perzistira ništa — čista funkcija
      (fixture in, domain objekti out).
- [ ] Svaki mapirani `ApprovedFact.status == FactStatus.APPROVED`.
- [ ] `BrandSnapshot.approved_fact_ids` tačno odgovara ID-jevima
      mapiranih facts (test provjerava da nijedan fact nije izgubljen ili
      duplikat).
- [ ] Validacija odbija fixture sa duplim `logical_fact_id`-jem unutar
      istog fixture-a (test dokazuje `ValidationError` ili ekvivalentno).
- [ ] Validacija odbija prazan `facts` niz.
- [ ] `resources/fixtures/` primjer prolazi validaciju I mapiranje u
      integracionom testu (end-to-end: JSON fajl -> Pydantic -> domain
      objekti).
- [ ] Ako je `Restriction` proširen: promjena je dokumentovana u commit
      poruci i docstring-u, i NE krši postojeći ACS-F1-001/002 kod koji
      `Restriction` već koristi (provjeriti `python -m pytest -q` i dalje
      prolazi u cijelosti, uključujući postojeće domain testove).
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

- Pydantic je korišten TAČNO na granici (fixture ingestion), ne procurio
  nazad u domain sloj;
- mapper ne duplira domain logiku niti pravi paralelne "shadow" tipove —
  vraća stvarne `Brand`/`BrandSnapshot`/`ApprovedFact`;
- `Restriction` proširenje (ako postoji) je opravdano fixture formatom,
  ne "za svaki slučaj" dodavanje polja;
- ne dira ništa u `domain/facts/`, `domain/campaign/`, `domain/content/`,
  `domain/visual/` (Crush teritorija za druge A4 fajlove, i njihova A3
  teritorija generalno);
- scope discipline — konkretno provjeriti da fajlovi navedeni u
  `forbidden_paths` (ACS-F1-004 teritorija: `campaign_brief.py` itd.)
  nisu dirani.

# Rollback

MEDIUM risk — nova, izolovana granica bez postojećih importera. Fix na
istoj branch bez proširenja scope-a ako review nađe problem. STOP i vrati
na puni ciklus samo ako se otkrije potreba da task dira nešto sa HIGH
liste (npr. SQLite persistencija — to je A5, van scope-a).

# Coordination

Paralelno sa **ACS-F1-004** (Crush) — `campaign_brief.py`,
`campaign_plan_output.py`, `social_post_generation_output.py`,
`revision_output.py`, `visual_direction_output.py`. `allowed_paths`
disjoint unutar `application/schemas/` (provjereno: svaki task navodi
tačne fajlove, ne cijeli direktorijum, izbjegava `__init__.py`
kolizije — oba taska dodaju u isti `application/schemas/__init__.py`
ako je potreban re-export; koordinator rješava trivijalni merge
konflikt na tom jednom fajlu ručno ako se desi, nije razlog za blokadu).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-003-brand-fixture-schema
Branch:   task/ACS-F1-003-brand-fixture-schema
Base:     main @ 0edae77
```
