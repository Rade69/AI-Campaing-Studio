# AI Campaign Studio — Faza 1 v1.4
## Agent-ready tehnički plan za implementaciju temelja + Vertical Slice 1

**Status:** izvršna tehnička specifikacija  
**Osnova:** AI Campaign Studio — Faza 0.6  
**Cilj:** pretvoriti zaključane odluke iz Faze 0.6 u funkcionalan, testabilan Vertical Slice 1 bez scope creep-a  
**Primarni jezik implementacije:** Python 3.12+  
**Produktni model:** desktop-first, local-first  
**UI framework:** NIJE unaprijed zaključan; PySide6 je vodeći kandidat, pywebview kontrolni kandidat  
**Persistence:** SQLite  
**Arhitektura:** Clean/Hexagonal core + Use Cases + Ports/Adapters + zamjenjivi Presentation sloj  
**Krajnji dokaz ove faze:** Campaign Engine B mora biti mjerljivo i ljudski ocijenjeno bolji od single-prompt kontrole A; social media je prvi output target, ali core campaign/domain model ostaje channel-agnostic

**Obavezni prethodni gate:** `Implementation Phase 0 v1.1 — Project Foundation` mora biti izvršen i završiti sa `P0-GATE = PASS` prije nove business/domain implementacije iz ovog dokumenta.

Ako `artifacts/phase0_foundation_gate.json` postoji i ima:

```json
{
  "status": "PASS"
}
```

agent NE izvršava ponovo foundation taskove koje je P0 već završio. Umjesto toga ih samo verifikuje i nastavlja od business/domain sloja.

**Kanonski način rada agenata:** `docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md`.

Svaki A-task iz ovog dokumenta mora imati vlastiti Task Contract prije koda. Ovaj dokument definiše ŠTA implementirati; workflow definiše KO radi, kako se izoluje rad, kako se koristi GitNexus, ko reviewa i kada je merge dozvoljen.



---

# 0. Kako agent treba koristiti ovaj dokument

Ovo nije brainstorming dokument.

Ovo je **izvršna specifikacija**.

Agent treba:

1. pratiti redoslijed faza;
2. ne preskakati gate-ove;
3. ne širiti scope bez eksplicitne odluke korisnika;
4. ne uvoditi novu arhitekturu ako postojeća iz ovog dokumenta rješava problem;
5. ne stavljati business logiku u GUI;
6. ne vezivati domain/application za AI providera, SQLite implementaciju, Qt, pywebview ili Playwright;
7. nakon svakog implementacionog bloka pokrenuti definisane testove;
8. jasno prijaviti šta je stvarno testirano, a šta nije;
9. ne praviti dodatne `.md` izvještaje poslije svakog koraka;
10. dokumentovati samo trajne arhitektonske odluke i rezultate obaveznih spike-ova.
11. prije MEDIUM/HIGH/shared-contract izmjene koristiti GitNexus prema `.agent/GITNEXUS_PROTOCOL.md`;
12. prije koda imati konkretan Task Contract sa `allowed_paths`, `forbidden_paths`, review fokusom i GitNexus pre-impact evidence;
13. prije reviewa za MEDIUM/HIGH pokrenuti GitNexus `detect-changes`;
14. ne merge-ovati bez eksplicitnog Human Owner odobrenja.

Ako implementacija otkrije da neka odluka iz plana tehnički ne radi, agent ne smije tiho improvizovati.

Mora:

```text
1. izolovati problem;
2. prikupiti dokaz/test;
3. predložiti najmanju izmjenu;
4. zadržati ostatak arhitekture;
5. označiti odluku koja se mora ponovo otvoriti.
```

---



# 0B. Faza 1 execution protocol

Faza 1 se NE izvršava kao jedan monolitni agentski zadatak.

Koordinator za svaki A-task:

```text
1. provjeri CURRENT_STATE i dependency baseline;
2. koristi GitNexus da razumije postojeći graph/blast radius;
3. napiše Task Contract;
4. definiše allowed/forbidden paths;
5. napravi/odredi worktree + branch;
6. aktivira coordination claim;
7. dodijeli implementera;
8. prikupi execution evidence;
9. traži nezavisan review prema risk tieru;
10. traži Human Owner approval;
11. merge;
12. post-merge gate;
13. GitNexus re-index;
14. CURRENT_STATE update;
15. claim release.
```

Default uloge:

```text
Pi / Crush → implementacija
Codex      → adversarial/test review
Claude     → architecture/integration review ili coordinator
Human Owner→ final merge approval
```

Za HIGH i rane architecture-wide Faza 1 taskove default je dual review `Codex + Claude`.

Ako task dira shared symbol/protocol/dataclass/repository/ContentPiece/ApprovedFact/Campaign target/AI port/bootstrap, GitNexus je obavezan čak i ako je diff mali.

LOW task može preskočiti GitNexus samo kada Task Contract eksplicitno dokumentuje da je resource-only i bez shared contracta.

---

# 0A. Obavezni P0 → Faza 1 handoff

Ovaj dokument pretpostavlja da postoji:

```text
AI_Campaign_Studio_Implementation_Phase_0_v1_1_Agent_Workflow_Integrated.md
```

i da je njegov završni gate:

```text
P0-GATE = PASS
```

## 0A.1 — Prije bilo kakvog rada

Agent prvo provjerava:

```text
artifacts/phase0_foundation_gate.json
```

Ako fajl ne postoji ili `status != PASS`:

```text
STOP
```

Ne počinjati Fazu 1.

Prvo izvršiti Implementation Phase 0 plan.

Ako fajl postoji i `status = PASS`, agent radi kratku verifikaciju:

```text
python -m ruff check .
python -m mypy src
python -m pytest -q
python scripts/validate_resources.py
python -m ai_campaign_studio.main --health-check
```

Ako bilo šta od ovoga pada:

```text
P0 foundation se smatra degradiranim.
```

Prvo popraviti foundation. Ne nastavljati sa business implementacijom preko crvenog P0 stanja.

## 0A.2 — Šta se NE radi ponovo

Ako je P0 PASS, sljedeći taskovi iz ovog dokumenta se ne implementiraju ispočetka:

```text
A1   Initialize repository
A2   Architecture boundaries
A3a  Channel / Platform / Format foundation
A3b  Localization foundation
```

Njihov status u Fazi 1 je:

```text
VERIFY ONLY
```

Agent samo potvrđuje da postojeći P0 foundation i dalje ispunjava njihove acceptance kriterije.

Ne kreirati paralelne foldere, nove registre, drugi translator ili drugi architecture-boundary checker.

## 0A.3 — Djelimično naslijeđeni taskovi

### A5 — SQLite

P0 je već završio:

```text
SQLite connection
migration runner
schema_migrations
foundation migration
Unit of Work / transaction foundation
```

A5 u Fazi 1 zato NE pravi novi DB foundation.

A5 nastavlja sa:

```text
business/domain migrations
Brand/Facts/Campaign/Content/Visual repository portovima
SQLite repository adapterima
round-trip business testovima
```

### A8 — AI provider/model foundation

P0 je već završio:

```text
Provider Registry
Model Registry foundation
provider resource definitions
SecretStore
provider config foundation
model selection foundation
```

A8 u Fazi 1 zato NE pravi drugi registry ili drugi SecretStore.

A8 dodaje samo:

```text
live provider adapters
Test Connection implementations
real model discovery/fallback behavior
default model selection workflow
TextGenerationPort
AI request/response contracts
prompt repository
telemetry
```

## 0A.4 — Gdje počinje stvarna nova implementacija

Prvi novi business/domain task je:

```text
A3 — Common + Domain enums/entities
```

Tu se prvi put uvode:

```text
Brand
ApprovedFact
BrandSnapshot
CampaignBrief
CampaignPlan
CampaignItem
ContentPiece
Claims
Revisions
Visual contracts
```

P0 ih namjerno nije implementirao.

Nakon A3 slijede:

```text
A4  boundary schemas + mappers
A5  business persistence nad postojećim SQLite foundationom
A6  fixture loading
A7+ prompts/AI/application pipeline
```

## 0A.5 — Pravilo protiv dupliranja

Ako fajl/folder već postoji iz P0:

```text
inspect → reuse → extend only if required
```

Ne:

```text
replace → parallel implementation → duplicate source of truth
```

Primjeri zabranjenog dupliranja:

```text
localization_v2/
platform_registry_new.py
database2/
second_migration_runner.py
another_secret_store.py
new_job_manager.py
```

## 0A.6 — Source of truth nakon handoffa

```text
P0 foundation contracts
        ↓
ostaju foundation source of truth

Faza 1
        ↓
dodaje business/domain ponašanje iznad njih
```

Ako Faza 1 zahtijeva izmjenu foundation contracta:

1. dokazati stvarnu potrebu;
2. napraviti najmanju kompatibilnu izmjenu;
3. ponovo pokrenuti P0 verification suite;
4. tek onda nastaviti.


# 1. Misija Faze 1

Faza 1 ne gradi cijeli proizvod.

Faza 1 mora dokazati sljedeće:

```text
HAND-WRITTEN BRAND FIXTURE
          ↓
CAMPAIGN BRIEF
          ↓
CAMPAIGN PLAN
          ↓
HUMAN REVIEW
          ↓
ALLOWED FACTS
          ↓
INDIVIDUAL POST GENERATION
          ↓
FACT-ID VALIDATION
          ↓
DETERMINISTIC LINTER
          ↓
POST REVIEW
          ↓
CAMPAIGN VISUAL SYSTEM
          ↓
LAYOUT SPEC
          ↓
DETERMINISTIC RENDER
          ↓
ZIP EXPORT
```

Paralelno mora postojati kontrola:

```text
SAME BRAND FIXTURE
       ↓
ONE GENERIC PROMPT
       ↓
6 POSTS
```

Na kraju se porede:

```text
CONTROL A
vs
SYSTEM B
```

Ako Sistem B nije jasno bolji, ne prelazi se na Website Ingestion.

---

# 2. Strogo izvan scope-a Faze 1

Agent NE implementira:

```text
NO website crawler
NO Website Ingestion produkcijski pipeline
NO PDF/DOCX/XLSX ingest
NO embeddings
NO vector database
NO RAG
NO VPS backup
NO social API
NO publishing
NO scheduler
NO inbox
NO social analytics
NO OCR
NO video generation
NO multi-agent framework
NO automatic stale-fact recrawl
NO production product catalog importer
NO full Brand Intelligence extraction
```

Dozvoljeno je definisati samo **port/granicu** koja će kasnije prihvatiti podatke iz Slicea 2.

Takođe je dozvoljeno definisati channel/platform/format registry i generički `ContentPiece`, ali Faza 1 ne implementira Email/Web/Print campaign generatore.

Početni social registry uključuje Instagram, Facebook, LinkedIn, X, TikTok, YouTube, Pinterest, Threads i Snapchat, ali Vertical Slice 1 može produkcijski renderovati/generisati samo mali dokazni podskup formata. Za ostale platforme registry i constraints moraju biti validni, ali njihov puni format-specific generator nije uslov G10.

Ne praviti mrtav kod za funkcionalnosti koje još ne postoje.

---

# 3. Glavni razvojni gate-ovi

Koristiti ove gate-ove kao obavezne tačke.

## G0 — P0 Foundation Verification Gate

Ovaj gate se više ne implementira od nule.

Mora biti potvrđeno:

- `artifacts/phase0_foundation_gate.json` postoji;
- `P0-GATE = PASS`;
- validan repo skeleton postoji;
- `pyproject.toml` postoji;
- test runner radi;
- import-boundary test radi;
- bootstrap/composition root radi;
- config/path handling radi;
- logging/redaction radi;
- localization registries rade;
- Channel/Platform/Format registry radi;
- Provider/Model Registry foundation radi;
- SecretStore foundation radi;
- SQLite/migration/UoW foundation radi;
- JobManager foundation radi;
- nema business logike u P0 sloju.

Ako verifikacija pada, Faza 1 se ne nastavlja.

## G1 — Domain Contract Gate

Mora postojati i biti testirano:

- Brand Fixture;
- ApprovedFact/version model;
- BrandSnapshot;
- CampaignBrief;
- CampaignPlan;
- CampaignItem;
- CampaignRole;
- Post;
- PostClaim;
- Revision;
- status transitions.

## G2 — Persistence Gate

Mora postojati:

- SQLite migration runner;
- početne migracije;
- repository portovi;
- SQLite repository adapteri;
- round-trip testovi;
- immutable fact/version ponašanje.

## G3 — AI & Prompt Gate

Mora postojati:

- provider-neutral `TextGenerationPort`;
- mock adapter;
- jedan stvarni provider adapter;
- prompt repository;
- prompt versioning;
- structured output validation;
- telemetry;
- retry/error policy.

## G4 — Campaign Planning Gate

Mora raditi:

```text
Brand Fixture + Campaign Brief → CampaignPlan
```

Plan mora biti:

- schema-valid;
- editable;
- reorderable;
- approveable;
- role-aware.

## G5 — Post Generation & Claim Gate

Mora raditi:

```text
CampaignItem + AllowedFacts → PostDraft
```

Sa:

- fact mapping;
- deterministic claim validation;
- numeric/risky phrase linter;
- warnings;
- revision history.

## G6 — Visual Contract Gate

Mora postojati:

- CampaignVisualSystem;
- LayoutSpec;
- ContentSlotContract;
- najmanje 2 layout primitive;
- layout validation;
- overflow detection.

