---
task_id: ACS-F1-001
phase: Faza-1
title: "Domain common extension + Brand domain + Facts domain (A3, dio 1)"
risk: MEDIUM
coordinator: claude
implementer: pi
reviewers: [claude]
status: "OPEN — contract written before code"
created_at: 2026-09-02
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/domain/common/ids.py
  - src/ai_campaign_studio/domain/common/errors.py
  - src/ai_campaign_studio/domain/brand/
  - src/ai_campaign_studio/domain/facts/
  - tests/unit/domain/common/
  - tests/unit/domain/brand/
  - tests/unit/domain/facts/
forbidden_paths:
  - src/ai_campaign_studio/domain/campaign/
  - src/ai_campaign_studio/domain/content/
  - src/ai_campaign_studio/domain/visual/
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
  - src/ai_campaign_studio/domain/common/timestamps.py
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
    - symbol: "domain/common/ids.py, domain/common/errors.py"
      upstream_risk: LOW
      upstream_count: "ids.py: new_id() used by jobs/manager.py, ai_registry, channels (existing P0 callers, untouched by this extension — only ADDING type aliases, not changing new_id()). errors.py: DomainError already exists as empty subclass of AppError, no existing subclasses of DomainError yet — safe to add InvalidStateTransition/InvariantViolation/EntityNotFound beneath it."
      downstream_notes: "Pure additive extension — no existing signature changes. New domain/brand/, domain/facts/ are brand-new directories, zero existing importers."
      affected_processes: []
  scope_fit: PASS
  unknowns: []
---

# Kontekst

Prvi Faza 1 business/domain task, sada kad je `P0-GATE = PASS` (svih 8 P0
taskova merged, `artifacts/phase0_foundation_gate.json` na main-u kaže
`status: PASS`). Ovo je task **A3 — Common + Domain enums/entities** iz
`AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md`, prvi dio
(domain/common extension + Brand + Facts). Drugi dio (Campaign + Content +
Visual) ide paralelno kao ACS-F1-002 (Crush).

**Rule 0A.5 (protiv dupliranja)**: `domain/common/ids.py` i
`domain/common/errors.py` VEĆ POSTOJE iz P0 (`new_id()`, `utc_now()`,
`AppError`/`DomainError`/... hijerarhija). Ovaj task ih PROŠIRUJE
(dodaje typed ID aliase i nove domain-specific exception klase), NE pravi
paralelnu verziju. `domain/common/timestamps.py` se NE dira — `utc_now()`
već postoji i zadovoljava potrebu.

**Risk**: MEDIUM, ne HIGH. Ovo je čist domain sloj (plain dataclasses/
enums, bez infrastructure zavisnosti) — nije na HIGH listi (SecretStore,
SQLite/migrations, architecture boundaries/bootstrap, registry contracts).
Postojeći `tests/architecture/test_import_boundaries.py` (hardened kroz 4
runde Codex review-a na ACS-P0-002) već je siguran safety net protiv
infrastructure importa u domain sloju — nije potrebno graditi novi
adversarial dokaz za tu granicu, samo je potvrditi kroz standardnu
verifikaciju. **Ostaje na §29 politici**: Claude-only review, PASS →
odmah commit/push/merge, bez Codex runde i bez posebnog Human Owner
odobrenja po tasku.

Prije koda pročitati:

```text
AGENTS.md
CLAUDE.md
docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md
.agent/CURRENT_STATE.md
AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md
  sekcije 0A (cijela — P0→Faza1 handoff pravila), 8 (domain model princip:
  plain dataclasses/enums, Pydantic samo na granicama), 9 (domain/common),
  10 (Brand domain), 11 (Facts domain)
```

# Objective

1. Proširiti `domain/common/ids.py` sa typed ID aliasima.
2. Proširiti `domain/common/errors.py` sa domain-specific exception klasama
   (podklase postojeće `DomainError`).
3. Implementirati `domain/brand/` (value objects + entities).
4. Implementirati `domain/facts/` (enums + entities + policies).

# Implementation steps

## `domain/common/ids.py` — proširiti

Dodati typed ID aliase (NewType ili jednostavan `str` alias — implementer
bira idiomatski Python pattern, konzistentno sa ostatkom P0 koda koji
koristi plain `str` za ID-jeve):

```text
ProjectId, BrandId, BrandSnapshotId, FactId, CampaignId, CampaignPlanId,
CampaignItemId, PostId, RevisionId, VisualSystemId
```

Ne mijenjati postojeći `new_id()`.

## `domain/common/errors.py` — proširiti

Dodati kao podklase postojeće `DomainError`:

```text
InvalidStateTransition
InvariantViolation
EntityNotFound
```

Pratiti postojeći `AppError` obrazac (`default_code`, `human_message`,
`technical_context` bez leak-a u `args`) — vidi postojeće klase u istom
fajlu kao primjer. Po potrebi dodati nove `ErrorCode` vrijednosti.

## `domain/brand/value_objects.py`

```text
BrandVoice (formality, tone[], preferred_terms[], forbidden_terms[],
            regional_vocabulary[], tone_examples[])
Audience (id, name, description, needs[], objections[])
ServiceDefinition (id, name, description)
Restriction
VisualIdentity (logo_path?, primary_colors[], secondary_colors[],
                font_families[], image_style_notes[])
```

