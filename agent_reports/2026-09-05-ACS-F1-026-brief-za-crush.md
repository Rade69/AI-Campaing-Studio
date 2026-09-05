# → ZA CRUSH — ACS-F1-026 (A/B evaluation harness, G10/A16)

**Od:** koordinator (Claude) · **Za:** Crush · **Datum:** 2026-09-05

Ovo je najveći task otkad si radio content_similarity.py — i direktno se
nadovezuje na njega. Human Owner je odobrio G10 (A/B evaluation harness)
kao dokaz da je Campaign Engine stvarno bolji od golog prompta, ne samo
pretpostavka.

## Prvi korak

Pročitaj kontrakt u cijelosti:
[agent_reports/ACS-F1-026-task-contract.md](agent_reports/ACS-F1-026-task-contract.md)
(`main @ bb88ea9`).

## Najvažnije da ne promakne

- **`resources/prompts/ab_control/v1.yaml` VEĆ POSTOJI** — neko ga je
  pripremio ranije. Koristi ga, ne piši novi prompt.
- **Tvoj `content_similarity.jaccard_similarity` (ACS-F1-025) se ponovo
  koristi** — plan eksplicitno traži "jednostavna lexical/Jaccard
  metrika... heuristic only" za tekst-sličnost, to je tačno tvoja
  funkcija. Uvezi je, ne piši novu.
- **`claim_linter.py`/`claim_validator.py` se ponovo koriste** za
  claim-bazirane metrike — ne izmišljaj paralelnu logiku.
- **`ApproveCampaignPlan` mora biti dio System B toka** — GUI bridge to
  danas NE radi (ACS-GUI-005 samo Create+GeneratePlan), ali System B
  MORA proći kroz odobravanje jer `GenerateSocialPost` zahtijeva
  APPROVED status. Lako je propustiti ovo jer bridge to ne radi — nemoj.
- **`None` vs `0` razlika** za metrike koje nisu mjerljive
  (`layout_failure_count` uvijek `None` jer vizuelni sistem ne postoji;
  `unique_role_count`/`duplicate_topic_count` `None` za Control A jer
  nema role/topic koncept) — nikad lažni "nula" umjesto "nije mjereno".

## Gdje raditi

```text
Worktree: H:\ai-campaign-studio-worktrees\ACS-F1-026-ab-eval-harness
Branch:   task/ACS-F1-026-ab-eval-harness
Base:     main @ bb88ea9
```

Worktree je već kreiran.

```bash
python -m pip install -e . --no-deps -q
```

## Kad završiš

Evidence izvještaj: `agent_reports/2026-09-05-ACS-F1-026-crush.md` (ne
commit-uj, ostavi u worktree-u, javi mi putanju). MEDIUM risk — nakon mog
review-a, ako PASS, ide direktno na merge (§29, bez Codex runde).
