---
task_id: ACS-F1-006
phase: Faza-1
title: "Campaign/Content/Visual/Revision SQLite persistence (A5, dio 2)"
risk: MEDIUM
coordinator: claude
implementer: crush
reviewers: [claude]
status: "OPEN — contract written before code"
created_at: 2026-09-02
dependencies: [ACS-F1-005]
allowed_paths:
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_campaign_repository.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_content_repository.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_visual_repository.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_revision_repository.py
  - resources/migrations/0002_campaign_content_visual.sql
  - tests/integration/database/repositories/test_sqlite_campaign_repository.py
  - tests/integration/database/repositories/test_sqlite_content_repository.py
  - tests/integration/database/repositories/test_sqlite_visual_repository.py
  - tests/integration/database/repositories/test_sqlite_revision_repository.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/ports/repositories.py
  - src/ai_campaign_studio/infrastructure/database/connection.py
  - src/ai_campaign_studio/infrastructure/database/migrations.py
  - src/ai_campaign_studio/infrastructure/database/unit_of_work.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_brand_repository.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_fact_repository.py
  - src/ai_campaign_studio/infrastructure/database/repositories/__init__.py
  - resources/migrations/0000_foundation.sql
  - resources/migrations/0001_brand_facts.sql
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
  head: 940d963
  index_status: fresh (analyze re-run 2026-09-02 post A4 merge)
  targets:
    - symbol: "new infrastructure/database/repositories/sqlite_{campaign,content,visual,revision}_repository.py"
      upstream_risk: LOW
      upstream_count: "Depends on ACS-F1-005's ports/repositories.py (CampaignRepositoryPort, ContentRepositoryPort, VisualRepositoryPort, RevisionRepositoryPort Protocol definitions) -- see Coordination section for sequencing. Adds one new migration file (0002) on top of 0000+0001, additive only, no existing business data."
      downstream_notes: "Brand-new adapter files, zero existing importers."
      affected_processes: []
  scope_fit: PASS
  unknowns: []
---

# Kontekst

Task **A5 — business persistence**, drugi dio. Paralelno sa
**ACS-F1-005** (Pi) — `ports/repositories.py` + Brand/Facts persistence.
Vidi taj kontrakt za punu HIGH-vs-MEDIUM risk tier diskusiju (ukratko:
"repository adapter" je eksplicitan MEDIUM primjer u
`docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md` §3; §4-ov pojačan standard za
SQLite/migrations važi SAMO za P0 taskove, ne za Faza 1; ova migracija je
čisto additivna, nema postojećih poslovnih podataka). §29 politika:
Claude-only review, PASS -> odmah commit/push/merge.

**VAŽNA ZAVISNOST**: ovaj task implementira `CampaignRepositoryPort`/
`ContentRepositoryPort`/`VisualRepositoryPort`/`RevisionRepositoryPort`
koje definiše ACS-F1-005 u `ports/repositories.py`. Vidi "Redoslijed rada"
ispod.

Prije koda pročitati:

```text
AGENTS.md
CLAUDE.md
docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md §3 (Risk tier), §7 (GitNexus), §11 (evidence)
.agent/CURRENT_STATE.md
AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md
  sekcija 0A.3 (A5), 16 (Repository portovi)
```

Pročitati postojeći P0 SQLite kod (ne pogađati konvencije — isti kao u
ACS-F1-005):

```text
src/ai_campaign_studio/infrastructure/database/connection.py
src/ai_campaign_studio/infrastructure/database/migrations.py
src/ai_campaign_studio/infrastructure/database/unit_of_work.py
resources/migrations/0000_foundation.sql
```

Pročitati domain entitete koje ovaj task perzistira (ne pogađati polja):

```text
src/ai_campaign_studio/domain/campaign/entities.py
src/ai_campaign_studio/domain/content/entities.py
src/ai_campaign_studio/domain/content/claims.py
src/ai_campaign_studio/domain/content/revisions.py
src/ai_campaign_studio/domain/visual/entities.py
src/ai_campaign_studio/domain/visual/layout.py
```

# Redoslijed rada (zbog zavisnosti na ACS-F1-005)

**Odmah, bez čekanja** (nema zavisnosti na `ports/repositories.py`):

- Dizajn migracije `0002_campaign_content_visual.sql` (DDL ne zavisi od
  Protocol definicija).
- Skeleton adapter fajlova sa metodama koje još ne moraju gađati tačan
  Protocol potpis.

**Tek kad koordinator potvrdi da je ACS-F1-005 merged** (ili barem da
`ports/repositories.py` sadrži `CampaignRepositoryPort` i ostale na
disku):

- Finalna implementacija adaptera koja stvarno implementira te Protocol
  interfejse.

Ako ACS-F1-005 još nije spreman kad implementer stigne do te tačke —
javiti koordinatoru, ne izmišljati privremene lokalne Protocol
definicije (0A.5 dupliranje).

# Objective

1. `resources/migrations/0002_campaign_content_visual.sql` — tabele za
   Campaign/CampaignBrief/CampaignPlan/CampaignItem, ContentPiece/
   ContentClaim/Revision, CampaignVisualSystem.
