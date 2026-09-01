---
task_id: ACS-P0-006
phase: P0
title: "SQLite connection + migration runner + Unit of Work foundation"
risk: HIGH
coordinator: claude
implementer: crush
reviewers: [codex, claude]
status: "OPEN — contract written before code"
created_at: 2026-09-01
dependencies: [ACS-P0-002]
allowed_paths:
  - src/ai_campaign_studio/ports/database.py
  - src/ai_campaign_studio/infrastructure/__init__.py
  - src/ai_campaign_studio/infrastructure/database/__init__.py
  - src/ai_campaign_studio/infrastructure/database/connection.py
  - src/ai_campaign_studio/infrastructure/database/migrations.py
  - src/ai_campaign_studio/infrastructure/database/unit_of_work.py
  - resources/migrations/0000_foundation.sql
  - tests/integration/database/
  - tests/unit/database/
forbidden_paths:
  - src/ai_campaign_studio/channels/
  - src/ai_campaign_studio/localization/
  - src/ai_campaign_studio/ai_registry/
  - src/ai_campaign_studio/infrastructure/secrets/
  - src/ai_campaign_studio/infrastructure/ai/
  - src/ai_campaign_studio/domain/brand/
  - src/ai_campaign_studio/domain/campaign/
  - src/ai_campaign_studio/domain/content/
  - src/ai_campaign_studio/bootstrap.py
  - src/ai_campaign_studio/main.py
  - presentation_qt/
  - presentation_webview/
gitnexus_required: true
adversarial_required: true
gitnexus:
  required: true
  repository: "H:\\AI Campaing Studio"
  worktree: main (pre-branch pre-impact)
  branch: main
  head: 820bbf9
  index_status: up-to-date
  targets:
    - symbol: "src/ai_campaign_studio/ports (folder)"
      upstream_risk: LOW
      upstream_count: 0
      downstream_notes: "ports/database.py je nov sestrinski fajl, nema overlap sa ports/{channels,localization}.py (003/004) ili ports/{ai_registry,secrets}.py (005, paralelni task)"
      affected_processes: []
    - symbol: "domain/common/errors.py:DatabaseError, MigrationError"
      upstream_risk: LOW
      upstream_count: 0
      downstream_notes: "postojeće AppError podklase iz ACS-P0-002, definisane ali još nekorištene — ovaj task ih prvi put stvarno koristi, ne redefinisati"
      affected_processes: []
  scope_fit: PASS
  unknowns: []
---

# Kontekst

Šesti coding task Implementation Phase 0. Zavisi samo od ACS-P0-002
(merged). Može raditi paralelno sa ACS-P0-005 — `allowed_paths` su disjoint
(provjereno protiv ACS-P0-005 kontrakta). Napomena: P0.19 "Foundation ports"
iz plana nabraja svih 5 port fajlova (`localization.py`, `channels.py`,
`ai_registry.py`, `secrets.py`, `database.py`) kao zajednički checkpoint —
ovaj task kreira samo `database.py` (svoj dio); preostala dva
(`ai_registry.py`/`secrets.py`) dolaze iz paralelnog ACS-P0-005. P0.19
"acceptance" (architecture test potvrđuje smjer zavisnosti) je već
strukturno pokriven postojećim `tests/architecture/test_import_boundaries.py`
iz ACS-P0-002 (skenira po sloju, ne po specifičnom fajlu) — ne treba novi
dediciran test, samo potvrditi da `ports/database.py` prolazi postojeći
boundary checker.

**HIGH risk** — workflow §22 eksplicitno navodi SQLite/migrations kao HIGH
(shared persistence foundation, destructive-migration potencijal), i
workflow §4 navodi "SQLite/migrations/UoW" eksplicitno u elevated P0
standard listi.

Prije koda implementer mora pročitati:

```text
AGENTS.md
CLAUDE.md
docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md
.agent/CURRENT_STATE.md
.agent/PROJECT_MAP.md
.agent/TASK_ROUTING.md
AI_Campaign_Studio_Implementation_Phase_0_v1_1_Agent_Workflow_Integrated.md
  sekcije 23–26 (P0.16–P0.19)
```

