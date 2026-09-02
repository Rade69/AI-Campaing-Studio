---
task_id: ACS-F1-010
phase: Faza-1
title: "SocialPostPayload persistence (ContentPiece.payload + migration)"
risk: HIGH
coordinator: claude
implementer: claude (Human Owner decision, 2026-09-02)
reviewers: [codex]  # Claude is implementer here -> cannot also be reviewer
  # (CLAUDE.md: "Implementer != reviewer"). Codex review + explicit Human
  # Owner merge approval are both still mandatory per HIGH-risk policy --
  # this task does NOT get a streamlined self-reviewed merge.
status: "OPEN — contract written before code"
created_at: 2026-09-02
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/domain/content/entities.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_content_repository.py
  - resources/migrations/0003_content_payload.sql
  - tests/integration/database/repositories/test_sqlite_content_repository.py
  - tests/integration/database/test_migrations.py
forbidden_paths:
  - src/ai_campaign_studio/domain/content/enums.py
  - src/ai_campaign_studio/domain/content/claims.py
  - src/ai_campaign_studio/domain/content/revisions.py
  - src/ai_campaign_studio/domain/campaign/
  - src/ai_campaign_studio/domain/brand/
  - src/ai_campaign_studio/domain/facts/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/infrastructure/database/connection.py
  - src/ai_campaign_studio/infrastructure/database/migrations.py
  - src/ai_campaign_studio/infrastructure/database/unit_of_work.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_brand_repository.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_fact_repository.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_campaign_repository.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_visual_repository.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_revision_repository.py
  - resources/migrations/0000_foundation.sql
  - resources/migrations/0001_brand_facts.sql
  - resources/migrations/0002_campaign_content_visual.sql
  - src/ai_campaign_studio/presentation/
  - src/ai_campaign_studio/presentation_webview/
  - src/ai_campaign_studio/bootstrap.py
  - src/ai_campaign_studio/main.py
gitnexus_required: true
adversarial_required: true
gitnexus:
  required: true
  repository: "H:\\AI Campaing Studio"
  worktree: main (pre-branch pre-impact)
  branch: main
  head: 5603030
  index_status: fresh (analyze re-run 2026-09-02 post ACS-F1-009 merge)
  targets:
    - symbol: "ContentPiece (domain/content/entities.py) — ADDITIVE field payload"
      upstream_risk: MEDIUM (tool heuristic, see downstream_notes for why actual risk is low)
      upstream_count: 9 (5 direct file-level importers, 4 transitive)
      downstream_notes: "gitnexus impact (upstream, includeTests=true) lists ports/repositories.py, domain/campaign/entities.py, application/mappers/campaign_brief_mapper.py, both sqlite_*_repository.py files as depth-1 importers, plus application/campaigns/*.py and infrastructure/database/repositories/__init__.py at depth 2. This is FILE-LEVEL import-graph noise, not semantic: none of those files construct a ContentPiece positionally today (only infrastructure/database/repositories/sqlite_content_repository.py does, and it is IN allowed_paths). Every ContentPiece construction in the codebase uses keyword arguments (confirmed by reading every existing call site) — a new OPTIONAL trailing field with default=None is backward compatible for all of them. Real blast radius: 1 file (sqlite_content_repository.py, in allowed_paths)."
      affected_processes: []
  scope_fit: PASS
  unknowns: []
---

# Kontekst

