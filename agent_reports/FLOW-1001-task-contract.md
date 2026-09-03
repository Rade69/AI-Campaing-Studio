---
task_id: FLOW-1001
title: "Content revisions (ReviseContentPiece)"
phase: Faza-1
risk: MEDIUM
coordinator: claude
implementer: TBD (Human Owner assigns)
reviewers: [claude]
status: "OPEN — contract written before code"
created_at: 2026-09-03
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/domain/content/revisions.py
  - src/ai_campaign_studio/application/posts/revise_content_piece.py
  - tests/unit/application/posts/test_revise_content_piece.py
  - tests/integration/application/posts/test_revise_content_piece_integration.py
  - tests/unit/domain/content/test_revisions.py
forbidden_paths:
  - src/ai_campaign_studio/domain/content/entities.py
  - src/ai_campaign_studio/domain/content/enums.py
  - src/ai_campaign_studio/domain/content/claims.py
  - src/ai_campaign_studio/application/posts/select_allowed_facts.py
  - src/ai_campaign_studio/application/posts/claim_validator.py
  - src/ai_campaign_studio/application/posts/claim_linter.py
  - src/ai_campaign_studio/application/posts/derive_content_status.py
  - src/ai_campaign_studio/application/posts/generate_social_post.py
  - src/ai_campaign_studio/application/campaigns/
  - src/ai_campaign_studio/application/schemas/
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
  head: 5118970
  index_status: fresh (analyze re-run 2026-09-03 post FLOW-1000 merge)
  targets:
    - symbol: "RevisionOrigin (domain/content/revisions.py) — adding sibling RevisionType enum"
      upstream_risk: LOW
      upstream_count: 11 (2 direct, 9 transitive)
      downstream_notes: "gitnexus impact (upstream, includeTests=true) lists sqlite_revision_repository.py and ports/repositories.py as direct importers, plus every application/campaigns and application/posts file transitively (they all import the repositories module for OTHER ports). This is file-level import-graph noise: none of them reference RevisionOrigin or the new RevisionType, and adding a new, unrelated sibling enum to the same file changes nothing they use. Real blast radius: this task's own new file."
      affected_processes: []
  scope_fit: PASS
  unknowns: []
---

# Kontekst

Task **A12 (dio 2 — poslednji preostali dio) — Content revisions** (plan sekcija 38). Poslednji
komad A12 grupe (dio 1 = ACS-F1-012, claim linter + status derivation, mergovano). Prvi task koji
koristi `RevisionRepositoryPort`/`SqliteRevisionRepository` (postoje od ACS-F1-006, nikad
korišteni u praksi do sad).

**Šta VEĆ postoji i ne treba graditi**:

```text
application/schemas/revision_output.py (ACS-F1-004) — RevisionOutput Pydantic schema,
  partial-update semantika VEĆ implementirana preko changed_fields (model_fields_set)
resources/prompts/revision/v1.yaml (ACS-F1-008) — prompt već postoji
ports/repositories.py — RevisionRepositoryPort (save_revision/get_revision/list_entity_revisions)
infrastructure/.../sqlite_revision_repository.py — SQLite adapter, potpuno gotov
domain/content/entities.py — ContentPiece.revision_ids polje već postoji
```

**Šta NEDOSTAJE i OVAJ task pravi**: `RevisionType` enum (10 revision tipova iz plan sekcije 38)
nema domain home — dodati ga u `domain/content/revisions.py` (isti fajl kao postojeći
`RevisionOrigin`, prirodno mjesto). Ovo je JEDINA aditivna domain izmjena — nova, potpuno
nezavisna enum klasa, ništa postojeće (`RevisionOrigin`, `Revision`) se ne mijenja. GitNexus
impact potvrđuje LOW rizik uprkos tome što je fajl u `domain/` (nije na HIGH listi — samo
migracije/SecretStore/registry contracts su HIGH, ne svaka domain izmjena).

