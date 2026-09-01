# Codex review request — ACS-P0-006

Za: Codex (adversarial/test reviewer)
Od: Claude (koordinator)
Datum: 2026-09-01

## Kontekst

Paralelni task uz ACS-P0-005 (AI Registry + SecretStore, review se vodi
odvojeno). `allowed_paths` su disjoint. Implementer (Crush) nije predao
formalni self-report (isti obrazac kao ACS-P0-001/004) — koordinator je
rekonstruisao evidence direktno iz koda i komandi, uključujući izvršenje
oba obavezna adversarial dokaza.

## Read protocol

1. `AGENTS.md`, `CLAUDE.md`
2. `docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md` §14/§15
3. `.agent/CURRENT_STATE.md`
4. `agent_reports/ACS-P0-006-task-contract.md`
5. `agent_reports/2026-09-01-ACS-P0-006-crush-confirmed.md` (coordinator evidence)
6. Sam diff (vidi ispod)

## Šta pregledati

```text
Repo:     H:\AI Campaing Studio  (main branch)
Worktree: H:\ai-campaign-studio-worktrees\ACS-P0-006-sqlite-foundation
Branch:   task/ACS-P0-006-sqlite-foundation
Commit:   92f3917 (base: main@820bbf9)
```

```bash
git -C "H:\AI Campaing Studio" diff main task/ACS-P0-006-sqlite-foundation --stat
git -C "H:\AI Campaing Studio" diff main task/ACS-P0-006-sqlite-foundation
```

Koristi merge-base diff za čist prikaz ako je main odmakao:
`git diff $(git merge-base main task/ACS-P0-006-sqlite-foundation) task/ACS-P0-006-sqlite-foundation`.
Svi fajlovi ovog taska su NOVI. GitNexus `detect-changes` iz worktree-a neće
raditi (poznato ograničenje) — tretiraj kao `UNKNOWN`.

## Napomena o environment-u

Fresh `.venv` je imao isti oštećen `pydantic_core` wheel viđen na
ACS-P0-004 — riješeno sa `pip install --force-reinstall --no-cache-dir
pydantic pydantic-core mypy`. Ako naiđeš na isto, isti fix bi trebalo da
pomogne.

## Fokus review-a

1. **Migration runner transaction/rollback korektnost** — `_apply_migration()`
   koristi `try: BEGIN...COMMIT except: ROLLBACK; raise`. Provjeri: da li
   postoji scenario gdje `connection.execute("ROLLBACK")` sam baci
   exception (npr. ako BEGIN nikad nije uspio) i ostavi konekciju u čudnom
   stanju? Da li `_ensure_schema_migrations()` (izvan transakcije, autocommit)
   može kreirati `schema_migrations` tabelu ali onda prva migracija padne na
   pola — je li DB stanje i dalje konzistentno za sljedeći run?
2. **Checksum algoritam** — `_checksum()` je sha256 nad `migration.sql`
   RAW sadržajem fajla (uključujući whitespace/line-endings). Provjeri: da
   li CRLF vs LF razlika u istom logičkom SQL-u (npr. git checkout na
   Windows sa `autocrlf`) može izazvati lažan "checksum mismatch" na
   identičnom migration fajlu? Ovo je repo koji već koristi CRLF
   normalizaciju (`.gitattributes`/autocrlf upozorenja vidljiva u svakom
   git komandu ove sesije) — realan rizik vrijedan provjere.
3. **`_split_statements()` naivni `;` split** — već zabilježeno kao
   ne-blocking opservacija u Claude reviewu. Probaj naći realan scenario
   gdje bi ovo bilo pravi problem za TRENUTNI `0000_foundation.sql` (ne
   hipotetički budući SQL) — ako nema, potvrdi da je opservacija, ne
   blocker.
4. **UoW edge case** — `SqliteUnitOfWork.__enter__` radi `BEGIN`
   bezuslovno. Šta ako se ista `UnitOfWork` instanca uđe dva puta (nested
   `with`, ili re-entry poslije prvog `commit()`)? Provjeri da li postoji
   realan double-BEGIN/double-commit rizik u očekivanom pattern-u korištenja
   (kontrakt ne traži nested support, ali provjeri da barem ne puca na
   nejasan način).
5. **Regresija** — 102 testa. Ponovo pokreni:
   ```bash
   cd "H:\ai-campaign-studio-worktrees\ACS-P0-006-sqlite-foundation"
   .\.venv\Scripts\python.exe -m pytest -q
   .\.venv\Scripts\python.exe -m ruff check .
   .\.venv\Scripts\python.exe -m mypy src
   ```
6. **Scope-clean diff?** (10 novih fajlova, sve u `allowed_paths`, ništa u
   paralelnom ACS-P0-005 scope-u).

## Traženi output

`agent_reports/2026-09-01-ACS-P0-006-review-codex.md`, isti format kao
`agent_reports/2026-09-01-ACS-P0-006-review-claude.md`.

Ako `PASS`/`PASS_WITH_NOTES` bez blocking findings, tražim Human Owner
odobrenje za merge (nezavisno od ACS-P0-005 statusa).
