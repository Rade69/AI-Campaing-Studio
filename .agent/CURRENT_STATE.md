# .agent/CURRENT_STATE.md

Živi status. Ne istorijski arhiv — istorija je u Git-u i `agent_reports/`.
Ažurira koordinator (default Claude) poslije svakog merge-a i svake promjene gate/task stanja.

**Zadnje ažurirano:** 2026-08-30 (coordinator: claude)

---

## Aktivna faza

Implementation Phase 0 — Foundation. Faza 1 je blokirana dok `artifacts/phase0_foundation_gate.json`
ne kaže `{"status": "PASS"}`.

## Aktivni dokumenti

- Arhitektura/proizvod SoT: `AI_Campaign_Studio_Faza_0_6_Channel_Model_LLM_Registry.md`
- Aktivni P0 plan: `AI_Campaign_Studio_Implementation_Phase_0_v1_1_Agent_Workflow_Integrated.md`
  (supersedes `AI_Campaign_Studio_Implementation_Phase_0_Project_Foundation_Agent_Plan.md` — ne koristiti taj)
- Aktivni Faza 1 plan (blokiran do P0-GATE): `AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md`
  (supersedes `AI_Campaign_Studio_Faza_1_v1_3_P0_Handoff_Agent_Ready_Tehnicki_Plan.md`)
- Proces: `docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md`
- GitNexus: `.agent/GITNEXUS_PROTOCOL.md`

## Trenutni P0 gate

NOT STARTED. `artifacts/phase0_foundation_gate.json` ne postoji. Nema koda, nema `src/`, `tests/`,
`pyproject.toml`. Repo je danas prvi put git-inicijalizovan (prije toga samo planning dokumenti,
bez `.git`).

## Aktivni taskovi

| Task | Status | Implementer | Reviewers | Napomena |
|---|---|---|---|---|
| ACS-P0-001 | OPEN — contract spreman, worktree+branch kreirani, čeka implementaciju (Crush) | Crush | Codex, Claude | Repo/tooling/bootstrap skeleton. Nema zavisnosti, prvi unblocked task. Worktree: `../ai-campaign-studio-worktrees/ACS-P0-001-repo-foundation`, branch `task/ACS-P0-001-repo-foundation`, bazirano na `main`@`85c5f41`. |
| ACS-P0-002..008 | BLOCKED | — | — | Čekaju da ACS-P0-001 (pa redom 002) budu stvarno merged u main. Vidi DAG u `.agent/PROJECT_MAP.md` §5. |

## Paralelizacija — trenutna provjera

Samo ACS-P0-001 je unblocked. Nema drugog taska sa disjoint `allowed_paths` spremnog za paralelan
rad u ovom trenutku — 003/004 mogu paralelno tek pošto 002 bude merged, i tek nakon provjere
`allowed_paths` preklapanja (`.agent/TASK_ROUTING.md`).

## Poznati blokatori

- GitNexus MCP je javio `CONNECT_TIMEOUT` u ovoj sesiji — nije required za ACS-P0-001
  (`gitnexus_required: false` u kontraktu), ali mora raditi prije ACS-P0-002 (HIGH, boundary-dirajući).
  Provjeriti/retry-ovati konekciju prije pripreme ACS-P0-002 kontrakta.
- Ova (koordinator) sesija nema direktan CLI pristup pravim Codex/Crush/Pi alatima — koordinator
  priprema worktree, branch i eksplicitna uputstva (Task Contract); Human Owner pokreće
  implementer/reviewer agente eksterno i javlja rezultat/diff nazad koordinatoru.
- `scripts/coordination.py` (claim/status/release) još ne postoji — nastaje kao dio ACS-P0-001/002
  tooling seta; do tada se coordination claim vodi ručno kroz ovaj fajl (jedan aktivan task odjednom,
  pa ovo trenutno nije problem jer je samo 001 unblocked).

## Verification baseline

Nema — nema koda za pokrenuti. Prvi baseline nastaje kad ACS-P0-001 prođe verification set iz svog
Task Contracta (`ruff`, `mypy`, `pytest`, import check).

## GitNexus index status

Nije indeksirano (očekivano — nema još korisnog source graph-a). Odmah nakon merge-a ACS-P0-001:

```bash
npx gitnexus analyze --skip-agents-md
npx gitnexus status
```

pa ažurirati ovu sekciju sa index datumom/statusom.

## Sljedeći task

ACS-P0-001 implementacija u worktree-u `../ai-campaign-studio-worktrees/ACS-P0-001-repo-foundation`,
branch `task/ACS-P0-001-repo-foundation`. Kontrakt: `agent_reports/ACS-P0-001-task-contract.md`.
