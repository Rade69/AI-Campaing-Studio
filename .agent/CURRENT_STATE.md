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
- Performance/Analytics arhitektonska dopuna: `AI_Campaign_Studio_Faza_0_7_Performance_Analytics_Architecture.md`
  - dopunjuje Fazu 0.6 samo za Performance/Analytics odluke;
  - sada zaključava anti-refactor seam-ove, ali NE pokreće Analytics runtime implementaciju u P0.
- Analytics-ready Faza 1 dopuna: `AI_Campaign_Studio_Faza_1_v1_5_Analytics_Ready_Implementation_Plan.md`
  - dopunjuje aktivni Faza 1 v1.4 plan;
  - prije Slice 1.5 uvodi samo stable IDs, revision/target identity, export manifest i `analytics_match_key`;
  - stvarni Performance modul počinje tek poslije potvrđenog `G10 Vertical Slice PASS`.

## Performance / Analytics status

```text
ARCHITECTURE: LOCKED / PLANNED
RUNTIME ANALYTICS IMPLEMENTATION: NOT STARTED
```

Tačan redoslijed:

```text
P0 Foundation
→ Faza 1 Campaign Engine
→ G10 Vertical Slice PASS
→ Slice 1.5 Performance Foundation
→ Slice 2 Brand / Website Ingestion
```

Analytics se **NE implementira sada u P0**.

Prije Slice 1.5 Faza 1 mora samo sačuvati seam-ove koji sprečavaju kasniji veliki refaktor:

```text
campaign_id
campaign_plan_id
campaign_item_id
content_piece_id
content_revision_id
channel_code / platform_code / format_code
export manifest.json
analytics_match_key
```

Kada `G10 = PASS`, koordinator mijenja ovaj status u `SLICE 1.5 ACTIVE`. Od tog trenutka svaki
Performance/Analytics Task Contract mora slijediti `.agent/TASK_ROUTING.md` sekciju
**Performance / Analytics task**.

## Trenutni P0 gate

NOT STARTED. `artifacts/phase0_foundation_gate.json` ne postoji. Nema koda, nema `src/`, `tests/`,
`pyproject.toml`. Repo je danas prvi put git-inicijalizovan (prije toga samo planning dokumenti,
bez `.git`).

## Aktivni taskovi

| Task | Status | Implementer | Reviewers | Napomena |
|---|---|---|---|---|
| ACS-P0-001 | REVIEWS COMPLETE (Claude PASS, Codex PASS_WITH_NOTES, no blocking findings) — čeka eksplicitno Human Owner odobrenje za merge | Crush | Codex, Claude | Repo/tooling/bootstrap skeleton. Commit `949d18c` na branch `task/ACS-P0-001-repo-foundation`. Evidence: `agent_reports/2026-08-30-ACS-P0-001-crush.md`. Claude review: `agent_reports/2026-08-30-ACS-P0-001-review-claude.md` (PASS). Codex review: `agent_reports/2026-08-30-ACS-P0-001-review-codex.md` (PASS_WITH_NOTES — jedina napomena je sandbox-specifičan mypy cache write izvan dozvoljenog root-a, bez nalaza u kodu; potvrđeno da testovi nisu placeholderi i da `main()` ne guta bootstrap grešku). Sljedeći korak: Human Owner "odobreno/merge" pa coordinator merge + post-merge gate + inicijalni GitNexus index. |
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
