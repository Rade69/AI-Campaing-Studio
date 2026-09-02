# .agent/CURRENT_STATE.md

Živi status. Ne istorijski arhiv — istorija je u Git-u i `agent_reports/`.
Ažurira koordinator (default Claude) poslije svakog merge-a i svake promjene gate/task stanja.

**Zadnje ažurirano:** 2026-09-02 (coordinator: claude) — **Task A3 GOTOV.** A4 (boundary schemas + mappers) kontrakti napisani i OPEN: **ACS-F1-003** (Pi — `brand_fixture.py` + mapper) i **ACS-F1-004** (Crush — preostalih 5 schema fajlova), paralelni, bez zavisnosti između njih, base `main @ 0edae77`. GUI mockup rekonsolidacija riješena (`docs/gui-v3/` kanonski, vidi "Sljedeći task"). pywebview sigurnosna politika dodana (`docs/PYWEBVIEW_SECURITY.md`). **OTVORENO PITANJE za MiniMax GUI-BASE task**: G9 UI Framework Gate (plan sekcija 3) traži uporedni pywebview vs PySide6 spike prije nego što se pywebview zaključa kao production izbor; AR5 eksplicitno zabranjuje production `presentation_webview/` prije G9. SPIKE-001 je testirao samo pywebview. Čeka Human Owner odluku (formalno zatvoriti G9 sada bez PySide6 poređenja, ili tražiti brzi PySide6 spike prvo) prije nego se piše formalni MiniMax kontrakt za production wiring.

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

**Faza 1 — Vertical Slice 1.** P0 Foundation je DONE (`P0-GATE = PASS`, 2026-09-02).
Aktivni plan: `AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md`. Task A3
("Common + Domain enums/entities") DONE (ACS-F1-001 + ACS-F1-002 merged). Sljedeći: A4.

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

**PASS — 2026-09-02.** Svih 8 P0 taskova (ACS-P0-001 do ACS-P0-008) su merged.
`artifacts/phase0_foundation_gate.json` postoji na `main` (commit `aef1b0d`),
regenerisan protiv stvarnog merge-ovanog main-a (ne stale/worktree stanja):

```json
{
  "phase": "implementation-phase-0",
  "status": "PASS",
  "checks": { ... svih 17 true ... },
  "ui_framework": "NOT_SELECTED",
  "campaign_engine_implemented": false,
  "website_ingestion_implemented": false,
  "notes": []
}
```

`src/ai_campaign_studio/` ima punu foundation površinu: `config/`, `logging/`,
`domain/common/`, `localization/`, `channels/`, `ai_registry/`,
`infrastructure/{secrets,database}/`, svih 5 `ports/` contracta, `jobs/`
(JobManager, sa ACS-HOTFIX-001 event-ordering fix-om), `presentation/`
(framework-neutral state/contracts), pun `bootstrap.py` composition root,
`--health-check` entrypoint, `scripts/{validate_resources,check_no_secrets,
generate_phase0_gate_report}.py`, i `tests/architecture/test_import_boundaries.py`.

