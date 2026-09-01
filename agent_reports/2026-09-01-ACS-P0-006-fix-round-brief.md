# ACS-P0-006 — fix round brief (BF-1, BF-2)

Za: Crush (isti branch)
Od: Claude (koordinator), poslije Codex REJECT-a
Datum: 2026-09-01

## Status

Codex review: `agent_reports/2026-09-01-ACS-P0-006-review-codex.md` —
`verdict: REJECT`, dva blocking findings. Koordinator je oba nezavisno
reprodukovao. Oba su stvaran transaction/state bug, ne teorijski slučaj —
ovo je HIGH task (SQLite/migrations), ostaje na punom Codex+Claude+Human
Owner ciklusu po novoj review politici (`docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md`
§29) jer spada u destructive-migration/persistence-foundation kategoriju.

**Task se NE spaja.** Fix runda na istoj branch-i
(`task/ACS-P0-006-sqlite-foundation`).

## BF-1 — `SqliteUnitOfWork` re-use poslije commit-a onemogući rollback

`__enter__()` ne resetuje `_committed` na `False`. Nakon prvog uspješnog
`with uow: ... uow.commit()`, ista instanca zadržava `_committed=True`
zauvijek. Ponovni `with uow:` na istoj instanci bez novog `commit()` poziva
NE rollback-uje (jer `__exit__` provjerava `if not self._committed`, a to je
i dalje `True` od prošlog puta).

Reprodukovano: drugi `with uow:` blok (insert bez commit-a) ostaje trajno
upisan — `count` je 2 umjesto očekivanog 1.

**Fix:** resetovati `self._committed = False` na početku `__enter__()` (prije
`BEGIN`), tako da svaki `with uow:` blok tretira commit-status nezavisno.

## BF-2 — migration runner rollback-uje tuđu (caller-owned) transakciju

`_apply_migration()`:

```python
try:
    connection.execute("BEGIN")
    ...
except Exception:
    connection.execute("ROLLBACK")
    raise
```

Ako caller VEĆ ima otvorenu transakciju na istoj konekciji, `BEGIN` baca
`sqlite3.OperationalError: cannot start a transaction within a transaction`
— ali `except` blok bezuslovno radi `ROLLBACK`, što briše caller-ovu
transakciju (koju runner nikad nije otvorio, pa nema pravo da je poništi).

Reprodukovano: caller otvori transakciju, upiše red, pozove
`run_migrations()` → runner-ov BEGIN padne → runner rollback-uje → caller-ov
red nestane (0 redova umjesto očekivanog 1).

**Fix:** premjestiti `connection.execute("BEGIN")` VAN `try` bloka, tako da
ako BEGIN sam baci, exception propagira odmah bez ulaska u
`except`/`ROLLBACK` granu (runner tada nikad nije "vlasnik" transakcije, pa
nema šta da rollback-uje):

```python
def _apply_migration(connection, migration):
    connection.execute("BEGIN")
    try:
        for statement in _split_statements(migration.sql):
            connection.execute(statement)
        connection.execute(
            "INSERT INTO schema_migrations ..." , (...)
        )
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise
```

## Obavezno

- Dva nova regresiona testa, svaki dokazano FAIL na trenutnom (`92f3917`)
  kodu prije fixa, PASS poslije:
  1. UoW re-use: commit u prvom `with`, drugi `with` bez commit-a mora
     rollback-ovati (izolovan insert iz drugog bloka ne smije preživjeti).
  2. Migration BEGIN failure: caller otvori transakciju + upiše red PRIJE
     `run_migrations()` poziva; runner mora baciti grešku BEZ da dirne
     caller-ov već upisan (necommitovan) red — caller-ov red mora ostati
     vidljiv poslije (na caller je da odluči commit/rollback svoje
     transakcije).
- Zadržati svih 102 postojeća testa zelenih.
- I dalje SAMO fajlovi unutar ACS-P0-006 `allowed_paths`
  (`infrastructure/database/unit_of_work.py`,
  `infrastructure/database/migrations.py`, i pripadajući test fajlovi). Ne
  dirati `_split_statements()`/checksum policy (Codex je potvrdio da nisu
  blocker), ne dirati ACS-P0-005 scope, ne uvoditi generički SQL parser.

## Verification

```bash
cd "H:\ai-campaign-studio-worktrees\ACS-P0-006-sqlite-foundation"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy src
git status --short
```

## Sljedeće

Koordinator provjerava novi delta protiv `92f3917` (ne cijeli task ponovo),
zatim fresh Codex re-review (HIGH task, ostaje na punom ciklusu). Human
Owner merge odluka čeka zatvorene nalaze.