# Objective

Izolovan, testabilan SQLite connection factory + pouzdan migration runner +
deterministički Unit of Work, bez ijedne Brand/Campaign/Content repository
implementacije (te dolaze kad domain postoji).

# Implementation steps

## P0.16 — SQLite connection foundation

1. `ports/database.py`: `DatabaseConnectionPort` — foundation Protocol. NE
   definisati još Brand/Campaign repository portove.
2. `infrastructure/database/connection.py`: `create_connection(database_path)`
   factory/funkcija. Pravila: `sqlite3`, `row_factory = sqlite3.Row`,
   `PRAGMA foreign_keys = ON`, razuman `busy_timeout`. WAL mode samo ako
   test potvrdi da je bez problema — ne uvoditi preranu DB optimizaciju.
   NE praviti globalni mutable connection singleton — factory/connection
   manager mora imati jasno definisan lifecycle (ko otvara, ko zatvara).

## P0.17 — Migration runner

3. `resources/migrations/0000_foundation.sql`: filename konvencija
   `NNNN_name.sql`. Sadrži SAMO foundation tabele koje stvarno trebaju prije
   Campaign domaina:
   - `app_metadata` (`key TEXT PRIMARY KEY`, `value TEXT NOT NULL`,
     `updated_at TEXT NOT NULL`);
   - `provider_configs` (`provider_code TEXT PRIMARY KEY`,
     `configured INTEGER NOT NULL DEFAULT 0`,
     `validated INTEGER NOT NULL DEFAULT 0`, `credential_ref TEXT NULL`,
     `base_url TEXT NULL`, `updated_at TEXT NOT NULL`) — **NE** `api_key`/
     `token`/`secret` kolona, nikad;
   - `model_selections` (`purpose TEXT PRIMARY KEY`,
     `provider_code TEXT NOT NULL`, `model_id TEXT NOT NULL`,
     `updated_at TEXT NOT NULL`) — P0 ne mora upisati izbor, samo šema.
   - `schema_migrations` (`version INTEGER PRIMARY KEY`, `name TEXT NOT NULL`,
     `applied_at TEXT NOT NULL`, `checksum TEXT NOT NULL`) — runner-ova
     vlastita tracking tabela.
4. `infrastructure/database/migrations.py`: discover SQL fajlove iz
   `resources/migrations/`, parse version/name iz filename-a, sortiraj,
   izračunaj checksum (npr. sha256 sadržaja), osiguraj `schema_migrations`
   tabelu, primijeni neprimijenjene migracije U TRANSAKCIJI, rollback na
   grešku (no partial apply), zapiši primijenjenu migraciju, odbij ako je
   već-primijenjena migracija promijenjena (checksum mismatch →
   `MigrationError` iz `domain/common/errors.py`, ACS-P0-002 — ne
   redefinisati). NE koristiti `CREATE TABLE IF NOT EXISTS` kao zamjenu za
   migration tracking kroz cijeli sistem (dozvoljeno samo za
   `schema_migrations` bootstrap tabelu samu).

## P0.18 — Unit of Work / transaction foundation

5. `infrastructure/database/unit_of_work.py`: `SqliteUnitOfWork` context
   manager (`with uow: ... uow.commit()`). Exception unutar `with` bloka →
   rollback. Ako `commit()` nije eksplicitno pozvan prije izlaska iz
   `with` bloka → rollback (explicit-commit-otherwise-rollback, po
   preporuci iz plana). NE sadržati `brand_repository`/
   `campaign_repository`/`post_repository` — ti dolaze kad domain postoji.

## P0.19 — Foundation ports (samo database.py dio ovog taska)

6. Potvrditi da `ports/database.py` prolazi postojeći
   `tests/architecture/test_import_boundaries.py` (ne importuje
   infrastructure). Ne kreirati novi arhitekturni test — postojeći već
   pokriva `ports/` sloj generički.

# Acceptance

- [ ] `create_connection` otvara temp DB, `SELECT 1` radi, `close`,
      re-open radi.
