# .agent/CURRENT_STATE.md

Živi status. Ne istorijski arhiv — istorija je u Git-u i `agent_reports/`.
Ažurira koordinator (default Claude) poslije svakog merge-a i svake promjene gate/task stanja.

**Zadnje ažurirano:** 2026-09-01 (coordinator: claude) — Codex round 2 PASS_WITH_NOTES za BF-1/BF-2; BF-3 (provider-coverage gap) + _KEY_VALUE bug riješeni, čeka lean Codex round 3. AGENTS.md ispravljen (§29 sync). SPIKE-001 (pywebview) otvoren paralelno.

---

## Review politika (Human Owner odluka, 2026-09-01) — PROVJERITI PRIJE SVAKOG NAREDNOG TASKA

Puni detalj: `docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md` §29.

```text
HIGH-risk / bezbjednosno kritično (SecretStore, SQLite/migrations, architecture
boundaries/bootstrap, AI/Channel/Localization registry contract, itd. — puna
lista u workflow §4) → NEPROMIJENJENO: Codex + Claude + eksplicitno Human
Owner merge odobrenje.

Sve ostalo (LOW/MEDIUM) → SAMO Claude review. Claude PASS → koordinator
ODMAH commit-uje i push-uje/merguje, bez Codex runde i bez posebnog
per-task Human Owner odobrenja.
```

## Agent-friendly file headers (Human Owner odluka, 2026-09-01)

Puni detalj: `docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md` §30. Faza 1
(ključni P0.00–P0.19 foundation fajlovi sa pretankim header-om) je urađena
2026-09-01 kao LOW-risk docstring-only izmjena, direktno commit-ovana/
push-ovana po review politici iznad (bez Codex runde). Od sada važi
touched-file rule: kad task materijalno mijenja postojeći source fajl,
provjeriti/dodati kvalitetan owns/does-not-own header u istom tasku.

Ako se tokom review-a pokaže da task ipak dira HIGH listu — STOP, vratiti na
puni ciklus, ne nastaviti olakšanim putem tiho.

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

NOT DONE — ACS-P0-001 do ACS-P0-007 (7 od 8 P0 taskova) su merged.
`artifacts/phase0_foundation_gate.json` još ne postoji (gate fajl nastaje tek u ACS-P0-008).
`src/ai_campaign_studio/` sada ima punu foundation površinu: `config/`, `logging/`, `domain/common/`,
`localization/`, `channels/`, `ai_registry/`, `infrastructure/{secrets,database}/`, svih 5 `ports/`
contracta, `jobs/` (JobManager), `presentation/` (framework-neutral state/contracts), pun
`bootstrap.py` composition root, `--health-check` entrypoint, i
`tests/architecture/test_import_boundaries.py`. ACS-P0-008 (Validators + CI + security + P0 gate)
je sada jedini preostali P0 task — posljednji prije `artifacts/phase0_foundation_gate.json` i
prelaska na Faza 1.

## ACS-HOTFIX-001 — RIJEŠENO (2026-09-01)

CI regresija otkrivena na `main`-u poslije ACS-P0-007 merge-a (GitHub
Actions run `33502313009`) — `JobManager` `CREATED`/`STARTED` event-ordering
race, popravljena i merged (`bcec979`). Vidi red u tabeli ispod za pun
istorijat. **Ostaje aktivna posljedica**: ACS-P0-008 (grana
`task/ACS-P0-008-validators-ci-security-gate`, još nije merged) je granata
sa main-a PRIJE ovog hotfix-a — kad MiniMax-ov fix round za BF-1/BF-2 stigne,
prije finalizacije treba merge-ovati ažurirani `main` (sa hotfix-om) u tu
granu, pa tek onda ponovo generisati `artifacts/phase0_foundation_gate.json`
tako da `pytest` check stvarno pokriva i JobManager fix.

**Environment napomena (relevantna za sve buduće taskove)**: dijeljeni
`.venv`-ov editable-install `.pth` fajl
(`H:\AI Campaing Studio\.venv\Lib\site-packages\__editable__.ai_campaign_studio-0.1.0.pth`)
može tiho pokazivati na PROŠLI worktree umjesto na fajl koji se trenutno
verifikuje — otkriveno i potvrđeno od implementera (MiniMax), koordinatora
i Codex-a tokom ACS-HOTFIX-001. Nakon svakog merge-a, `.pth` treba ručno
provjeriti/vratiti na `main` checkout
(`H:\AI Campaing Studio\src`) prije post-merge gate-a — inače se gate testira
protiv pogrešnog koda. Za verifikaciju u worktree-u, eksplicitan
`PYTHONPATH` override je pouzdaniji od oslanjanja na `.pth` stanje.