Plain dataclasses. Koristiti `tuple[str, ...]` za liste, ne `list[str]`
(lekcija iz ACS-P0-004/005 — immutable kolekcije u frozen modelima).

## `domain/brand/entities.py`

```text
Brand (id, name, created_at)
BrandSnapshot (id, brand_id, version, language, locale, script, voice,
               audiences, services, visual_identity, restrictions,
               approved_fact_ids[], created_at) — IMMUTABLE (frozen=True),
               nikad se ne mijenja nakon kreiranja
```

## `domain/facts/enums.py`

```text
FactStatus: APPROVED, SUPERSEDED, SOFT_DELETED
```

Bez `PROPOSED` — taj status dolazi u Slice 2.

## `domain/facts/entities.py`

```text
SourceReference (source_type, uri, snapshot_id?, chunk_id?)
ApprovedFact (id, logical_fact_id, version, content, source_ref, status,
              created_at, superseded_by?, deleted_at?) — IMMUTABLE version
```

## `domain/facts/policies.py`

```text
is_fact_usable(fact) -> bool
assert_fact_usable(fact) -> None  # raise ako nije usable
create_next_fact_version(previous, new_content, source_ref) -> ApprovedFact
```

`create_next_fact_version` NE mutira stari fact tekst — vraća NOVI
`ApprovedFact` sa `version + 1`, i (implementer odlučuje da li ova funkcija
i markira `previous` kao `SUPERSEDED` — pošto su fact objekti immutable,
"markiranje" znači vraćanje NOVOG immutable snapshot-a starog facta sa
`status=SUPERSEDED, superseded_by=<novi id>`, ne in-place mutaciju).
Dokumentovati odabrani pristup jasno u docstring-u.

# Acceptance

- [ ] Svi novi moduli su plain dataclasses/enums (Pydantic NIJE korišten u
      domain sloju — to je za granice, kasniji task).
- [ ] `BrandSnapshot` i `ApprovedFact` su `frozen=True` (immutable) —
      test dokazuje da pokušaj mutacije baca `FrozenInstanceError` (ili
      ekvivalentan Python mehanizam).
- [ ] `create_next_fact_version` ne mutira originalni `ApprovedFact` objekat
      (test: originalni objekat identičan prije/poslije poziva).
- [ ] `is_fact_usable`/`assert_fact_usable` ispravno rade za sve
      `FactStatus` vrijednosti (APPROVED usable, SUPERSEDED/SOFT_DELETED
      nisu).
- [ ] Nema infrastructure importa nigdje u `domain/brand/`, `domain/facts/`,
      izmijenjenim `domain/common/*` fajlovima — potvrđeno kroz postojeći
      `tests/architecture/test_import_boundaries.py` (pokrenuti ga
      eksplicitno, ne pretpostaviti).
- [ ] `python -m pytest -q`, `ruff check .`, `mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest -q
python -m pytest tests/architecture/test_import_boundaries.py -v
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- domain modeli su STVARNO plain dataclasses, ne Pydantic bez potrebe (per
  sekcija 8 pravilo);
- `tuple[str, ...]` umjesto `list[str]` za immutable kolekcije u frozen
  modelima;
- `create_next_fact_version`-ov pristup versioning-u je konzistentan i
  jasno dokumentovan (immutable-replace, ne in-place mutate);
- nove `DomainError` podklase prate postojeći `AppError` obrazac tačno
  (nema leak-a `technical_context`-a u `args`);
- nema dupliranja postojećeg `new_id()`/`utc_now()` — samo proširenje
  `ids.py` sa type aliasima;
- scope discipline — nema dirania `campaign/`, `content/`, `visual/`
  (ACS-F1-002 teritorija).

# Rollback

MEDIUM risk — čist domain sloj, nema runtime uticaja na postojeći
foundation kod (samo dodaje, ne mijenja postojeće funkcije). Ako review
otkrije problem, fix na istoj branch bez proširenja scope-a. Ako se
pokaže da task ipak dira nešto sa HIGH liste (npr. potreba da se mijenja
postojeći `AppError` hijerarhija na nekompatibilan način) — STOP, vratiti
na puni Codex ciklus, ne nastaviti tiho olakšanim putem.

# Coordination

Paralelno sa **ACS-F1-002** (Crush) — `domain/campaign/`, `domain/content/`,
`domain/visual/`. `allowed_paths` su disjoint (uključujući provjeru da
nijedan `__init__.py` paket-fajl nije naveden u oba kontrakta — lekcija iz
ACS-P0-005/006 incidenta).

**Zavisnost za ACS-F1-002**: taj task treba `domain/common/ids.py`-jeve
typed ID aliase (za tipove kao `BrandSnapshotId`, `FactId` referencirane u
`campaign`/`content` entitetima). Ako ACS-F1-002 stigne do pisanja
`entities.py` fajlova prije nego što ovaj task merge-uje, koordinator
javlja da sačeka — `enums.py`/`roles.py`/`templates.py` fajlovi u
ACS-F1-002 nemaju tu zavisnost i mogu se raditi odmah.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-001-domain-common-brand-facts
Branch:   task/ACS-F1-001-domain-common-brand-facts
Base:     main @ 215d528
```
