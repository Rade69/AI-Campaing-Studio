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
- **A/B evaluation harness (R1 — "je li Campaign Engine stvarno bolji od plain LLM prompta")**
  je već detaljno specificiran u `AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md`
  §47–50 i A16–A20 (Control A/System B skripte, 11 determinističkih metrika, blind human-eval
  rubrika, Kill/Pivot gate). NE pisati novi "evaluation criteria" dokument kad G10 postane
  aktuelan — vidi `.agent/PROJECT_MAP.md` §7 za tačan pointer po sekciji.

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
| ACS-P0-003 | **REJECTED (Codex) — fix runda u toku, NE MERGE** | Pi | Codex, Claude | HEAD i dalje `0c23bcf`. Codex review: `agent_reports/2026-08-31-ACS-P0-003-review-codex.md` — 3 blocking findings, sva potvrđena nezavisno: **BF-1** malformed format template (`"Broken {"`) baca neuhvaćen `ValueError` iz `Translator.t()` (samo `KeyError`/`IndexError` su hvatani); **BF-2** non-string i18n katalog vrijednost (npr. nested dict) prolazi `validate_resources.py` bez greške, pa `Translator.t()` puca sa `AttributeError` kad se pozove `.format()` na non-str; **BF-3** invalid JSON ruši `validate_i18n()` sa neuhvaćenim `JSONDecodeError` jer `_duplicate_keys()` parsira PRIJE postojećeg try/except bloka. Fix brief: `agent_reports/2026-08-31-ACS-P0-003-fix-round-brief.md`. |
| ACS-P0-004 | **DONE — merged u main** | Crush | Codex, Claude | Merge commit `5ecf43f` (`--no-ff`, task branch `task/ACS-P0-004-channel-registry` @ `be3767a`). 3 review runde: Codex REJECT×2 (BF-1..3 pa BF-4, 4 stvarna nalaza — TypeError umjesto RegistryError, mutable "frozen" model, duplicate reference, `or []` falsy-scalar zamka), svaki fix nezavisno re-verifikovan od koordinatora, round 3 `PASS_WITH_NOTES` bez blocking findings. Crush nije predao nijedan self-report kroz cio task — sva evidence rekonstruisana od koordinatora. Finalni decision packet: `agent_reports/2026-08-31-ACS-P0-004-final-decision-packet.md`. Human Owner approval: "odobravam". Post-merge gate PASS na `main` (65 testova, ruff, mypy, health-check). Worktree uklonjen (clean, bez force-a). |
| ACS-P0-005 | **UNBLOCKED, contract nije napisan** | Pi (default) | Codex, Claude (HIGH — SecretStore) | Scope: P0.14–P0.15 (AI Provider/Model Registry + SecretStore). Čeka na Human Owner odluku da li kreće odmah (treći paralelni task) ili poslije 003/004. |
| ACS-P0-006 | **UNBLOCKED, contract nije napisan** | Crush (default) | Codex, Claude (HIGH — SQLite/migrations) | Scope: P0.16–P0.19. Isto pitanje kao 005. |
| ACS-P0-007..008 | BLOCKED | — | — | 007 čeka 003+004+005+006; 008 čeka sve. DAG u `.agent/PROJECT_MAP.md` §5. |

## Paralelizacija — trenutna provjera

ACS-P0-003 i ACS-P0-004 pokrenuti paralelno (2026-08-31) — `allowed_paths` provjereno disjoint;
prvi dokaz da paralelni obrazac radi je uspješan (obje strane review-ovane i jedna već merged,
bez međusobne kolizije). ACS-P0-004 je sada DONE; ACS-P0-003 je jedini preostali aktivan task.
ACS-P0-005/006 su tehnički unblocked ali contract nije napisan — čekaju Human Owner odluku o
redoslijedu (paralelno sa/poslije 003).

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

Uspostavljen na `main` poslije merge-a ACS-P0-004 (2026-08-31, root `.venv`, Python 3.14.1):

```text
import ai_campaign_studio  → OK (0.1.0)
python -m pytest -q        → 65 passed
python -m ruff check .     → All checks passed!
python -m mypy src         → Success: no issues found in 23 source files
python -m ai_campaign_studio.main --health-check → exit 0
```

## CI

`.github/workflows/ci.yml` postoji od 2026-08-31 (dodano ranije nego što plan predviđa za
ACS-P0-008, na osnovu eksterne analize repoa koja je flag-ovala nedostatak CI gate-a).
Pokreće `ruff check .` → `mypy src` → `pytest -q` na `push`/`pull_request` ka `main`, GitHub-ov
Python 3.12 runner (donja granica iz `requires-python`). Prvi run zelen: https://github.com/Rade69/AI-Campaing-Studio/actions
(run `33413783089`, 30s). Ovo NE zamjenjuje ručnu post-merge gate provjeru koordinatora — i dalje
ručno pokretati pun set prije/poslije merge-a, CI je dodatna, ne jedina zaštita (npr. ne pokriva
`--health-check` niti GitNexus korake).

## Repo na GitHub-u

`origin` = `https://github.com/Rade69/AI-Campaing-Studio` (javan repo). `main` i svi task branch-evi
(`task/ACS-P0-001..004`) se guraju poslije svake značajnije izmjene. Historija provjerena na
secrete prije prvog push-a (2026-08-31) — čisto.

## GitNexus index status

Indeksirano poslije merge-a ACS-P0-004:

```text
Indexed commit: 5ecf43f (= trenutni main HEAD)
Status: up-to-date
2428 nodes | 2703 edges | 23 clusters | 10 flows
```

`mcp__gitnexus__*` MCP alati su dostupni u koordinator sesiji (pored CLI), ali dijele istu
worktree-binding limitaciju — vidi blokatore. Prije narednog pre-impact-a, ako main odmakne,
ponovo pokrenuti `npx gitnexus analyze --skip-agents-md` pa `npx gitnexus status`.

## Sljedeći task

ACS-P0-003 (localization) je jedini preostali aktivan task — čeka Codex review (brief poslat,
odgovor nije stigao). ACS-P0-005/006 su unblocked ali contract nije napisan — čekaju Human Owner
odluku o redoslijedu. Prvi paralelni par (003+004) je dokazao da obrazac radi (004 uspješno
merged bez kolizije sa 003) — osnova za odluku o proširenju paralelizma na 005/006.
