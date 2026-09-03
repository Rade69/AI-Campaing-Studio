# .agent/CURRENT_STATE.md

Živi status. Ne istorijski arhiv — istorija je u Git-u i `agent_reports/`.
Ažurira koordinator (default Claude) poslije svakog merge-a i svake promjene gate/task stanja.

**Zadnje ažurirano:** 2026-09-03 (coordinator: claude) — **FLOW-1001 — Content revisions
(ReviseContentPiece) kontrakt napisan, OPEN, implementer TBD.** Poslednji preostali komad A12
plan-grupe (dio 1 = ACS-F1-012, mergovano). Dodaje `RevisionType` enum (aditivno u
`domain/content/revisions.py`, GitNexus potvrdio LOW impact) + `ReviseContentPiece` use-case koji
koristi VEĆ postojeći `RevisionOutput` schema (ACS-F1-004, partial-update preko
`changed_fields`), VEĆ postojeći `RevisionRepositoryPort`/`SqliteRevisionRepository` (ACS-F1-006,
prva stvarna upotreba), i reuse-uje `claim_validator`/`claim_linter`/`derive_content_status`
(ACS-F1-011/012). Dvije namjerne scope granice dokumentovane u kontraktu:
`NEW_VISUAL_DIRECTION` odbijen (RevisionOutput nema `visual_direction` polje, čeka Visual System
pipeline A13+), claims se ponovo lintuju ali NE regenerišu (RevisionOutput nema `claims` polje).
Kodifikuje postojeću `ContentPiece` docstring invarijantu: revizija prethodno-APPROVED sadržaja
UVIJEK vraća `NEEDS_REVIEW`. Worktree spreman:
`../ai-campaign-studio-worktrees/FLOW-1001-content-revisions`. Detalji:
`agent_reports/FLOW-1001-task-contract.md`.

Prethodni entry (2026-09-03): **FLOW-1000 — Plan-approved guard u
GenerateSocialPost merged u main.** `GenerateSocialPost.execute()` sad odbija bilo koji plan koji
nije `CampaignPlanStatus.APPROVED` (`InvariantViolation`, bačeno PRIJE `campaign_item` pretrage i
PRIJE bilo kakvog AI poziva/perzistencije) — zatvara poznat gap iz ACS-F1-014 (plan sekcija 32:
"Post generation ne smije krenuti sa DRAFT planom"). Postojeći happy-path testovi ažurirani na
`APPROVED` fixture (nisu oslabljeni); novi negativni testovi STVARNO dokazuju da AI port nije
pozvan (`ai_port.calls == []`) za DRAFT/SUPERSEDED plan, plus integration test na pravoj SQLite
bazi (nula persistovanih `content_pieces`). Koordinator nezavisno reprodukovao pytest (502 u
izolovanom worktree-u, 516 na `main` post-merge)/ruff/mypy/import-boundaries (16) čisti, pročitao
cio diff (guard klauzula + import + test izmjene). MEDIUM risk → Claude-only review → odmah merge
po §29. Merge commit `92d2b0c` (`--no-ff` u `1e16b1a`). Worktree uklonjen (clean). **Ovo je bio
prvi task pod novom `FLOW-NNNN` šemom — proces je funkcionisao identično kao za stare
ACS-F1-XXX taskove.**

Prethodni entry (2026-09-02): **FLOW-1000 — Plan-approved guard u
GenerateSocialPost kontrakt napisan, OPEN, implementer TBD.** Prvi task pod novom `FLOW-NNNN`
šemom (§31). Zatvara poznat gap iz ACS-F1-014: `GenerateSocialPost` ne provjerava da je plan
`APPROVED` prije generisanja posta. Worktree spreman:
`../ai-campaign-studio-worktrees/FLOW-1000-plan-approved-guard`. Detalji:
`agent_reports/FLOW-1000-task-contract.md`.

Prethodni entry (2026-09-02): **ACS-F1-014 (A10 — Plan editing/
versioning/approval) merged u main.** `EditCampaignPlan` (pozivalac šalje CIJELU novu listu itema;
stari DRAFT plan → `SUPERSEDED`, novi → `DRAFT` `version+1`, atomično; editovanje APPROVED/
SUPERSEDED plana odbijeno) + `ReorderCampaignItem` (validira permutaciju postojećih item id-jeva,
`order→1..N`, STVARNO delegira na `EditCampaignPlan`, ne duplira logiku — potvrđeno čitanjem) +
`ApproveCampaignPlan` (`CampaignPlan→APPROVED` + `Campaign→PLAN_APPROVED` atomično, provjere:
item count, unique order, non-empty topic/goal). **Vrijedna implementer dizajn odluka**: svaki
item u novoj verziji plana dobija SVJEŽ id (ne zadržava stari), jer je `campaign_items.id`
globalni `PRIMARY KEY` (potvrđeno u migraciji) — stari SUPERSEDED plan i dalje drži stare id-e,
pa bi reuse pucao na constraint. `generate_social_post.py` NIJE diran (poznat gap — post
generation ne provjerava da je plan APPROVED — ostaje dokumentovan, namjerno van scope-a da se
izbjegne konflikt sa ACS-F1-012). Koordinator nezavisno reprodukovao pytest (499 u izolovanom
worktree-u, 512 na `main` post-merge)/ruff/mypy/import-boundaries (16) čisti, pročitao sav kod
(3 use-case fajla + svih 5 test fajlova, uključujući 2 prava atomicity testa na SQLite bazi za
edit i approve). MEDIUM risk → Claude-only review → odmah merge po §29. Merge commit `f230db0`
(`--no-ff` u `6aec5ca`). Worktree uklonjen (clean).

Prethodni entry (2026-09-02): **ACS-F1-012 (A12 dio 1 — Claim linter +
final ContentStatus derivacija) merged u main.** `claim_linter.py` (data-driven pravila iz
`resources/claim_rules/default_v1.yaml` — prohibited termini + currency simboli) primijenjen na
SVAKI claim: prohibited termin → `PROHIBITED` (nadjačava ČAK i `VERIFIED_BY_FACT`), numeric signal
(cijena/postotak/trajanje/datum/broj) na claim koji NIJE već `VERIFIED_BY_FACT` → `UNSUPPORTED` sa
reason code-om. `derive_content_status.py` (čista funkcija) → `NEEDS_REVIEW` ako ima
PROHIBITED/UNSUPPORTED, inače `DRAFT`, nikad `APPROVED`. Prežicao `GenerateSocialPost`
(ACS-F1-011) — zamijenio interim `GENERATING`/`NEEDS_REVIEW` logiku ovom finalnom. Ažurirao
POSTOJEĆE ACS-F1-011 testove (GENERATING→DRAFT na happy path-u, nije ih oslabio) + dodao novi
regression test koji dokazuje da `PROHIBITED` stvarno nadjačava fact-backed claim end-to-end.
Koordinator nezavisno reprodukovao pytest (472 u izolovanom worktree-u, 485 na `main` post-merge)/
ruff/mypy/import-boundaries (16) čisti, pročitao sav kod (linter, status derivacija, rewiring diff,
svi test fajlovi). Sekcija 38 (Content revisions) namjerno van scope-a, ide u budući ACS-F1-013.
MEDIUM risk → Claude-only review → odmah merge po §29. Merge commit `a4baeed` (`--no-ff` u
`4218750`). Worktree uklonjen (clean).

