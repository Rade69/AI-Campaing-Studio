# .agent/CURRENT_STATE.md

Živi status. Ne istorijski arhiv — istorija je u Git-u i `agent_reports/`.
Ažurira koordinator (default Claude) poslije svakog merge-a i svake promjene gate/task stanja.

**Zadnje ažurirano:** 2026-08-31, poslije merge-a ACS-P0-002 (coordinator: claude)

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

NOT DONE — ACS-P0-001 i ACS-P0-002 od 8 P0 taskova su merged. `artifacts/phase0_foundation_gate.json`
još ne postoji (gate fajl nastaje tek u ACS-P0-008). `src/ai_campaign_studio/` sada ima
`config/`, `logging/`, `domain/common/`, prazne `application/`/`ports/`/`presentation/` seam-ove, i
`tests/architecture/test_import_boundaries.py` (prvi automatski architecture-boundary invariant).

## Aktivni taskovi

| Task | Status | Implementer | Reviewers | Napomena |
|---|---|---|---|---|
| ACS-P0-001 | **DONE — merged u main** | Crush | Codex, Claude | Merge commit `def4ea1` (`--no-ff`, task branch `task/ACS-P0-001-repo-foundation` @ `949d18c`). Reviews: Claude PASS, Codex PASS_WITH_NOTES (no blocking findings). Human Owner approval: "Odobravam". Post-merge gate PASS. Worktree uklonjen. |
| ACS-P0-002 | **DONE — merged u main** | Pi | Codex, Claude | Merge commit `e187a56` (`--no-ff`, task branch `task/ACS-P0-002-config-boundaries` @ `d6dc783`). 5 review rundi: Codex REJECT×4 (BF-1: boundary-checker bypassi pa lexical/class-scope resolution bugovi), svaki fix nezavisno re-verifikovan od koordinatora (kombinovana adversarial reprodukcija do 11 bypass/scope oblika u finalnoj rundi), round 5 `PASS_WITH_NOTES` bez blocking findings. Finalni decision packet: `agent_reports/2026-08-31-ACS-P0-002-final-decision-packet.md` (READY FOR HUMAN APPROVAL, R1–R6 reziduelni rizici). Human Owner approval: "Slažem se". Post-merge gate PASS na `main` (43 testa, ruff, mypy, health-check, Python 3.14.1). Worktree uklonjen (`--force`, samo Pi-jevi već-inkorporirani raw report fajlovi izgubljeni, bez sadržajnog gubitka). |
| ACS-P0-003 | IMPLEMENTED, Claude review PASS, čeka Codex review + Human Owner approval | Pi | Codex, Claude (elevated §4) | Commit `0c23bcf` na `task/ACS-P0-003-localization`. Evidence: `agent_reports/2026-08-31-ACS-P0-003-pi-confirmed.md`. Claude review: `agent_reports/2026-08-31-ACS-P0-003-review-claude.md` (PASS). Codex brief: `agent_reports/2026-08-31-ACS-P0-003-codex-review-request.md`. Oba adversarial dokaza (translator fallback, i18n key-parity) potvrđena nezavisno od koordinatora u svježem worktree `.venv`-u. |
| ACS-P0-004 | **OPEN — contract spreman, worktree+branch kreirani, čeka implementaciju (Crush)** | Crush | Codex, Claude (elevated §4 — registry contract) | Scope: P0.13. Kontrakt: `agent_reports/ACS-P0-004-task-contract.md`. Worktree `../ai-campaign-studio-worktrees/ACS-P0-004-channel-registry`, branch `task/ACS-P0-004-channel-registry` od `main@a712ce3`. Paralelno sa 003. `scripts/validate_resources.py` namjerno SAMO u 003 da se allowed_paths ne preklope. `adversarial_required: true` (duplicate-code rejection + unknown-format-reference rejection). |
| ACS-P0-005 | **UNBLOCKED, contract nije napisan** | Pi (default) | Codex, Claude (HIGH — SecretStore) | Scope: P0.14–P0.15 (AI Provider/Model Registry + SecretStore). Čeka na Human Owner odluku da li kreće odmah (treći paralelni task) ili poslije 003/004. |
| ACS-P0-006 | **UNBLOCKED, contract nije napisan** | Crush (default) | Codex, Claude (HIGH — SQLite/migrations) | Scope: P0.16–P0.19. Isto pitanje kao 005. |
| ACS-P0-007..008 | BLOCKED | — | — | 007 čeka 003+004+005+006; 008 čeka sve. DAG u `.agent/PROJECT_MAP.md` §5. |

## Paralelizacija — trenutna provjera

ACS-P0-003 i ACS-P0-004 pokrenuti paralelno (2026-08-31) — `allowed_paths` provjereno disjoint
(vidi njihove kontrakte); jedina inicijalna kolizija (`scripts/validate_resources.py` u oba) je
riješena prije kreiranja worktree-ova dodjelom fajla isključivo ACS-P0-003. ACS-P0-005/006 su
tehnički unblocked ali contract nije napisan — čekaju Human Owner odluku o redoslijedu (treći/četvrti
paralelni task ili sekvencijalno poslije 003/004).

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

Uspostavljen na `main` poslije merge-a ACS-P0-002 (2026-08-31, root `.venv`, Python 3.14.1):

```text
import ai_campaign_studio  → OK (0.1.0)
python -m pytest -q        → 43 passed
python -m ruff check .     → All checks passed!
python -m mypy src         → Success: no issues found in 18 source files
python -m ai_campaign_studio.main --health-check → exit 0
```

## GitNexus index status

Indeksirano poslije merge-a ACS-P0-002:

```text
Indexed commit: e187a56 (= trenutni main HEAD)
Status: up-to-date
2106 nodes | 2215 edges | 11 clusters | 1 flows
```

`mcp__gitnexus__*` MCP alati su sada dostupni u koordinator sesiji (pored CLI), ali dijele istu
worktree-binding limitaciju — vidi blokatore. Prije ACS-P0-003+ pre-impact-a, ako main odmakne,
ponovo pokrenuti `npx gitnexus analyze --skip-agents-md` pa `npx gitnexus status`.

## Sljedeći task

Nema jednog "sljedećeg" — ACS-P0-003, 004, 005 i 006 su svi unblocked (vidi tabelu iznad). Koordinator
treba: (1) odlučiti redoslijed/paralelizam sa Human Ownerom, (2) provjeriti `allowed_paths` disjoint
za bilo koji par pokrenut paralelno, (3) GitNexus pre-impact prije svakog Task Contracta (HIGH taskovi
005/006 to zahtijevaju eksplicitno), (4) pripremiti worktree/branch/contract po istom obrascu kao
001/002.