**Zašto ovaj task postoji, zašto je odvojen od A11, zašto je HIGH:** Pri pisanju
kontrakta za A11 ("Allowed Facts + Social Content Generation", plan sekcija
34 "Social Content generation pipeline") otkriven je pravi arhitektonski
gap, već DOKUMENTOVAN kao svjestan scope-granica u ACS-F1-006 review
zapisu (`.agent/CURRENT_STATE.md`, ACS-F1-006 red): **`ContentPiece` domain
entitet nema polje za sam generisani sadržaj posta**
(`SocialPostPayload` — headline/caption/hook/body/cta/hashtags/
visual_direction, već postoji kao domain dataclass u
`domain/content/entities.py` od ACS-F1-002, ali ga NIŠTA ne perzistuje).
`ContentPiece.payload_type` je samo diskriminator ("ovo JESTE
SOCIAL_POST"), ne nosilac stvarnog teksta.

Bez ovog polja A11 ne može perzistovati stvaran generisani post — samo
metapodatke o njemu. Zato ovaj task MORA završiti (i biti mergovan) PRIJE
A11 (ACS-F1-011, koji na njega eksplicitno zavisi).

**Zašto HIGH, ne MEDIUM kao ACS-F1-005..009:** Task uvodi PRVU `ALTER
TABLE` migraciju u projektu (`resources/migrations/0000..0002.sql` su svi
bili čisto `CREATE TABLE`). Po `CLAUDE.md`/workflow §4, SQLite/migrations
je eksplicitno na HIGH-risk listi → puni Codex + Claude + eksplicitno
Human Owner merge odobrenje, NE streamlined MEDIUM/Claude-only put iz §29.
**Stvaran blast radius je mali** (vidi GitNexus impact napomenu u
frontmatter-u — 1 novo OPCIONO polje sa default `None`, 1 nova kolona, 1
repository metoda proširena) — ovo NIJE arhitektonski refaktor, samo mala
aditivna izmjena koja slučajno pada u HIGH kategoriju zbog "dotiče
migracije" pravila. Napomenuto da Codex/Human Owner mogu kalibrisati dubinu
review-a prema stvarnom riziku, ne prema nominalnoj kategoriji.

Prije koda pročitati:

```text
AGENTS.md
CLAUDE.md
docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md
.agent/CURRENT_STATE.md (ACS-F1-006 red — originalna dokumentacija ovog gap-a)
AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md
  sekcija "34. Social Content generation pipeline" (samo da vidiš ZAŠTO
  payload treba postojati — ovaj task ne implementira pipeline, samo
  persistence temelj za njega)
```

Pročitati postojeći kod (ne pogađati potpise):

```text
src/ai_campaign_studio/domain/content/entities.py (ContentPiece, SocialPostPayload)
src/ai_campaign_studio/infrastructure/database/repositories/sqlite_content_repository.py
resources/migrations/0002_campaign_content_visual.sql (content_pieces DDL — tačan postojeći
  kolone spisak, NE mijenjati nijednu postojeću)
tests/integration/database/repositories/test_sqlite_content_repository.py
tests/integration/database/test_migrations.py
```

# Objective

1. `ContentPiece.payload: SocialPostPayload | None = None` — novo,
   OPCIONO, trailing polje (aditivno, ne mijenja nijedno postojeće polje
   ni njihov redoslijed).
2. `resources/migrations/0003_content_payload.sql` — `ALTER TABLE
   content_pieces ADD COLUMN payload_json TEXT;` (nullable — stariji/budući
   payload tipovi možda nemaju `SocialPostPayload`).
3. `SqliteContentRepository.save_content_piece`/`_content_piece_from_row`
   — serijalizuj/deserijalizuj `payload` kroz `payload_json` (NULL ako
   `payload is None`).

# Implementation steps

## `domain/content/entities.py`

Dodati TAČNO jedno polje na `ContentPiece`, na kraju (poslije
`revision_ids`):

```python
payload: SocialPostPayload | None = None
```

Ne dirati `SocialPostPayload` (već postoji, već ispravan), ne dirati
`__post_init__` (novo polje ne treba tuple-coercion).

## Migracija

```sql
ALTER TABLE content_pieces ADD COLUMN payload_json TEXT;
```

Jedna linija, u novom fajlu `0003_content_payload.sql`. Ne dirati
`0000`/`0001`/`0002` fajlove niti `migrations.py` runner (već radi sa
numerisanim fajlovima automatski).

## `sqlite_content_repository.py`

`save_content_piece`: dodati `payload_json` kolonu u INSERT/UPSERT
(`json.dumps(dataclasses.asdict(content_piece.payload)) if
content_piece.payload is not None else None`). `_content_piece_from_row`:
`payload=SocialPostPayload(**json.loads(row["payload_json"])) if
row["payload_json"] is not None else None`. Ne dirati nijednu drugu
metodu/red u fajlu (`get_content_piece`, `list_campaign_content`,
`_claim_from_row` ostaju netaknuti osim što `_content_piece_from_row`
sad popunjava i `payload`).

# Acceptance

- [ ] `ContentPiece.payload` je JEDINO novo polje na entitetu — diff
      dokazuje da ništa drugo nije dirano.
- [ ] Round-trip test: `ContentPiece` sa popunjenim `payload` (svi field-ovi
      `SocialPostPayload`, uključujući `hashtags` tuple i opcioni
      `visual_direction`) → save → get → `==` jednakost (dataclass
      value equality).
- [ ] Round-trip test: `ContentPiece` sa `payload=None` → save → get →
      `payload is None` (ne prazan `SocialPostPayload`, stvarno `None` —
      razlika između "nema payloada" i "payload sa praznim poljima" mora
      ostati vidljiva).
- [ ] `save_content_piece` ostaje idempotentan (re-save mijenja
      `payload_json`, ne duplira red — isti UPSERT obrazac kao postojeće
      kolone).
- [ ] Migration test (`test_migrations.py`) i dalje prolazi sa tri
      postojeće + ova nova migracija (ako test hardkodira tačan broj
      migracija, ažurirati ga da je tolerantan na dodatne — isti obrazac
      kao ACS-F1-005-ov fix istog testa, dokumentovan u
      `.agent/CURRENT_STATE.md`).
- [ ] Postojeći `content_pieces`/`content_claims` testovi (bez `payload`)
      i dalje prolaze nepromijenjeni — `payload_json` kolona ne kvari
      redove koji je ne postavljaju.
- [ ] `python -m pytest -q`, `ruff check .`, `mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest -q
python -m pytest tests/architecture/test_import_boundaries.py -v
python -m pytest tests/integration/database/repositories/test_sqlite_content_repository.py tests/integration/database/test_migrations.py -v
python -m ruff check .
python -m mypy src
```

# Review focus — Claude + Codex

- `ContentPiece` diff je STRIKTNO aditivno (jedno trailing opciono polje,
  ništa drugo) — pročitati cijeli diff;
- migracija je STVARNO samo `ALTER TABLE ADD COLUMN` (nullable) — nema
  `DROP`/`RENAME`/promjene tipa postojeće kolone, nema data-loss rizika za
  postojeće redove (kolona je nova, default NULL);
- `payload=None` vs `payload=SocialPostPayload(...)` razlika PREŽIVLJAVA
  round-trip (adversarial test: prazan/None mora ostati različit od
  praznog objekta sa svim string poljima `""`);
- `save_content_piece` idempotentnost i dalje radi (re-save update-uje
  `payload_json`, ne kreira duplikat reda);
- nema dirania `content_claims`/drugih tabela/drugih repository fajlova.

# Rollback

**HIGH risk — puna procedura.** Ne commit-ovati/merge-ovati bez eksplicitne
Codex review runde I eksplicitnog Human Owner odobrenja, bez obzira na
malu stvarnu veličinu izmjene. Ako implementer zaključi da treba više od
jedne dodatne kolone (npr. da payload treba svoju tabelu, ili da treba
dirati postojeću kolonu) — STOP, vratiti kontraktu na redizajn prije
nastavka, ne proširivati scope tiho.

# Coordination

Blokira **ACS-F1-011** (A11 — Allowed Facts + Social Content Generation),
koji zavisi od `ContentPiece.payload` da bi mogao perzistovati generisan
post. ACS-F1-011 kontrakt je već napisan i OPEN, čeka merge ovog taska.
Nezavisan je od svega ostalog trenutno otvorenog.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-010-social-post-payload-persistence
Branch:   task/ACS-F1-010-social-post-payload-persistence
Base:     main @ 5603030
```