Prethodni entry (2026-09-02): **VAŽNO za sve buduće taskove: Task-ID
šema promijenjena (Human Owner odluka, `docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md` §31).**
`ACS-<FAZA>-NNN` (npr. `ACS-F1-014`) je zamijenjen sa **`FLOW-NNNN — <opisan naslov>`** za SVE
NOVE taskove, počevši od `FLOW-1000`. Broj je globalni sekvencijalni brojač (ne resetuje se po
fazi), i NIKAD se ne pominje sam bez naslova ("FLOW-1000 — SocialPostPayload persistence", ne
samo "FLOW-1000"). **Postojećih 14 taskova (ACS-P0-001..008, ACS-F1-001..014, ACS-GUI-001/002,
ACS-HOTFIX-001) OSTAJU pod starim imenima** — retroaktivno preimenovanje nije urađeno (već
DONE/merged, nema koristi od diranja branch/worktree/istorije). ACS-F1-012 i ACS-F1-014 (kontrakti
ispod, napisani PRIJE ove odluke) takođe zadržavaju stara imena. **Sljedeći task koji se otvori
dobija `FLOW-1000`, ne `ACS-F1-015`.**

Prethodni entry (2026-09-02): **Dva nova kontrakta napisana: ACS-F1-012
i ACS-F1-014.**

- **ACS-F1-012** ("A12 dio 1" — Claim linter + final `ContentStatus` derivacija, plan sekcije
  36-37, NE sekcija 38/revizije). Implementer: **Pi**, NIJE blokiran (sve od čega zavisi već
  postoji na main-u), worktree spreman, brief poslat
  (`agent_reports/2026-09-02-ACS-F1-012-brief-za-pi.md`). Prežicava već-mergovan
  `generate_social_post.py` (ACS-F1-011) — mijenja interim status logiku (`GENERATING`/
  `NEEDS_REVIEW`) na finalnu (`DRAFT`/`NEEDS_REVIEW`), zahtijeva ažuriranje ACS-F1-011-ovih
  postojećih testova (Pi upozoren da ih ažurira, ne oslabi).
- **ACS-F1-014** ("A10" plan-numeracija — Plan editing/versioning/approval: `EditCampaignPlan` +
  `ReorderCampaignItem` + `ApproveCampaignPlan`). **Task-ID namjerno ACS-F1-014, ne ACS-F1-013**
  — taj broj je već rezervisan za budući "Content revisions" task (plan sekcija 38) u
  ACS-F1-012-ovim dokumentima. Implementer TBD. Dokumentuje POZNAT, namjerno neriješen gap:
  `GenerateSocialPost` ne provjerava da je plan `APPROVED` prije generisanja posta — nije
  popravljeno u ovom tasku da se izbjegne fajl-konflikt sa paralelnim ACS-F1-012 (oba bi dirala
  `generate_social_post.py`). Nezavisan je od ACS-F1-012 (različit paket), može ići paralelno,
  ali **ne dira `generate_social_post.py`**.

**A8 (live provider adapter) ostaje odgođen po Human Owner odluci — "ostavljamo još malo".**

Prethodni entry (2026-09-02): **ACS-F1-011 (A11 — GenerateSocialPost)
merged u main.** `select_allowed_facts` (deterministički, samo `is_fact_usable` fact-ovi, lexical
matching) + `claim_validator` (plan sekcija 35, SAMO fact-id dio — FACT claim treba postojeći/
usable/dozvoljen fact_id → `VERIFIED_BY_FACT`, inače `UNSUPPORTED` sa reason code-om;
CTA/OPINION/CREATIVE → uvijek `NON_FACTUAL`) + `GenerateSocialPost` orchestration (učitava
Campaign/Plan/CampaignItem/BrandSnapshot/facts → `post_generation` prompt → AI poziv → schema+claim
validacija → interim status `NEEDS_REVIEW`/`GENERATING`, nikad `DRAFT` → atomic persist
`ContentPiece` sa `payload`-om iz ACS-F1-010). Integration test lanči `LoadBrandFixture` →
`CreateCampaign` → (ručno sastavljen plan) → `GenerateSocialPost` na pravoj SQLite bazi sa pravim
fact-om iz `brightsmile.json` fixture-a, PLUS bonus atomicity test (mid-persist failure ostavlja
`content_pieces` praznim). Koordinator nezavisno reprodukovao pytest (458 u izolovanom worktree-u,
471 na `main` post-merge)/ruff/mypy/import-boundaries (16) čisti, potvrdio `git status` scope
(sve novo, ništa van `application/posts/`+testovi), potvrdio bez `channels`/`ai_registry` importa.
MEDIUM risk → Claude-only review → odmah merge po §29. Merge commit `1c28789` (`--no-ff` u
`13d5b3a`). Worktree uklonjen (clean). **A11 (posljednji "odmah dostupan" application-layer
generation task) je time GOTOV — campaign plan I social post generation sad oba postoje end-to-end
nad mock AI adapterom.**

Prethodni entry (2026-09-02): **ACS-F1-010 merged u main (HIGH risk, puni
ciklus).** Implementer bio Claude (Human Owner odluka) — pošto Claude nije mogao sam sebe
reviewovati ("Implementer != reviewer"), review je uradio Codex (`PASS_WITH_NOTES`, nema blocking
findings, plus nezavisna adversarial provjera: None-vs-prazan-payload distinkcija preživljava
round-trip, potvrđeno na scratch bazi sa samo migracijama 0000-0002 pa dodavanjem 0003). Finalni
decision packet: `agent_reports/2026-09-02-ACS-F1-010-final-decision-packet.md`. Human Owner
odobrenje: "Odobravam". Merge commit `1de7423` (`--no-ff` u `faaa5d7`). Post-merge gate: 455
testova (scoped, isključujući MiniMax-ove necommit-ovane scratch fajlove — vidi napomena ispod),
`ruff check src tests scripts` čist, mypy čist, boundaries (16) čisti. Worktree uklonjen (clean).
**ACS-F1-011 sad UNBLOCKED — Pi je već krenuo** (worktree sinhronizovan sa main-om, `application/
posts/select_allowed_facts.py` i `claim_validator.py` u toku, necommit-ovano).

