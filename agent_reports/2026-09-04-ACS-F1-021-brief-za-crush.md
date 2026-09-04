# → ZA CRUSH — ACS-F1-021 (GenerateSocialPost bez initial Revision)

**Od:** koordinator (Claude) · **Za:** Crush · **Datum:** 2026-09-04

Nezavisan spoljni code review je našao (koordinator nezavisno
reprodukovao) da `GenerateSocialPost` nikad ne kreira `Revision` zapis za
AI-jevu originalnu generaciju posta — `revision_ids` ostaje prazan tuple.
To pogađa `content_revision_id` identitet koji je eksplicitno zaključan
kao potreban prije G10 Analytics (Slice 1.5).

## Prvi korak

Pročitaj kontrakt u cijelosti:
[agent_reports/ACS-F1-021-task-contract.md](agent_reports/ACS-F1-021-task-contract.md)
(`main @ 3d759ac`).

## Kratko, u čemu je bug

`domain/content/entities.py`: `revision_ids: tuple[RevisionId, ...] = ()`
— `GenerateSocialPost.execute()` nikad ga ne postavlja. Kad se post
KASNIJE prvi put revidira (`ReviseContentPiece`), `next_version =
len(existing) + 1` daje `version=1` toj prvoj pravoj izmjeni — kao da je
to originalna verzija, iako je stvarna v1 bila AI generacija.

## Gdje raditi

```text
Worktree: H:\ai-campaign-studio-worktrees\ACS-F1-021-initial-revision
Branch:   task/ACS-F1-021-initial-revision
Base:     main @ 3d759ac
```

Worktree je već kreiran.

```bash
python -m pip install -e . --no-deps -q
```

## Šta uraditi

Kontrakt ima tačan opis (Implementation steps 1-6) — uključujući TAČAN
kod za novi `Revision` objekat (`previous_value=json.dumps(None)`, ne
prazan string, obrazloženje je u kontraktu). Pogledaj
`revise_content_piece.py` kao referencu za pattern (kako se
`RevisionRepositoryPort` već koristi tamo) — NE DIRAJ taj fajl, samo čitaj
kao primjer.

**Najvažniji test koji tražim**: pozovi `GenerateSocialPost` pa onda
`ReviseContentPiece` na ISTOM postu (integration test, prava SQLite baza)
i dokaži da prva prava izmjena dobija `version=2`, ne `version=1`. To je
regresioni dokaz da je bug stvarno zatvoren, ne samo da novi kod
"izgleda ispravno".

## Kad završiš

Evidence izvještaj: `agent_reports/2026-09-04-ACS-F1-021-crush.md` (ne
commit-uj, ostavi u worktree-u, javi mi putanju). MEDIUM risk — nakon mog
review-a, ako PASS, ide direktno na merge (§29, bez Codex runde).
