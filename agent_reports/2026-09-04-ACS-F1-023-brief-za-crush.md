# → ZA CRUSH — ACS-F1-023 (nema UNIQUE constraint-a u šemi)

**Od:** koordinator (Claude) · **Za:** Crush · **Datum:** 2026-09-04

Treći, temeljitiji spoljni code review prolaz je našao (koordinator
nezavisno potvrdio, `grep -rn "UNIQUE" resources/migrations/*.sql` → nula
pogodaka) da cijela SQL šema nema nijedan UNIQUE constraint. Konkretno:
`revisions` versioning se računa u Python-u
(`len(existing) + 1`, iz tvog ACS-F1-021 rada), ništa to ne štiti na
nivou baze; `campaign_items."order"` unutar plana provjerava se samo u
use-case sloju.

## Prvi korak

Pročitaj kontrakt u cijelosti:
[agent_reports/ACS-F1-023-task-contract.md](agent_reports/ACS-F1-023-task-contract.md)
(`main @ 1d4c177`).

## Kratko, šta treba

Nova append-only migracija `resources/migrations/0004_uniqueness_constraints.sql`
sa TAČNO dva `CREATE UNIQUE INDEX` iskaza (SQLite nema `ALTER TABLE ADD
CONSTRAINT`) — kontrakt ima tačan SQL. Provjerio sam UNAPRIJED da ovo
neće pokvariti postojeće upsert putanje (`save_revision` konfliktuje na
`id`, ne na `(entity_type, entity_id, version)`; `save_plan` radi
delete-and-reinsert unutar iste transakcije) — detalji u kontraktu.

## Gdje raditi

```text
Worktree: H:\ai-campaign-studio-worktrees\ACS-F1-023-unique-constraints
Branch:   task/ACS-F1-023-unique-constraints
Base:     main @ 1d4c177
```

Worktree je već kreiran.

```bash
python -m pip install -e . --no-deps -q
```

## Važna napomena

Ako novi indeks otkrije da neki POSTOJEĆI test fixture pravi duplikate
(padne postojeći test) — NE MIJENJAJ indeks da test prođe. To je nalaz
(test fixture pravi podatke koje šema sad ispravno odbija), javi meni.

## Kad završiš

Evidence izvještaj: `agent_reports/2026-09-04-ACS-F1-023-crush.md` (ne
commit-uj, ostavi u worktree-u, javi mi putanju). MEDIUM risk — nakon mog
review-a, ako PASS, ide direktno na merge (§29, bez Codex runde). Prije
finalnog merge-a ja ću i sam primijeniti migraciju protiv svoje postojeće
lokalne dev baze da potvrdim da nema već-postojećih duplikata.

Ovo ide paralelno sa ACS-F1-022 (MiniMax, role_sequence) i ACS-F1-020
(Pi, claim_linter fix runda) — disjoint fajlovi, nema koordinacije
potrebne među vama.