## G7 — Renderer Gate

Mora biti završen renderer spike:

```text
HTML/CSS + Playwright
vs
SVG-based kandidat
```

i odabran produkcijski renderer za Slice 1.

## G8 — Export & Evaluation Gate

Mora raditi:

- ZIP export;
- campaign JSON manifest;
- captions;
- PNG render;
- AI telemetry summary;
- A/B evaluation harness.

## G9 — UI Framework Gate

Mora biti napravljen isti reprezentativni Post Studio spike u:

```text
PySide6
vs
pywebview + HTML/CSS/JS
```

i dokumentovan izbor frameworka.

## G10 — Vertical Slice Integration Gate

Mora raditi kompletan put:

```text
fixture → brief → plan → review → posts → validation → render → export
```

uz A/B poređenje.

---

# 4. Arhitektonska pravila — bez izuzetka

## AR1 — Dependency direction

Dozvoljeni smjer:

```text
Presentation
      ↓
Application
      ↓
Domain

Infrastructure
      ↑
     Ports
      ↑
Application
```

Praktično:

```text
domain
  ne importuje ništa iz application/infrastructure/presentation/jobs

ports
  može importovati domain tipove i stdlib

application
  može importovati domain + ports

infrastructure
  može importovati domain + ports + application DTO gdje je nužno

jobs
  može pozivati application use-caseove i emitovati framework-neutral events

presentation
  može pozivati application/use-case facade i slušati job state
```

## AR2 — Zabranjeni importi

`domain/` NE smije importovati:

```text
PySide6
PyQt6
pywebview
playwright
sqlite3 repository implementation
openai
anthropic
requests
Flask
Pillow
```

`application/` NE smije importovati:

```text
PySide6
pywebview
sqlite repository implementation
provider SDK
Playwright
```

`presentation/` NE smije direktno pozivati:

```text
provider SDK
sqlite queries
renderer implementation
filesystem persistence implementation
```

## AR3 — Nema `services/` kao kante za sve

Ne praviti:

```text
campaign_service.py
ai_service.py
brand_service.py
utils.py
helpers.py
```

ako fajl nema jednu jasno definisanu odgovornost.

Preferirati use-case imena:

```text
generate_campaign_plan.py
approve_campaign_plan.py
generate_post.py
revise_post.py
render_post.py
export_campaign.py
```

## AR4 — Jedan source of truth po konceptu

Primjeri:

```text
CampaignRole enum       → jedno mjesto
ClaimType enum          → jedno mjesto
PostStatus enum         → jedno mjesto
reason codes            → jedno mjesto
migration schema        → jedno mjesto
prompt version metadata → prompt fajl
```

Ne praviti paralelne string konstante u GUI-u, exporteru i domainu.

## AR5 — Framework-neutral Presentation contracts

Do završetka G9 ne praviti production GUI arhitekturu vezanu za Qt ili pywebview.

Prvo definisati:

```text
presentation/state
presentation/contracts
presentation/ui_models
```

Tek nakon spike-a:

```text
presentation_qt/
```

ili:

```text
presentation_webview/
```

## AR6 — UI framework, renderer i browser worker su odvojene odluke

Nikada ne pretpostaviti:

```text
pywebview UI
=> Playwright renderer
=> Playwright website ingest
=> isti Chromium proces
```

To su tri nezavisna adaptera.

---


# 4A. Jezička arhitektura

## LANG1 — UI ima samo dva jezika

```text
AppLocale
- EN
- BHS_LATIN
```

Ne praviti:

```text
BS_UI
SR_UI
HR_UI
```

Svi lokalni UI stringovi koriste jedan `BHS` translation set.

## LANG2 — UI language i AI content language su odvojeni

```text
AppLocale
```

kontroliše samo aplikacijski interfejs.

```text
ContentLanguageContext
```

kontroliše generisani marketinški sadržaj.

Model:

```text
ContentLanguageFamily:
EN
BHS

BHSRegionalVariant:
NEUTRAL
BS
SR
HR

Script:
LATIN
```

`ContentLanguageContext`:

```text
language_family
regional_variant
script
locale
preferred_terms[]
forbidden_terms[]
regional_vocabulary[]
tone_examples[]
```

## LANG3 — Regionalna varijanta nije novi jezik aplikacije

Regional variant utiče na:

- terminologiju;
- stil;
- preferred terms;
- forbidden terms;
- few-shot primjere.

Ne utiče na:

- fact IDs;
- provenance;
- CampaignRole;
- state transitions;
- persistence identity.

## LANG4 — Translation keys, ne hardcoded UI stringovi

Presentation kod ne smije sadržati produkcijske stringove kao:

```text
"Kreiraj kampanju"
"Create campaign"
```

nego:

```text
t("campaign.create")
```

Resources:

```text
resources/i18n/en.json
resources/i18n/bhs.json
```

## LANG5 — Translation layer je framework-neutral

Ne vezivati core translation sistem direktno za:

```text
Qt tr()
gettext
web framework i18n
```

dok UI framework nije odabran.

Presentation adapter može mapirati centralni `TranslatorPort` na konkretan toolkit.

## LANG6 — BHS MVP koristi latinicu

Obavezno testirati:

```text
č ć š ž đ
Č Ć Š Ž Đ
```

Ćirilica nije dio Faze 1.



# 4B. Channel / Platform / Format arhitektura

## CH1 — Campaign Engine je channel-agnostic

Core domain ne smije pretpostaviti da je svaki `CampaignItem` Instagram/Facebook post.

Model:

```text
CampaignItem
- target
- role
- topic
- goal
```

Target:

```text
CampaignTarget
- channel
- platform_code
- format_code
```

## CH2 — Channel enum je mali i stabilan

```text
Channel:
SOCIAL
EMAIL
WEB
PAID_AD
PRINT
DIRECT_MESSAGE
```

Novi channel se dodaje samo kada predstavlja novu marketinšku kategoriju.

## CH3 — Platform registry je data-driven

Ne koristiti zatvoren enum za sve social platforme.

`PlatformDefinition`:

```text
code
display_name
channel
supported_formats[]
text_constraints
visual_constraints
content_rules
enabled
```

`resources/platforms/*.yaml` je source of truth za početne definicije.

## CH4 — Format definition

Format nije slobodan string.

`FormatDefinition`:

```text
code
display_name
required_fields[]
optional_fields[]
text_constraints
visual_constraints
```

Početni social formati po platformi mogu biti samo oni koji su potrebni za Fazu 1 test.

Registry ipak mora moći učitati i dodatne definicije.

## CH5 — ContentPiece, ne Post kao core output

Core entity:

```text
ContentPiece
```

Minimalno:

```text
id
campaign_item_id
target
status
brand_snapshot_id
facts_allowed
claims
revisions
payload_type
```

Za Fazu 1:

```text
payload_type = SOCIAL_POST
```

`SocialPostPayload`:

```text
headline?
caption
hook?
body?
cta?
hashtags[]
visual_direction?
```

Kasniji email/web/ads payloadi se dodaju bez promjene CampaignPlan modela.

---

# 4C. AI Provider / Model Registry arhitektura

## AI-R1 — Provider credential ≠ model

Credential se čuva jednom po provideru.

```text
ProviderConfig
- provider_code
- configured
- credential_ref
- base_url?
```

`credential_ref` pokazuje na OS keyring entry.

Ne sadrži secret vrijednost.

## AI-R2 — Provider definitions

```text
AIProviderDefinition
- provider_code
- display_name
- adapter_type
- supports_model_discovery
- requires_api_key
- base_url_mode
```

Početni:

```text
OPENAI
ANTHROPIC
GOOGLE
DEEPSEEK
OPENROUTER
OPENAI_COMPATIBLE
```

## AI-R3 — ModelProfile

```text
ModelProfile
- provider_code
- model_id
- display_name
- capabilities
- context_window?
- supports_temperature?
- enabled
- source
```

`source`:

```text
DISCOVERED
REGISTRY
MANUAL
```

## AI-R4 — Capabilities

```text
TEXT_GENERATION
STRUCTURED_OUTPUT
VISION
IMAGE_GENERATION
TOOL_USE
```

Use-case bira model prema capability zahtjevu.

## AI-R5 — Provider UX

Settings flow:

```text
select provider
    ↓
enter API key
    ↓
TEST CONNECTION
    ↓
discover/list models
    ↓
select default model
```

Ako korisnik prvo klikne model:

```text
model → provider lookup → provider setup
```

## AI-R6 — OpenAI-compatible

Config:

```text
display_name
base_url
api_key
model_id
```

Known provider adapteri ne traže Base URL od korisnika.

## AI-R7 — Model discovery fallback

Ako provider može listati modele:

```text
discover
```

Ako ne:

```text
registry models
+
manual model id
```

GUI ne hardkoduje model listu.

## AI-R8 — MVP routing

Faza 1 implementira:

```text
default_text_model
```

Arhitektura podržava kasnije:

```text
campaign_planning_model
post_generation_model
revision_model
visual_direction_model
```

ali ne praviti routing kompleksnost prije mjerenja.


# 5. Početna struktura repozitorija

Agent prvo kreira sljedeću strukturu.

