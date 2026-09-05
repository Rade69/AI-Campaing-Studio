# → ZA PI — ACS-F1-027 (human_eval.py, §49)

**Od:** koordinator (Claude) · **Za:** Pi · **Datum:** 2026-09-05

Zadnji poznat komad A16 (G10 A/B evaluation harness) — nakon
`run_control_a`/`run_system_b` (ACS-F1-026, merged), treba slijep paket
za ljudsku ocjenu.

## Prvi korak

Pročitaj kontrakt u cijelosti:
[agent_reports/ACS-F1-027-task-contract.md](agent_reports/ACS-F1-027-task-contract.md)
(`main @ 0be4145`).

## Ključna stvar da ne promakne

Slijep paket ("Campaign X"/"Campaign Y") NE SMIJE sadržati ništa što bi
odalo koje je Control A a koje System B — nema `role`, nema `topic`,
nema `claims`, nema `platform_code`. Samo tekst posta
(headline/caption/hook/body/cta/hashtags). Reveal mapping je POTPUNO
odvojena povratna vrijednost, nikad dio istog objekta koji se
serijalizuje u fajl koji evaluator čita.

Randomizacija MORA ići preko injektovanog `rng` parametra (ne globalni
`random.random()` direktno) — inače test ne može kontrolisati/dokazati
oba moguća ishoda.

## Gdje raditi

```text
Worktree: H:\ai-campaign-studio-worktrees\ACS-F1-027-human-eval-package
Branch:   task/ACS-F1-027-human-eval-package
Base:     main @ 0be4145
```

Worktree je već kreiran.

```bash
python -m pip install -e . --no-deps -q
```

## Kad završiš

Evidence izvještaj: `agent_reports/2026-09-05-ACS-F1-027-pi.md` (ne
commit-uj, ostavi u worktree-u, javi mi putanju). MEDIUM risk — nakon mog
review-a, ako PASS, ide direktno na merge (§29, bez Codex runde).

Nakon merge-a JA ću ručno pokrenuti cijeli A16 lanac (Control A + System
B + tvoj human eval paket) protiv BrightSmile fixture-a sa pravim
provider ključem kao finalnu live verifikaciju — to nije dio tvog posla,
samo da znaš šta slijedi.