**Partial revision contract (plan sekcija 38, KRITIČNO pravilo)**: svaki `RevisionType` smije
promijeniti SAMO određen podskup `SocialPostPayload` polja. Primjer iz plana: `NEW_HEADLINE`
smije promijeniti samo `headline` (+ claims direktno vezane za headline, ako ih model vrati
odvojeno — VIDI "Namjerno van scope-a" ispod, ovaj task NE implementira claim-level reviziju).
`RevisionOutput.changed_fields` (već postoji, koristi Pydantic `model_fields_set`) daje TAČNO koja
polja je AI stvarno vratio — use-case MORA provjeriti da je `changed_fields` PODSKUP dozvoljenih
polja za dati `revision_type`, inače `InvariantViolation` (fail loud, NE tiho ignorisati/
djelimično primijeniti).

**Dozvoljena polja po revision_type-u** (implementer primjenjuje TAČNO ovu mapu, ne izmišlja
alternativu — plan eksplicitno specificira samo `NEW_HEADLINE` primjer, ostatak je razuman,
dokumentovan zaključak koordinatora za preostalih 9 tipova):

```python
_ALLOWED_FIELDS: dict[RevisionType, frozenset[str]] = {
    RevisionType.NEW_HEADLINE: frozenset({"headline"}),
    RevisionType.NEW_CTA: frozenset({"cta"}),
    RevisionType.STRONGER_HOOK: frozenset({"hook"}),
    RevisionType.SHORTER: frozenset({"headline", "caption", "hook", "body"}),
    RevisionType.LONGER: frozenset({"headline", "caption", "hook", "body"}),
    RevisionType.MORE_PROFESSIONAL: frozenset({"headline", "caption", "hook", "body"}),
    RevisionType.MORE_FRIENDLY: frozenset({"headline", "caption", "hook", "body"}),
    RevisionType.LESS_PROMOTIONAL: frozenset(
        {"headline", "caption", "hook", "body", "cta"}
    ),
    RevisionType.CUSTOM: frozenset(
        {"headline", "caption", "hook", "body", "cta", "hashtags"}
    ),
    # NEW_VISUAL_DIRECTION namjerno IZOSTAVLJENO iz mape — vidi "Namjerno van scope-a".
}
```

`hashtags` je van dozvoljenih polja za SVE tipove osim `CUSTOM` — plan ne daje eksplicitan primjer
za hashtag reviziju, a `CUSTOM` je jedini tip gdje je "bilo šta" legitimno po definiciji.

**Namjerno van scope-a (ne graditi, ne izmišljati zaobilazno rješenje)**:

- `RevisionType.NEW_VISUAL_DIRECTION` — `RevisionOutput` schema (ACS-F1-004, već postoji) NEMA
  `visual_direction` polje uopšte (samo headline/caption/hook/body/cta/hashtags). Vizuelni sistem
  (`CampaignVisualSystem`, plan sekcije 39-41) ne postoji još kao implementiran pipeline (A13+).
  `ReviseContentPiece` MORA i dalje prihvatiti `RevisionType.NEW_VISUAL_DIRECTION` kao validnu
  enum vrijednost (kompletnost liste iz plana), ali `execute()` odmah baca jasnu grešku
  (`InvariantViolation`, poruka objašnjava da čeka na Visual System pipeline) AKO se taj tip
  pozove — NE tiho no-op, NE pokušaj da zaobiđe nedostajuće schema polje.
- Claim-level revizija ("claims koji direktno pripadaju headline-u ako ih model vraća odvojeno")
  — `RevisionOutput` nema `claims` polje uopšte. Ovaj task NE regeneriše/mijenja
  `ContentPiece.claims` — samo ih PONOVO validira/lintuje NEPROMIJENJENE (plan eksplicitno traži
  "fact validation" i "linter" ponovo poslije revizije, čak i ako se claims sami ne mijenjaju).
- Nova repository metoda — sve što treba (`get_content_piece`, `save_content_piece`,
  `save_revision`, `list_entity_revisions`) već postoji.

**Risk**: MEDIUM — nova, izolovana orchestration logika + jedna aditivna domain enum klasa sa
potvrđenim LOW upstream impact-om. §29: Claude-only review, PASS → odmah merge.

Prije koda pročitati:

```text
AGENTS.md
CLAUDE.md
docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md
.agent/CURRENT_STATE.md
AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md
  sekcija 38 "Content revisions" (uključujući "Partial revision contract")
```

Pročitati postojeći kod (ne pogađati potpise):