**Faza 1 više NIJE blokirana** (uslov iz "Aktivna faza" sekcije je ispunjen).
Prije nego što se formalno pređe na Faza 1 rad: pročitati plan §37 (P0.30
STOP) — agent ne nastavlja automatski sa Brand/Facts/CampaignPlan/
ContentPiece/OpenAI generation/GUI/renderer dok Human Owner eksplicitno ne
potvrdi prelazak. Napomena: SPIKE-001 (pywebview UI validacija, kasnije
prošireno u punu GUI izradu od strane MiniMax-a) je već u toku paralelno —
to je Human Owner odluka da se UI rad počne i prije formalnog P0.29/P0.30
zapisa, van P0 Task Contract sistema (vidi SPIKE_NOTES.md u tom worktree-u).

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
| ACS-F1-001 | **DONE — merged u main** | Pi | Claude (MEDIUM) | Merge commit `2e83911` (`--no-ff`, branch `task/ACS-F1-001-domain-common-brand-facts` @ `47bffde`). Scope: `domain/common` extension (10 typed ID aliasa kao `NewType`, 3 nove `DomainError` podklase) + `domain/brand/` (frozen value objects + entities) + `domain/facts/` (FactStatus, immutable ApprovedFact, versioning policies). Koordinator nezavisno pročitao sav kod, pokrenuo pun test suite (242 testa) + architecture boundary suite (15 testova), i sam reprodukovao immutability/InvariantViolation/non-mutation invarijante van test suite-a. MEDIUM risk → Claude-only review → odmah merge po §29, bez posebnog Human Owner odobrenja. Post-merge gate PASS na `main`, CI zeleno (potvrđeno uživo). Worktree uklonjen (clean). |
| ACS-F1-002 | **DONE — merged u main** | Crush | Claude (MEDIUM) | Merge commit `b30166b` (`--no-ff`, branch `task/ACS-F1-002-domain-campaign-content-visual` @ `2404ba9`). Korak 1 (enums/roles/templates/slots, bez zavisnosti) + Korak 2 (entities.py, content/claims.py, content/revisions.py, visual/layout.py — nakon što je ACS-F1-001 dao typed ID aliase). Svi typed ID-jevi ispravno importovani iz `domain.common.ids`, bez lokalnih duplikata (0A.5). `LayoutSpec` polja su sva tipizirani enumi (novi `ImagePosition`/`HeadlinePosition`/`HeadlineScale`/`Overlay`/`LogoPosition`/`CtaStyle` dodati u `visual/enums.py`). Koordinator nezavisno pročitao sav kod, pokrenuo pun test suite (263 testa) + architecture boundary suite (15 testova), i sam reprodukovao immutability i `lead_generation_v1` sekvencu (7 uloga, bez duplikata) van test suite-a. MEDIUM risk → Claude-only review → odmah merge po §29. Post-merge gate PASS na `main`, CI zeleno (potvrđeno uživo). Worktree uklonjen (clean). |
| ACS-HOTFIX-001 | **DONE — merged u main** | MiniMax | Codex, Claude (HIGH) | Merge commit `bcec979` (`--no-ff`, branch `hotfix/ACS-HOTFIX-001-job-event-ordering` @ `56a67d2`). Fix: `threading.Lock()` → `RLock()`, `CREATED` emit pomjeren unutar `submit()`-ovog lock bloka, `_emit()` sad drži lock kroz cio callback dispatch. Novi deterministički test (slow-callback adversarial probe) — dokazano da je probabilistički pristup propustio bug tri runde zaredom. Koordinator i Codex NEZAVISNO otkrili isti nalaz: fix ima redundantnu zaštitu (bilo koja dva od tri elementa su samostalno dovoljna) — ne defekt. Codex `PASS_WITH_NOTES`, bez blocking findings. Finalni decision packet: `agent_reports/2026-09-01-ACS-HOTFIX-001-final-decision-packet.md`. Human Owner approval: "Odobravam". Post-merge gate PASS na `main` (171 testova, ruff, mypy, health-check, 20x targeted loop čist) — **nakon ručnog ispravljanja `.pth`-a** koji je prvo pokazivao na uklonjeni worktree (vidi napomenu iznad). Worktree uklonjen (clean, bez force-a). |
| ACS-P0-001 | **DONE — merged u main** | Crush | Codex, Claude | Merge commit `def4ea1` (`--no-ff`, task branch `task/ACS-P0-001-repo-foundation` @ `949d18c`). Reviews: Claude PASS, Codex PASS_WITH_NOTES (no blocking findings). Human Owner approval: "Odobravam". Post-merge gate PASS. Worktree uklonjen. |
| ACS-P0-002 | **DONE — merged u main** | Pi | Codex, Claude | Merge commit `e187a56` (`--no-ff`, task branch `task/ACS-P0-002-config-boundaries` @ `d6dc783`). 5 review rundi: Codex REJECT×4 (BF-1: boundary-checker bypassi pa lexical/class-scope resolution bugovi), svaki fix nezavisno re-verifikovan od koordinatora (kombinovana adversarial reprodukcija do 11 bypass/scope oblika u finalnoj rundi), round 5 `PASS_WITH_NOTES` bez blocking findings. Finalni decision packet: `agent_reports/2026-08-31-ACS-P0-002-final-decision-packet.md` (READY FOR HUMAN APPROVAL, R1–R6 reziduelni rizici). Human Owner approval: "Slažem se". Post-merge gate PASS na `main` (43 testa, ruff, mypy, health-check, Python 3.14.1). Worktree uklonjen (`--force`, samo Pi-jevi već-inkorporirani raw report fajlovi izgubljeni, bez sadržajnog gubitka). |
| ACS-P0-003 | **DONE — merged u main** | Pi | Codex, Claude | Merge commit `e8c0a54` (`--no-ff`, task branch `task/ACS-P0-003-localization` @ `7df75c3`). 2 review runde: Codex REJECT×1 (BF-1..3: neuhvaćen `ValueError` na malformed template, non-string katalog vrijednost ruši translator, neuhvaćen `JSONDecodeError` u validatoru), fix nezavisno re-verifikovan od koordinatora, round 2 `PASS_WITH_NOTES` bez blocking findings (uključujući mixed valid/invalid-JSON edge case). Finalni decision packet: `agent_reports/2026-08-31-ACS-P0-003-final-decision-packet.md`. Human Owner approval: "odobravam". Post-merge gate PASS na `main` (91 test, ruff, mypy, validate_resources, health-check). Worktree uklonjen (`--force`, samo Pi-jevi već-inkorporirani raw report fajlovi izgubljeni). |
| ACS-P0-004 | **DONE — merged u main** | Crush | Codex, Claude | Merge commit `5ecf43f` (`--no-ff`, task branch `task/ACS-P0-004-channel-registry` @ `be3767a`). 3 review runde: Codex REJECT×2 (BF-1..3 pa BF-4, 4 stvarna nalaza — TypeError umjesto RegistryError, mutable "frozen" model, duplicate reference, `or []` falsy-scalar zamka), svaki fix nezavisno re-verifikovan od koordinatora, round 3 `PASS_WITH_NOTES` bez blocking findings. Crush nije predao nijedan self-report kroz cio task — sva evidence rekonstruisana od koordinatora. Finalni decision packet: `agent_reports/2026-08-31-ACS-P0-004-final-decision-packet.md`. Human Owner approval: "odobravam". Post-merge gate PASS na `main` (65 testova, ruff, mypy, health-check). Worktree uklonjen (clean, bez force-a). |
| ACS-P0-005 | **DONE — merged u main** | Pi | Codex, Claude | Merge commit `c76eb9b` (`--no-ff`, task branch `task/ACS-P0-005-ai-registry-secrets` @ `2ff5f4e`). 2 review runde: Codex REJECT×1 (BF-1..3: secret leak kroz exception `__cause__`, env-var collision za nekanonska imena, modeli za nepoznatog providera), fix nezavisno re-verifikovan od koordinatora, round 2 `PASS_WITH_NOTES` bez blocking findings. Finalni decision packet: `agent_reports/2026-09-01-ACS-P0-005-final-decision-packet.md`. Human Owner approval: "Odobravam". Trivijalan add/add merge konflikt na `infrastructure/__init__.py` (obje 005 i 006 kontrakte su nezavisno listale isti fajl — moja greška u allowed_paths disjoint provjeri za taj par) — riješen ručno, samo docstring razlika. Post-merge gate PASS na `main`. Worktree uklonjen (`--force`, samo Pi-jevi već-inkorporirani raw report fajlovi izgubljeni). |
| ACS-P0-006 | **DONE — merged u main** | Crush | Codex, Claude | Merge commit `298bbd3` (`--no-ff`, task branch `task/ACS-P0-006-sqlite-foundation` @ `8d45167`). 2 review runde: Codex REJECT×1 (BF-1/2: UoW re-use nakon commit-a onemogući rollback, migration runner rollback-uje caller-owned transakciju kad BEGIN padne), fix nezavisno re-verifikovan od koordinatora, round 2 `PASS_WITH_NOTES` bez blocking findings. Finalni decision packet: `agent_reports/2026-09-01-ACS-P0-006-final-decision-packet.md`. Human Owner approval: "odobravam". Post-merge gate PASS na `main` (104 testa, ruff, mypy, health-check). Worktree uklonjen (clean, bez force-a). Usput: `.codex_tmp/` scratch fajl Codex-a je nakratko interferisao sa `ruff check .` (nije gitignored) — nestao je sam prije nego što je trebalo trajno rješenje, nije naš kod. |
| ACS-P0-007 | **DONE — merged u main** | Pi | Codex, Claude | Merge commit `1071eff` (`--no-ff`, task branch `task/ACS-P0-007-jobs-presentation-bootstrap` @ `c553379`). Scope: P0.20–P0.23 (Jobs + Presentation contracts + Bootstrap wiring). Tri Codex REJECT/REJECT/PASS_WITH_NOTES runde: BF-1 (submit-after-shutdown orphan job), BF-2 (dynamic-import guard bypass), R2-BF-1 (queued job trajno PENDING nakon shutdown-cancellation) — sva tri nalaza nezavisno reprodukovana od koordinatora PRIJE svake fix-runde I nezavisno reverifikovana POSLIJE (uključujući reprodukciju Codex-ovog 100-job concurrent submit/shutdown stress probe-a). Codex round 3: PASS_WITH_NOTES, bez blocking findings. Finalni decision packet: `agent_reports/2026-09-01-ACS-P0-007-final-decision-packet.md`. Human Owner approval: "Odobravam". Post-merge gate PASS na `main` (170 testova, ruff, mypy, oba health-check entrypointa, Python 3.14.1). Čist merge, bez konflikta. Jedan prihvaćen non-blocking rezidual (double-indirection dynamic-import bypass u presentation guardu, eksplicitno van scope-a po Codex-ovoj preporuci). Worktree uklonjen (clean, bez force-a). |
| ACS-P0-008 | **DONE — merged u main — POSLJEDNJI P0 TASK, P0-GATE = PASS** | MiniMax | Codex, Claude (HIGH) | Merge commit `aef1b0d` (`--no-ff`, task branch `task/ACS-P0-008-validators-ci-security-gate` @ `5774303`). Tok: Codex round 1 REJECT (BF-1 scanner self-poisoning, BF-2 raw-value leak) → fix round 1 → Codex round 2 `PASS_WITH_NOTES` → BF-3 (secret scanner provider-coverage gap, Google/OpenRouter propust, flagovano iz eksterne analize, empirijski potvrđeno) + `_KEY_VALUE` character-class bug (MiniMax sam otkrio) → Codex round 3 `PASS_WITH_NOTES`, bez blocking findings. Svaki nalaz kroz sve tri runde nezavisno potvrđen od koordinatora DRUGAČIJOM probom od implementera/Codex-a. Finalni decision packet: `agent_reports/2026-09-02-ACS-P0-008-final-decision-packet.md`. Human Owner approval: "Merdžuj, komituj i pušuj na github". Post-merge gate PASS na `main` (217 testova, ruff, mypy, validate_resources, check_no_secrets, health-check, 10x race-stress loop čist) — `.pth` provjeren prije verifikacije (lekcija iz ACS-HOTFIX-001). Gate report regenerisan protiv stvarnog merge-ovanog main-a: `status: PASS`, svih 17 checkova `true`. Worktree uklonjen (`--force`, samo LF/CRLF whitespace artifact, bez sadržajnog gubitka). |