```text
ai-campaign-studio/
│
├── pyproject.toml
├── README.md
├── .gitignore
├── config.example.toml
│
├── src/
│   └── ai_campaign_studio/
│       ├── __init__.py
│       ├── bootstrap.py
│       ├── main.py
│       │
│       ├── config/
│       │   ├── __init__.py
│       │   ├── settings.py
│       │   └── paths.py
│       │
│       ├── localization/
│       │   ├── __init__.py
│       │   ├── enums.py
│       │   ├── language_context.py
│       │   └── translator.py
│       │
│       ├── channels/
│       │   ├── __init__.py
│       │   ├── enums.py
│       │   ├── definitions.py
│       │   └── registry.py
│       │
│       ├── ai_registry/
│       │   ├── __init__.py
│       │   ├── provider_models.py
│       │   ├── model_profiles.py
│       │   └── registry.py
│       │
│       ├── domain/
│       │   ├── __init__.py
│       │   │
│       │   ├── common/
│       │   │   ├── __init__.py
│       │   │   ├── ids.py
│       │   │   ├── errors.py
│       │   │   └── timestamps.py
│       │   │
│       │   ├── brand/
│       │   │   ├── __init__.py
│       │   │   ├── entities.py
│       │   │   ├── value_objects.py
│       │   │   └── policies.py
│       │   │
│       │   ├── facts/
│       │   │   ├── __init__.py
│       │   │   ├── entities.py
│       │   │   ├── enums.py
│       │   │   └── policies.py
│       │   │
│       │   ├── campaign/
│       │   │   ├── __init__.py
│       │   │   ├── entities.py
│       │   │   ├── enums.py
│       │   │   ├── roles.py
│       │   │   ├── templates.py
│       │   │   └── policies.py
│       │   │
│       │   ├── content/
│       │   │   ├── __init__.py
│       │   │   ├── entities.py
│       │   │   ├── enums.py
│       │   │   ├── social_payload.py
│       │   │   ├── claims.py
│       │   │   ├── revisions.py
│       │   │   └── policies.py
│       │   │
│       │   └── visual/
│       │       ├── __init__.py
│       │       ├── entities.py
│       │       ├── enums.py
│       │       ├── layout.py
│       │       └── slots.py
│       │
│       ├── application/
│       │   ├── __init__.py
│       │   │
│       │   ├── schemas/
│       │   │   ├── __init__.py
│       │   │   ├── brand_fixture.py
│       │   │   ├── campaign_brief.py
│       │   │   ├── campaign_plan_output.py
│       │   │   ├── social_post_generation_output.py
│       │   │   ├── revision_output.py
│       │   │   ├── visual_direction_output.py
│       │   │   └── export_manifest.py
│       │   │
│       │   ├── mappers/
│       │   │   ├── __init__.py
│       │   │   ├── fixture_mapper.py
│       │   │   ├── campaign_mapper.py
│       │   │   ├── post_mapper.py
│       │   │   └── visual_mapper.py
│       │   │
│       │   ├── brands/
│       │   │   ├── __init__.py
│       │   │   └── load_brand_fixture.py
│       │   │
│       │   ├── campaigns/
│       │   │   ├── __init__.py
│       │   │   ├── create_campaign.py
│       │   │   ├── generate_campaign_plan.py
│       │   │   ├── edit_campaign_plan.py
│       │   │   ├── reorder_campaign_item.py
│       │   │   └── approve_campaign_plan.py
│       │   │
│       │   ├── content/
│       │   │   ├── __init__.py
│       │   │   ├── generate_content_piece.py
│       │   │   ├── generate_social_post.py
│       │   │   ├── revise_content_piece.py
│       │   │   └── approve_content_piece.py
│       │   │
│       │   ├── validation/
│       │   │   ├── __init__.py
│       │   │   ├── claim_validator.py
│       │   │   ├── claim_linter.py
│       │   │   └── reason_mapper.py
│       │   │
│       │   ├── visual/
│       │   │   ├── __init__.py
│       │   │   ├── generate_visual_system.py
│       │   │   ├── plan_post_layout.py
│       │   │   └── validate_layout.py
│       │   │
│       │   ├── rendering/
│       │   │   ├── __init__.py
│       │   │   └── render_post.py
│       │   │
│       │   ├── export/
│       │   │   ├── __init__.py
│       │   │   └── export_campaign.py
│       │   │
│       │   ├── evaluation/
│       │   │   ├── __init__.py
│       │   │   ├── run_control_a.py
│       │   │   ├── run_system_b.py
│       │   │   ├── deterministic_metrics.py
│       │   │   └── human_eval.py
│       │   │
│       │   └── orchestration/
│       │       ├── __init__.py
│       │       └── vertical_slice_1.py
│       │
│       ├── ports/
│       │   ├── __init__.py
│       │   ├── ai.py
│       │   ├── ai_registry.py
│       │   ├── localization.py
│       │   ├── channels.py
│       │   ├── prompts.py
│       │   ├── repositories.py
│       │   ├── rendering.py
│       │   ├── telemetry.py
│       │   ├── storage.py
│       │   └── secrets.py
│       │
│       ├── infrastructure/
│       │   ├── __init__.py
│       │   │
│       │   ├── ai/
│       │   │   ├── __init__.py
│       │   │   ├── provider_registry.py
│       │   │   ├── model_registry.py
│       │   │   ├── mock_adapter.py
│       │   │   ├── openai_adapter.py
│       │   │   ├── anthropic_adapter.py
│       │   │   ├── google_adapter.py
│       │   │   ├── deepseek_adapter.py
│       │   │   ├── openrouter_adapter.py
│       │   │   └── openai_compatible_adapter.py
│       │   │
│       │   ├── prompts/
│       │   │   ├── __init__.py
│       │   │   └── yaml_prompt_repository.py
│       │   │
│       │   ├── database/
│       │   │   ├── __init__.py
│       │   │   ├── connection.py
│       │   │   ├── migrations.py
│       │   │   ├── unit_of_work.py
│       │   │   └── repositories/
│       │   │       ├── __init__.py
│       │   │       ├── brand_repository.py
│       │   │       ├── campaign_repository.py
│       │   │       ├── post_repository.py
│       │   │       └── telemetry_repository.py
│       │   │
│       │   ├── rendering/
│       │   │   ├── __init__.py
│       │   │   └── selected_renderer.py
│       │   │
│       │   ├── export/
│       │   │   ├── __init__.py
│       │   │   └── zip_exporter.py
│       │   │
│       │   ├── filesystem/
│       │   │   ├── __init__.py
│       │   │   └── local_project_storage.py
│       │   │
│       │   └── secrets/
│       │       ├── __init__.py
│       │       ├── environment_secret_store.py
│       │       └── keyring_secret_store.py
│       │
│       ├── jobs/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   ├── events.py
│       │   ├── cancellation.py
│       │   └── manager.py
│       │
│       └── presentation/
│           ├── __init__.py
│           ├── contracts.py
│           ├── state.py
│           └── ui_models.py
│
├── resources/
│   ├── i18n/
│   │   ├── en.json
│   │   └── bhs.json
│   │
│   ├── regional_language/
│   │   ├── bhs_neutral_v1.yaml
│   │   ├── bhs_bs_v1.yaml
│   │   ├── bhs_sr_v1.yaml
│   │   └── bhs_hr_v1.yaml
│   │
│   ├── platforms/
│   │   ├── instagram.yaml
│   │   ├── facebook.yaml
│   │   ├── linkedin.yaml
│   │   ├── x.yaml
│   │   ├── tiktok.yaml
│   │   ├── youtube.yaml
│   │   ├── pinterest.yaml
│   │   ├── threads.yaml
│   │   └── snapchat.yaml
│   │
│   ├── ai_providers/
│   │   ├── openai.yaml
│   │   ├── anthropic.yaml
│   │   ├── google.yaml
│   │   ├── deepseek.yaml
│   │   ├── openrouter.yaml
│   │   └── openai_compatible.yaml
│   │
│   ├── migrations/
│   │   ├── 0001_core.sql
│   │   ├── 0002_visual.sql
│   │   └── 0003_telemetry.sql
│   │
│   ├── campaign_roles/
│   │   └── v1.yaml
│   │
│   ├── campaign_templates/
│   │   └── v1.yaml
│   │
│   ├── claim_rules/
│   │   └── default_v1.yaml
│   │
│   └── templates/
│       └── README.txt
│
├── prompts/
│   ├── campaign_plan/
│   │   └── v1.yaml
│   ├── post_generation/
│   │   └── v1.yaml
│   ├── revision/
│   │   └── v1.yaml
│   ├── visual_direction/
│   │   └── v1.yaml
│   └── ab_control/
│       └── v1.yaml
│
├── fixtures/
│   └── brands/
│       └── dental_clinic_v1.json
│
├── spikes/
│   ├── renderer/
│   │   ├── html_playwright/
│   │   └── svg_candidate/
│   │
│   └── ui/
│       ├── shared_fixture/
│       ├── qt_post_studio/
│       └── webview_post_studio/
│
├── scripts/
│   ├── run_slice1.py
│   ├── run_ab_evaluation.py
│   └── init_dev_project.py
│
├── tests/
│   ├── architecture/
│   │   └── test_import_boundaries.py
│   ├── unit/
│   │   ├── domain/
│   │   └── application/
│   ├── integration/
│   │   ├── database/
│   │   ├── prompts/
│   │   ├── ai/
│   │   ├── rendering/
│   │   └── export/
│   ├── golden/
│   │   ├── fixtures/
│   │   └── test_campaign_engine.py
│   └── ui_spike/
│       └── evaluation_template.json
│
└── artifacts/
    └── .gitkeep
```

Napomena:

`artifacts/` služi samo za lokalne generated rezultate testova/spike-ova i mora biti git-ignored osim `.gitkeep`.

---

# 6. `pyproject.toml` — obavezni dependency princip

Agent ne treba odmah instalirati veliki stack.

## Core dependencies

Minimalno:

```text
pydantic
PyYAML
platformdirs
Pillow
keyring
```

## AI adapteri

Faza 1 mora podržati plug-and-play provider setup za početni built-in skup:

```text
OpenAI
Anthropic
Google
DeepSeek
OpenRouter
OpenAI-compatible
```

Za svaki built-in adapter preferirati zvanični SDK kada je stabilan i praktičan; ako adapter koristi direktni HTTP API, koristiti jedan zajednički HTTP client dependency umjesto dupliranja transport logike.

Tačne SDK pakete i njihove aktuelne verzije agent mora provjeriti u trenutku implementacije.

Ne hardkodovati model listu u dependency ili GUI sloj.

## Renderer spike

```text
playwright
```

samo za HTML/Playwright kandidat.

## UI spike extras

Kandidat A:

```text
PySide6
```

Kandidat B:

```text
pywebview
```

Ne dodavati Flask po defaultu.

## Dev dependencies

```text
pytest
pytest-cov
ruff
mypy
```

Opcionalno:

```text
pytest-timeout
```

## Pravilo

Ako dependency nema aktivnu funkciju u Fazi 1, ne dodavati ga.

---

# 7. Konfiguracija i putanje

## `config/settings.py`

Definisati framework-neutral `AppSettings`.

Minimalna polja:

```text
app_name
environment
data_dir
projects_dir
database_path
prompt_dir
resource_dir
artifact_dir
ai_provider
ai_model
ai_max_retries
ai_timeout_seconds
log_level
```

Ne držati API key kao polje koje se serijalizuje na disk.

## `config/paths.py`

Koristiti `platformdirs`.

Mora vratiti:

```text
app_data_dir
project_root_dir
database_dir
cache_dir
log_dir
```

Na Windowsu ne hardkodovati:

```text
C:\Users\...
```

## `config.example.toml`

Sadrži samo nesenzitivne vrijednosti.

Primjer:

```toml
ai_provider = "openai"
ai_model = "<configure>"
log_level = "INFO"
```

Ne stavljati pravi ključ.

---


# 7A. Localization modeli

## `localization/enums.py`

```text
AppLocale:
EN
BHS_LATIN

ContentLanguageFamily:
EN
BHS

BHSRegionalVariant:
NEUTRAL
BS
SR
HR

Script:
LATIN
```

Ne koristiti magic stringove po promptovima.

## `localization/language_context.py`

`ContentLanguageContext`:

```text
language_family
regional_variant
script
locale
preferred_terms
forbidden_terms
regional_vocabulary
tone_examples
```

Validation:

```text
EN
→ regional_variant mora biti NEUTRAL

BHS
→ regional_variant može biti NEUTRAL/BS/SR/HR

Faza 1
→ script mora biti LATIN
```

## `localization/translator.py`

Framework-neutral translator:

```text
Translator
- load locale resource
- t(key, **params)
- fallback_to_english
```

Ako key nedostaje u BHS:

```text
fallback EN
+
log missing translation key
```

Ne prikazivati sam key korisniku ako EN fallback postoji.


# 8. Domain modeli — tačne odgovornosti

Domain modeli su **plain Python dataclasses/enums**.

Pydantic se koristi na granicama:

- fixture input;
- AI structured output;
- export manifest;
- config validation gdje je korisno.

Ne praviti Pydantic kopiju svakog domain objekta bez potrebe.

---

# 9. `domain/common`

## `ids.py`

Centralne typed ID vrijednosti ili helperi:

```text
new_id() -> str UUID4
```

Poželjno imati type aliases:

```text
ProjectId
BrandId
BrandSnapshotId
FactId
CampaignId
CampaignPlanId
CampaignItemId
PostId
RevisionId
VisualSystemId
```

## `errors.py`

Base domain errors:

```text
DomainError
InvalidStateTransition
InvariantViolation
EntityNotFound
```

## `timestamps.py`

Jedan helper:

```text
utc_now()
```

Svi persistence timestampovi moraju biti UTC ISO-8601.

---

# 10. Brand domain

## `brand/value_objects.py`

Minimalno:

```text
BrandVoice
Audience
ServiceDefinition
Restriction
VisualIdentity
```

`BrandVoice`:

```text
formality
tone[]
preferred_terms[]
forbidden_terms[]
regional_vocabulary[]
tone_examples[]
```

`Audience`:

```text
id
name
description
needs[]
objections[]
```

`ServiceDefinition`:

```text
id
name
description
```

`VisualIdentity`:

```text
logo_path?
primary_colors[]
secondary_colors[]
font_families[]
image_style_notes[]
```

## `brand/entities.py`

### Brand

```text
Brand
- id
- name
- created_at
```

### BrandSnapshot

Immutable.

```text
BrandSnapshot
- id
- brand_id
- version
- language
- locale
- script
- voice
- audiences
- services
- visual_identity
- restrictions
- approved_fact_ids[]
- created_at
```

Pravilo:

BrandSnapshot se nikada ne mijenja nakon kreiranja.

---

# 11. Facts domain

## `facts/enums.py`

```text
FactStatus:
APPROVED
SUPERSEDED
SOFT_DELETED
```

Za Slice 1 nema `PROPOSED`; taj status dolazi u Slice 2 `FactCandidate` workflowu.

## `facts/entities.py`

### SourceReference

Čak i ručni fixture mora imati provenance placeholder.

```text
SourceReference
- source_type
- uri
- snapshot_id?
- chunk_id?
```

Za fixture:

```text
source_type = "fixture"
uri = "fixture://dental_clinic_v1"
```

### ApprovedFact

Immutable version.

```text
ApprovedFact
- id
- logical_fact_id
- version
- content
- source_ref
- status
- created_at
- superseded_by?
- deleted_at?
```

## `facts/policies.py`

Funkcije:

```text
is_fact_usable(fact)
assert_fact_usable(fact)
create_next_fact_version(previous, new_content, source_ref)
```

Ne mutirati tekst starog facta.

---

# 12. Campaign domain

## `campaign/enums.py`

### CampaignStatus

```text
DRAFT
PLAN_GENERATED
PLAN_APPROVED
GENERATING_POSTS
IN_REVIEW
APPROVED
EXPORTED
```

### CampaignPlanStatus

```text
DRAFT
APPROVED
SUPERSEDED
```

### CampaignItemStatus

```text
PLANNED
APPROVED
GENERATED
REJECTED
```

## `campaign/roles.py`

Enum:

```text
PROBLEM
EDUCATION
INSIGHT
BENEFIT
PROOF
TRUST
OBJECTION
MYTH_BUSTING
COMPARISON
BEHIND_THE_SCENES
PRODUCT
OFFER
URGENCY
ACTION
COMMUNITY
STORY
FAQ
```

Ne moraju svi biti korišteni u prvom fixture-u.

## `campaign/templates.py`

Domain representation:

```text
CampaignTemplate
- id
- name
- role_sequence[]
```

Početni resource template:

```text
lead_generation_v1
```

Sekvenca:

```text
PROBLEM
EDUCATION
PROOF
OBJECTION
BENEFIT
OFFER
ACTION
```

Ako je brief = 6 postova, planner može odabrati 6 od 7 uz opravdanu kombinaciju; test treba provjeriti da nema duplikata bez razloga.

## `campaign/entities.py`

### CampaignBrief

Domain objekat:

```text
id
offer
goal
audience_text
targets[]
content_piece_count
content_language_context
special_instructions[]
created_at
```

### Campaign

```text
id
brand_id
brand_snapshot_id
brief_id
status
created_at
```

### CampaignPlan

```text
id
campaign_id
version
status
items[]
created_at
```

### CampaignItem

```text
id
order
role
topic
goal
target_audience_id?
facts_needed[]
status
```

`facts_needed` ne mora sadržati actual fact ID ako planner samo kaže semantičku potrebu.