## Aktivni taskovi

| Task | Status | Implementer | Reviewers | Napomena |
|---|---|---|---|---|
| ACS-HOTFIX-001 | **DONE — merged u main** | MiniMax | Codex, Claude (HIGH) | Merge commit `bcec979` (`--no-ff`, branch `hotfix/ACS-HOTFIX-001-job-event-ordering` @ `56a67d2`). Fix: `threading.Lock()` → `RLock()`, `CREATED` emit pomjeren unutar `submit()`-ovog lock bloka, `_emit()` sad drži lock kroz cio callback dispatch. Novi deterministički test (slow-callback adversarial probe) — dokazano da je probabilistički pristup propustio bug tri runde zaredom. Koordinator i Codex NEZAVISNO otkrili isti nalaz: fix ima redundantnu zaštitu (bilo koja dva od tri elementa su samostalno dovoljna) — ne defekt. Codex `PASS_WITH_NOTES`, bez blocking findings. Finalni decision packet: `agent_reports/2026-09-01-ACS-HOTFIX-001-final-decision-packet.md`. Human Owner approval: "Odobravam". Post-merge gate PASS na `main` (171 testova, ruff, mypy, health-check, 20x targeted loop čist) — **nakon ručnog ispravljanja `.pth`-a** koji je prvo pokazivao na uklonjeni worktree (vidi napomenu iznad). Worktree uklonjen (clean, bez force-a). |
| ACS-P0-001 | **DONE — merged u main** | Crush | Codex, Claude | Merge commit `def4ea1` (`--no-ff`, task branch `task/ACS-P0-001-repo-foundation` @ `949d18c`). Reviews: Claude PASS, Codex PASS_WITH_NOTES (no blocking findings). Human Owner approval: "Odobravam". Post-merge gate PASS. Worktree uklonjen. |
| ACS-P0-002 | **DONE — merged u main** | Pi | Codex, Claude | Merge commit `e187a56` (`--no-ff`, task branch `task/ACS-P0-002-config-boundaries` @ `d6dc783`). 5 review rundi: Codex REJECT×4 (BF-1: boundary-checker bypassi pa lexical/class-scope resolution bugovi), svaki fix nezavisno re-verifikovan od koordinatora (kombinovana adversarial reprodukcija do 11 bypass/scope oblika u finalnoj rundi), round 5 `PASS_WITH_NOTES` bez blocking findings. Finalni decision packet: `agent_reports/2026-08-31-ACS-P0-002-final-decision-packet.md` (READY FOR HUMAN APPROVAL, R1–R6 reziduelni rizici). Human Owner approval: "Slažem se". Post-merge gate PASS na `main` (43 testa, ruff, mypy, health-check, Python 3.14.1). Worktree uklonjen (`--force`, samo Pi-jevi već-inkorporirani raw report fajlovi izgubljeni, bez sadržajnog gubitka). |
| ACS-P0-003 | **DONE — merged u main** | Pi | Codex, Claude | Merge commit `e8c0a54` (`--no-ff`, task branch `task/ACS-P0-003-localization` @ `7df75c3`). 2 review runde: Codex REJECT×1 (BF-1..3: neuhvaćen `ValueError` na malformed template, non-string katalog vrijednost ruši translator, neuhvaćen `JSONDecodeError` u validatoru), fix nezavisno re-verifikovan od koordinatora, round 2 `PASS_WITH_NOTES` bez blocking findings (uključujući mixed valid/invalid-JSON edge case). Finalni decision packet: `agent_reports/2026-08-31-ACS-P0-003-final-decision-packet.md`. Human Owner approval: "odobravam". Post-merge gate PASS na `main` (91 test, ruff, mypy, validate_resources, health-check). Worktree uklonjen (`--force`, samo Pi-jevi već-inkorporirani raw report fajlovi izgubljeni). |
| ACS-P0-004 | **DONE — merged u main** | Crush | Codex, Claude | Merge commit `5ecf43f` (`--no-ff`, task branch `task/ACS-P0-004-channel-registry` @ `be3767a`). 3 review runde: Codex REJECT×2 (BF-1..3 pa BF-4, 4 stvarna nalaza — TypeError umjesto RegistryError, mutable "frozen" model, duplicate reference, `or []` falsy-scalar zamka), svaki fix nezavisno re-verifikovan od koordinatora, round 3 `PASS_WITH_NOTES` bez blocking findings. Crush nije predao nijedan self-report kroz cio task — sva evidence rekonstruisana od koordinatora. Finalni decision packet: `agent_reports/2026-08-31-ACS-P0-004-final-decision-packet.md`. Human Owner approval: "odobravam". Post-merge gate PASS na `main` (65 testova, ruff, mypy, health-check). Worktree uklonjen (clean, bez force-a). |
| ACS-P0-005 | **DONE — merged u main** | Pi | Codex, Claude | Merge commit `c76eb9b` (`--no-ff`, task branch `task/ACS-P0-005-ai-registry-secrets` @ `2ff5f4e`). 2 review runde: Codex REJECT×1 (BF-1..3: secret leak kroz exception `__cause__`, env-var collision za nekanonska imena, modeli za nepoznatog providera), fix nezavisno re-verifikovan od koordinatora, round 2 `PASS_WITH_NOTES` bez blocking findings. Finalni decision packet: `agent_reports/2026-09-01-ACS-P0-005-final-decision-packet.md`. Human Owner approval: "Odobravam". Trivijalan add/add merge konflikt na `infrastructure/__init__.py` (obje 005 i 006 kontrakte su nezavisno listale isti fajl — moja greška u allowed_paths disjoint provjeri za taj par) — riješen ručno, samo docstring razlika. Post-merge gate PASS na `main`. Worktree uklonjen (`--force`, samo Pi-jevi već-inkorporirani raw report fajlovi izgubljeni). |
| ACS-P0-006 | **DONE — merged u main** | Crush | Codex, Claude | Merge commit `298bbd3` (`--no-ff`, task branch `task/ACS-P0-006-sqlite-foundation` @ `8d45167`). 2 review runde: Codex REJECT×1 (BF-1/2: UoW re-use nakon commit-a onemogući rollback, migration runner rollback-uje caller-owned transakciju kad BEGIN padne), fix nezavisno re-verifikovan od koordinatora, round 2 `PASS_WITH_NOTES` bez blocking findings. Finalni decision packet: `agent_reports/2026-09-01-ACS-P0-006-final-decision-packet.md`. Human Owner approval: "odobravam". Post-merge gate PASS na `main` (104 testa, ruff, mypy, health-check). Worktree uklonjen (clean, bez force-a). Usput: `.codex_tmp/` scratch fajl Codex-a je nakratko interferisao sa `ruff check .` (nije gitignored) — nestao je sam prije nego što je trebalo trajno rješenje, nije naš kod. |
| ACS-P0-007 | **DONE — merged u main** | Pi | Codex, Claude | Merge commit `1071eff` (`--no-ff`, task branch `task/ACS-P0-007-jobs-presentation-bootstrap` @ `c553379`). Scope: P0.20–P0.23 (Jobs + Presentation contracts + Bootstrap wiring). Tri Codex REJECT/REJECT/PASS_WITH_NOTES runde: BF-1 (submit-after-shutdown orphan job), BF-2 (dynamic-import guard bypass), R2-BF-1 (queued job trajno PENDING nakon shutdown-cancellation) — sva tri nalaza nezavisno reprodukovana od koordinatora PRIJE svake fix-runde I nezavisno reverifikovana POSLIJE (uključujući reprodukciju Codex-ovog 100-job concurrent submit/shutdown stress probe-a). Codex round 3: PASS_WITH_NOTES, bez blocking findings. Finalni decision packet: `agent_reports/2026-09-01-ACS-P0-007-final-decision-packet.md`. Human Owner approval: "Odobravam". Post-merge gate PASS na `main` (170 testova, ruff, mypy, oba health-check entrypointa, Python 3.14.1). Čist merge, bez konflikta. Jedan prihvaćen non-blocking rezidual (double-indirection dynamic-import bypass u presentation guardu, eksplicitno van scope-a po Codex-ovoj preporuci). Worktree uklonjen (clean, bez force-a). |
| ACS-P0-008 | **BF-3 riješen — čeka lean Codex round 3** | MiniMax | Codex, Claude (HIGH) | Scope: P0.24–P0.30. Grana `task/ACS-P0-008-validators-ci-security-gate` @ `ab44871` (nije merged; uključuje main sa ACS-HOTFIX-001). Tok: Codex round 1 REJECT (BF-1 scanner self-poisoning, BF-2 raw-value leak) → fix round 1 (`8f43b28`, koordinator nezavisno potvrdio) → main merge → **Codex round 2 PASS_WITH_NOTES** (`agent_reports/2026-09-01-ACS-P0-008-review-codex-round2.md`, bez blocking findings, nezavisno ponovio Anthropic probu). Eksterna ChatGPT analiza (produkt/security review) je flagovala **BF-3**: scanner patterns pokrivaju samo OPENAI/ANTHROPIC, ali `EnvironmentSecretStore` generiše `AI_CAMPAIGN_STUDIO_<PROVIDER>_API_KEY` za SVE providere — Google/OpenRouter leak-ovi prolaze neopaženo, DeepSeek slučajno pokriven. Koordinator empirijski potvrdio prije slanja MiniMax-u. Fix: opšti `ai_campaign_studio_env` pattern koji prati naming convention strukturno (pokriva i buduće providere automatski). MiniMax je usput samostalno otkrio i popravio **`_KEY_VALUE` character-class bug** (`_` slučajno u regex klasi, false-positive na Python identifiere 16+ karaktera). Koordinator nezavisno potvrdio oba (Google-shaped ključ drugačiji od implementerovih proba; direktna regex-behavior provjera za `_KEY_VALUE`). **Usput**: GitHub push protection je blokirao push jer je evidence report sadržao key-shaped literal (demo vrijednost u "before" repro bloku) koji je izgledao kao pravi DeepSeek ključ — squash-ovano u jedan čist commit sa EXAMPLE-markiranim placeholder vrijednostima, uspješno pushovano. 217 testova, ruff/mypy čisto. Lean Codex round 3 request pripremljen (samo BF-3 + bug, BF-1/BF-2 već potvrđeni) i pushovan. |