Prethodni entry (2026-09-02): **Dva nova kontrakta napisana za A11:
ACS-F1-010 i ACS-F1-011, oba OPEN, implementer TBD.** Pri pisanju A11 kontrakta otkriven pravi
gap: `ContentPiece` nema polje za sam generisani post (`SocialPostPayload`) — već dokumentovano
kao svjestan scope-granica u ACS-F1-006. Zatvaranje gap-a zahtijeva prvu `ALTER TABLE` migraciju
u projektu → HIGH risk po CLAUDE.md pravilu (SQLite/migrations), puni Codex+Claude+Human Owner
ciklus, ne streamlined MEDIUM put. Zato DVA odvojena kontrakta:

- **ACS-F1-010** (HIGH, blokira ACS-F1-011): aditivno `ContentPiece.payload` polje +
  `resources/migrations/0003_content_payload.sql` (`ALTER TABLE content_pieces ADD COLUMN
  payload_json TEXT`) + `SqliteContentRepository` read/write. GitNexus impact potvrđuje mali
  stvaran blast radius uprkos HIGH kategoriji (napomenuto u kontraktu za Codex/Human Owner
  kalibraciju review dubine).
- **ACS-F1-011** (MEDIUM, status BLOCKED dok ACS-F1-010 ne merguje): `GenerateSocialPost` —
  `select_allowed_facts` (deterministički, bez embeddings/vector DB) + Fact-ID validator (plan
  sekcija 35, SAMO taj dio — NE puni A12 linter) + orchestration. Dokumentovano interim
  `ContentStatus` pravilo: bilo koji `UNSUPPORTED` claim → `NEEDS_REVIEW`, inače `GENERATING`
  (NIKAD `DRAFT` — taj status je rezervisan za "nema upozorenja" ishod A12-ovog lintera, koji ovaj
  task ne implementira).

Oba worktree-a kreirana, implementer nije dodijeljen. Detalji:
`agent_reports/ACS-F1-010-task-contract.md`, `agent_reports/ACS-F1-011-task-contract.md`.

Prethodni entry (2026-09-02): **ACS-F1-009 (A9 — CreateCampaign +
GenerateCampaignPlan) merged u main.** Prvi task koji stvarno spaja ACS-F1-007 i ACS-F1-008 u
generation pipeline: `CreateCampaign` (validacija → mapper → atomic persist brief+campaign) i
`GenerateCampaignPlan` (Campaign→BrandSnapshot→CampaignBrief→prompt→`TextGenerationPort`→
schema+domain validacija→atomic persist plan + `Campaign.status→PLAN_GENERATED`). `ports/
repositories.py` diff je striktno aditivan (`get_brief`, ništa drugo promijenjeno — lično
diff-ovao). Integration test lanči SVA TRI use-case-a zajedno (`LoadBrandFixture` →
`CreateCampaign` → `GenerateCampaignPlan`) na pravoj SQLite bazi — prvi pravi end-to-end dokaz da
Faza 1 slojevi rade zajedno, ne samo izolovano. Atomicity (oba use-case-a) i role-diversity/
duplicate-topic domain provjere nezavisno reprodukovane na pravoj bazi. Koordinator nezavisno
reprodukovao pytest (439 u izolovanom worktree-u, 452 na `main` post-merge)/mypy/import-boundaries
čisti. **Napomena:** `main` trenutno ima paralelno, van formalnog task-sistema, MiniMax-ove
necommit-ovane izmjene (`presentation_webview/__main__.py` window-state persistencija + scratch
debug fajlovi `diagnose_close.py`/`test_window_close.py` u root-u) — zbog toga
`scripts/generate_phase0_gate_report.py` i whole-repo `ruff check .` trenutno FAIL lokalno (ruff
greške su isključivo u ta dva scratch fajla, ne u ičemu iz ACS-F1-009). CI na GitHub-u vidi samo
pushed/committed stanje pa ostaje zeleno — vidi CI red ispod. Ne dirati ta dva fajla/scratch
fajlove dok MiniMax ne javi da je gotovo (Human Owner eksplicitno tražio da se sačeka).
Worktree uklonjen (clean).

Prethodni entry (2026-09-02): **Human Owner live-pokrenuo pravu
pywebview aplikaciju i podijelio screenshot-e sva 5 sidebar ekrana** (Početna/Brend/Kampanje/
Kalendar/Podešavanja) na stvarnoj mašini, Edge WebView2, stilizovano (CSS/JS se učitavaju —
potvrđuje da `d71d84d` static-assets fix stvarno radi u praksi, ne samo u testu). Koordinator
pregledao svih 5 screenshot-a protiv `DEFAULT_FIXTURE` vrijednosti i `docs/gui-v3` reference:
Kalendar dani 3/5/9 sa tačnim eventima/bojama, Kampanje sva 3 reda sa tačnim statusima/brojevima,
Brend sve 3 činjenice + glas brenda bedževi + status datum, Podešavanja svih 5 providera "Nije
povezano", Početna brojke (3/18/6/12) i liste — sve se poklapa, nema vizuelnih grešaka. Ovo
zatvara jedinu preostalu prazninu iz ACS-GUI-002 review-a (implementer nije mogao live-testirati u
svom env-u, koordinator to nije ponovio pri merge-u za taj konkretan task — vidi ACS-GUI-002 red u
tabeli ispod). **Sva GUI-BASE površina (shell + svih 5 ekrana) je sada live-verifikovana, ne samo
test-verifikovana.**

Prethodni entry (2026-09-02): **Novi task napisan: ACS-F1-009** (A9 —
`CreateCampaign` + `GenerateCampaignPlan` use-caseovi, spaja ACS-F1-007 + ACS-F1-008 u prvi pravi
generation pipeline). A8 (pravi live provider adapter) EKSPLICITNO odgođen po Human Owner odluci —
ACS-F1-009 zavisi samo od `TextGenerationPort` Protocol-a, ne od konkretnog adaptera. Kontrakt
uključuje jednu usko-skopiranu aditivnu izmjenu na `CampaignRepositoryPort` (`get_brief` — zatvara
persistence read-path rupu, GitNexus upstream impact = LOW). Worktree kreiran:
`../ai-campaign-studio-worktrees/ACS-F1-009-campaign-brief-plan-generation`, branch
`task/ACS-F1-009-campaign-brief-plan-generation` @ `main 23b08ca`. Implementer: **Pi** (Human Owner odluka, 2026-09-02). Detalji:
`agent_reports/ACS-F1-009-task-contract.md`.

Prethodni entry (2026-09-02): **ACS-F1-007, ACS-F1-008, ACS-GUI-002 sva tri merged u main** (paralelni round, svi Claude-only MEDIUM review PASS, svi commit-ovani/push-ovani odmah po §29, bez posebnog Human Owner odobrenja per-task). Redoslijed merge-a: F1-007 → F1-008 → GUI-002, svi čisti merge-evi bez konflikta (disjoint `allowed_paths`). Nakon sva tri: **425 testova, ruff/mypy čisti, `python scripts/generate_phase0_gate_report.py` → `status: PASS`, svih 17 checkova true**. Detalji po tasku u tabeli ispod. Sve tri worktree uklonjene (clean, bez force-a); task branch-evi ostavljeni lokalno (isti pattern kao P0/F1-001..006).