## Paralelizacija — trenutna provjera

Drugi paralelni par (ACS-P0-005 + ACS-P0-006, pokrenut 2026-09-01) je uspješno završen — oba
merged (006 prvo, pa 005), sa jednim trivijalnim add/add merge konfliktom na
`infrastructure/__init__.py` (obje kontrakte su nezavisno listale isti `__init__.py` u
`allowed_paths` — propust u disjoint provjeri za ovaj par, upisan kao lekcija za naredne
paralelne parove: provjeriti i package `__init__.py` fajlove, ne samo "glavne" module fajlove).
ACS-P0-007 je sada jedini kandidat — nema drugog unblocked P0 taska za paralelizam trenutno.

## Poznati blokatori

- **PROCES-GREŠKA (koordinator, 2026-09-02): CI status na task branch push-ovima
  nije bio redovno provjeravan tokom review ciklusa, pa je slomljen `ci.yml` prošao
  nezapaženo kroz cijeli ACS-P0-008 review (Claude, Codex x3 runde) i merge.**
  Uzrok: ACS-P0-008 je proširio `ci.yml` health-check korakom koji je koristio bash
  heredoc (`python - <<'PY' ... PY`) UNUTAR uvučenog YAML block scalar-a
  (`run: |`). Heredoc terminator linija je naslijedila YAML uvlačenje, pa nikad nije
  tačno odgovarala bash-ovom zahtjevu da `<<'PY'` terminator bude na početku linije
  bez uvlačenja — GitHub Actions je odbijao da parsira CIJELI workflow fajl (0 job-ova,
  "likely failed because of a workflow file issue") na SVAKOM push-u od trenutka kad
  je ta izmjena landovala (task branch, ACS-HOTFIX-001 merge, ACS-P0-008 merge — svi
  crveni, svi neprimijećeni). Otkriveno tek nakon P0-008 merge-a kad je koordinator
  eksplicitno provjerio `gh run list` post-merge. Popravljeno (`95a799f`): uklonjena
  fragilna heredoc/env-var mašinerija, zamijenjena postojećim, već testiranim
  `python -m ai_campaign_studio.main --health-check` entrypoint-om (GitHub Actions
  runner je svježa, jednokratna VM — default `platformdirs.user_data_dir` je
  bezbjedan za pisanje, temp-dir override nikad nije bio stvarno potreban u CI-ju).
  Dodan `.gitattributes` (`text eol=lf` za `.github/workflows/*.yml` i `*.sh`) kao
  dodatna zaštita, iako CRLF nije bio stvaran uzrok ovog konkretnog problema (commit-ovan
  blob je već bio LF — autocrlf je uticao samo na lokalno radno stablo).
  **Lekcija za ubuduće**: nakon SVAKOG push-a na task branch ili main, provjeriti
  `gh run list --branch <branch> --limit 1` kao dio standardne verifikacije — ne
  samo na "značajnim" merge-ovima. Heredoc unutar YAML `run: |` bloka je generalno
  fragilan obrazac — izbjegavati ga, koristiti zaseban script fajl ili `python -c`
  jednolinijski poziv umjesto toga.
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

