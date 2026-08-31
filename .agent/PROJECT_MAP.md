# .agent/PROJECT_MAP.md — AI Campaign Studio

Statička mapa: šta postoji, šta je predviđeno, gdje živi koji dokument.
Za trenutno aktivan task/gate stanje vidi `.agent/CURRENT_STATE.md`.

---

## 1. Doc index (source of truth po sloju)

| Dokument | Uloga | Autoritet |
|---|---|---|
| `AI_Campaign_Studio_Faza_0_6_Channel_Model_LLM_Registry.md` | arhitektonska/proizvodna osnova cijelog projekta | najviši (poslije Human Owner odluke) |
| `AI_Campaign_Studio_Faza_0_7_Performance_Analytics_Architecture.md` | Performance/Analytics arhitektonska dopuna Faze 0.6; zaključava seam-ove sada, runtime modul kasnije | Analytics architecture SoT |
| `AI_Campaign_Studio_Implementation_Phase_0_v1_1_Agent_Workflow_Integrated.md` | aktivni P0 izvršni plan (supersedes ne-v1.1 varijantu) | P0 execution SoT |
| `AI_Campaign_Studio_Implementation_Phase_0_Project_Foundation_Agent_Plan.md` | superseded — istorijski, ne koristiti kao SoT | referenca samo |
| `AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md` | aktivni Faza 1 plan (supersedes v1.3), blokiran dok P0-GATE != PASS | Faza 1 execution SoT |
| `AI_Campaign_Studio_Faza_1_v1_5_Analytics_Ready_Implementation_Plan.md` | analytics-ready dopuna v1.4: stable IDs + revision/target identity + export manifest; Slice 1.5 poslije G10 | Analytics implementation SoT |
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

## 6. Performance / Analytics — planirana granica i trenutak implementacije

Analytics je arhitektonski planiran sada, ali **nije P0 runtime scope**.

Source of truth:

```text
AI_Campaign_Studio_Faza_0_7_Performance_Analytics_Architecture.md
AI_Campaign_Studio_Faza_1_v1_5_Analytics_Ready_Implementation_Plan.md
```

Redoslijed:

```text
P0 Foundation
→ Faza 1 Campaign Engine
→ G10 Vertical Slice PASS
→ Slice 1.5 Performance Foundation
→ Slice 2 Brand / Website Ingestion
```

### Faza 1 mora pripremiti prije Slice 1.5

Bez Performance tabela/UI/API-ja:

```text
Campaign.id
CampaignPlan.id
CampaignItem.id
ContentPiece.id
Revision.id / content revision identity
Channel / Platform / Format target identity
manifest.json u exportu
analytics_match_key
```

### Slice 1.5 uvodi

```text
DistributionInstance
PerformanceSnapshot
PerformanceImportBatch
canonical metric calculator
CSV/manual performance import
deterministički matching
Campaign Performance read model/UI
Content Performance read model/UI
```

Direktne Meta/TikTok/LinkedIn/Google Ads integracije i AI performance learning dolaze tek kasnije,
nakon dokazane upotrebe osnovnog Performance modula.

Za svaki Performance/Analytics task koristiti `.agent/TASK_ROUTING.md` sekciju
**Performance / Analytics task**.

## 7. A/B evaluation harness — gdje živi (ne pisati novi dokument)

Krajnji dokaz Faze 1 ("Campaign Engine B mora biti mjerljivo i ljudski ocijenjeno bolji od
single-prompt kontrole A") je već detaljno operacionalizovan u
`AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md` — ne treba novi dokument niti
ponovo izmišljati kriterijume kad G10 postane aktuelan. Tačna mjesta:

```text
§47 A/B kontrola          — run_control_a.py (jedan AI poziv, bez CampaignRole/fact-selection/
                             plan-review) vs System B (puni pipeline)
§48 Determinističke metrike — deterministic_metrics.py: unique_role_count, duplicate_topic_count,
                             exact_duplicate_caption_count, unsupported_fact_claim_count,
                             forbidden_phrase_hits, numeric_claim_violations, missing_fact_ids,
                             schema_failure_count, layout_failure_count, headline_overflow_count,
                             cta_unique_count
§49 Human evaluation       — human_eval.py, blind A/B (evaluator ne zna koje je koje), rubrika 1–5:
                             Brand fit, Language naturalness, Campaign coherence, Post diversity,
                             Usefulness, Visual consistency
§50 Kill/Pivot gate        — System B mora pokazati: manje unsupported claims, veću coherence,
                             bolju post diversity, barem jednaku naturalness, prihvatljiv
                             latency/stability — inače se NE ide na Slice 2, prvo se revidira
                             core (CampaignRole rules, prompt design, fact selection, brief
                             schema, post generation contract), ne dodaje RAG/više agenata
A16–A20 (task lista)       — acceptance kriterijumi za harness/UI spike/production adapter/
                             full slice integration/exit evaluation (PASS→Slice 2, FAIL→iteracija)
G10                        — Vertical Slice Integration Gate: fixture → brief → plan → review →
                             posts → validation → render → export, uz A/B poređenje
```

Ako neko (agent ili Human Owner) razmatra pisanje novog "evaluation criteria" dokumenta za R1
(da li je Campaign Engine stvarno bolji od plain LLM prompta) — prvo pročitati ova mjesta. Novi
dokument bi kršio AR4 ("Jedan source of truth po konceptu") iz Faze 1 v1.4 §4.