```text
src/ai_campaign_studio/domain/content/revisions.py (RevisionOrigin, Revision — STIL primjer)
src/ai_campaign_studio/domain/content/entities.py (ContentPiece — PROČITATI docstring, već
  eksplicitno kaže: "an APPROVED ContentPiece must never be changed silently. Revising approved
  content must create a new Revision record and return the status to NEEDS_REVIEW.")
src/ai_campaign_studio/application/schemas/revision_output.py (RevisionOutput.changed_fields)
src/ai_campaign_studio/application/posts/generate_social_post.py (STIL primjer za AIRequest
  building, atomic persist pattern — NE diraj ovaj fajl)
src/ai_campaign_studio/application/posts/claim_validator.py (validate_claim — reuse, ne duplirati)
src/ai_campaign_studio/application/posts/claim_linter.py (lint_claim, load_claim_rules — reuse)
src/ai_campaign_studio/application/posts/derive_content_status.py (derive_content_status — reuse)
src/ai_campaign_studio/ports/repositories.py (RevisionRepositoryPort, ContentRepositoryPort —
  metode već postoje, NE dodavati nove)
src/ai_campaign_studio/infrastructure/database/repositories/sqlite_revision_repository.py
resources/prompts/revision/v1.yaml
```

# Objective

1. `domain/content/revisions.py` — dodati `RevisionType` StrEnum (svih 10 tipova iz plana).
2. `application/posts/revise_content_piece.py` — `ReviseContentPiece` use-case.

# Implementation steps

## `RevisionType` (domain/content/revisions.py)

```python
class RevisionType(StrEnum):
    SHORTER = "SHORTER"
    LONGER = "LONGER"
    STRONGER_HOOK = "STRONGER_HOOK"
    MORE_PROFESSIONAL = "MORE_PROFESSIONAL"
    MORE_FRIENDLY = "MORE_FRIENDLY"
    LESS_PROMOTIONAL = "LESS_PROMOTIONAL"
    NEW_CTA = "NEW_CTA"
    NEW_HEADLINE = "NEW_HEADLINE"
    NEW_VISUAL_DIRECTION = "NEW_VISUAL_DIRECTION"
    CUSTOM = "CUSTOM"
```

Dodati ISPOD postojećeg `RevisionOrigin` — ne dirati `RevisionOrigin`/`Revision` definicije.

## `ReviseContentPiece`

```python
class ReviseContentPiece:
    def __init__(
        self, content_repo: ContentRepositoryPort, fact_repo: FactRepositoryPort,
        prompt_repo: PromptRepositoryPort, ai_port: TextGenerationPort,
        unit_of_work: _UnitOfWork,
    ) -> None: ...
    def execute(
        self, content_piece_id: PostId, revision_type: RevisionType, instruction: str,
    ) -> ContentPiece: ...
```

Tok:

1. `piece = content_repo.get_content_piece(content_piece_id)` — `None` → `EntityNotFound`.
2. `piece.payload is None` → `InvariantViolation` (ništa za revidirati — post nikad nije
   generisan).