Uspostavljen na `main` poslije merge-a ACS-P0-008 — **P0-GATE = PASS** (2026-09-02, root `.venv`,
Python 3.14.1, `.pth` ručno provjeren/vraćen na main checkout — vidi napomenu iznad):

```text
import ai_campaign_studio          → OK (0.1.0)
python -m pytest -q                → 217 passed
python -m ruff check .             → All checks passed!
python -m mypy src                 → Success: no issues found in 51 source files
python scripts/validate_resources.py → All resources are valid
python scripts/check_no_secrets.py   → NO CONFIRMED SECRET IN TRACKED FILES
python -m ai_campaign_studio.main --health-check → exit 0
python scripts/generate_phase0_gate_report.py → status: PASS, svih 17 checkova true
10x loop -k "event_sequence or event_ordering_under_slow" → 10/10 čisto
```

## CI

`.github/workflows/ci.yml` postoji od 2026-08-31, prošireno u ACS-P0-008 (2026-09-01/02).
Pokreće `ruff check .` → `mypy src` → `pytest -q` → resource validation → no-secret scan →
health-check (izolovan temp data dir preko `AppPaths(data_dir_override=...)`, bez keyring/GUI/
network) na `push`/`pull_request` ka `main`, GitHub-ov Python 3.12 runner (donja granica iz
`requires-python`). Merge commit ACS-HOTFIX-001 (`bcec979`) i ACS-P0-008 (`aef1b0d`) oba zelena
na GitHub Actions. Ovo NE zamjenjuje ručnu post-merge gate provjeru koordinatora — i dalje ručno
pokretati pun set prije/poslije merge-a, CI je dodatna, ne jedina zaštita (npr. ne pokriva
`generate_phase0_gate_report.py` niti GitNexus korake).

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

