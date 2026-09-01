# ACS-P0-006 — implementer/execution evidence — coordinator-confirmed

**Implementer:** Crush (nema self-report — isti obrazac kao ACS-P0-001/004)
**Branch/worktree:** `task/ACS-P0-006-sqlite-foundation`,
`../ai-campaign-studio-worktrees/ACS-P0-006-sqlite-foundation`
**Base:** `main@820bbf9`
**Commit:** `92f3917` (author Crush, committed by coordinator)

## Files changed — nezavisno potvrđeno

Svi novi fajlovi, tačno unutar `allowed_paths`: `ports/database.py`,
`infrastructure/{__init__,database/__init__,database/connection,
database/migrations,database/unit_of_work}.py`,
`resources/migrations/0000_foundation.sql`,
`tests/integration/database/{test_connection,test_migrations}.py`,
`tests/unit/database/test_unit_of_work.py`. `pyproject.toml` netaknut.
Nijedan `forbidden_path` diran (ai_registry/, infrastructure/secrets/,
channels/, localization/ — sve netaknuto, uključujući paralelni
ACS-P0-005 scope).

## Kod — pročitan u cjelini

- `connection.py`: `create_connection()` — svaki poziv vraća SVJEŽU
  konekciju (nema globalnog singleton-a), `isolation_level = None`
  (autocommit, transakcije eksplicitne preko BEGIN/COMMIT/ROLLBACK),
  `row_factory = sqlite3.Row`, `PRAGMA foreign_keys = ON`, `busy_timeout`
  5000ms.
- `migrations.py`: `discover_migrations()` parsira `NNNN_name.sql`
  filename regex-om, sortira po verziji, računa sha256 checksum.
  `run_migrations()` osigurava `schema_migrations` tabelu, primjenjuje
  neprimijenjene migracije, odbija checksum mismatch na već-primijenjenoj
  migraciji (`MigrationError`, ponovo koristi ACS-P0-002 error taxonomy —
  ne redefiniše). `_apply_migration()` radi BEGIN/apply/INSERT
  schema_migrations red/COMMIT unutar `try`, ROLLBACK + re-raise u
  `except`.
- `unit_of_work.py`: `SqliteUnitOfWork` — `__enter__` radi BEGIN,
  `commit()` radi COMMIT i postavlja `_committed = True`, `__exit__`
  radi ROLLBACK ako `_committed` nije `True`, vraća `False` (exception se
  NE guta). Nema Brand/Campaign/Content repository koda.
- `0000_foundation.sql`: `app_metadata`, `provider_configs` (BEZ
  api_key/token/secret kolone — potvrđeno i testom), `model_selections` —
  tačno prema shemi iz plana.
- `ports/database.py`: `DatabaseConnectionPort` Protocol — minimalan
  (`commit`/`rollback`/`close`), framework-neutral.

## Nezavisna verifikacija — DOSLOVAN output (poslije env fix-a)

Fresh `.venv` je imao isti oštećen `pydantic_core` wheel kao ranije na
ACS-P0-004 — popravljeno sa `pip install --force-reinstall --no-cache-dir
pydantic pydantic-core mypy`.

```text
$ ./.venv/Scripts/python.exe -m pytest -q
........................................................................ [ 70%]
..............................                                           [100%]
102 passed in 1.24s

$ ./.venv/Scripts/python.exe -m ruff check .
All checks passed!

$ ./.venv/Scripts/python.exe -m mypy src
Success: no issues found in 34 source files
```

## Adversarial proof — nezavisno izvršen (implementer nije predao pisani
dokaz, koordinator je sam sproveo obje procedure iz kontrakta)

**Checksum mismatch:** privremeno uklonjen checksum-check iz
`run_migrations()` (samo `continue` na već-primijenjenu verziju, bez
provjere) → `test_checksum_mismatch_raises_migration_error` FAIL (`DID NOT
RAISE MigrationError`). Vraćeno → PASS.

**Failure rollback / no partial apply:** privremeno uklonjen
transaction/rollback wrapping iz `_apply_migration()` (direktan execute bez
BEGIN/ROLLBACK) → `test_failure_rollback_no_partial_apply` FAIL
(`partial_table` ostaje u DB poslije neuspjelog apply-a). Vraćeno (byte-identično
originalu) → PASS. `git status --short` čist poslije restauracije.

## GitNexus

`gitnexus_impact: UNKNOWN` (poznato ograničenje). Kompenzovano: svi fajlovi
novi, `ports/` folder je imao 0 upstream callera prije taska (pre-impact iz
kontrakta), `ports/database.py` je nov sestrinski fajl bez callera — nema
blast radius-a. `MigrationError`/`DatabaseError` iz ACS-P0-002 su prvi put
stvarno iskorišteni ovim taskom (ranije definisani ali nekorišteni).

## Acceptance checklist

Svih 9 stavki iz kontrakta — PASS, potvrđeno gore + testovima
(`test_connection_select_one_and_reopen`, `test_foreign_keys_enabled`,
`test_row_factory_is_sqlite_row`, `test_fresh_db_migration_applies_foundation`,
`test_idempotency_second_run_applies_nothing`,
`test_failure_rollback_no_partial_apply`,
`test_checksum_mismatch_raises_migration_error`,
`test_provider_configs_has_no_secret_columns`, `test_commit_persists`,
`test_exception_rolls_back`, `test_no_commit_rolls_back`).

## Arhitekturne opservacije (ne blocking, za review)

- `_split_statements()` u `migrations.py` dijeli SQL naivno na `;` — radi
  ispravno za trenutni `0000_foundation.sql` (proste CREATE TABLE izjave
  bez ugniježđenih `;` u string literalima), ali nije generički SQL
  parser. Prihvatljivo za P0 foundation scope; buduće migracije sa
  kompleksnijim SQL-om (trigers, CASE u string vrijednosti) bi trebale
  ponovo razmotriti ovaj pristup.

## Not verified

- GitNexus automated impact (structural limitation).
- Formalni Codex review — brief pripremljen zasebno.
