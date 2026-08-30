# .agent/PROJECT_MAP.md — AI Campaign Studio

Statička mapa: šta postoji, šta je predviđeno, gdje živi koji dokument.
Za trenutno aktivan task/gate stanje vidi `.agent/CURRENT_STATE.md`.

---

## 1. Doc index (source of truth po sloju)

| Dokument | Uloga | Autoritet |
|---|---|---|
| `AI_Campaign_Studio_Faza_0_6_Channel_Model_LLM_Registry.md` | arhitektonska/proizvodna osnova cijelog projekta | najviši (poslije Human Owner odluke) |
| `AI_Campaign_Studio_Implementation_Phase_0_v1_1_Agent_Workflow_Integrated.md` | aktivni P0 izvršni plan (supersedes ne-v1.1 varijantu) | P0 execution SoT |
| `AI_Campaign_Studio_Implementation_Phase_0_Project_Foundation_Agent_Plan.md` | superseded — istorijski, ne koristiti kao SoT | referenca samo |
| `AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md` | aktivni Faza 1 plan (supersedes v1.3), blokiran dok P0-GATE != PASS | Faza 1 execution SoT |
| `AI_Campaign_Studio_Faza_1_v1_3_P0_Handoff_Agent_Ready_Tehnicki_Plan.md` | superseded — istorijski, ne koristiti kao SoT | referenca samo |
| `docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md` | kanonski agentski proces (risk tier, review, GitNexus, merge) | proces SoT |
| `.agent/GITNEXUS_PROTOCOL.md` | GitNexus hard-gate protokol | proces SoT (GitNexus dio) |
| `AGENTS.md` / `CLAUDE.md` | thin router-i, prvi ulaz za agente | routing only, ne duplirati sadržaj ovdje |

## 2. Fizička struktura repoa (trenutno stanje)

```text
.
├── AGENTS.md
├── CLAUDE.md
├── AI_Campaign_Studio_Faza_0_6_Channel_Model_LLM_Registry.md
├── AI_Campaign_Studio_Faza_1_v1_3_P0_Handoff_Agent_Ready_Tehnicki_Plan.md      (superseded)
├── AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md                 (active)
├── AI_Campaign_Studio_Implementation_Phase_0_Project_Foundation_Agent_Plan.md  (superseded)
├── AI_Campaign_Studio_Implementation_Phase_0_v1_1_Agent_Workflow_Integrated.md (active)
├── docs/
│   └── AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md
├── .agent/
│   ├── GITNEXUS_PROTOCOL.md
│   ├── CURRENT_STATE.md
│   ├── PROJECT_MAP.md   (ovaj fajl)
│   └── TASK_ROUTING.md
└── agent_reports/
    └── ACS-P0-001-task-contract.md
```

Nema još: `src/`, `tests/`, `pyproject.toml`, `.gitignore`, `scripts/coordination.py`, `artifacts/`.
Ovi nastaju kroz ACS-P0-001 i naredne P0 taskove — vidi sekciju 3.

## 3. Ciljna struktura poslije P0 (iz Implementation Phase 0 v1.1 + Faza 0.6)

```text
src/ai_campaign_studio/
├── __init__.py
├── main.py
├── bootstrap.py                  (composition root — bez business logike u P0-001)
├── domain/
│   ├── brand/                    (kasnije, ne u P0-001)
│   ├── campaign/                 (kasnije, ne u P0-001)
│   └── content/                  (kasnije, ne u P0-001)
├── application/                  (use cases, kasnije)
├── ports/                        (kasnije)
├── infrastructure/
│   └── ai/                       (provider SDK adapteri, kasnije, ne u P0-001)
presentation_qt/                  (kasnije, dok UI-GATE ne prođe)
presentation_webview/             (kasnije, kontrolni kandidat)
tests/
artifacts/
    .gitkeep
```

Arhitektonski smjer (Clean/Hexagonal):

```text
Presentation → Application/Use Cases → Domain ← Ports ← Infrastructure adapters
```

`domain/`, `infrastructure/ai/`, `presentation_qt/`, `presentation_webview/` su eksplicitno `forbidden_paths` u ACS-P0-001 — ne diraju se u foundation tasku.

## 4. Paket i tooling (P0.04–P0.05 target)

- Paket: `ai_campaign_studio`, src-layout, Python 3.12+.
- Bez PySide6/pywebview/provider SDK dependency-ja u P0-001.
- Standardni P0 verification set: `ruff`, `mypy`, `pytest`, `scripts/validate_resources.py`, `--health-check`.

## 5. P0 task paketi → fajl/scope (iz workflow doc §22–23)

| Task | Scope (P0.xx) | Implementer default | Risk | Zavisi od |
|---|---|---|---|---|
| ACS-P0-001 | P0.00–P0.05 repo/tooling/bootstrap skeleton | Crush | MEDIUM | — |
| ACS-P0-002 | P0.06–P0.10 config/logging/common + arch boundaries | Pi | HIGH (foundation) | 001 |
| ACS-P0-003 | P0.11–P0.12 localization + regional resources | Pi | — | 002 |
| ACS-P0-004 | P0.13 Channel/Platform/Format registry | Crush | — | 002 |
| ACS-P0-005 | P0.14–P0.15 AI Provider/Model Registry + SecretStore | Pi | HIGH | 002 |
| ACS-P0-006 | P0.16–P0.19 SQLite + migrations + UoW | Crush | HIGH | 002 |
| ACS-P0-007 | P0.20–P0.23 Jobs + Presentation contracts + Bootstrap | Pi | HIGH | 003,004,005,006 |
| ACS-P0-008 | P0.24–P0.30 Validators + CI + security + P0 gate | Crush | HIGH | sve prethodne |

DAG: `001 → 002 → {003,004,005,006} → 007 → 008 → P0-GATE PASS`. 003–006 se ne granaju dok 002 nije stvarno merged u main.