**A3 "Common + Domain enums/entities" je GOTOV** — i ACS-F1-001 i ACS-F1-002 merged u main
(2026-09-02). Cijeli domain sloj (`domain/common`, `brand`, `facts`, `campaign`, `content`,
`visual`) sad postoji, 263 testa, CI zeleno. Sljedeći task u planu: **A4 — boundary schemas +
mappers** (Pydantic granice: `application/schemas/brand_fixture.py` itd. — vidi plan sekciju 15).
Contract za A4 nije napisan. Poslije A4: A5 (business persistence nad postojećim SQLite
foundationom), A6 (fixture loading — Brand Fixture, prvi stvaran podatak), A7+ (prompts/AI/
application pipeline).

Paralelno već u toku, van formalnog Faza 1 Task Contract sistema: **SPIKE-001** (pywebview UI,
`spike/pywebview-content-studio` grana) — MiniMax radi GUI prema mokapu.

**GUI mockup rekonsolidacija RIJEŠENA (2026-09-02).** `GUI-architecture/` direktorijum
(untracked, nepoznatog porijekla) je pročitan u cjelosti, sadržaj procijenjen kao kvalitetan
i usklađen sa zaključanim arhitektonskim odlukama (minimalan sidebar scope, Analytics guard
prisutan dva puta, Quick Actions + facts + compliance u Studiju, ispravna razlika između
postojećih `PresentationFacade` metoda i onoga što tek treba F1 contracte). **Human Owner je
eksplicitno potvrdio V3 kao kanonski GUI kandidat** — `mockup_proposal`/`mockup_proposal_v2`
iz SPIKE-001 grane ostaju samo referenca/exploration, nisu više kandidat za production wiring.
Paket je premješten iz untracked `GUI-architecture/` u trackovan **`docs/gui-v3/`**
(`README.md`, `V3_PLAN.md`, `INTEGRATION.md`, `screens/01_pocetna` … `09_podesavanja`,
`shared/app.css`, `shared/app.js`; redundantne root-nivo duplikate, `.zip` i
`phase0_foundation_gate.json` kopiju sam izbacio pri premještanju — originalni
`GUI-architecture/` direktorijum obrisan).

