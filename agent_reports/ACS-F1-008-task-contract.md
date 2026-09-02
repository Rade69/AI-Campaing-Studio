---
task_id: ACS-F1-008
phase: Faza-1
title: "A7 — Prompt repository + AI port + mock adapter"
risk: MEDIUM
coordinator: claude
implementer: crush
reviewers: [claude]
status: "OPEN — contract written before code"
created_at: 2026-09-02
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/ports/ai.py
  - src/ai_campaign_studio/ports/prompts.py
  - src/ai_campaign_studio/infrastructure/prompts/__init__.py
  - src/ai_campaign_studio/infrastructure/prompts/yaml_prompt_repository.py
  - src/ai_campaign_studio/infrastructure/ai/__init__.py
  - src/ai_campaign_studio/infrastructure/ai/mock_adapter.py
  - resources/prompts/
  - tests/unit/ports/test_ai.py
  - tests/unit/infrastructure/prompts/
  - tests/unit/infrastructure/ai/
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/ports/repositories.py
  - src/ai_campaign_studio/ports/ai_registry.py
  - src/ai_campaign_studio/ai_registry/
  - src/ai_campaign_studio/infrastructure/database/
  - src/ai_campaign_studio/infrastructure/secrets/
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
  head: b4b324f
  index_status: fresh (analyze re-run 2026-09-02 post ACS-GUI-001 merge)
  targets:
    - symbol: "new ports/ai.py, ports/prompts.py, infrastructure/prompts/, infrastructure/ai/"
      upstream_risk: NONE
      upstream_count: 0
      downstream_notes: "All brand-new files/directories, zero existing importers. Distinct from the already-existing ports/ai_registry.py (P0 provider/model registry) -- no overlap, no modification of that file."
      affected_processes: []
  scope_fit: PASS
  unknowns: []
---

# Kontekst

Task **A7 — Prompt repository + AI port + mock adapter** (plan sekcije 17
"AI port", 18 "Prompt repository", 19 "Prompt pravila za EN/BHS", 20
"AI adapter implementacija" — samo `mock_adapter.py` dio, ne live
provider adapteri). Nezavisno od **ACS-F1-007** (Pi, A6) — različiti
vertikalni tok (prompts/AI infrastruktura, ne brand fixture loading).

**Šta ovo NIJE**: ovo nije provider/model registry (taj već postoji,
P0-gotov, `ports/ai_registry.py`/`ai_registry/` — NE DIRATI). Ovo nije
live provider konekcija (OpenAI/Anthropic/itd. adapteri su A8, kasnije).
Ovo nije puna telemetry infrastruktura (`ports/telemetry.py`,
`AICallTelemetry`/`PipelineTelemetry`, `TelemetryRepositoryPort` — sve
to je van scope-a ovog taska, Performance/Analytics deferral kao i kod
ACS-F1-005-ovog `TelemetryRepositoryPort`). `AITelemetry` u ovom tasku
je SAMO lagan value object unutar `AIResponse` (latency/tokens/retry
info koje sam response nosi), ne perzistovan event.

**Bez mock adaptera application testovi (buduće campaign plan/post
generation use-caseovi) bi bili zavisni od mreže** — ovo je razlog zašto
je mock prvi adapter koji se implementira, prije bilo kojeg live
providera.

**Risk**: MEDIUM — nova, izolovana infrastruktura bez postojećih
importera, ne dira SecretStore/registry/bootstrap. §29 politika:
Claude-only review, PASS -> odmah commit/push/merge.

Prije koda pročitati:

```text
AGENTS.md
CLAUDE.md
docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md
.agent/CURRENT_STATE.md
AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md
  sekcija 17 (AI port), 17A (samo da vidiš razliku prema ai_registry —
  ne diraš taj fajl), 18 (Prompt repository — svih 5 obaveznih
  promptova), 19 (Prompt pravila za EN/BHS), 20 (samo mock_adapter.py
  dio + Retry policy pravila)
```

Pročitati postojeći srodan kod radi konzistentnosti stila (ne kopirati
slijepo):

```text
src/ai_campaign_studio/ports/ai_registry.py (Protocol stil primjer)
src/ai_campaign_studio/ports/repositories.py (Protocol stil primjer, ACS-F1-005)
src/ai_campaign_studio/domain/common/errors.py (postojeća AppError hijerarhija
  — ako trebaju nove error klase za AI_SCHEMA_ERROR, pratiti taj obrazac)
```