- [ ] `PRAGMA foreign_keys` je uključen (test čita pragma vrijednost, ne
      samo pretpostavlja).
- [ ] Fresh DB migration: `0 → 0000` (schema_migrations ima jedan red
      poslije prvog run-a).
- [ ] Idempotency: drugi run migration runnera na već-migriranoj DB → 0
      novih migracija primijenjeno.
- [ ] Failure rollback: namjerno invalid SQL u temp migration fixture-u →
      no partial apply (DB stanje netaknuto poslije neuspjelog pokušaja).
- [ ] Checksum mismatch: promijenjen already-applied SQL fajl (u testu, ne
      u pravom `resources/migrations/`) → `MigrationError`.
- [ ] UoW: insert unutar `with uow: ... uow.commit()` → red postoji poslije;
      insert + exception (bez commit-a) → red ne postoji; insert bez
      eksplicitnog `commit()` poziva → red ne postoji.
- [ ] `provider_configs` tabela NEMA `api_key`/`token`/`secret` kolonu
      (test koji introspektuje schema i to provjerava).
- [ ] `python -m pytest -q`, `ruff check .`, `mypy src` prolaze.
- [ ] Nema globalnog mutable connection singleton-a.

# Adversarial test (obavezno — adversarial_required: true)

Za migration checksum-mismatch invariant:

1. test tvrdi da runner odbija promijenjenu already-applied migraciju;
2. privremeno ukloniti checksum-check iz `migrations.py` — test mora FAIL
   (runner tiho prihvata izmijenjenu migraciju);
3. vratiti — test mora PASS;
4. dokumentovati oba outputa.

Isto za "failure rollback, no partial apply": privremeno ukloniti
transaction/rollback wrapping oko apply-a — test sa namjerno invalid
migracijom mora FAIL (djelimično primijenjena migracija ostaje u DB); vratiti
— test mora PASS.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest -q
python -m ruff check .
python -m mypy src
git status --short
```

# Review focus — Codex

- da li checksum-mismatch i rollback adversarial testovi stvarno padaju na
  poznato lošoj varijanti;
- da li idempotency test stvarno pokreće runner DVA puta na istoj DB, ne
  samo jednom;
- edge cases: prazan `resources/migrations/` direktorij, migration fajl sa
  neparsabilnim filename-om, concurrent-ish pristup (dva UoW instance na
  istoj konekciji ako je relevantno za trenutni connection lifecycle
  dizajn);
- da li `provider_configs`/`model_selections` schema stvarno nema
  secret-like kolonu.

# Review focus — Claude

- `infrastructure/database/*` ne curi u `domain`/`application`/`ports`
  (dependency direction);
- `DatabaseConnectionPort` je framework-neutral, ne zna sqlite3 detalje
  direktno u portu (port je apstrakcija, `connection.py` je implementacija);
- connection lifecycle je eksplicitan, ne globalni singleton;
- `SqliteUnitOfWork` ne sadrži nijedan Brand/Campaign/Content repository;
- integracija sa `domain/common/errors.py` (`DatabaseError`,
  `MigrationError`) iz ACS-P0-002 — ne duplira error taxonomy.

# Rollback

HIGH task (destructive-migration potencijal, shared persistence
foundation). Ako review otkrije da checksum-mismatch ili rollback
adversarial test ne dokazuje invariant — NE spajati, fix na istoj branch
bez proširenja scope-a.

# Dependency baseline

Zavisi od ACS-P0-002 (merged, `main`@`820bbf9`). Ne granati sa starijeg
main-a.

# Coordination

Paralelno sa ACS-P0-005 — `allowed_paths` potpuno disjoint (provjereno).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-P0-006-sqlite-foundation
Branch:   task/ACS-P0-006-sqlite-foundation
Base:     main @ 820bbf9
```

Nakon merge-a: post-merge gate, GitNexus detect-changes prije reviewa (ili
manuelni ekvivalent), GitNexus re-index poslije merge-a, CURRENT_STATE
update. Nakon što OBA (005 i 006) budu merged, ACS-P0-007 postaje
unblocked.