Post generation use-case radi actual fact selection.

---

# 13. Content domain

## `content/enums.py`

### ContentStatus

```text
PLANNED
GENERATING
DRAFT
NEEDS_REVIEW
APPROVED
REJECTED
EXPORTED
```

### ContentPayloadType

```text
SOCIAL_POST
```

Faza 1 implementira samo `SOCIAL_POST`.

Kasnije se mogu dodati:

```text
EMAIL
AD_CREATIVE
LANDING_PAGE
PRINT
DIRECT_MESSAGE
```

bez promjene CampaignPlan modela.

### ClaimType

```text
FACT
CTA
OPINION
CREATIVE
```

### ClaimStatus

```text
VERIFIED_BY_FACT
UNSUPPORTED
USER_APPROVED
PROHIBITED
NON_FACTUAL
```

## `content/claims.py`

### ContentClaim

```text
id
text
type
fact_ids[]
status
reason_codes[]
```

## `content/revisions.py`

### Revision

```text
id
entity_type
entity_id
version
timestamp
origin
provider?
model?
prompt_version?
previous_value
new_value
instruction?
```

`origin`:

```text
MANUAL
AI
SYSTEM
```

## `content/entities.py`

### CampaignTarget

```text
channel
platform_code
format_code
```

### ContentPiece

```text
id
campaign_item_id
target
payload_type
status
brand_snapshot_id
facts_allowed[]
claims[]
revision_ids[]
created_at
updated_at
```

### SocialPostPayload

```text
headline
caption
hook
body
cta
hashtags[]
visual_direction?
```

Pravilo:

Approved ContentPiece se ne mijenja tiho.

Revizija Approved sadržaja mora kreirati novi revision zapis i vratiti status u `NEEDS_REVIEW`.

# 14. Visual domain

## `visual/enums.py`

Minimalni primitive za Slice 1:

```text
HERO
SPLIT
```

Arhitektura mora dozvoliti kasnije:

```text
FAQ
QUOTE
PRODUCT
CTA
STAT
COMPARISON
TESTIMONIAL
FEATURE
```

## `visual/entities.py`

### CampaignVisualSystem

```text
id
campaign_id
style[]
primary_layout_family
secondary_layout_family?
headline_scale
image_treatment
logo_rule
cta_rule
alignment
created_at
```

## `visual/layout.py`

### LayoutSpec

```text
primitive
image_position
headline_position
headline_scale
overlay
logo_position
cta_style
alignment
format
```

Dozvoljene vrijednosti moraju biti enum/value object, ne slobodni stringovi iz LLM-a.

## `visual/slots.py`

### ContentSlotContract

```text
slot_name
target_chars
max_chars
max_lines
preferred_case
allow_wrap
font_family
min_font_size
max_font_size
bounding_box
line_height
alignment
overflow_policy
```

Za Slice 1 minimalno:

```text
headline
cta
```

Caption nije dio raster layouta u prvom rendereru.

---

# 15. Pydantic boundary schemas

## `application/schemas/brand_fixture.py`

Mora validirati fixture JSON.

Polja:

```text
brand.name
default_content_language_context
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

Mapper ga pretvara u immutable domain `ApprovedFact`.

## `campaign_brief.py`

Validira input iz GUI/CLI harnessa.

## `campaign_plan_output.py`

LLM output:

```json
{
  "campaign_theme": "...",
  "items": [
    {
      "order": 1,
      "role": "PROBLEM",
      "topic": "...",
      "goal": "...",
      "facts_needed": ["location", "implantology service"]
    }
  ]
}
```

Mora:

- imati tačno `content_piece_count` itema;
- order mora biti unique;
- role mora biti dozvoljen enum;
- topic ne smije biti prazan.

## `social_post_generation_output.py`

LLM output:

```json
{
  "headline": "...",
  "caption": "...",
  "hook": "...",
  "body": "...",
  "cta": "...",
  "hashtags": ["..."],
  "claims": [
    {
      "text": "...",
      "type": "FACT",
      "fact_ids": ["fact_..."]
    }
  ]
}
```

## `revision_output.py`

Samo polja koja se mijenjaju.

Ne dozvoliti da "NEW_HEADLINE" revision slučajno promijeni caption.

## `visual_direction_output.py`

Sadrži:

```text
CampaignVisualSystem candidate
LayoutSpec candidate
```

Svaka vrijednost mora biti schema-validirana.

---

# 16. Repository portovi

## `ports/repositories.py`

Ne praviti jedan generički repository za sve.

Definisati Protocol interfejse:

```text
BrandRepositoryPort
FactRepositoryPort
CampaignRepositoryPort
ContentRepositoryPort
VisualRepositoryPort
RevisionRepositoryPort
TelemetryRepositoryPort
```

Primjeri:

### `BrandRepositoryPort`

```text
save_brand(brand)
save_snapshot(snapshot)
get_snapshot(snapshot_id)
```

### `FactRepositoryPort`

```text
save_fact(fact)
get_fact(fact_id)
list_snapshot_facts(snapshot_id)
```

### `CampaignRepositoryPort`

```text
save_campaign(campaign)
save_brief(brief)
save_plan(plan)
get_campaign(campaign_id)
get_plan(plan_id)
```

### `ContentRepositoryPort`

```text
save_content_piece(content_piece)
get_content_piece(content_piece_id)
list_campaign_content(campaign_id)
```

Ne izlagati SQL detalje.

---

# 17. AI port

## `ports/ai.py`

Provider-neutral modeli:

```text
AIMessage
AIRequest
AIResponse
AITelemetry
```

`AIRequest`:

```text
purpose
prompt_name
prompt_version
system_text
user_text
json_schema
temperature?
max_output_tokens?
metadata
```

`AIResponse`:

```text
raw_text?
structured_payload?
provider
model
input_tokens?
output_tokens?
latency_ms
finish_reason?
request_id?
```

Protocol:

```text
TextGenerationPort.generate(request: AIRequest) -> AIResponse
```

Application sloj radi Pydantic validaciju structured payload-a.

Provider adapter ne vraća domain entity direktno.

---


# 17A. AI Registry portovi

## `ports/ai_registry.py`

```text
AIProviderRegistryPort
ModelRegistryPort
```

`AIProviderRegistryPort`:

```text
list_providers()
get_provider(provider_code)
test_connection(provider_code, credential_ref, base_url?)
discover_models(provider_code)
```

`ModelRegistryPort`:

```text
list_models(provider_code?)
get_model(provider_code, model_id)
resolve_default_text_model()
supports(model_profile, required_capabilities)
```

## `ports/channels.py`

```text
PlatformRegistryPort
```

```text
list_platforms(channel?)
get_platform(code)
list_formats(platform_code)
get_format(platform_code, format_code)
```


# 18. Prompt repository

## `ports/prompts.py`

```text
PromptRepositoryPort.get(name, version)
```

## YAML prompt metadata

Svaki prompt:

```yaml
name:
version:
purpose:
input_contract:
output_contract:
language_support:
instructions:
examples:
```

Prompt fajl nije samo tekst.

## Obavezni promptovi

### `campaign_plan/v1.yaml`

Input:

- BrandSnapshot summary;
- CampaignBrief;
- CampaignRole definitions;
- campaign template candidate;
- fact categories available.

Output:

- CampaignPlanOutputSchema.

### `post_generation/v1.yaml`

Input:

- CampaignItem;
- BrandSnapshot;
- AllowedFacts;
- language context;
- ContentSlotContract;
- platform;
- role rules.

Output:

- SocialPostGenerationOutputSchema.

### `revision/v1.yaml`

Input:

- current post;
- explicit revision command;
- immutable fields;
- allowed facts.

### `visual_direction/v1.yaml`

Output samo schema-valid layout/design intent.

### `ab_control/v1.yaml`

Jedan generički prompt koji dobija isti fixture + brief i traži N postova.

Ne davati CampaignRoles pipeline informacije Kontroli A.

---

# 19. Prompt pravila za EN/BHS

Svaki generation prompt mora eksplicitno dobiti:

```text
language_family
regional_variant
locale
script
preferred_terms
forbidden_terms
regional_vocabulary
tone_examples
```

Za lokalni test fixture koristiti:

```text
language_family: BHS
regional_variant: BS
locale: bs-BA
script: LATIN
```

Dodatno testirati:

```text
regional_variant: NEUTRAL
regional_variant: SR
regional_variant: HR
```

Ne praviti tri odvojena prompt sistema.

Svi koriste isti BHS prompt contract, a regionalni vocabulary/few-shot kontekst se dodaje kroz `ContentLanguageContext`.

Za engleski:

```text
language_family: EN
regional_variant: NEUTRAL
locale: en
script: LATIN
```

U testovima obavezno provjeriti glyph/string očuvanje:

```text
č ć š ž đ
Č Ć Š Ž Đ
```

Few-shot pravilo:

- English output → engleski primjeri;
- BHS output → lokalni primjeri;
- BS/SR/HR varijanta → najmanje jedan terminološki primjer gdje regionalna razlika stvarno postoji.

Ne koristiti samo engleske examples sa instrukcijom `write in Bosnian/Serbian/Croatian`.

---


# 19A. UI translation resources

## `resources/i18n/en.json`

Canonical English UI set.

Primjer:

```json
{
  "app.title": "AI Campaign Studio",
  "campaign.create": "Create campaign",
  "campaign.plan.approve": "Approve plan",
  "post.approve": "Approve post",
  "facts.used": "Facts used",
  "warning.unsupported_number": "Number found without an approved fact"
}
```

## `resources/i18n/bhs.json`

Jedan zajednički lokalni UI set.

Primjer:

```json
{
  "app.title": "AI Campaign Studio",
  "campaign.create": "Kreiraj kampanju",
  "campaign.plan.approve": "Odobri plan",
  "post.approve": "Odobri objavu",
  "facts.used": "Korištene činjenice",
  "warning.unsupported_number": "Broj je pronađen bez odobrene činjenice"
}
```

Ne održavati zasebne `bs.json`, `sr.json`, `hr.json`.

## `resources/regional_language/*.yaml`

Ovi fajlovi nisu UI prevodi.

Oni sadrže terminološke preference za AI copy.

Primjer:

```yaml
language_family: BHS
regional_variant: BS
preferred_terms:
  - ...
forbidden_terms:
  - ...
regional_vocabulary:
  - canonical: ...
    preferred: ...
```

Ako nema stvarne regionalne razlike, ne dodavati nepotrebno pravilo.


# 20. AI adapter implementacija

## `mock_adapter.py`

Prvi adapter koji se implementira.

Mora omogućiti:

- deterministic fixtures;
- error simulation;
- invalid-schema simulation;
- rate-limit simulation;
- telemetry simulation.

Bez mock adaptera application testovi će postati zavisni od mreže.

## Provider adapteri

Faza 1 provider setup je završen tek kada postoje:

```text
mock_adapter.py
openai_adapter.py
anthropic_adapter.py
google_adapter.py
deepseek_adapter.py
openrouter_adapter.py
openai_compatible_adapter.py
```

Svaki adapter implementira samo odgovarajuće AI portove i provider discovery/test-connection capability gdje je dostupna.

Ako neki provider ne podržava pouzdan model discovery, adapter koristi registry fallback ili manual model ID umjesto lažnog discovery-a.

Pravila:

- nema business logike;
- nema CampaignRole logike;
- nema claim validation;
- nema persistence;
- nema GUI;
- transformiše provider API ↔ `AIRequest/AIResponse`.

## Retry policy

Application orchestration:

```text
attempt 1
  ↓
schema valid?
  ├─ yes → continue
  └─ no
       ↓
attempt 2 with explicit schema-repair instruction
       ↓
schema valid?
  ├─ yes
  └─ no → AI_SCHEMA_ERROR
```

Ne praviti beskonačne retry petlje.

Network/rate-limit retry policy može biti u adapteru, ali ograničen.

Svaki retry mora biti logovan.

---

# 21. Telemetry

## `ports/telemetry.py`

Event modeli:

```text
AICallTelemetry
PipelineTelemetry
```

Za svaki AI poziv:

```text
provider
model
prompt_name
prompt_version
input_tokens
output_tokens
latency_ms
retry_count
context_size
schema_valid
error_type
timestamp
campaign_id?
content_piece_id?
```

Nikada ne logovati API ključ.

Full prompt payload nije obavezan.

## Campaign summary

Izračunati:

```text
number_of_calls
total_input_tokens
total_output_tokens
total_latency
schema_failure_rate
retry_rate
```

---

# 22. SQLite — migration strategija

Ne koristiti ručno `CREATE TABLE IF NOT EXISTS` rasuto po repository fajlovima.

Koristiti:

```text
resources/migrations/
```

i tabelu:

```text
schema_migrations
```

## `migrations.py`

Radi:

```text
1. otvori DB
2. pročita current version
3. pronađe nove SQL fajlove
4. izvrši svaki u transactionu
5. zapiše migration version
```

Ako migration faila:

```text
rollback
DATABASE_ERROR
```

---

# 23. Početna SQLite šema

## `0001_core.sql`

Tabele:

```text
projects
brands
approved_facts
brand_snapshots
brand_snapshot_facts
campaign_briefs
campaigns
campaign_plans
campaign_items
content_pieces
content_claims
revisions
provider_configs
model_selections
```

### `projects`

```text
id TEXT PRIMARY KEY
display_name TEXT NOT NULL
created_at TEXT NOT NULL
```

### `brands`

```text
id TEXT PRIMARY KEY
project_id TEXT NOT NULL
name TEXT NOT NULL
created_at TEXT NOT NULL
```

### `approved_facts`

```text
id TEXT PRIMARY KEY
brand_id TEXT NOT NULL
logical_fact_id TEXT NOT NULL
version INTEGER NOT NULL
content TEXT NOT NULL
source_ref_json TEXT NOT NULL
status TEXT NOT NULL
created_at TEXT NOT NULL
superseded_by TEXT NULL
deleted_at TEXT NULL
UNIQUE(logical_fact_id, version)
```

### `brand_snapshots`

```text
id TEXT PRIMARY KEY
brand_id TEXT NOT NULL
version INTEGER NOT NULL
payload_json TEXT NOT NULL
created_at TEXT NOT NULL
UNIQUE(brand_id, version)
```

### `brand_snapshot_facts`

```text
brand_snapshot_id TEXT NOT NULL
fact_id TEXT NOT NULL
PRIMARY KEY(brand_snapshot_id, fact_id)
```

### `campaign_briefs`

```text
id TEXT PRIMARY KEY
payload_json TEXT NOT NULL
created_at TEXT NOT NULL
```

### `campaigns`

```text
id TEXT PRIMARY KEY
brand_id TEXT NOT NULL
brand_snapshot_id TEXT NOT NULL
brief_id TEXT NOT NULL
status TEXT NOT NULL
created_at TEXT NOT NULL
```

### `campaign_plans`

```text
id TEXT PRIMARY KEY
campaign_id TEXT NOT NULL
version INTEGER NOT NULL
status TEXT NOT NULL
created_at TEXT NOT NULL
UNIQUE(campaign_id, version)
```

### `campaign_items`

```text
id TEXT PRIMARY KEY
plan_id TEXT NOT NULL
sort_order INTEGER NOT NULL
role TEXT NOT NULL
topic TEXT NOT NULL
goal TEXT NOT NULL
target_audience_id TEXT NULL
facts_needed_json TEXT NOT NULL
status TEXT NOT NULL
UNIQUE(plan_id, sort_order)
```

### `content_pieces`

```text
id TEXT PRIMARY KEY
campaign_item_id TEXT NOT NULL
channel TEXT NOT NULL
platform_code TEXT NOT NULL
format_code TEXT NOT NULL
payload_type TEXT NOT NULL
payload_json TEXT NOT NULL
status TEXT NOT NULL
brand_snapshot_id TEXT NOT NULL
facts_allowed_json TEXT NOT NULL
created_at TEXT NOT NULL
updated_at TEXT NOT NULL
```

### `content_claims`

```text
id TEXT PRIMARY KEY
content_piece_id TEXT NOT NULL
text TEXT NOT NULL
claim_type TEXT NOT NULL
fact_ids_json TEXT NOT NULL
status TEXT NOT NULL
reason_codes_json TEXT NOT NULL
```

### `revisions`

```text
id TEXT PRIMARY KEY
entity_type TEXT NOT NULL
entity_id TEXT NOT NULL
version INTEGER NOT NULL
timestamp TEXT NOT NULL
origin TEXT NOT NULL
provider TEXT NULL
model TEXT NULL
prompt_version TEXT NULL
previous_value_json TEXT NOT NULL
new_value_json TEXT NOT NULL
instruction TEXT NULL
```

---


### `provider_configs`

```text
provider_code TEXT PRIMARY KEY
configured INTEGER NOT NULL
validated INTEGER NOT NULL
credential_ref TEXT NULL
base_url TEXT NULL
updated_at TEXT NOT NULL
```

Ne čuvati API ključ u ovoj tabeli.

### `model_selections`

```text
purpose TEXT PRIMARY KEY
provider_code TEXT NOT NULL
model_id TEXT NOT NULL
updated_at TEXT NOT NULL
```

Početni purpose:

```text
DEFAULT_TEXT
```

Kasnije:

```text
CAMPAIGN_PLANNING
CONTENT_GENERATION
REVISION
VISUAL_DIRECTION
```


# 24. `0002_visual.sql`

Tabele:

```text
campaign_visual_systems
layout_specs
render_artifacts
```

### `campaign_visual_systems`

```text
id
campaign_id
payload_json
created_at
```

### `layout_specs`

```text
id
content_piece_id
format
payload_json
validation_status
created_at
```

### `render_artifacts`

```text
id
content_piece_id
format
path
checksum
created_at
```

---

# 25. `0003_telemetry.sql`

Tabela:

```text
ai_call_logs
```

Kolone:

```text
id
campaign_id?
content_piece_id?
provider
model
prompt_name
prompt_version
input_tokens?
output_tokens?
latency_ms
retry_count
context_size?
schema_valid
error_type?
created_at
```

---

# 26. Unit of Work

## `unit_of_work.py`

Za multi-repository use-case koji mora biti atomic.

Primjer:

```text
generate post
  ↓
save post
save claims
save revision
save telemetry reference
```

Ako persistence dio faila:

```text
rollback
```

Use-case ne smije znati SQL transaction detalje.

Minimalni interface:

```text
begin()
commit()
rollback()
```

ili context manager.

---

# 27. Brand Fixture — prvi stvarni podatak

`fixtures/brands/dental_clinic_v1.json`

Mora biti dovoljno kvalitetan da testira:

- B/H/S;
- facts;
- restrictions;
- voice;
- audiences;
- services;
- visual identity;
- numeric claims;
- prohibited claims.

Minimalno 12–20 Approved Facts.

Primjer kategorija:

```text
location
services
contact
opening information
process
offer facts
brand identity
```

Ne ubacivati neprovjerene medicinske superlative samo da test prođe.

Dodati najmanje:

- jedan numeric fact;
- jednu cijenu ili trajanje samo ako fixture eksplicitno kaže;
- jednu restriction stavku;
- jedan forbidden term;
- nekoliko tone examples.

---

# 28. `load_brand_fixture.py`

Use-case:

```text
JSON path
  ↓
Pydantic validation
  ↓
map to Brand
  ↓
map facts
  ↓
create BrandSnapshot
  ↓
persist all
```

Output:

```text
brand_id
brand_snapshot_id
fact_ids[]
```

Acceptance:

- invalid fixture faila prije DB upisa;
- transaction rollback;
- snapshot immutable;
- svaki fact ima source_ref.

---

# 29. Campaign Brief use-case

`create_campaign.py`

Input:

```text
brand_snapshot_id
CampaignBriefSchema
```

Radi:

1. validate brief;
2. create brief;
3. create Campaign DRAFT;
4. persist.

Ne generiše plan.

---

# 30. Campaign Plan generation

`generate_campaign_plan.py`

Pipeline:

```text
Campaign
  ↓
BrandSnapshot
  ↓
CampaignBrief
  ↓
CampaignRole definitions
  ↓
Campaign template candidate
  ↓
Prompt
  ↓
TextGenerationPort
  ↓
Pydantic CampaignPlanOutput
  ↓
domain validation
  ↓
CampaignPlan DRAFT
  ↓
persist
```

## Domain validation

Mora provjeriti:

- item count = brief.content_piece_count;
- order unique;
- role valid;
- topic non-empty;
- role diversity >= minimalni prag;
- nema identičnih topic stringova;
- Campaign status prelazi u `PLAN_GENERATED`.

Ne koristiti LLM da validira svoj output.

---

# 31. Campaign plan manual edit

## `edit_campaign_plan.py`

Dozvoljeno:

```text
change topic
change goal
change role
delete item
add item
replace item
```

Svaka izmjena kreira novu `CampaignPlan.version`.

Stari plan:

```text
SUPERSEDED
```

Novi:

```text
DRAFT
```

Ne mutirati odobreni plan.

## `reorder_campaign_item.py`

Reorder takođe pravi novu plan verziju.

---

# 32. Approve Campaign Plan

`approve_campaign_plan.py`

Provjerava:

- plan postoji;
- plan nije superseded;
- broj itema je validan;
- nema duplicate order;
- svaki item ima role/topic/goal.

Status:

```text
CampaignPlan → APPROVED
Campaign → PLAN_APPROVED
```

Post generation ne smije krenuti sa DRAFT planom.

---

# 33. Allowed Fact Selection

U Slice 1 ne uvoditi embeddings.

Selection prvo koristi:

1. `facts_needed`;
2. service/audience/role metadata;
3. deterministic keyword/tag mapping iz fixture-a.

Ako nema dovoljno metadata, dopušten je jednostavan lexical matcher.

Ne uvoditi vector DB.

Use-case može biti mali helper:

```text
application/posts/select_allowed_facts.py
```

Ako se pokaže da selection logika raste, izdvojiti ga.

Output:

```text
AllowedFactSet
- fact_ids[]
- selection_reasons{}
```

Mora zadržati samo `APPROVED` i non-superseded facts.

---

# 34. Social Content generation pipeline

`generate_social_post.py`

Tačan redoslijed:

```text
CampaignItem
     ↓
Campaign + BrandSnapshot
     ↓
Select Allowed Facts
     ↓
Role rules
     ↓
Language Context
     ↓
CampaignTarget
     ↓
PlatformDefinition + FormatDefinition rules
     ↓
ContentSlotContract
     ↓
Prompt build
     ↓
AI call
     ↓
Pydantic schema validation
     ↓
map to ContentPiece + SocialPostPayload
     ↓
FACT-ID validator
     ↓
deterministic linter
     ↓
derive PostStatus
     ↓
persist ContentPiece + Claims + Revision
```

Ne renderovati u istom use-caseu.

---

# 35. Fact-ID validator

`claim_validator.py`

Za svaki claim:

## FACT

Mora:

- imati najmanje 1 `fact_id`;
- svaki fact postoji;
- fact status = APPROVED;
- fact nije superseded;
- fact nije soft-deleted;
- fact ID je bio u `facts_allowed`.

Ako prođe:

```text
VERIFIED_BY_FACT
```

Ako ne:

```text
UNSUPPORTED
```

+ reason code.

## CTA

Default:

```text
NON_FACTUAL
```

ali numeric CTA i dalje može pasti na linter.

## OPINION / CREATIVE

Default:

```text
NON_FACTUAL
```

ali prohibited phrase linter se i dalje primjenjuje.

---

# 36. Claim linter

`claim_linter.py`

Rule config:

```text
resources/claim_rules/default_v1.yaml
```

## Početni reason codes

```text
unsupported-number
unsupported-price
unsupported-percent
unsupported-date
unsupported-duration
prohibited-claim
risky-superlative
missing-fact-id
fact-not-approved
fact-superseded
fact-not-offered
```

## Numeric patterns

Detektovati:

- valute;
- `%`;
- godine;
- datume;
- trajanja;
- količine;
- popuste.

B/H/S valute:

```text
KM
BAM
EUR
€
RSD
```

Ne mora savršeno razumjeti semantiku.

Cilj je signal:

```text
"ovdje postoji numeric claim koji mora biti fact-backed"
```

## Prohibited/risky terms

Početna lista:

```text
najbolji
vodeći
garantujemo
100%
bez rizika
potpuno sigurno
najjeftiniji
jedini
certifikovan
```

Industry/brand restrictions se dodaju u isti evaluation pass.

---

# 37. Derivacija Content statusa

Nakon validatora/lintera:

Ako postoji:

```text
PROHIBITED
```

→ `NEEDS_REVIEW`

Ako postoji:

```text
UNSUPPORTED FACT
```

→ `NEEDS_REVIEW`

Ako nema warninga:

→ `DRAFT`

Ne auto-approve post.

Korisnik/agent kasnije eksplicitno radi `approve_post`.

---

# 38. Content revisions

`revise_content_piece.py`

Input:

```text
content_piece_id
revision_type
instruction
```

Početni revision types:

```text
SHORTER
LONGER
STRONGER_HOOK
MORE_PROFESSIONAL
MORE_FRIENDLY
LESS_PROMOTIONAL
NEW_CTA
NEW_HEADLINE
NEW_VISUAL_DIRECTION
CUSTOM
```

## Partial revision contract

Primjer:

```text
NEW_HEADLINE
```

Smije promijeniti samo:

```text
headline
claims koji direktno pripadaju headline-u ako ih model vraća odvojeno
```

Ne smije mijenjati caption.

Nakon AI revisiona ponovo:

```text
schema validation
fact validation
linter
revision record
```

---

# 39. Visual System generation

`generate_visual_system.py`

Input:

```text
BrandSnapshot
CampaignBrief
CampaignPlan
```

Output:

```text
CampaignVisualSystem
```

Za Slice 1 ne dozvoliti proizvoljne style vrijednosti.

Npr.:

```text
style:
clean
clinical
calm
warm
bold
minimal
editorial
```

Layout family:

```text
HERO
SPLIT
```

AI bira iz dozvoljene liste.

---

# 40. Layout planning

`plan_post_layout.py`

Input:

```text
CampaignVisualSystem
CampaignItem
Post
supported primitives
format
```

Output:

```text
LayoutSpec
```

Mora biti schema-valid.

Ne dozvoliti AI-u da vrati CSS.

---

# 41. ContentSlotContract — Slice 1 defaults

Za `1080x1350`:

## HERO headline

Početni kandidat:

```text
target_chars: 28–42
max_chars: 55
max_lines: 2
min_font_size: 48
max_font_size: 72
```

## SPLIT headline

```text
target_chars: 24–38
max_chars: 48
max_lines: 3
min_font_size: 42
max_font_size: 64
```

Ovo nisu trajne dizajnerske istine.

To su početni test parametri.

Golden/render test treba ih kalibrisati.

---

# 42. Renderer spike

Ne implementirati production renderer prije spike-a.

Folder:

```text
spikes/renderer/
```

## Kandidat R-A — HTML/CSS + Playwright

Testirati:

- font loading;
- deterministic viewport;
- text measurement;
- PNG screenshot;
- 1080x1350;
- B/H/S glyphs;
- overflow;
- startup time;
- persistent browser;
- crash/cancel.

## Kandidat R-B — SVG-based

Može koristiti:

- generisani SVG;
- browser/Pillow/rasterizer gdje je najjednostavnije.

Cilj nije savršena biblioteka.

Cilj je poređenje:

```text
determinism
layout control
text measurement
packaging
performance
implementation complexity
```

## Spike output

Jedan strukturisani rezultat:

```text
artifacts/renderer_spike_result.json
```

Polja:

```text
candidate
render_success
overflow_detection
bhs_glyphs_ok
avg_render_ms
memory_notes
packaging_notes
implementation_notes
decision
```

Tek nakon odluke kreirati:

```text
infrastructure/rendering/selected_renderer.py
```

---

# 43. Renderer port

`ports/rendering.py`

```text
RenderRequest
RenderResult
RendererPort
```

`RenderRequest`:

```text
content_piece_id
format
layout_spec
content
visual_system
image_path?
logo_path?
output_path
```

`RenderResult`:

```text
status
output_path
warnings[]
measured_slots{}
render_ms
```

Renderer ne zna Campaign repository.

Dobije sve kroz request.

---

# 44. Layout validation

`validate_layout.py`

Provjerava:

```text
supported primitive
supported format
slot bounding boxes
max lines
font range
overflow
required assets
```

Ako headline ne stane:

```text
LAYOUT_VALIDATION_ERROR
```

Application može tražiti:

```text
SHORTEN_HEADLINE
```

Ne regenerisati cijeli post.

---

# 45. Slice 1 render formati

Obavezno:

```text
1080x1350
```

Opcionalno ako prvi format stabilno radi:

```text
1080x1080
```

Story `1080x1920` nije potreban za G10.

Arhitektura mora podržati format enum bez refaktora.

---

# 46. Export

`export_campaign.py`

Output:

```text
campaign-export.zip
├── campaign.json
├── content-01/
│   ├── feed.png
│   ├── caption.txt
│   └── content.json
├── post-02/
│   ├── feed.png
│   ├── caption.txt
│   └── content.json
...
└── telemetry/
    └── ai_summary.json
```

## `campaign.json`

Sadrži:

```text
campaign_id
brand_snapshot_id
brief
plan_version
visual_system_id
content_piece_ids[]
created_at
exported_at
```

Ne uključivati API ključeve.

## ZIP pravilo

Export se pravi iz snapshotovanih/persistovanih podataka.

Ne iz slučajnog trenutnog UI state-a.

---

# 47. A/B kontrola

## Control A

`run_control_a.py`

Dobija:

```text
Brand Fixture summary
Campaign Brief
N posts
```

Jedan AI poziv.

Ne koristiti:

- CampaignRole sequence;
- AllowedFact selection per post;
- Campaign Plan review;
- per-post generation.

Može dobiti sve Approved Facts kao obični brand context jer cilj nije sabotirati kontrolu.

## System B

Koristi puni pipeline.

---

# 48. Determinističke metrike

`deterministic_metrics.py`

Po kampanji izračunati:

```text
unique_role_count
duplicate_topic_count
exact_duplicate_caption_count
unsupported_fact_claim_count
forbidden_phrase_hits
numeric_claim_violations
missing_fact_ids
schema_failure_count
layout_failure_count
headline_overflow_count
cta_unique_count
```

Za tekst similarity u Fazi 1:

Ne uvoditi embeddings kao dependency samo zbog jedne metrike.

Može se koristiti jednostavna lexical/Jaccard metrika kao pomoćna, uz oznaku:

```text
heuristic only
```

Pravi embedding threshold ostaje kasnija odluka.

---

# 49. Human evaluation

`human_eval.py`

Generisati evaluacioni JSON/CSV obrazac:

```text
Brand fit:              1–5
Language naturalness:   1–5
Campaign coherence:     1–5
Post diversity:         1–5
Usefulness:             1–5
Visual consistency:     1–5
Comments
```

Evaluator ne treba znati unaprijed da li gleda A ili B ako možemo napraviti blind comparison.

Poželjno:

```text
Campaign X
Campaign Y
```

pa tek kasnije reveal.

---

# 50. Kill/Pivot gate

Nakon najmanje nekoliko realnih runova istog fixture-a:

Ako System B ne pokazuje:

- manje unsupported claims;
- veću campaign coherence;
- bolju post diversity;
- barem jednaku language naturalness;
- prihvatljiv latency/stability;

ne implementirati Slice 2.

Prvo revidirati:

```text
CampaignRole rules
prompt design
fact selection
brief schema
post generation contract
```

Ne pokušavati problem riješiti dodavanjem RAG-a ili više agenata.

---

# 51. Framework-neutral jobs

## `jobs/models.py`

```text
JobStatus:
PENDING
RUNNING
CANCELLING
CANCELLED
SUCCEEDED
FAILED
```

`JobState`:

```text
id
job_type
status
progress_current
progress_total
phase
message
error_type?
error_message?
started_at?
finished_at?
```

## `events.py`

Framework-neutral event:

```text
JobEvent
- job_id
- event_type
- payload
```

## `cancellation.py`

Thread-safe cancellation token.

## `manager.py`

Početno može koristiti:

```text
ThreadPoolExecutor
```

Za network/AI I/O.

Renderer/Playwright može koristiti subprocess adapter.

Ne koristiti Qt signals u ovom modulu.

---

# 52. UI framework spike — obavezan

Ne graditi svih 6 ekrana prije G9.

Napraviti isti Post Studio spike.

## Shared fixture

`spikes/ui/shared_fixture/post_studio_fixture.json`

Sadrži:

- headline;
- caption;
- CTA;
- 2 verified facts;
- 1 warning;
- post status;
- fake image path;
- progress state.

## Kandidat UI-A — PySide6

Folder:

```text
spikes/ui/qt_post_studio/
```

Mora prikazati i prebacivanje:

```text
EN ↔ BHS
```

bez ponovnog pokretanja spike-a, ako toolkit to razumno podržava.

Mora prikazati:

- sidebar ili header;
- preview;
- rounded cards;
- headline field;
- caption field;
- CTA;
- facts chips;
- warning card;
- quick actions;
- selected state;
- progress update.

Dozvoljeno:

- QSS;
- standardni Qt widgets;
- ograničen custom painting samo gdje ima stvarnu vrijednost.

Ako spike zahtijeva veliki broj custom-painted widgeta, to se bilježi kao trošak.

## Kandidat UI-B — pywebview

Folder:

```text
spikes/ui/webview_post_studio/
```

Koristiti:

- HTML;
- CSS;
- mali JS;
- pywebview bridge.

Ne uvoditi React/Vue/Svelte samo zbog spike-a.

Ne uvoditi Flask osim ako bridge ne može riješiti potrebnu komunikaciju.

---

# 53. UI spike test matrica

Oba kandidata moraju proći isti test.

## Vizuelno

Testirati isti ekran u:

```text
EN
BHS
```

Posebno provjeriti da duži BHS stringovi ne lome layout.

```text
rounded cards
chips
warning panel
spacing
typography
hover
selected state
preview
light/dark kandidat
```

## Windows desktop

Testirati:

```text
100% scaling
125% scaling
150% scaling
window resize
minimum window
```

## Lokalni workflow

Testirati:

```text
file dialog
drag/drop image
clipboard paste
open local image
save/export dialog
```

## Runtime

Testirati:

```text
background progress update
cancel button
startup time
memory
```

## Packaging smoke test

Napraviti minimalni executable/package prototip za oba kandidata.

Ne traži se production installer.

Traži se dokaz da framework može biti spakovan.

---

# 54. UI framework odluka

Rezultat zapisati u:

```text
artifacts/ui_framework_spike_result.json
```

Polja:

```text
candidate
visual_fidelity_score
high_dpi_score
native_integration_score
background_jobs_score
packaging_score
maintenance_score
startup_ms
memory_mb
known_limitations[]
decision
```

Tek tada agent kreira produkcijski Presentation adapter.

Ako PySide6 pobijedi:

```text
src/ai_campaign_studio/presentation_qt/
```

Ako pywebview pobijedi:

```text
src/ai_campaign_studio/presentation_webview/
```

Ne držati oba production sloja.

Gubitnički spike ostaje samo u `spikes/`.

---

# 55. Production MVP ekrani nakon G9

Implementirati samo:

```text
1. Settings / AI Providers
2. Fixture/Brand selector
3. Campaign Brief
4. Campaign Plan
5. Campaign Board
6. Post Studio
7. Export
```

## Presentation pravilo

Ekran ne poziva AI adapter.

Primjer:

```text
Button click
   ↓
ViewModel/Presenter
   ↓
Application facade / use-case
   ↓
JobManager
   ↓
Use case
```

---

# 56. Presentation contracts

`presentation/contracts.py`

Definisati akcije:

```text
set_app_locale
load_fixture
create_campaign
generate_plan
approve_plan
generate_post
revise_post
approve_post
render_post
export_campaign
cancel_job
```

`presentation/state.py`

Drži samo UI state:

```text
app_locale
selected_project
selected_campaign
selected_plan
selected_post
current_job
notifications
```

Ne duplicirati domain stanje.

---

# 57. Bootstrap / Composition Root

`bootstrap.py` je jedino mjesto koje zna konkretne adaptere.

Primjer:

```text
Settings
  ↓
SQLite connection
  ↓
Repositories
  ↓
Prompt repository
  ↓
AI adapter
  ↓
Renderer adapter
  ↓
Use cases
  ↓
JobManager
  ↓
Presentation facade
```

Ne raditi dependency injection framework.

Plain Python composition je dovoljan.

---

# 58. `main.py`

Nakon UI odluke:

```text
load settings
run migrations
build container/bootstrap
launch selected presentation
```

Ako DB migration faila:

- ne pokretati GUI kao da je sve u redu;
- prikazati jasnu startup grešku.

---

# 59. Development CLI harness

Iako proizvod nije CLI-first, agent mora imati brz način da testira engine prije GUI-a.

## `scripts/run_slice1.py`

Radi:

```text
load fixture
create campaign
generate plan
auto-approve plan ONLY for dev harness
generate posts
render
export
print summary
```

Auto-approve je dozvoljen samo u dev harnessu.

Produkciona aplikacija zahtijeva human approval.

## `scripts/run_ab_evaluation.py`

Pokreće:

```text
Control A
System B
metrics
human eval package
```

---

# 60. Error taxonomy

Centralno definisati machine-readable error codes.

Početni skup:

```text
NETWORK_ERROR
RATE_LIMIT
PROVIDER_ERROR
AI_SCHEMA_ERROR
MISSING_FACT
PROHIBITED_CLAIM
LAYOUT_VALIDATION_ERROR
RENDER_ERROR
DATABASE_ERROR
BACKUP_ERROR
SOURCE_PARSE_ERROR
SITEMAP_ERROR
CRAWL_BUDGET_EXCEEDED
PLAYWRIGHT_WORKER_ERROR
STRUCTURED_DATA_ERROR
SOURCE_CONFLICT
STALE_FACT_WARNING
CHECKPOINT_ERROR
UI_BRIDGE_ERROR
UI_RENDERING_ERROR
```

Faza 1 neće proizvesti sve ove greške, ali taxonomy može biti definisan.

Ne implementirati nepostojeće feature handlere.

Za Slice 1 obavezno koristiti:

```text
NETWORK_ERROR
RATE_LIMIT
PROVIDER_ERROR
AI_SCHEMA_ERROR
MISSING_FACT
PROHIBITED_CLAIM
LAYOUT_VALIDATION_ERROR
RENDER_ERROR
DATABASE_ERROR
UI_BRIDGE_ERROR
UI_RENDERING_ERROR
```

---

# 61. Logging

Kategorije:

```text
UI
APPLICATION
DOMAIN
AI
RENDER
DATABASE
SOURCE
BACKUP
```

Za Fazu 1 aktivno:

```text
UI
APPLICATION
DOMAIN
AI
RENDER
DATABASE
```

Log record:

```text
timestamp
level
category
event
entity_id?
job_id?
message
error_code?
```

Ne logovati:

- API key;
- secrets;
- puni sensitive prompt po defaultu.

---

# 62. Secret storage

## `SecretStorePort`

```text
get_secret(name)
set_secret(name, value)
delete_secret(name)
```

## Dev adapter

`EnvironmentSecretStore`

Čita environment variable.

## Desktop adapter

`KeyringSecretStore`

Za production desktop.

Ne čuvati key u:

```text
config.toml
SQLite
project_manifest.json
logs
```

---


# 62A. AI provider/model setup

## Provider setup use-caseovi

Dodati:

```text
application/ai/
├── configure_provider.py
├── test_provider_connection.py
├── discover_models.py
├── select_default_model.py
└── list_available_models.py
```

### `configure_provider`

Input:

```text
provider_code
api_key
base_url?   # samo za OpenAI-compatible/custom
```

Radi:

```text
save secret to SecretStorePort
save non-secret provider config
```

Ne označava provider kao validated dok Test Connection ne prođe.

### `test_provider_connection`

Mora vratiti typed rezultat:

```text
CONNECTED
INVALID_API_KEY
NETWORK_ERROR
RATE_LIMIT
PROVIDER_ERROR
```

### `discover_models`

Ako provider podržava listing:

```text
API discovery
```

inače:

```text
registry fallback
```

### `select_default_model`

Provjerava:

```text
provider configured
model exists/manual allowed
TEXT_GENERATION supported
STRUCTURED_OUTPUT supported za use-caseove koji ga zahtijevaju
```

MVP Settings UI:

```text
AI Providers / Models

[ OpenAI ]
[ Anthropic ]
[ Google ]
[ DeepSeek ]
[ OpenRouter ]
[ OpenAI-compatible ]

klik provider/model
      ↓
API Key
[________________]

[ TEST CONNECTION ]

✓ Connected

Model
[ discovered / registry / manual ▼ ]

Default text model
[______________________________]
```

Ako korisnik klikne konkretan model iz model browsera, aplikacija prvo resolve-a `provider_code`, zatim otvara odgovarajući provider credential setup.


# 63. Project storage

`local_project_storage.py`

Project folder:

```text
projects/<UUID>/
```

Minimalno:

```text
project_manifest.json
assets/
renders/
exports/
```

SQLite baza može biti app-globalna za Slice 1 ili per-project.

Preporuka za prvi slice:

```text
jedna app SQLite baza
+
project-specific asset folders
```

To smanjuje migracionu/povezivačku kompleksnost.

`project_manifest.json`:

```text
project_id
display_name
created_at
```

---

# 64. Architecture test

`tests/architecture/test_import_boundaries.py`

AST scan ili sličan lagani test.

Provjeriti najmanje:

```text
domain ne importuje infrastructure
domain ne importuje presentation
domain ne importuje provider SDK
application ne importuje presentation
application ne importuje infrastructure adapters
application ne importuje PySide6/pywebview/playwright
```

Ovaj test mora ostati kroz cijeli razvoj.

Ako agent mora kršiti boundary, prvo treba promijeniti arhitekturu eksplicitno.

---


# 64A. Channel registry testovi

Obavezno:

```text
load all platform YAML files
unique platform codes
all referenced formats exist
channel values valid
disabled platform hidden from normal selection
unknown platform fails explicitly
new registry entry can be added without Campaign Engine code change
```

Početne platforme:

```text
Instagram
Facebook
LinkedIn
X
TikTok
YouTube
Pinterest
Threads
Snapchat
```

Ne zahtijeva da sve imaju kompletan production generator u Fazi 1.

---

# 64B. AI provider/model registry testovi

Obavezno:

```text
provider registry loads
unique provider codes
API key never persisted in SQLite
keyring credential_ref roundtrip
test-connection success/failure mapping
model discovery mocked
registry fallback works
manual model ID works for OpenAI-compatible
capability validation works
default text model resolution works
unknown/unconfigured provider rejected
```


# 65. Unit test plan — domain

Obavezni testovi:

## Facts

```text
approved fact usable
superseded fact unusable
new version does not mutate old version
soft-deleted fact unusable
```

## Campaign

```text
cannot approve invalid plan
cannot generate posts before approved plan
reorder creates new version
edit approved plan creates new version
```

## Claims

```text
FACT without fact_id unsupported
FACT with unoffered fact unsupported
FACT with superseded fact unsupported
valid FACT verified
CTA non-factual
```

## Content state

```text
DRAFT → APPROVED valid
APPROVED revision → NEEDS_REVIEW
invalid state transition raises
```

## Visual

```text
unsupported primitive rejected
invalid slot font range rejected
invalid bounding box rejected
```

---

# 66. Unit test plan — application

Koristiti fake repositories + mock AI adapter.

Testirati:

```text
LoadBrandFixture
CreateCampaign
GenerateCampaignPlan
ApproveCampaignPlan
GeneratePost
RevisePost
ApprovePost
GenerateVisualSystem
PlanPostLayout
RenderPost use-case with fake renderer
ExportCampaign with fake storage
```

Svaki test mora potvrditi side effects.

Ne samo return value.

---

# 67. Integration test plan — database

Koristiti temp SQLite DB.

Testirati:

```text
migration from empty DB
migration idempotency
brand roundtrip
snapshot roundtrip
fact roundtrip
campaign/plan/items roundtrip
post/claims roundtrip
revision roundtrip
visual roundtrip
telemetry roundtrip
transaction rollback
```

---

# 68. Integration test plan — AI

Mock adapter obavezno.

Za stvarni provider:

- jedan opt-in smoke test;
- ne pokretati automatski u CI;
- označiti markerom:

```text
@pytest.mark.live_ai
```

CI/golden testovi ne smiju trošiti API bez eksplicitnog uključivanja.

---

# 69. Integration test plan — prompts

Provjeriti:

```text
all prompt YAML files load
name/version match path
declared output schema exists
required language fields present
few-shot example supports B/H/S where required
```

---

# 70. Golden test plan

Početni fixture:

```text
Dental Clinic
```

Golden test nije:

```text
caption mora biti identičan string
```

jer LLM output varira.

Golden test provjerava strukturu i metrike:

```text
6 posts
valid roles
no duplicate order
all FACT claims fact-backed
no prohibited phrase if fixture forbids it
layout valid
render file exists
export manifest valid
```

Human eval ostaje odvojeno.

---


# 70A. UI localization testovi

Obavezno:

```text
en.json i bhs.json imaju isti set obaveznih ključeva
missing BHS key pada na EN fallback
unknown key se loguje
parameter interpolation radi
runtime locale switch osvježava UI state
```

Ne testirati Qt/webview detalje u core translator testu.


# 71. EN/BHS i regional-variant testovi

Obavezno imati primjere:

```text
č ć š ž đ
```

Testovi:

- fixture parse;
- `ContentLanguageContext` validation;
- EN prompt serialization;
- BHS/NEUTRAL prompt serialization;
- BHS/BS prompt serialization;
- BHS/SR prompt serialization;
- BHS/HR prompt serialization;
- SQLite roundtrip;
- JSON export;
- caption text;
- renderer;
- ZIP content;
- UI translation resource parity.

Dodati targeted terminološki fixture koji provjerava da regionalna varijanta utiče na preferred terminology, ali ne mijenja fact IDs/provenance.

Ako dijakritik pukne bilo gdje, gate ne prolazi.

---

# 72. Visual/render stress fixture

Napraviti:

```text
short headline
normal headline
max-length headline
headline with čćšžđ
CTA short
CTA max
```

Renderer mora proći sve osim slučaja namjerno dizajniranog za overflow.

Overflow test mora dokazati da validator detektuje problem.

---

# 73. Implementacioni redoslijed za agenta

Agent radi ovim redom **nakon potvrđenog `P0-GATE = PASS`**.

Taskovi označeni `VERIFY ONLY` se ne implementiraju ponovo.

---

## A1 — VERIFY ONLY: Repository foundation

P0 već mora imati kreiran repository, `pyproject.toml`, `src/` layout, tooling i test tree.

Agent sada samo provjerava:

```text
git status
python -c "import ai_campaign_studio"
python -m pytest -q
python -m ruff check .
python -m mypy src
```

Ako foundation nedostaje:

```text
STOP → vratiti se na Implementation Phase 0
```

Ne kreirati repository ponovo.

Acceptance:

- postojeći P0 repository foundation je green;
- nema dupliranih package rootova;
- nema novih paralelnih config/tooling fajlova.

---

## A2 — VERIFY ONLY: Architecture boundaries

P0 već mora imati:

```text
tests/architecture/test_import_boundaries.py
```

Agent:

1. pokreće boundary test;
2. provjerava da novi business moduli koje će dodavati poštuju postojeća pravila;
3. NE pravi drugi architecture checker.

Acceptance:

- P0 boundary suite green prije A3;
- svaka kasnija Faza 1 izmjena zadržava suite green.

---

## A3 — Common + Domain enums/entities

Implementirati:

- IDs;
- timestamps;
- errors;
- brand;
- facts;
- campaign;
- post;
- visual.

Acceptance:

- domain unit testovi green;
- nema infrastructure importa.

---

## A3a — VERIFY ONLY: Channel / Platform / Format foundation

P0 već mora imati:

```text
channels/
ports/channels.py
resources/platforms/
```

i početne definicije za:

```text
Instagram
Facebook
LinkedIn
X
TikTok
YouTube
Pinterest
Threads
Snapchat
```

Agent samo potvrđuje:

```text
registry loads
codes unique
formats valid
Campaign Engine još ne sadrži platform-specific hardcoded business logiku
```

Ako Faza 1 treba dodatni format za stvarni MVP generator:

- dodati novu data-driven format definiciju;
- ne praviti novi registry.

Acceptance:

- postojeći P0 registry ostaje source of truth.

---

## A3b — VERIFY ONLY: Localization foundation

P0 već mora imati:

```text
localization/
resources/i18n/en.json
resources/i18n/bhs.json
resources/regional_language/
```

Agent sada samo potvrđuje:

```text
EN/BHS parity
runtime locale switch
BHS regional variants
UTF-8 / čćšžđ
```

Ako Faza 1 uvodi nove UI stringove:

- dodati iste translation keys u `en.json` i `bhs.json`;
- ne praviti novi localization layer.

Acceptance:

- P0 localization foundation ostaje source of truth.

---

## A4 — Pydantic boundary schemas + mappers

Implementirati fixture, brief i AI output schemas.

Acceptance:

- valid fixtures prolaze;
- invalid enum/order/content_piece_count fail;
- mapperi vraćaju domain tipove.

---

## A5 — Business persistence nad postojećim P0 SQLite foundationom

P0 je već napravio:

```text
database connection
migration runner
schema_migrations
0000_foundation.sql
Unit of Work
```

NE praviti ništa od toga ponovo.

Faza 1 sada dodaje:

```text
resources/migrations/0001_domain_core.sql
resources/migrations/0002_visual.sql
resources/migrations/0003_telemetry.sql
```

i business repository portove/adapters za:

```text
Brand
ApprovedFact
BrandSnapshot
CampaignBrief
Campaign
CampaignPlan
CampaignItem
ContentPiece
ContentClaim
Revision
Visual state
Telemetry
```

Acceptance:

- P0 migration history ostaje validna;
- migracije se nastavljaju od postojećeg broja;
- P0 checksum test i dalje prolazi;
- business round-trip testovi green;
- rollback radi;
- API secrets nisu u business tabelama.

---

## A6 — Fixture load use-case

Implementirati `dental_clinic_v1.json` i `LoadBrandFixture`.

Acceptance:

- brand + facts + snapshot persistovani;
- svaki fact provenance ima `fixture://...`;
- load nije partial ako jedna stavka faila.

---

## A7 — Prompt repository + AI port + mock adapter

Implementirati YAML loader i mock adapter.

Acceptance:

- prompt version load;
- invalid prompt metadata fail;
- mock adapter može simulirati valid/invalid output.

---

## A8 — Live AI adapters + prompt/model execution nad postojećim P0 registryjem

P0 je već napravio:

```text
Provider Registry
Model Registry foundation
provider resource definitions
SecretStore
provider_configs foundation
model_selections foundation
```

NE praviti drugi registry, drugi SecretStore niti novu provider-config bazu.

Faza 1 dodaje:

```text
TextGenerationPort
AIRequest / AIResponse
PromptRepositoryPort
YAML PromptRepository adapter
ConfigureProvider use-case
TestProviderConnection use-case
DiscoverModels use-case
SelectDefaultModel use-case
OpenAI adapter
Anthropic adapter
Google adapter
DeepSeek adapter
OpenRouter adapter
OpenAI-compatible adapter
AI telemetry
```

Acceptance:

- svaki built-in provider koristi postojeći P0 `provider_code`;
- API key ostaje u postojećem `SecretStorePort`;
- Test Connection vraća typed rezultat;
- model discovery ili registry/manual fallback radi;
- default text model se može odabrati;
- promjena modela ne zahtijeva Campaign Engine izmjenu;
- P0 provider/secret tests i dalje prolaze.

---

## A9 — Campaign Brief + Campaign Planning

Implementirati CreateCampaign + GenerateCampaignPlan.

Acceptance:

- plan ima N itema;
- role valid;
- unique order;
- persistovan;
- Campaign status `PLAN_GENERATED`.

---

## A10 — Plan editing/versioning/approval

Implementirati edit/reorder/approve.

Acceptance:

- old plan ostaje;
- new version kreiran;
- samo approved plan dozvoljava post generation.

---

## A11 — Allowed Facts + Social Content Generation

Implementirati fact selection i GeneratePost.

Acceptance:

- svaki post dobija `facts_allowed`;
- AI output validiran;
- claims persistovani.

---

## A12 — Claim validator + linter + revisions

Implementirati deterministic validation.

Acceptance:

- unsupported numeric claim detektovan;
- prohibited phrase detektovan;
- valid FACT verification;
- partial revision ne mijenja druge fieldove.

---

## A13 — Campaign Visual System + LayoutSpec

Implementirati domain/application visual contract.

Acceptance:

- LLM može izabrati samo dozvoljene vrijednosti;
- HERO/SPLIT rade;
- invalid layout rejected.

---

## A14 — Renderer spike + production renderer

Napraviti oba spike kandidata.

Acceptance:

- rezultat spike-a zapisan;
- odabran renderer;
- produkcijski adapter koristi port;
- 1080x1350 render radi;
- B/H/S glyph test green;
- overflow detection radi.

---

## A15 — ZIP export + telemetry summary

Acceptance:

- ZIP struktura validna;
- PNG + caption + post JSON;
- campaign manifest;
- AI summary.

---

## A16 — A/B evaluation harness

Acceptance:

- isti fixture/brief ide u A i B;
- deterministic metrics generisane;
- blind human-eval paket generisan.

---

## A17 — UI framework spike

Napraviti Post Studio u oba kandidata.

Acceptance:

- ista test matrica;
- structured evaluation result;
- pobjednik eksplicitno dokumentovan;
- nema implementacije svih ekrana prije odluke.

---

## A18 — Production Presentation adapter

Implementirati pobjednički framework.

Acceptance:

- 7 minimalnih ekrana;
- nema business logic u views;
- background jobs ne blokiraju UI;
- cancel radi gdje je podržan.

---

## A19 — Full Vertical Slice integration

Pokrenuti:

```text
fixture
→ campaign brief
→ plan
→ manual approval
→ six posts
→ validation
→ render
→ export
```

Acceptance:

- nema ručnog DB editovanja;
- nema hidden CLI bypassa u production pathu;
- export iz approved/persisted state-a.

---

## A20 — Exit evaluation

Pokrenuti više A/B runova.

Rezultat:

```text
PASS → spremno za planiranje Slice 2
FAIL → ostaje se u Campaign Engine iteraciji
```

Ne prelaziti na crawler zato što je "sljedeća faza".

---

# 74. Git/commit pravila za coding agenta

Preporučeni commit boundaries:

```text
feat(core): initialize architecture skeleton
feat(domain): add campaign and fact models
feat(db): add sqlite migrations and repositories
feat(ai): add prompt contracts and provider adapter
feat(campaign): implement campaign planning
feat(posts): implement fact-first generation
feat(validation): add claim validator and linter
feat(visual): add visual system and layout contracts
feat(render): add selected deterministic renderer
feat(export): add campaign zip export
test(eval): add A/B harness
spike(ui): compare PySide6 and pywebview
feat(ui): implement selected presentation adapter
```

Ne praviti jedan commit sa cijelom fazom.

---

# 75. Šta agent ne smije raditi "za svaki slučaj"

Zabranjeno prije stvarne potrebe:

```text
generic plugin framework
event bus framework
microservices
REST API
local web server samo zato što može
Redis
PostgreSQL
Docker runtime dependency
Celery
Kafka
vector DB
GraphQL
Electron
React app prije UI gate-a
multi-agent orchestration
custom dependency injection framework
```

Ako se nešto od ovoga pokaže potrebno, mora postojati konkretan problem i test.

---

# 75A. Handoff rizik — dupliranje P0 foundationa

## R0 — Faza 1 ponovo implementira P0

Signal:

```text
novi translator
novi platform registry
novi migration runner
novi SecretStore
novi JobManager
novi bootstrap
```

iako odgovarajući P0 modul već postoji i `P0-GATE = PASS`.

Akcija:

```text
STOP
```

Prvo provjeriti može li postojeći P0 contract biti proširen.

Dupliranje foundationa je arhitektonska greška, ne validan shortcut.

---

# 76. Anti-patterni koje treba aktivno spriječiti

## R1 — Giant service

Ako fajl prelazi u odgovornosti:

```text
load brand
call AI
save DB
validate claims
render
export
```

refaktorisati po use-case granicama.

## R2 — GUI business logic

Ako view zna:

```text
SQL
OpenAI
fact validation rules
campaign role rules
```

arhitektura je prekršena.

## R3 — AI kao validator svega

Ne koristiti LLM za:

```text
fact existence
fact approval
numeric detection
prohibited phrase detection
state transitions
schema validation
```

## R4 — Mutable history

Ne editovati:

```text
ApprovedFact version
BrandSnapshot
Approved CampaignPlan
```

u mjestu.

## R5 — Renderer u Post Generation use-caseu

Generation i render su odvojeni.

## R6 — UI decision po osjećaju

UI spike mora imati istu test matricu.

## R7 — Provider lock-in

Provider-specific request object ne smije procuriti u application use-case.

---

# 77. Minimalni performance ciljevi za Slice 1

Ovo nisu marketinški SLA.

To su engineering sanity checkovi.

## UI

Background AI/render job ne smije zamrznuti UI.

## Database

Tipične repository operacije trebaju biti praktično instant za mali lokalni projekat.

## Renderer

Cilj:

```text
jedan 1080x1350 render u razumnom lokalnom vremenu
```

Ne optimizovati prije mjerenja.

## Campaign

Logovati total latency.

Ne postavljati hard SLA dok ne vidimo stvarne modele/provider latency.

---


# 77.5. Agentski/GitNexus acceptance

Faza 1 se ne može proglasiti završenom ako:

- relevantni MEDIUM/HIGH taskovi nemaju GitNexus pre-impact evidence;
- reviewer nije dobio `detect-changes` rezultat;
- Task Contracti nisu pisani prije koda;
- implementer i reviewer nisu nezavisni;
- merge-ovi nemaju Human Owner approval;
- GitNexus main index nije osvježen poslije završnih merge-ova.

---

# 77A. P0 prerequisite acceptance

Prije evaluacije bilo kojeg Faza 1 acceptance kriterija mora važiti:

```text
P0-GATE = PASS
```

i ponovljena P0 verification suite mora biti green.

Faza 1 se ne može proglasiti završenom ako je tokom razvoja degradiran foundation koji je P0 prethodno potvrdio.

---

# 78. Acceptance criteria — Faza 1 završena

Faza 1 je završena samo ako su svi ključni kriteriji potvrđeni testom ili stvarnim runom.

## AC1 — Architecture

- import boundaries green;
- nema giant service;
- application nije vezan za UI/provider/SQLite implementation.

## AC2 — Brand

- fixture se učitava;
- facts su immutable/versioned;
- BrandSnapshot postoji.

## AC3 — Campaign

- brief postoji;
- structured plan postoji;
- manual edit/versioning postoji;
- approval gate radi.

## AC4 — Content / Social output

- Campaign Engine koristi `CampaignTarget`;
- ContentPiece se generiše pojedinačno;
- SocialPostPayload radi za prvi MVP target;
- facts_allowed postoji;
- claims mapiraju fact IDs;
- invalid claims se ne predstavljaju kao verified;
- platform rules dolaze iz registryja.

## AC5 — Linter

- prohibited;
- numeric;
- missing fact;
- superseded fact;
- not-offered fact.

## AC6 — Revisions

- partial revision radi;
- history se čuva.

## AC7 — Visual

- CampaignVisualSystem;
- LayoutSpec;
- 2 primitive;
- ContentSlotContract;
- overflow detection.

## AC8 — Render

- 1080x1350 PNG;
- B/H/S glyphs;
- selected renderer documented;
- render errors typed.

## AC9 — Export

- valid ZIP;
- manifest;
- captions;
- PNG;
- post JSON;
- telemetry summary.

## AC10 — AI telemetry

- provider/model;
- prompt version;
- latency;
- retry;
- schema validity;
- tokens kada provider daje podatak.

## AC10b — Localization

- UI podržava `EN` i `BHS`;
- centralni translation keys postoje;
- nema zasebnih BS/SR/HR UI resource setova;
- `ContentLanguageContext` podržava EN i BHS;
- BHS podržava `NEUTRAL/BS/SR/HR`;
- BHS latinica i dijakritici prolaze persistence/render/export;
- regionalna varijanta ne mijenja facts/provenance.


## AC10c — Channels / Platforms

- Brand Intelligence je channel-agnostic;
- CampaignBrief koristi targets;
- registry sadrži početne social platforme;
- dodavanje nove platform definicije ne zahtijeva izmjenu Campaign Engine domain koda.

## AC10d — AI provider/model setup

- korisnik može konfigurisati provider;
- API key ide u SecretStore;
- Test Connection radi;
- model discovery ili registry fallback radi;
- default text model se može odabrati;
- Campaign Engine koristi `TextGenerationPort`;
- OpenAI-compatible custom provider radi sa `base_url + api_key + model_id`.


## AC11 — UI framework

- PySide6 spike završen;
- pywebview spike završen;
- ista matrica;
- framework izabran.

## AC12 — A/B

- Control A postoji;
- System B postoji;
- metrics postoje;
- human eval postoji.

## AC13 — Exit gate

System B pokazuje dovoljno vrijednosti da opravda Slice 2.

Ako ne:

```text
Faza 1 NIJE gotova.
```

---

# 79. Definition of Done za svaki task

Agent ne smije reći "gotovo" samo zato što kod postoji.

Task je gotov kada:

```text
code implemented
+
unit/integration test written
+
tests pass
+
architecture boundary preserved
+
error path tested where relevant
+
no unrelated scope added
```

Ako nije moguće testirati nešto:

```text
NISAM POTVRDIO
```

i tačno navesti šta nedostaje.

---

# 80. Minimalna dokumentacija koju agent mora održavati

Ne praviti dokumentaciju za svaki commit.

Trajno održavati samo:

```text
README.md
```

sa:

- setup;
- run tests;
- run dev harness;
- launch app;
- project paths.

I nakon obaveznih spike-ova:

```text
artifacts/renderer_spike_result.json
artifacts/ui_framework_spike_result.json
```

Ako se donese nova trajna arhitektonska odluka koja mijenja Fazu 0.4, tek tada napraviti kratki ADR.

Ne praviti desetine dnevnih `.md` izvještaja.

---

# 81. Donor granica prema WebshopAudit-u

U Fazi 1 se **ne implementira Website Ingestion**.

Ali arhitektura mora ostaviti mjesto za kasnije donor komponente:

```text
HttpFetcherAdapter
SitemapDiscovery
PageMetadataExtractor
StructuredDataExtractor
SourceEvidence
SourceSnapshotDiffService
```

Ne kopirati ih sada samo da folder postoji.

Jedino što se iz starog projekta može odmah prenijeti kao obrazac je:

```text
background progress/cancellation
deterministic reason mapping
checkpoint thinking
human review state thinking
```

bez Qt zavisnosti.

Slice 2 tek kasnije adaptira konkretan fetch/sitemap/parser kod.

---

# 82. Plan za kasnije priključenje Slicea 2 — bez implementacije sada

Faza 1 treba pripremiti samo jednu stabilnu činjenicu:

Campaign Engine prima:

```text
BrandSnapshot
+
ApprovedFacts
```

Ne smije ga zanimati da li su oni nastali iz:

```text
hand-written fixture
website
PDF
DOCX
XLSX
manual notes
```

Zato Slice 2 kasnije samo zamjenjuje:

```text
Fixture Loader
```

sa:

```text
Brand Ingestion + Human Review
```

Campaign Engine ostaje isti.

Ako Website Ingestion kasnije zahtijeva refaktor Campaign Enginea, granica u Fazi 1 nije dobro napravljena.

---

# 83. Konačna mentalna slika implementacije

```text
                 PRESENTATION
       (EN/BHS, framework selected later)
                      │
                      ▼
                  JOB MANAGER
                      │
                      ▼
                APPLICATION
      ┌───────────────┼────────────────┐
      │               │                │
      ▼               ▼                ▼
 Campaign UseCase  Content UseCase   Render/Export UseCase
      │               │                │
      └───────────────┼────────────────┘
                      ▼
                    DOMAIN
             Brand / Facts / Campaign
              Content / Claims / Visual
                      ▲
                      │
                    PORTS
      ┌───────────────┼─────────────────┐
      ▼               ▼                 ▼
 AI Adapter      SQLite Repos       Renderer Adapter
      │               │                 │
      └───────────────┼─────────────────┘
                      ▼
                INFRASTRUCTURE
```

Slice 1 data flow:

```text
Dental Fixture
     ↓
BrandSnapshot
     ↓
Campaign Brief
     ↓
Campaign Plan
     ↓
Human Approval
     ↓
Allowed Facts
     ↓
Post Generation
     ↓
Claim Validation
     ↓
Linter
     ↓
Post Review
     ↓
Visual System
     ↓
LayoutSpec
     ↓
Renderer
     ↓
ZIP Export
     ↓
A/B Evaluation
```

---

# 84. Završna instrukcija coding agentu

Pretpostavka ovog dokumenta je da je **Implementation Phase 0 već završen sa `P0-GATE = PASS`**.

Tvoj cilj nije da napraviš što više koda.

Tvoj cilj je da dokažeš **najmanju arhitekturu koja pouzdano podržava centralni proizvodni workflow**.

Red prioriteta:

```text
1. correctness
2. architecture boundaries
3. testability
4. reproducible state
5. clear human review
6. visual viability
7. UI fidelity
8. convenience
```

Ako biraš između:

```text
više funkcionalnosti
```

i:

```text
manjeg, testiranog Vertical Slicea
```

izaberi manji Vertical Slice.

Ako implementacija počne zahtijevati crawler, RAG, multi-agent framework ili kompleksan SaaS backend da bi dokazala prvi use case, scope je pobjegao.

**Faza 1 završava dokazom Campaign Enginea, ne količinom napisanog koda.**
