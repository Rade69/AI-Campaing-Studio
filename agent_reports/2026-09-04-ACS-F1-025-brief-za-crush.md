# → ZA CRUSH — ACS-F1-025 (provjera sličnosti objava u kampanji)

**Od:** koordinator (Claude) · **Za:** Crush · **Datum:** 2026-09-04

Human Owner je ovo lično odobrio kao prioritet, prije nastavka GUI
bridge rada — gađa originalni strah koji je pokrenuo cijeli razgovor o
smislenosti aplikacije: da AI generiše hrpu generičkih, međusobno skoro
identičnih objava. Trenutno ništa ne provjerava stvaran tekst dvije
objave, samo da li su im uloge (roles) različite na nivou plana.

## Prvi korak

Pročitaj kontrakt u cijelosti:
[agent_reports/ACS-F1-025-task-contract.md](agent_reports/ACS-F1-025-task-contract.md)
(`main @ 1ef79aa`).

## Kratko, šta treba

Novi čist modul `content_similarity.py` (Jaccard sličnost nad skupom
riječi, stdlib, bez embeddings) + poziv u `generate_social_post.py`
nakon generisanja: uporedi novi post sa SVIM postojećim objavama u istoj
kampanji (`content_repo.list_campaign_content(campaign_id)` — VEĆ
POSTOJI, ne treba novi port metod). Ako je sličnost iznad praga (0.6),
novi post dobija `NEEDS_REVIEW`.

**Bitno**: jednosmjerno — samo NOVI post se ocjenjuje, postojeće objave
se NIKAD ne diraju/re-snimaju. Bez novog polja na `ContentPiece`
(`domain/` je forbidden) — status je dovoljan signal za sada, "sa kojim
postom je sličan" ostaje za budući GUI task.

## Gdje raditi

```text
Worktree: H:\ai-campaign-studio-worktrees\ACS-F1-025-content-similarity
Branch:   task/ACS-F1-025-content-similarity
Base:     main @ 1ef79aa
```

Worktree je već kreiran.

```bash
python -m pip install -e . --no-deps -q
```

## Kad završiš

Evidence izvještaj: `agent_reports/2026-09-04-ACS-F1-025-crush.md` (ne
commit-uj, ostavi u worktree-u, javi mi putanju). MEDIUM risk — nakon mog
review-a, ako PASS, ide direktno na merge (§29, bez Codex runde).
