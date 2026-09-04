# → ZA MINIMAX — ACS-F1-022 (role_sequence nikad enforced)

**Od:** koordinator (Claude) · **Za:** MiniMax · **Datum:** 2026-09-04

Treći, temeljitiji spoljni code review prolaz je našao (koordinator
nezavisno potvrdio) da `CampaignTemplate.role_sequence` — struktura koja
razlikuje ovaj alat od generičkog prompta — nikad se stvarno ne
provjerava protiv generisanog plana. Jedina domain provjera je "bar 2
različite uloge od bilo koje od 17", ne "uloge pripadaju template-u".

## Prvi korak

Pročitaj kontrakt u cijelosti:
[agent_reports/ACS-F1-022-task-contract.md](agent_reports/ACS-F1-022-task-contract.md)
(`main @ 1d4c177`).

## Ključna dizajn odluka (već zaključana u kontraktu, ne improvizuj)

Ovo je **subset provjera**, NE exact-match niti provjera redoslijeda —
`content_piece_count` (npr. 3) je tipično MANJI od
`len(LEAD_GENERATION_V1.role_sequence)` (7), pa AI legitimno bira podskup
uloga. Ne uvoditi provjeru reda.

## Gdje raditi

```text
Worktree: H:\ai-campaign-studio-worktrees\ACS-F1-022-role-sequence-enforcement
Branch:   task/ACS-F1-022-role-sequence-enforcement
Base:     main @ 1d4c177
```

Worktree je već kreiran.

```bash
python -m pip install -e . --no-deps -q
```

## Kad završiš

Evidence izvještaj: `agent_reports/2026-09-04-ACS-F1-022-minimax.md` (ne
commit-uj, ostavi u worktree-u, javi mi putanju). MEDIUM risk — nakon mog
review-a, ako PASS, ide direktno na merge (§29, bez Codex runde).

Ovo ide paralelno sa ACS-F1-023 (Crush, UNIQUE indeksi) i ACS-F1-020
(Pi, claim_linter fix runda) — disjoint fajlovi, nema koordinacije
potrebne među vama.