## Paralelizacija — trenutna provjera

Drugi paralelni par (ACS-P0-005 + ACS-P0-006, pokrenut 2026-09-01) je uspješno završen — oba
merged (006 prvo, pa 005), sa jednim trivijalnim add/add merge konfliktom na
`infrastructure/__init__.py` (obje kontrakte su nezavisno listale isti `__init__.py` u
`allowed_paths` — propust u disjoint provjeri za ovaj par, upisan kao lekcija za naredne
paralelne parove: provjeriti i package `__init__.py` fajlove, ne samo "glavne" module fajlove).
ACS-P0-007 je sada jedini kandidat — nema drugog unblocked P0 taska za paralelizam trenutno.

## Poznati blokatori

- **GitHub push protection hvata secret-shaped demo vrijednosti u evidence reportima.**
  Kad `agent_reports/*.md` dokumentuje "before" reprodukciju secret-scanner nalaza
  (npr. `check_no_secrets.py` fix-round evidence), literal poput
  `sk-abcdefghijklmnopqrstuvwxyz123456` je dovoljno key-shaped da GitHub-ov vlastiti
  secret scanning push protection blokira push, iako je fajl van scope-a našeg
  `check_no_secrets.py` (koji isključuje `*.md`). Rješenje: u evidence reportima
  koristiti eksplicitno EXAMPLE-markirane placeholder vrijednosti
  (`sk-EXAMPLE-abcdefghijklmnopqrstuvwxyz`) umjesto punih key-shaped literala, čak i
  kad demonstriraš da je fix "prije" hvatao takav string. Otkriveno na ACS-P0-008
  BF-3 fix rundi (2026-09-01) — push odbijen, ispravljeno squash-ovanjem commit-a sa
  ispravljenim tekstom prije ponovnog push-a.
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

