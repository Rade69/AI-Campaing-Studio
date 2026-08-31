# .agent/CURRENT_STATE.md

Živi status. Ne istorijski arhiv — istorija je u Git-u i `agent_reports/`.
Ažurira koordinator (default Claude) poslije svakog merge-a i svake promjene gate/task stanja.

**Zadnje ažurirano:** 2026-08-30, poslije merge-a ACS-P0-001 (coordinator: claude)

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

NOT DONE — samo ACS-P0-001 od 8 P0 taskova je merged. `artifacts/phase0_foundation_gate.json` još
ne postoji (gate fajl nastaje tek u ACS-P0-008). Postoji sada: `src/`, `tests/`, `pyproject.toml`,
`.gitignore`, `.venv` (root, editable install), sve zeleno na `main`.

## Aktivni taskovi

| Task | Status | Implementer | Reviewers | Napomena |
|---|---|---|---|---|
| ACS-P0-001 | **DONE — merged u main** | Crush | Codex, Claude | Merge commit `def4ea1` (`--no-ff`, task branch `task/ACS-P0-001-repo-foundation` @ `949d18c`). Reviews: Claude PASS (`agent_reports/2026-08-30-ACS-P0-001-review-claude.md`), Codex PASS_WITH_NOTES (`agent_reports/2026-08-30-ACS-P0-001-review-codex.md`, no blocking findings). Human Owner approval: eksplicitno "Odobravam". Post-merge gate PASS na `main` (import/pytest 3-3/ruff/mypy, Python 3.14.1). Worktree uklonjen (`git worktree remove`), branch `task/ACS-P0-001-repo-foundation` ostavljen netaknut u historiji. |
| ACS-P0-002 | **REJECTED round 3 (Codex) — BF-1 scope-tracking bug, fix round 3 u toku, NE MERGE** | Pi | Codex, Claude | HEAD i dalje `3ab8eb7`. Codex round 3: `agent_reports/2026-08-31-ACS-P0-002-review-codex-round3.md` — svih 9 ranije poznatih oblika ostaju zatvoreni, ali `_collect_import_aliases()` koristi jedan globalni dict bez lexical-scope tracking-a; nepovezan `import X as loader` u jednoj funkciji može pregaziti alias koji stvarno koristi druga funkcija, sakrivajući stvaran forbidden import. Koordinator reprodukovao (`evil()`/`innocent()` primjer) — test PROLAZI kad ne bi trebalo, potvrđeno. Human Owner odluka (2026-08-31): nastaviti fix rundu (ne prihvatati kao dokumentovano ograničenje) jer je ovo stvaran correctness bug, ne samo teoretski slučaj. Fix round 3 brief: `agent_reports/2026-08-31-ACS-P0-002-fix-round3-brief.md` — traži scope-stack (module + per-function) umjesto flat dict-a. |
| ACS-P0-003..008 | BLOCKED | — | — | 003–006 čekaju da 002 bude merged (ne granati prije toga); 007 čeka 003+004+005+006; 008 čeka sve. DAG u `.agent/PROJECT_MAP.md` §5. |

## Paralelizacija — trenutna provjera

Samo ACS-P0-002 je sljedeći unblocked task. Nema kandidata za paralelan rad dok 002 ne bude
merged — 003 i 004 mogu tek tada, uz provjeru `allowed_paths` preklapanja (`.agent/TASK_ROUTING.md`).

## Poznati blokatori

- Proces-learning iz ACS-P0-002: Claude-ov arhitekturni review dao je PASS na
  `test_import_boundaries.py` provjeravajući samo direktne/alias/uslovne import oblike; Codex je
  istim testom otkrio da relative import, dynamic `importlib`/`__import__` sa literal stringom, i
  case-sensitivity bug (`Flask` vs `flask`) prolaze neopaženo. Za buduće boundary/invariant reviewe
  (ACS-P0-003+): Claude mora eksplicitno probati relative importe, dynamic import pozive, i
  case/naming varijante stvarnih modula, ne samo "direct import + alias + conditional" obrazac.
- Ova (koordinator) sesija nema direktan CLI pristup pravim Codex/Crush/Pi alatima — koordinator
  priprema worktree, branch i eksplicitna uputstva (Task Contract); Human Owner pokreće
  implementer/reviewer agente eksterno i javlja rezultat/diff nazad koordinatoru. Za ACS-P0-001 je
  ovaj obrazac funkcionisao (Codex review dobijen i verifikovan).
- `.agent/GITNEXUS_PROTOCOL.md` §9 i workflow §19 referenciraju `npx gitnexus check --cycles --repo .`
  — ta komanda ne postoji u instaliranoj GitNexus CLI verziji (`unknown command 'check'`; stvarne
  komande vidi `npx gitnexus --help`). Cycle-check korak je preskočen post-merge gate-u za ACS-P0-001
  (nebitno za 3 fajla bez međuzavisnosti). Treba ažurirati protokol dokument na stvarne CLI komande
  prije nego što cycle-check postane bitan (ACS-P0-002+, kad se uvode moduli sa međuzavisnostima).
- `scripts/coordination.py` (claim/status/release) još ne postoji. Do sada nije bio problem (uvijek
  samo jedan unblocked task). Postaje relevantno ako se 003–006 pokrenu paralelno.
- GitNexus `detect-changes`/`context`/`impact` binduju se na registrovani glavni checkout, ne na
  linked worktree (`--repo .` iz worktree-a vraća "Repository not found"; iz glavnog checkout-a
  vraća diff glavnog radnog stabla, ne task branch-a). Potvrđeno i od implementera (Pi, ACS-P0-002)
  i od koordinatora — nije izolovan slučaj. `gitnexus_impact` se za MEDIUM/HIGH taskove trenutno
  mora tretirati kao `UNKNOWN` i kompenzovati ručnim diff/file review-om (kao za ACS-P0-002), ne kao
  "nema impacta". Riješiti prije nego što broj paralelnih worktree-ova poraste (ACS-P0-003..006).
- Nekomitovane Performance/Analytics dopune (`AGENTS.md`, `CLAUDE.md`, `.agent/PROJECT_MAP.md`,
  `.agent/TASK_ROUTING.md`, dva nova plan dokumenta) postoje u radnom stablu, dodane iz druge
  sesije — nisu commit-ovane od strane koordinatora, ostavljene netaknute.

## Verification baseline

Uspostavljen na `main` poslije merge-a ACS-P0-001 (2026-08-30, root `.venv`, Python 3.14.1):

```text
import ai_campaign_studio  → OK
python -m pytest -q        → 3 passed
python -m ruff check .     → All checks passed!
python -m mypy src         → Success: no issues found in 3 source files
```

## GitNexus index status

Indeksirano poslije merge-a ACS-P0-001:

```text
Indexed commit: def4ea1 (= trenutni main HEAD)
Status: up-to-date
1678 nodes | 1669 edges | 1 clusters | 0 flows
```

Prije ACS-P0-002 pre-impact-a, ako main odmakne, ponovo pokrenuti `npx gitnexus analyze --skip-agents-md`
pa `npx gitnexus status` da se potvrdi `up-to-date` na trenutnom HEAD-u.

## Sljedeći task

ACS-P0-002 implementacija u worktree-u
`../ai-campaign-studio-worktrees/ACS-P0-002-config-boundaries`, branch
`task/ACS-P0-002-config-boundaries`. Kontrakt: `agent_reports/ACS-P0-002-task-contract.md`.