Prethodni entry (2026-09-02): **POST-MERGE BAG NAĐEN I POPRAVLJEN (`d71d84d`): `write_all_pages()` nikad nije kopirao `static/app.css`/`app.js` u runtime temp direktorijum**, pa je Human Owner uživo vidio goli, nestilizovan HTML (svaka generisana stranica linkuje `../static/app.css` relativno, ali taj fajl nikad nije postojao u temp dir-u — 404). Promakao kroz OBA ACS-GUI-001 review round-a jer su svi postojeći testovi provjeravali samo STRING sadržaj href/src u HTML-u, nikad da referencirani fajl stvarno postoji na disku; round-2 live-launch test je provjerio samo da se `Chrome_WidgetWin` proces inicijalizuje (edgechromium, ne mshtml), ne da je stranica stvarno renderovana stilizovano. **Lekcija za buduće review-e GUI/file-generation koda: kad test tvrdi da fajl "postoji" ili je "linkovan", provjeriti stvaran filesystem side-effect, ne samo string u generisanom sadržaju.**

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
Aktivni plan: `AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md`. A3–A7 svi
DONE i merged (domain enums/entities, boundary schemas, business persistence, brand
fixture load, prompt+AI+mock infra). GUI paralelno: ACS-GUI-001/002 (shell + svih 5
sidebar ekrana) takođe merged. Sljedeći: A8 (live provider adapter(i) nad
`TextGenerationPort`) i/ili prvi pravi generation use-case (campaign plan/post) koji
koristi ACS-F1-007 (loaded brand) + ACS-F1-008 (prompts/AI port/mock adapter) zajedno.

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
| ACS-F1-003 | **DONE — merged u main** | Pi | Claude (MEDIUM) | Merge commit `b3369f1` (`--no-ff` u `380a279`, branch `task/ACS-F1-003-brand-fixture-schema`). `application/schemas/brand_fixture.py` (Pydantic) + `application/mappers/brand_fixture_mapper.py` (mapira u postojeće `Brand`/`BrandSnapshot`/`ApprovedFact`) + demo fixture `resources/fixtures/brightsmile.json`. `Restriction` NIJE proširen (implementer procijenio da fixture ne treba dodatna polja — dobra disciplina protiv "za svaki slučaj"). Worktree nije bio pre-kreiran od koordinatora (implementer ga sam napravio na `main @ 0a6dbc4` umjesto navedenog `0edae77` — obrazloženo i prihvaćeno, `0edae77` je bio predak kontrakt-commita). Koordinator nezavisno reprodukovao pytest/ruff/mypy/import-boundaries sa čistim `PYTHONPATH` overrideom, pročitao sav schema/mapper/test kod. MEDIUM risk → Claude-only review → odmah merge po §29. Post-merge gate PASS na `main` (290 testova ukupno nakon oba A4 merge-a). Worktree uklonjen (clean). |
| ACS-F1-004 | **DONE — merged u main** | Crush | Claude (MEDIUM) | Merge commit `894c457` (`--no-ff` u `380a279`, branch `task/ACS-F1-004-campaign-content-visual-schemas`). Pet Pydantic schema fajlova (campaign_brief, campaign_plan_output, social_post_generation_output, revision_output, visual_direction_output). `domain/visual/enums.py` čisto additivno prošireno (`ImageTreatment`/`LogoRule`/`CtaRule`) — verifikovano `git diff` da nijedan postojeći enum član nije dirat. Isti worktree-base napomena kao ACS-F1-003. Trivijalan `application/schemas/__init__.py` add/add merge konflikt (oba taska dodala docstring-only fajl) — koordinator ručno spojio u opisniji docstring, bez funkcionalnog uticaja. Koordinator nezavisno reprodukovao pytest/ruff/mypy/import-boundaries, pročitao sve schema fajlove + adversarial testove (odbijanje proizvoljnih enum stringova, dupli `order`, partial-update semantika). MEDIUM risk → Claude-only review → odmah merge po §29. Post-merge gate PASS na `main`. Worktree uklonjen (clean, nakon jednog retry-a zbog file lock-a). |
| ACS-F1-005 | **DONE — merged u main** | Pi | Claude (MEDIUM) | Merge commit `4d9e127` (`--no-ff` u `b3dd5ee`, branch `task/ACS-F1-005-brand-facts-persistence`). Svih 7 repository Protocol-a (`ports/repositories.py`, `@runtime_checkable`) + `SqliteBrandRepository`/`SqliteFactRepository` na postojećem P0 SQLite temelju (migracija `0001_brand_facts.sql`: brands/brand_snapshots/approved_facts/brand_snapshot_facts, `position` kolona na join tabeli da tuple `approved_fact_ids` round-trip-uje bez gubitka redoslijeda — nadograđeno u odnosu na kontrakt-DDL, dokumentovano). `save_*` idempotentni (`ON CONFLICT DO UPDATE`). `TelemetryRepositoryPort` samo interface, bez adaptera/migracije (Performance/Analytics deferral). Usput popravljena 2 P0 assertion-a u `tests/integration/database/test_migrations.py` (van `allowed_paths`, dokumentovano kao OUT_OF_SCOPE_FINDING u evidence izvještaju — postojeći testovi su hardkodirali tačno jednu migraciju, sad tolerantni na dodatne). Koordinator nezavisno reprodukovao pytest (303)/ruff/mypy/import-boundaries, pročitao sav port/adapter/test kod (round-trip dataclass `==`, idempotentnost, FK enforcement, `position`-ordering svi testirani). MEDIUM risk → Claude-only review → odmah merge po §29. Post-merge gate PASS na `main`. Worktree uklonjen (clean). |
| ACS-F1-006 | **DONE — merged u main** | Crush | Claude (MEDIUM) | Merge commit `6b93ab5` (`--no-ff` u `9def55c`, branch `task/ACS-F1-006-campaign-content-visual-persistence`). Bio blokiran na ACS-F1-005 (korak 2), sekvenca ispoštovana ispravno (provjerio worktree prije nastavka, javio blokadu, nije izmišljao lokalne Protocol definicije). Nakon ACS-F1-005 merge-a: `git merge main` u svoj branch, implementirao `SqliteCampaignRepository`/`SqliteContentRepository`/`SqliteVisualRepository`/`SqliteRevisionRepository` (migracija `0002_campaign_content_visual.sql`, isti DDL stil kao ACS-F1-005 uključujući `position` kolonu na `content_claims` join tabeli — primijenio Pi-jevu lekciju bez da mu je eksplicitno rečeno). `SocialPostPayload` namjerno nije perzistiran (domain `ContentPiece` nema `payload` polje, `ContentRepositoryPort` nema odgovarajuće metode — dokumentovano kao scope granica, ne tiha rupa). `repositories/__init__.py` ispravno NIJE dirao (van `allowed_paths`, ACS-F1-005 teritorija) — koordinator dodao re-export nakon merge-a (`9def55c`). Koordinator nezavisno reprodukovao pytest (320)/ruff/mypy/import-boundaries (52 architecture+integration), pročitao migraciju i sva 4 adaptera + round-trip/idempotentnost/izolacija/FK/ordering testove. MEDIUM risk → Claude-only review → odmah merge po §29. Post-merge gate PASS na `main`. Worktree uklonjen (clean). |
| ACS-GUI-001 | **DONE — merged u main** | MiniMax | Claude (MEDIUM, 2 runde) | Merge commit `cad003e` (`--no-ff` u `9259792`, branch `task/ACS-GUI-001-gui-base-shell`). Prvi produkcijski GUI task nakon G9 zatvaranja. Round 1: sigurnosni dio (edgechromium/debug/WebView2 fail-loud) odličan, ali 3 nalaza (static assets nisu doslovna kopija docs/gui-v3/shared/, neatražen `.lang-toggle`, sidebar/topbar nije DRY) blokirala merge — vidi `agent_reports/2026-09-02-ACS-GUI-001-review-claude-round1.md`. Round 2: sva tri riješena (SHA-256-verifikovana bajt-identična kopija; `.lang-toggle` uklonjen sa regression testom; `screens/_static_pages.py` `write_all_pages()` renderuje svih 5 ekrana kroz jedan `render_shell()`, DRY-enforcement test). Koordinator nezavisno reprodukovao pun test suite (346 na `main` post-merge)/ruff/mypy/import-boundaries, pročitao sav izmijenjen kod, verifikovao SHA-256 sam, i live-pokrenuo `python -m ai_campaign_studio.presentation_webview` na stvarnoj mašini — proces log potvrđuje pravi `Chrome_WidgetWin` (Edge WebView2), ne mshtml fallback. MEDIUM risk → Claude-only review (2 runde) → merge po §29 nakon PASS. Worktree uklonjen (clean). |
| ACS-F1-007 | **DONE — merged u main** | Pi | Claude (MEDIUM) | Merge commit `5bcbf41` (`--no-ff`, branch `task/ACS-F1-007-load-brand-fixture` @ `70127d2`). A6 `LoadBrandFixture` use-case (`application/brands/load_brand_fixture.py`) orkestrira ACS-F1-003 schema/mapper + ACS-F1-005 repositories: validira JSON kroz `BrandFixtureSchema` PRIJE bilo kakvog repository poziva, mapira, perzistira brand+facts+snapshot u jednoj `SqliteUnitOfWork` transakciji. Zavisi samo od `BrandRepositoryPort`/`FactRepositoryPort` + lokalni duck-typed `_UnitOfWork` Protocol (implementer ga dodao kao treći konstruktor parametar van kontrakt-primjera, opravdano za atomicity — prihvaćeno), bez SQLite importa. Atomicity STVARNO testirana na pravoj SQLite bazi (mid-load failure na 2. `save_fact`, sve 4 tabele COUNT=0 poslije), `fixture://` provenance provjerena čitanjem nazad, invalid-fixture (prazan `facts`) odbijen od `BrandFixtureSchema`-inog `_validate_facts` validatora prije ijednog repo poziva. Implementer sam kreirao worktree na `main @ ed5b8d4` umjesto navedenog `b4b324f` (noviji commit, prihvatljivo, dokumentovano). Koordinator nezavisno reprodukovao pytest (352 u izolovanom worktree-u, 354 na `main` post-merge)/ruff/mypy/import-boundaries (15), pročitao use-case + oba test fajla + `SqliteUnitOfWork.__exit__` semantiku. MEDIUM risk → Claude-only review → odmah merge po §29. Worktree uklonjen (clean). |
| ACS-F1-008 | **DONE — merged u main** | Crush | Claude (MEDIUM) | Merge commit `2aed9fe` (`--no-ff`, branch `task/ACS-F1-008-prompt-ai-mock` @ `0aaef6d`). A7 — `ports/ai.py` (`AIMessage`/`AIRequest`/`AIResponse`/`AITelemetry` + `TextGenerationPort` Protocol) i `ports/prompts.py` (`PromptDefinition` + `PromptRepositoryPort`), oba framework-neutral (nema yaml/http/SDK importa — verifikovano čitanjem). `YamlPromptRepository` učitava i validira svih 8 metadata polja za svih 5 obaveznih promptova (`campaign_plan`/`post_generation`/`revision`/`visual_direction`/`ab_control`) — nedostajuće/null polje baca `ValueError` pri `get()`, nepostojeća verzija isto (bez silent fallback-a). `ab_control/v1.yaml` provjeren ručno (koordinator čitao fajl) — ne sadrži nijedan CampaignRole naziv, namjerna dizajn granica ispoštovana. `MockAdapter` implementira svih 5 modova (deterministic/error/invalid-schema/rate-limit/telemetry), bez network poziva, bez business logike. `ports/ai_registry.py`/`ai_registry/` netaknuti (potvrđeno `git status`). Proširio `tests/architecture/test_import_boundaries.py` za `infrastructure/ai/` (eksplicitno dozvoljeno acceptance stavkom, isti pattern kao ACS-GUI-001 za `presentation_webview/`) — jedina izmjena van `allowed_paths`. Koordinator nezavisno reprodukovao pytest (362 u izolovanom worktree-u, 370 na `main` post-merge)/ruff/mypy/import-boundaries (16), pročitao sva 4 core fajla + svih 5 YAML promptova (skriptom provjerio da svih 8 polja postoje u sve 5 fajla). MEDIUM risk → Claude-only review → odmah merge po §29. Čist merge, bez konflikta sa ACS-F1-007. Worktree uklonjen (clean). |
| ACS-GUI-002 | **DONE — merged u main** | MiniMax | Claude (MEDIUM) | Merge commit `af6723d`-predecessor (`--no-ff` u `2aed9fe`, branch `task/ACS-GUI-002-remaining-sidebar-screens` @ `99f3502`). Preostala 4 sidebar ekrana (Brend/Kampanje/Kalendar/Podešavanja) zamijenila ACS-GUI-001 placeholder sadržaj realnim, fixture-driven `render_body()` — isti pattern kao Početna (frozen dataclass fixtures + `html.escape()`). Koordinator uporedio string-po-string protiv `docs/gui-v3/screens/{02,03,06,09}_*/index.html` — Brend markup je bajt-za-bajt identičan referenci; Kampanje ispravno pretvorio SVA tri "Otvori" dugmeta (uključujući referenci-in jedini pravi `<a href="../04_opis_kampanje/...">`) u `data-action="toast"` stub (ekran ne postoji u `presentation_webview`); Kalendar ispravno izostavio `?campaign=` banner/stepper (`data-campaign-only` blokovi u referenci) — samo globalni pogled portovan; Podešavanja bajt-za-bajt identičan. Nijedan `<a href>` ka nepostojećem ekranu, nema remote asset referenci (CSP `default-src 'self'` netaknut), `shell/`/`screens/__init__.py`/`_static_pages.py`/`pocetna/`/`static/`/`__main__.py` svi netaknuti (git diff potvrdio). 55 novih testova (fixture-driven invariant, XSS escaping, CSS klase, no-`<a href>`, no-remote-asset po ekranu). Očekivani test failure (`test_write_all_pages_placeholder_screens_carry_only_their_label`, van implementer-ovog `allowed_paths`) reprodukovan i popravljen od koordinatora nakon merge-a (`af6723d`) — preimenovan u `test_write_all_pages_screens_carry_real_content`, sada provjerava stvaran sadržaj (`BrightSmile Oral Care`/`Proljetna kolekcija`/`queue/retry`/`AI provajderi`) umjesto uklonjenog `"ACS-GUI-002"` placeholder markera. Koordinator nezavisno reprodukovao pytest (393 u izolovanom worktree-u minus gate-report subprocess artefakt, 425 na `main` post-merge)/ruff/mypy/import-boundaries. Live pywebview launch NIJE ponovljen za ovaj task pri merge-u (implementer je test-env bez display/webview modula; prethodni ACS-GUI-001 live-test je tada bio jedina live-launch evidencija). **Praznina zatvorena naknadno (2026-09-02, isti dan): Human Owner je live-pokrenuo aplikaciju i podijelio screenshot-e svih 5 ekrana — koordinator ih uporedio protiv `DEFAULT_FIXTURE`, sve tačno, stilizovano, bez grešaka** (vidi entry na vrhu fajla). MEDIUM risk → Claude-only review → odmah merge po §29. Worktree uklonjen (clean). |
| ACS-F1-009 | **DONE — merged u main** | Pi | Claude (MEDIUM) | Merge commit `4a7d643` (`--no-ff` u `5134b4c`, branch `task/ACS-F1-009-campaign-brief-plan-generation`). A9 — `CreateCampaign` (validira `CampaignBriefInput` → `map_campaign_brief` → atomic persist brief+DRAFT campaign) + `GenerateCampaignPlan` (učitava Campaign/BrandSnapshot/CampaignBrief → `LEAD_GENERATION_V1` template → `PromptRepositoryPort.get("campaign_plan","1")` → `AIRequest` → `TextGenerationPort.generate` → `validate_campaign_plan_output` + deterministička domain validacija (bez duplikata tema, min. 2 distinktne role kad ima ≥2 itema, implementer dokumentovao prag) → atomic persist plan + `Campaign.status→PLAN_GENERATED`). Oba use-case-a zavise samo od portova + lokalnog `_UnitOfWork` Protocol-a (isti obrazac kao ACS-F1-007). Dodao TAČNO jednu aditivnu metodu `CampaignRepositoryPort.get_brief()` + SQLite implementaciju (`_brief_from_row`) — koordinator line-by-line diff-ovao `ports/repositories.py`, potvrđeno da nijedna postojeća metoda nije dirana. Integration test `test_end_to_end_fixture_to_plan` lanči `LoadBrandFixture` → `CreateCampaign` → `GenerateCampaignPlan` zajedno na pravoj SQLite bazi — prvi pravi cross-task end-to-end dokaz. Atomicity za oba use-case-a testirana mid-failure na pravoj bazi (`save_campaign` failuje nakon uspješnog `save_plan`/`save_brief` → sve rollback-uje). Koordinator nezavisno reprodukovao pytest (439 u izolovanom worktree-u, 452 na `main` post-merge)/mypy/import-boundaries (16) čisti; whole-repo `ruff check .` i `generate_phase0_gate_report.py` trenutno kontaminirani MiniMax-ovim necommit-ovanim scratch fajlovima (van scope-a ovog taska — vidi napomena na vrhu fajla), `ruff check src tests scripts` (tracked-only) čist. MEDIUM risk → Claude-only review → odmah merge po §29. Worktree uklonjen (clean). |
| ACS-F1-010 | **DONE — merged u main** | Claude | Codex (HIGH) | Merge commit `1de7423` (`--no-ff` u `faaa5d7`, branch `task/ACS-F1-010-social-post-payload-persistence`). Aditivno `ContentPiece.payload: SocialPostPayload \| None = None` (jedno trailing polje) + prva `ALTER TABLE` migracija u projektu (`resources/migrations/0003_content_payload.sql` — `content_pieces.payload_json TEXT`, nullable) + `SqliteContentRepository` read/write proširen. Zatvara persistence gap dokumentovan u ACS-F1-006 (ContentPiece nije imao mjesto za stvaran generisan post) koji bi inače blokirao ACS-F1-011. **Netipičan implementer**: Claude (Human Owner odluka) — pošto je Claude i koordinator i implementer na ovom tasku, review NIJE mogao biti "Claude-only" (Implementer != reviewer) — umjesto toga Codex je uradio jedinu review rundu, `PASS_WITH_NOTES`, bez blocking findings, plus SVOJA nezavisna adversarial provjera (scratch DB samo sa 0000-0002, potvrda da `payload_json` ne postoji, pa primjena 0003, potvrda da se pojavljuje, pa `payload=None` vs namjerno prazan `SocialPostPayload` — oba ostaju semantički različita nakon round-trip-a). Finalni decision packet: `agent_reports/2026-09-02-ACS-F1-010-final-decision-packet.md`. Human Owner odobrenje: "Odobravam". Post-merge gate: 455 testova (scoped `ruff check src tests scripts` čist — whole-repo `ruff`/gate-report i dalje kontaminirani MiniMax-ovim necommit-ovanim scratch fajlovima, nepovezano sa ovim taskom), mypy čist, boundaries (16) čisti. Worktree uklonjen (clean). |
| ACS-F1-011 | **DONE — merged u main** | Pi | Claude (MEDIUM) | Merge commit `1c28789` (`--no-ff` u `13d5b3a`, branch `task/ACS-F1-011-allowed-facts-post-generation`). A11 — `select_allowed_facts` (deterministički, samo `is_fact_usable` fact-ovi, case-insensitive lexical substring matching protiv `facts_needed`, prazan `facts_needed` → prazan set, nije greška) + `claim_validator` (plan sekcija 35 TAČNO, ne 36 — FACT claim treba postojeći+usable+dozvoljen fact_id → `VERIFIED_BY_FACT`, inače `UNSUPPORTED` sa reason code-om `missing-fact-id`/`fact-not-found`/`fact-not-approved`/`fact-not-offered`; CTA/OPINION/CREATIVE → uvijek `NON_FACTUAL`) + `GenerateSocialPost` (učitava Campaign/Plan/CampaignItem in-memory pretragom kroz `plan.items`/BrandSnapshot/facts → `post_generation` prompt → `AIRequest` → AI poziv → `SocialPostGenerationOutput.model_validate` (Pydantic greška PRIJE perzistencije) → claim-po-claim validacija → interim `ContentStatus` pravilo TAČNO kako je kontrakt specificirao (bilo koji `UNSUPPORTED` → `NEEDS_REVIEW`, inače `GENERATING`, NIKAD `DRAFT`) → atomic persist `ContentPiece` sa `payload`-om iz ACS-F1-010). Zavisi samo od portova + lokalnog `_UnitOfWork` Protocol-a — koordinator potvrdio bez `channels`/`ai_registry` importa (`grep` sweep). Integration test lanči `LoadBrandFixture` → `CreateCampaign` → (ručno sastavljen plan, plan generation već pokriven ACS-F1-009) → `GenerateSocialPost` na pravoj SQLite bazi sa pravim fact-om iz `brightsmile.json`, PLUS bonus atomicity test (mid-persist failure na `save_content_piece` ostavlja `content_pieces` praznim — nije bio formalno tražen acceptance kriterijum za single-write use-case, implementer ga ipak dodao). Koordinator nezavisno reprodukovao pytest (458 u izolovanom worktree-u, 471 na `main` post-merge)/ruff/mypy/import-boundaries (16) čisti, pročitao sav kod (3 core fajla + 4 test fajla) i git status scope (sve novo, ništa van `application/posts/`+testovi). MEDIUM risk → Claude-only review → odmah merge po §29. Worktree uklonjen (clean). **A11 gotov — campaign plan I social post generation sad oba postoje end-to-end nad mock AI adapterom, isti obrazac spreman za A8 (live provider) kad god se odluči da ide.** |
| ACS-F1-012 | **DONE — merged u main** | Pi | Claude (MEDIUM) | Merge commit `a4baeed` (`--no-ff` u `4218750`, branch `task/ACS-F1-012-claim-linter-status`). "A12 dio 1" — `claim_linter.py` (data-driven pravila iz `resources/claim_rules/default_v1.yaml`) primijenjen na SVAKI claim bez obzira na trenutni status: prohibited/riskantan termin (case-insensitive substring) → `PROHIBITED` + `prohibited-claim` reason (nadjačava ČAK i `VERIFIED_BY_FACT` — riskantan jezik ostaje riskantan i kad je fact-backed); numeric signal (cijena/postotak/trajanje/datum/goli broj, provjereno tim redoslijedom) na claim koji NIJE već `VERIFIED_BY_FACT` → `UNSUPPORTED` sa odgovarajućim reason code-om. `derive_content_status.py` (čista funkcija) — bilo koji `PROHIBITED`/`UNSUPPORTED` → `NEEDS_REVIEW`, inače `DRAFT`, nikad `APPROVED`. Prežicao `GenerateSocialPost` (ACS-F1-011) — zamijenio interim `GENERATING`/`NEEDS_REVIEW` logiku ovom finalnom; ažurirao POSTOJEĆE ACS-F1-011 testove (happy path `GENERATING`→`DRAFT`, nije ih oslabio/obrisao) + dodao novi regression test (`test_prohibited_claim_yields_needs_review`) koji dokazuje da `PROHIBITED` stvarno nadjačava fact-backed claim end-to-end kroz cijeli use-case, ne samo u izolovanom linter unit testu. Sekcija 38 (Content revisions) namjerno van scope-a — ide u budući ACS-F1-013. Koordinator nezavisno reprodukovao pytest (472 u izolovanom worktree-u, 485 na `main` post-merge)/ruff/mypy/import-boundaries (16) čisti, pročitao sav kod (linter, status derivacija, rewiring diff, oba nova + oba ažurirana test fajla) i git status scope (`select_allowed_facts.py`/`claim_validator.py`/`domain/` potvrđeno netaknuti). MEDIUM risk → Claude-only review → odmah merge po §29. Worktree uklonjen (clean). |
| ACS-F1-014 | **DONE — merged u main** | Crush | Claude (MEDIUM) | Merge commit `f230db0` (`--no-ff` u `6aec5ca`, branch `task/ACS-F1-014-campaign-plan-editing`). "A10" (plan-numeracija, ne task-ID ACS-F1-010) — `EditCampaignPlan` (pozivalac šalje cijelu novu listu itema; stari DRAFT→SUPERSEDED, novi→DRAFT `version+1`, atomično; editovanje APPROVED/SUPERSEDED odbijeno) + `ReorderCampaignItem` (validira permutaciju, `order→1..N`, delegira na `EditCampaignPlan` — DRY potvrđen čitanjem) + `ApproveCampaignPlan` (`CampaignPlan→APPROVED` + `Campaign→PLAN_APPROVED` atomično). Implementer dizajn odluka: svaki item nove verzije dobija SVJEŽ id (`campaign_items.id` je globalni PRIMARY KEY, stari SUPERSEDED plan drži stare id-e — reuse bi pucao na constraint) — dobro uočeno, jasno dokumentovano, koordinator nezavisno potvrdio protiv migracije. `generate_social_post.py` NIJE diran (poznat gap, namjerno van scope-a da se izbjegne konflikt sa ACS-F1-012). Koordinator nezavisno reprodukovao pytest (499 u izolovanom worktree-u, 512 na `main` post-merge)/ruff/mypy/import-boundaries (16) čisti, pročitao sav kod (3 use-case fajla + 5 test fajlova, uključujući 2 prava atomicity testa na SQLite bazi). MEDIUM risk → Claude-only review → odmah merge po §29. Worktree uklonjen (clean). |
| FLOW-1000 — Plan-approved guard u GenerateSocialPost | **DONE — merged u main** | Pi | Claude (MEDIUM) | Merge commit `92d2b0c` (`--no-ff` u `1e16b1a`, branch `task/FLOW-1000-plan-approved-guard`). Prvi task pod novom `FLOW-NNNN` šemom (§31). Jedna guard klauzula: `GenerateSocialPost.execute()` odbija plan koji nije `APPROVED` (`InvariantViolation`, prije `campaign_item` pretrage/AI poziva/perzistencije) — zatvara poznat gap iz ACS-F1-014. Postojeći happy-path testovi ažurirani na `APPROVED` fixture (nisu oslabljeni); novi negativni testovi dokazuju `ai_port.calls == []` za DRAFT/SUPERSEDED plan (unit) + nula persistovanih `content_pieces` (integration, prava SQLite baza). Koordinator nezavisno reprodukovao pytest (502 u izolovanom worktree-u, 516 na `main` post-merge)/ruff/mypy/import-boundaries (16) čisti, pročitao cio diff. MEDIUM risk → Claude-only review → odmah merge po §29. Worktree uklonjen (clean). |
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