Uspostavljen na `main` poslije merge-a ACS-HOTFIX-001 (2026-09-01, root `.venv`, Python 3.14.1,
`.pth` ručno provjeren/vraćen na main checkout — vidi napomenu iznad):

```text
import ai_campaign_studio          → OK (0.1.0)
python -m pytest -q                → 171 passed
python -m ruff check .             → All checks passed!
python -m mypy src                 → Success: no issues found in 51 source files
python -m ai_campaign_studio.main --health-check → exit 0
20x loop -k "event_sequence or event_ordering_under_slow" → 20/20 čisto
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

Indeksirano poslije file-header Faze 1 commit-a:

```text
Indexed commit: 14433da (= trenutni main HEAD)
Status: up-to-date
3398 nodes | 4062 edges | 54 clusters | 30 flows
```

`mcp__gitnexus__*` MCP alati su dostupni u koordinator sesiji (pored CLI), ali dijele istu
worktree-binding limitaciju — vidi blokatore. Prije narednog pre-impact-a, ako main odmakne,
ponovo pokrenuti `npx gitnexus analyze --skip-agents-md` pa `npx gitnexus status`.

## Sljedeći task

ACS-P0-001–007 su svi DONE. ACS-P0-008 (Validators + CI + security + P0 gate, P0.24–P0.30) je
jedini preostali P0 task — posljednji prije `artifacts/phase0_foundation_gate.json` i prelaska na
Faza 1. Contract nije napisan.