# Objective

1. `ports/ai.py` — `AIMessage`, `AIRequest`, `AIResponse`, `AITelemetry`
   (framework-neutral modeli) + `TextGenerationPort.generate()` Protocol.
2. `ports/prompts.py` — `PromptRepositoryPort.get(name, version)`.
3. `infrastructure/prompts/yaml_prompt_repository.py` — YAML loader,
   implementira `PromptRepositoryPort`.
4. `resources/prompts/<name>/v1.yaml` — svih 5 obaveznih promptova.
5. `infrastructure/ai/mock_adapter.py` — implementira
   `TextGenerationPort`, deterministic/error/invalid-schema/rate-limit/
   telemetry simulation.

# Implementation steps

## `ports/ai.py`

Tačno iz plana sekcija 17:

```text
AIRequest: purpose, prompt_name, prompt_version, system_text, user_text,
           json_schema, temperature?, max_output_tokens?, metadata
AIResponse: raw_text?, structured_payload?, provider, model,
            input_tokens?, output_tokens?, latency_ms, finish_reason?,
            request_id?
AIMessage: implementer projektuje razumno (role + content je standardni
           oblik za chat-style poruke — dokumentovati izbor)
AITelemetry: lagan snapshot (latency_ms, input_tokens?, output_tokens?,
             retry_count) — NE `ports/telemetry.py`-jev
             AICallTelemetry (to je drugi, kasniji koncept)
TextGenerationPort.generate(request: AIRequest) -> AIResponse
```

Plain dataclasses ili `@runtime_checkable Protocol` gdje odgovara (isti
obrazac kao `ports/repositories.py`) — ovo je port sloj, framework-
neutral, bez sqlite/http/provider SDK importa.

## `ports/prompts.py`

```text
PromptRepositoryPort.get(name: str, version: str) -> PromptDefinition
```

`PromptDefinition` (ili slično imenovan tip) nosi sva polja iz YAML
metadata (vidi ispod) — definisati ga u ovom fajlu ili u `ports/ai.py`
(implementer bira, dokumentuje).

## YAML prompt metadata — svaki prompt fajl

```yaml
name: ...
version: ...
purpose: ...
input_contract: ...
output_contract: ...
language_support: ...
instructions: ...
examples: ...
```

"Prompt fajl nije samo tekst" — svih 7 polja moraju biti prisutna i
validirana pri učitavanju (nevalidan/nepotpun prompt metadata mora
FAILOVATI pri load-u, ne tiho proći sa `None` poljima).

## Svih 5 obaveznih promptova (`resources/prompts/<name>/v1.yaml`)

```text
campaign_plan/v1.yaml       — input: BrandSnapshot summary, CampaignBrief,
                               CampaignRole definitions, campaign template
                               candidate, fact categories available.
                               output: CampaignPlanOutputSchema (referenca
                               na postojeći application/schemas/campaign_plan_output.py)
post_generation/v1.yaml     — input: CampaignItem, BrandSnapshot,
                               AllowedFacts, language context,
                               ContentSlotContract, platform, role rules.
                               output: SocialPostGenerationOutputSchema
revision/v1.yaml            — input: current post, explicit revision
                               command, immutable fields, allowed facts.
visual_direction/v1.yaml    — output: samo schema-valid layout/design
                               intent (referenca na
                               visual_direction_output.py)
ab_control/v1.yaml          — generički prompt, isti fixture+brief, N
                               postova. NE davati CampaignRoles pipeline
                               informacije (ovo je namjerno — Kontrola A
                               ne smije "vidjeti" role sekvencu, to bi
                               kvarilo A/B poređenje).
```

Ovo su YAML **definicije/metadata** (`instructions` polje sadrži stvaran
prompt tekst) — ne implementira se stvarni LLM poziv u ovom tasku (to
radi mock/live adapter kroz `TextGenerationPort`).

## Prompt EN/BHS pravila (sekcija 19)

Svaki generation prompt (instructions/metadata) mora eksplicitno
predvidjeti da dobija: `language_family`, `regional_variant`, `locale`,
`script`, `preferred_terms`, `forbidden_terms`, `regional_vocabulary`,
`tone_examples` — ovo je već postojeći `ContentLanguageContext` oblik
(ACS-F1-003 ga već koristi) — referencirati ga u `input_contract`
polju prompt metadata, ne izmišljati paralelnu strukturu.