**Osvježeno na `main @ af6723d`** poslije merge-a ACS-F1-007 + ACS-F1-008 + ACS-GUI-002
(2026-09-02, isti `.venv`, `.pth` provjeren):

```text
python -m pytest -q                → 425 passed
python -m ruff check .             → All checks passed!
python -m mypy src                 → Success: no issues found in 108 source files
python scripts/validate_resources.py → All resources are valid
python scripts/check_no_secrets.py   → NO CONFIRMED SECRET IN TRACKED FILES
python -m ai_campaign_studio.main --health-check → status: ok
python scripts/generate_phase0_gate_report.py → status: PASS, svih 17 checkova true
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

Reindeksirano poslije merge-a ACS-F1-007 + ACS-F1-008 + ACS-GUI-002:

```text
Indexed commit: af6723d (= trenutni main HEAD)
Status: up-to-date
6456 nodes | 8584 edges | 167 clusters | 71 flows
```

`mcp__gitnexus__*` MCP alati su dostupni u koordinator sesiji (pored CLI), ali dijele istu
worktree-binding limitaciju — vidi blokatore. Prije narednog pre-impact-a, ako main odmakne,
ponovo pokrenuti `npx gitnexus analyze --skip-agents-md` pa `npx gitnexus status`.

## Sljedeći task

**Cijeli campaign application-layer pipeline je sad GOTOV, end-to-end, i ispravan po svim
domain invarijantama iz plana**: domain sloj (ACS-F1-001/002), boundary schemas (ACS-F1-003/004),
business persistence (ACS-F1-005/006), fixture load (ACS-F1-007), prompt repository + AI port +
mock adapter (ACS-F1-008), CreateCampaign + GenerateCampaignPlan (ACS-F1-009), SocialPostPayload
persistence (ACS-F1-010, HIGH), GenerateSocialPost (ACS-F1-011), claim linter + status derivation
(ACS-F1-012), plan editing/versioning/approval (ACS-F1-014), plan-approved guard (**FLOW-1000**)
svi merged u main (2026-09-02/03), 516 testova, sve zeleno. GUI paralelno: svih 5 sidebar ekrana
takođe merged i **live-verifikovano od Human Owner-a**.

Tok: LoadBrandFixture → CreateCampaign → GenerateCampaignPlan → EditCampaignPlan/
ReorderCampaignItem/ApproveCampaignPlan → GenerateSocialPost (sad ODBIJA ne-APPROVED plan) →
claim_linter/derive_content_status → finalan `ContentStatus` (`DRAFT`/`NEEDS_REVIEW`). Svaki
korak atomičan, nezavisno testiran, lančano integration-testiran preko pravih SQLite baza. Nema
poznatih otvorenih gap-ova u ovom pipeline-u trenutno.

Nijedan kontrakt trenutno OPEN. Kandidati za sljedeći **`FLOW-NNNN`** task (broj nastavlja od
`FLOW-1001` — `FLOW-1000` je potrošen): **"Content revisions" task** (plan sekcija 38,
`revise_content_piece.py` — jedini preostali dio A12 grupe), **A8 — live provider adapter** (i
dalje odgođen po Human Owner odluci, 2026-09-02). GUI dizajn iteracija (vidi ispod) je paralelan,
nezavisan trak — čeka MiniMax-ov trenutni popravak (u toku, sad dira sva 4 GUI-relevantna sloja:
`shared/`, `screens/_static_pages.py`, `shell/__init__.py`, `static/`, plus novi
`brand-logo.png` asset i Codex-ove scratch probe skripte u root-u — koordinator i dalje ne dira
ništa od toga dok se ne javi da je gotovo). **ACS-GUI-003** (campaign workflow ekrani) i dalje
čeka da application use-caseovi budu dovoljno razvijeni da ih GUI stvarno poziva — što je sad
sve tačnije, pipeline je kompletan.

## GUI dizajn — otvoreno pitanje (Human Owner feedback, 2026-09-02)

Human Owner nije zadovoljan trenutnim izgledom uprkos tome što je live-verifikacija (screenshot-i,
vidi gore) potvrdila da render radi ispravno: **paneli su nekonzistentni, pojavljuje se skrol
(cilj je "jedan pogled" bez skrolovanja), blizu smo mokapa ali ne na zamišljenom nivou.**
Dogovoreni pristup: **prvo iterirati na `docs/gui-v3` mokapima** (brzo, vizuelno, bez re-wiring
troška), tek onda prenijeti odobreni dizajn u `presentation_webview/`. **Trenutno na čekanju:**
MiniMax radi necommit-ovane popravke direktno u `presentation_webview/__main__.py` (window-state
persistencija, van formalnog task-sistema — vidi napomena na vrhu fajla) — koordinator čeka da
MiniMax završi prije nego što dirne bilo šta u `docs/gui-v3`/`presentation_webview/`, po
eksplicitnom zahtjevu Human Owner-a. Target veličina prozora za "bez skrola" cilj NIJE utvrđena
(pitanje ostalo otvoreno kad je razgovor skrenuo na "sačekajmo MiniMax-a").

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
`presentation_webview/`/`js_api`.

## G9 — UI Framework Gate: ZATVOREN (2026-09-02)

Plan (`AI_Campaign_Studio_Faza_1_v1_4_...md` sekcija 3, G9) formalno traži uporedni
`pywebview vs PySide6` spike prije zaključavanja UI frameworka; AR5 (sekcija 4) eksplicitno
zabranjuje production `presentation_webview/`/`presentation_qt/` arhitekturu prije G9. SPIKE-001
je testirao SAMO pywebview (nikad nije rađen PySide6 spike). **Human Owner je eksplicitno
odlučio (2026-09-02) zatvoriti G9 bez PySide6 poređenja** — obrazloženje: pywebview je već
dokazan kroz SPIKE-001 (BHS layout robustan, real desktop window radi, Windows nativni chrome),
i sada postoji `docs/PYWEBVIEW_SECURITY.md` hardening politika. **UI framework je zaključan:
pywebview.** `presentation_webview/` production wiring je od ovog trenutka dozvoljen (prvi
task: ACS-GUI-001, MiniMax, GUI-BASE shell). Ovo NE poništava potrebu da se
`docs/PYWEBVIEW_SECURITY.md` politika primijeni od prvog reda tog koda.

Sljedeći koraci za GUI: kad se A4+ application/use-case slojevi za Brand/Campaign pojave, otvoriti
formalni lightweight task (van Task Contract sistema, po uzoru na SPIKE-001, ili kao pravi F1
contract — odlučiti tada) za wiring `docs/gui-v3/` u `presentation_webview/` po strukturi iz
`INTEGRATION.md`.