3. `revision_type is RevisionType.NEW_VISUAL_DIRECTION` → `InvariantViolation` odmah (vidi "Van
   scope-a" gore — jasna poruka, ne pokušaj obrade).
4. `allowed_fields = _ALLOWED_FIELDS[revision_type]` (mapa iz Kontekst sekcije).
5. Za svaki `fact_id` u `piece.facts_allowed`, `fact_repo.get_fact(fact_id)` da dobiješ tekst
   fact-ova za prompt kontekst (isti razlog kao u `GenerateSocialPost` — model mora vidjeti
   stvaran tekst, ne samo ID).
6. `prompt = prompt_repo.get("revision", "1")`.
7. Konstruisati `AIRequest`: `system_text=prompt.instructions`, `user_text` sadrži trenutni post
   (svih 6 `SocialPostPayload` polja), `revision_type.value`, `instruction`, EKSPLICITNU listu
   "immutable fields" (sva `SocialPostPayload` polja MINUS `allowed_fields` — model treba znati
   šta NE smije dirati), tekst dozvoljenih fact-ova, `json_schema =
   RevisionOutput.model_json_schema()`.
8. `response = ai_port.generate(request)` — `structured_payload is None` →
   `InvariantViolation`.
9. `output = RevisionOutput.model_validate(response.structured_payload)` (Pydantic greška
   propagira PRIJE bilo kakve perzistencije).
10. **Partial contract provjera**: ako `output.changed_fields - allowed_fields` nije prazan skup
    → `InvariantViolation` (model je dirao polje van dozvoljenog opsega za ovaj `revision_type` —
    fail loud, ne primijeni djelimično).
11. Konstruisati `new_payload = dataclasses.replace(piece.payload, **{f: getattr(output, f) for f
    in output.changed_fields})` (samo eksplicitno vraćena polja se mijenjaju, ostatak ostaje
    identičan starom payload-u).
12. Ponovo validirati/lintovati POSTOJEĆE (nepromijenjene) claims:
    `relinted_claims = tuple(lint_claim(c, rules) for c in piece.claims)` (claims se NE
    regenerišu, samo ponovo prolaze linter — plan eksplicitno traži "fact validation, linter"
    ponovo poslije revizije).
13. `natural_status = derive_content_status(relinted_claims)`.
14. **APPROVED-invarijanta** (iz `ContentPiece` docstring-a, doslovno): ako je
    `piece.status is ContentStatus.APPROVED`, finalni status je UVIJEK
    `ContentStatus.NEEDS_REVIEW`, bez obzira šta `natural_status` kaže (revidiran sadržaj MORA
    ponovo biti pregledan od čovjeka). Inače, finalni status je `natural_status`.
15. Odrediti sljedeći `version` broj: `len(revision_repo... )` — **PAŽNJA: use-case NEMA
    `RevisionRepositoryPort` injektovan po trenutnom potpisu iznad — implementer MORA dodati
    `revision_repo: RevisionRepositoryPort` kao šesti konstruktorski parametar** (potpis iznad je
    orijentacija, ne finalan — GitNexus impact provjera za `RevisionRepositoryPort` je već
    urađena, LOW rizik). `next_version = len(revision_repo.list_entity_revisions("ContentPiece",
    str(content_piece_id))) + 1`.
16. Konstruisati `Revision` (`id=RevisionId(new_id())`, `entity_type="ContentPiece"`,
    `entity_id=str(content_piece_id)`, `version=next_version`, `timestamp=utc_now()`,
    `origin=RevisionOrigin.AI`, `previous_value=json.dumps(dataclasses.asdict(piece.payload))`,
    `new_value=json.dumps(dataclasses.asdict(new_payload))`, `provider=response.provider`,
    `model=response.model`, `prompt_version="1"`,
    `instruction=f"[{revision_type.value}] {instruction}"`).
17. Konstruisati `updated_piece = dataclasses.replace(piece, payload=new_payload,
    claims=relinted_claims, status=final_status, revision_ids=(*piece.revision_ids,
    revision.id), updated_at=utc_now())`.
18. Perzistirati `revision_repo.save_revision(revision)` +
    `content_repo.save_content_piece(updated_piece)` unutar JEDNE `SqliteUnitOfWork` transakcije.
19. Vratiti `updated_piece`.

# Acceptance

- [ ] `RevisionType` ima svih 10 vrijednosti iz plan sekcije 38.
- [ ] `NEW_HEADLINE` revizija mijenja SAMO `headline`, ostatak payload-a identičan (test).
- [ ] Model koji vrati polje van dozvoljenog opsega (npr. `NEW_HEADLINE` revizija koja i
      pokuša promijeniti `caption`) → `InvariantViolation` PRIJE perzistencije (repository
      netaknut — test dokazuje).
- [ ] `NEW_VISUAL_DIRECTION` → `InvariantViolation` odmah, bez AI poziva (fake AI port
      `call_count`/`calls` ostaje 0 — test).
- [ ] Revizija posta bez `payload` (nikad generisan) → `InvariantViolation`.
- [ ] Revizija `APPROVED` posta → finalni status UVIJEK `NEEDS_REVIEW`, čak i ako revidiran
      sadržaj prođe linter bez upozorenja (test — ovo je direktna provjera `ContentPiece`
      docstring invarijante).
- [ ] Revizija ne-`APPROVED` posta (npr. `DRAFT`) → finalni status prati `derive_content_status`
      normalno (test).
- [ ] Claims se NE mijenjaju sadržajno (isti `text`/`fact_ids`), samo se ponovo lintuju (test —
      npr. dokazati da `claim.id` ostaje isti, samo `status`/`reason_codes` mogu biti
      ažurirani ako linter pravila drugačije rezultuju).
- [ ] `Revision` zapis persistovan sa ispravnim `version` (1 za prvu reviziju, 2 za drugu itd. —
      test sa dvije uzastopne revizije istog posta).
- [ ] `ContentPiece.revision_ids` raste za tačno jedan element po reviziji (test).
- [ ] Atomicity: mid-persist failure (npr. `save_content_piece` failuje nakon uspješnog
      `save_revision`) → NIŠTA nije trajno promijenjeno (stari `ContentPiece` ostaje u bazi
      nepromijenjen — test na pravoj SQLite bazi).
- [ ] Nevalidan AI output (fali obavezno... — provjeri da li `RevisionOutput` uopšte ima
      required polja; ako su sva opciona, koristi drugi failure mode, npr. malformed JSON ili
      pogrešan tip) → jasna greška prije perzistencije.
- [ ] Use-case zavisi samo od portova (`ContentRepositoryPort`, `FactRepositoryPort`,
      `RevisionRepositoryPort`, `PromptRepositoryPort`, `TextGenerationPort`) + lokalnog
      `_UnitOfWork` Protocol-a.
- [ ] Integration test na pravoj SQLite bazi, po mogućnosti lanči
      LoadBrandFixture → CreateCampaign → GenerateCampaignPlan → ApproveCampaignPlan →
      GenerateSocialPost → ReviseContentPiece (pun end-to-end lanac, isti obrazac kao prethodni
      taskovi) ako je to razumno bez prevelikog test setup-a; ako implementer procijeni da je
      setup pretežak, minimalno koristiti pravu SQLite bazu sa ručno ubačenim `ContentPiece`
      (isti nivo kao dosadašnji "minimalni" integration testovi).
- [ ] `python -m pytest -q`, `ruff check .`, `mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest -q
python -m pytest tests/architecture/test_import_boundaries.py -v
python -m pytest tests/unit/application/posts/test_revise_content_piece.py tests/integration/application/posts/test_revise_content_piece_integration.py tests/unit/domain/content/test_revisions.py -v
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- `RevisionType` diff je STRIKTNO aditivan u `domain/content/revisions.py` — `RevisionOrigin`/
  `Revision` netaknuti (diff dokaz);
- partial-field contract STVARNO primijenjen (`changed_fields` provjera protiv dozvoljene mape,
  ne samo tvrđena u docstring-u) — testirati BAREM jedan slučaj gdje model "pokuša" prekoračiti
  granicu;
- `APPROVED → uvijek NEEDS_REVIEW` invarijanta iz `ContentPiece` docstring-a stvarno primijenjena,
  ne zaobiđena;
- claims se NE regenerišu, samo ponovo lintuju (provjeri da `claim.text`/`claim.fact_ids` ostaju
  identični prije/poslije);
- `NEW_VISUAL_DIRECTION` eksplicitno odbijen bez AI poziva;
- atomicity stvarno testirana na pravoj SQLite bazi;
- reuse `validate_claim`/`lint_claim`/`derive_content_status` (ACS-F1-011/012) — bez duplirane
  logike;
- scope discipline — `generate_social_post.py`/`claim_validator.py`/`claim_linter.py`/
  `derive_content_status.py`/`select_allowed_facts.py` netaknuti (samo importovani, ne mijenjani).

# Rollback

MEDIUM risk — izolovana orchestration logika + jedna potvrđeno-LOW-impact aditivna domain enum
klasa. Fix na istoj branch bez proširenja scope-a. STOP i vrati na puni ciklus samo ako se pokaže
potreba da `RevisionOutput` schema (ACS-F1-004 teritorija) treba izmjenu (npr. da podrži
`NEW_VISUAL_DIRECTION`) — to je van ovog kontrakta.

# Coordination

Nezavisan od svega trenutno otvorenog (nema drugih OPEN taskova). Zadnji preostali komad A12
grupe iz plana — poslije ovog, A12 (Claim validator + linter + revisions) je u potpunosti
implementiran.

```text
Worktree: ../ai-campaign-studio-worktrees/FLOW-1001-content-revisions
Branch:   task/FLOW-1001-content-revisions
Base:     main @ 5118970
```