## `infrastructure/ai/mock_adapter.py`

Implementira `TextGenerationPort`. Mora omogućiti (konstruktor
parametri ili named factory metode — implementer bira):

- **deterministic fixtures** — isti `AIRequest` uvijek vraća isti
  `AIResponse` (za reproducibilne testove).
- **error simulation** — mod koji baca exception (network-like error).
- **invalid-schema simulation** — mod koji vraća `structured_payload`
  koji NE prolazi odgovarajuću Pydantic schema validaciju (za testiranje
  retry policy u budućim use-caseovima).
- **rate-limit simulation** — mod koji simulira rate-limit grešku.
- **telemetry simulation** — vraćen `AIResponse` uvijek nosi popunjen
  `latency_ms`/`input_tokens`/`output_tokens` (makar simulirane
  vrijednosti), tako da pozivalac može testirati telemetry-zavisan kod
  bez prave mreže.

Nema business logike, nema CampaignRole logike, nema claim validation,
nema persistence — samo transformiše `AIRequest` u simulisan
`AIResponse` (pravilo iz sekcije 20).

# Acceptance

- [ ] `ports/ai.py` i `ports/prompts.py` su framework-neutral (nema
      `yaml`/http/provider SDK importa — ti idu u infrastructure sloj).
- [ ] `yaml_prompt_repository.py` implementira `PromptRepositoryPort`,
      učitava sve 5 prompt fajlova.
- [ ] Nevalidan/nepotpun prompt YAML (fali npr. `output_contract`) baca
      grešku pri `get()`, ne prolazi tiho (test dokazuje).
- [ ] `get(name, version)` za nepostojeću verziju vraća jasnu grešku, ne
      `None`/silent fallback na drugu verziju.
- [ ] Mock adapter: svih 5 simulacionih modova (deterministic/error/
      invalid-schema/rate-limit/telemetry) su testirani pojedinačno.
- [ ] Mock adapter ne uvozi nikakav provider SDK, ne pravi mrežne pozive
      (potvrđeno kroz `tests/architecture/test_import_boundaries.py` —
      provjeriti da li taj test već pokriva `infrastructure/ai/`, ako ne
      proširiti ga isto kao što je ACS-GUI-001 proširio za
      `presentation_webview`).
- [ ] `ab_control/v1.yaml` eksplicitno NE sadrži CampaignRole pipeline
      informacije (provjeriti sadržaj ručno — ovo je namjerna dizajn
      granica, ne slučajni propust).
- [ ] Nema izmjena `ports/ai_registry.py`, `ai_registry/` (P0 teritorija,
      različit koncept).
- [ ] `python -m pytest -q`, `ruff check .`, `mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest -q
python -m pytest tests/architecture/test_import_boundaries.py -v
python -m pytest tests/unit/infrastructure/prompts tests/unit/infrastructure/ai tests/unit/ports -v
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- `ports/ai.py`/`ports/prompts.py` stvarno framework-neutral;
- svih 5 prompt YAML fajlova imaju sva 7 obaveznih metadata polja;
- mock adapter genuinely simulira sve navedene modove (test po mod, ne
  jedan generički test koji tvrdi da "mock radi");
- `ab_control` prompt namjerno ne curi CampaignRole informacije;
- nema konceptualnog miješanja sa `ports/ai_registry.py` (provider/model
  registry ostaje netaknut, različit koncept od `TextGenerationPort`);
- `AITelemetry` ostaje lagan response-embedded snapshot, ne puna
  telemetry persistence infrastruktura (scope discipline).

# Rollback

MEDIUM risk — nova, izolovana infrastruktura bez postojećih importera.
Fix na istoj branch bez proširenja scope-a. STOP i vrati na puni ciklus
samo ako se pokaže potreba da task dira SecretStore/registry/bootstrap.

# Coordination

Nezavisno od **ACS-F1-007** (Pi, A6) — potpuno disjoint `allowed_paths`,
nema zavisnosti, oba mogu ići paralelno odmah. Nezavisno i od
**ACS-GUI-002** (MiniMax).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-008-prompt-ai-mock
Branch:   task/ACS-F1-008-prompt-ai-mock
Base:     main @ b4b324f
```