2. `sqlite_campaign_repository.py` — implementira `CampaignRepositoryPort`.
3. `sqlite_content_repository.py` — implementira `ContentRepositoryPort`.
4. `sqlite_visual_repository.py` — implementira `VisualRepositoryPort`.
5. `sqlite_revision_repository.py` — implementira `RevisionRepositoryPort`.
6. Round-trip integracioni testovi za sva četiri.

# Implementation steps

## `resources/migrations/0002_campaign_content_visual.sql`

Isti DDL stil kao `0001_brand_facts.sql` (TEXT PRIMARY KEY, TEXT ISO
timestamp, INTEGER 0/1 bool, FK reference gdje ima smisla — npr.
`campaign_items.plan_id REFERENCES campaign_plans(id)`,
`content_pieces.campaign_item_id REFERENCES campaign_items(id)`). Za
value object grafove sa ugniježdenim listama (npr. `CampaignItem.facts_needed`,
`ContentPiece.claims`/`facts_allowed`/`revision_ids`, `SocialPostPayload`
polja) — isti pristup kao ACS-F1-005: JSON kolona za ugniježdeni graf je
prihvatljivo, ILI zasebna join tabela gdje je FK integritet vrijedniji
(implementer bira po slučaju, dokumentuje izbor po tabeli). `CampaignItem.role`
i svi enum-tipizirani atributi (`CampaignStatus`, `ContentStatus`,
`ClaimType`, `ClaimStatus`, `LayoutPrimitive`, itd.) čuvaju se kao TEXT
(enum `.value`), ne integer kod.

FK poredak mora poštovati `PRAGMA foreign_keys = ON` (već aktivno):
campaigns -> campaign_briefs/campaign_plans -> campaign_items ->
content_pieces -> (claims/revisions) -> campaign_visual_systems.

## SQLite adapteri

Isti konstruktor-obrazac kao ACS-F1-005 (`sqlite3.Connection` ili
`SqliteUnitOfWork`, dokumentovati izbor — mora biti KONZISTENTAN sa
ACS-F1-005-ovim izborom, provjeriti taj kod prije pisanja svog, ne
izmišljati drugačiji pattern za isti sloj). `save_*` idempotentne
(insert-or-replace po primarnom ključu).

`sqlite_content_repository.py` posebno: `ContentPiece.claims` (tuple
`ContentClaim`) i `revision_ids` (tuple `RevisionId`) moraju round-trip-
ovati tačno — ovo je polje koje docstring `ContentPiece`-a označava kao
"Approved content ne mijenja se tiho" ugovor; repository sloj SAM ne
implementira to pravilo (to je use-case posao, van ovog taska), ali mora
vjerno čuvati/vraćati status + revision_ids bez gubitka da bi taj ugovor
bio provodljiv kasnije.

# Acceptance

- [ ] `SqliteCampaignRepository`/`SqliteContentRepository`/
      `SqliteVisualRepository`/`SqliteRevisionRepository` implementiraju
      svoje Protocol-e iz `ports/repositories.py` (ACS-F1-005) tačno.
- [ ] Round-trip test za svaki: save -> get -> polje-po-polje identično
      originalu, uključujući ugniježdene liste (claims, facts_needed,
      hashtags, itd.) i enum vrijednosti (vraćene kao pravi domain enum,
      ne goli string).
- [ ] `list_campaign_content(campaign_id)` vraća tačno content piece-ove
      te kampanje, ništa više/manje (test sa dvije kampanje dokazuje
      izolaciju).
- [ ] Idempotentnost: `save_*` pozvan dvaput sa istim ID-jem ne duplira
      redove.
- [ ] Migracija `0002` se primjenjuje čisto poslije `0000`+`0001` na
      svježoj bazi.
- [ ] FK poredak testiran (insert child prije parenta baca violation).
- [ ] Nema izmjena `ports/repositories.py`, `sqlite_brand_repository.py`,
      `sqlite_fact_repository.py`, `0000_foundation.sql`,
      `0001_brand_facts.sql` (ACS-F1-005 teritorija).
- [ ] `python -m pytest -q`, `ruff check .`, `mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest -q
python -m pytest tests/architecture/test_import_boundaries.py -v
python -m pytest tests/integration/database -v
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- adapteri stvarno implementiraju ACS-F1-005-ove Protocol potpise tačno
  (ne blago drugačije metode koje "slično rade");
- round-trip testovi provjeravaju SVAKO polje, posebno enum vrijednosti
  (vraćene kao domain enum, ne string) i ugniježdene liste;
- konstruktor-obrazac konzistentan sa ACS-F1-005 (isti pristup
  connection/UoW injection);
- migracija `0002` ne dira `0000`/`0001`, FK poredak ispravan;
- scope discipline — nema dirania Brand/Facts teritorije.

# Rollback

MEDIUM risk, isto obrazloženje kao ACS-F1-005 (additive migracija, nema
postojećih podataka u riziku). Fix na istoj branch bez proširenja scope-a.
STOP i vrati na puni ciklus ako se pokaže potreba za destruktivnom
migracijom.

# Coordination

Paralelno sa **ACS-F1-005** (Pi), sekvencirano na Protocol definicijama
(vidi "Redoslijed rada"). `allowed_paths` disjoint po domenu unutar
`infrastructure/database/repositories/`.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-006-campaign-content-visual-persistence
Branch:   task/ACS-F1-006-campaign-content-visual-persistence
Base:     main @ 940d963
```
