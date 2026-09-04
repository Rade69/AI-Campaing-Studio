# → ZA MINIMAX — ACS-GUI-006 (orphan DRAFT kampanja kompenzaciono brisanje)

**Od:** koordinator (Claude) · **Za:** MiniMax · **Datum:** 2026-09-04

Ovo je tvoj vlastiti nalaz iz samo-pregleda ACS-GUI-005 — hvala na tome.
ACS-F1-024 (provider fallback) je mergovan, pa je red na ovo (dijelili
ste isti `bridge/__init__.py` fajl, namjerno sekvencirano da se izbjegne
konflikt).

## Prvi korak

Pročitaj kontrakt u cijelosti:
[agent_reports/ACS-GUI-006-task-contract.md](agent_reports/ACS-GUI-006-task-contract.md)
(`main @ 4cbb67d`).

## Kratko, šta treba

Ako `GenerateCampaignPlan` padne (nakon što je `CreateCampaign` već
commit-ovao svoju odvojenu transakciju), bridge treba pokušati obrisati
tu orphan DRAFT kampanju kao kompenzacionu akciju — best-effort, ne
smije maskirati originalnu `GENERATION_FAILED` grešku ako brisanje samo
ne uspije.

**Ovo je PRVA delete metoda u cijelom repository/port sloju** — projekat
je do sada čist append-only. Kontrakt eksplicitno traži da
`CampaignRepositoryPort.delete_campaign` docstring jasno ograniči namjenu
(kompenzaciona akcija, ne opšta "obriši kampanju" funkcija) — pazi na to,
biće fokus review-a.

## Gdje raditi

```text
Worktree: H:\ai-campaign-studio-worktrees\ACS-GUI-006-orphan-campaign-cleanup
Branch:   task/ACS-GUI-006-orphan-campaign-cleanup
Base:     main @ 4cbb67d
```

Worktree je već kreiran.

```bash
python -m pip install -e . --no-deps -q
```

## Kad završiš

Evidence izvještaj: `agent_reports/2026-09-04-ACS-GUI-006-minimax.md` (ne
commit-uj, ostavi u worktree-u, javi mi putanju). MEDIUM risk — nakon mog
review-a, ako PASS, ide direktno na merge (§29, bez Codex runde).