Dva gapa nađena nezavisnom provjerom HTML-a (nisu bila u README-u) su **POPRAVLJENA
(2026-09-02, commit `9f744ac`)** direktno u `docs/gui-v3/`, prije wiring-a:
1. Stepper "done" koraci (ekrani 04–08) su sada pravi `<a class="step done">` linkovi ka
   odgovarajućem ekranu, umjesto inertnih divova — usklađeno sa `V3_PLAN.md` tvrdnjom da
   stepper omogućava povratak. Dodano `[hidden]{display:none!important}` i
   `text-decoration:none` za `.step` u `shared/app.css`.
2. `screens/06_kalendar/index.html` (dvostruka uloga: globalni Kalendar iz sidebar-a I korak 3
   campaign workflow-a) sada ima query-param-driven campaign banner (`?campaign=...` iz
   `05_plan_kampanje` linka) — breadcrumb + stepper + "Nastavi → Studio sadržaja" dugme se
   pojave samo kad se stranica otvori sa tim parametrom; direktan pristup iz sidebar-a ostaje
   nepromijenjen (čist globalni pogled). Toggle logika je čisto prezentaciona (čita URL param,
   ne poziva business logiku) u `shared/app.js`.

**Sigurnosna politika za pywebview dodana (2026-09-02): `docs/PYWEBVIEW_SECURITY.md`.** Human
Owner je tražio maksimalno bezbjedan pywebview 6.2.1 setup. Istraženo protiv zvanične
dokumentacije (bez trenutnih CVE-ova). Najkritičniji nalaz: na Windows-u pywebview bez
eksplicitnog `gui='edgechromium'` tiho pada na `mshtml` (IE/Trident, deprecated, bez zakrpa)
ako WebView2 Runtime nije instaliran — mora se forsirati `edgechromium` i eksplicitno
detektovati odsustvo Runtime-a umjesto tihog downgrade-a. Dokument pokriva i debug/DevTools,
`js_api` allowlisting, CSP, eksterne linkove, storage/private_mode, i dependency pinning.
Referenciran kao obavezan read-set u `.agent/TASK_ROUTING.md` za svaki budući task koji dira
`presentation_webview/`/`js_api`. Politika obavezuje bez obzira što pywebview još nije
formalno zaključan kao UI framework (UI spike gate nije prošao) — važi od prvog reda
produkcijskog koda ako/kad se zaključa.

Sljedeći koraci za GUI: kad se A4+ application/use-case slojevi za Brand/Campaign pojave, otvoriti
formalni lightweight task (van Task Contract sistema, po uzoru na SPIKE-001, ili kao pravi F1
contract — odlučiti tada) za wiring `docs/gui-v3/` u `presentation_webview/` po strukturi iz
`INTEGRATION.md`.
