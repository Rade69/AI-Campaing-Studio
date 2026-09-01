# AI Campaign Studio — kanonski agentski workflow

**Status:** ACTIVE  
**Namjena:** jedini kanonski procesni dokument za Claude, Codex, Pi, Crush i buduće coding agente  
**Project architecture source of truth:** `AI_Campaign_Studio_Faza_0_6_Channel_Model_LLM_Registry.md`  
**Foundation execution source:** aktivni Implementation Phase 0 dokument iz `.agent/CURRENT_STATE.md`  
**Business implementation source:** aktivni Faza 1 dokument iz `.agent/CURRENT_STATE.md`

---

# 1. Osnovni princip

Ništa se ne prihvata na riječ.

Tvrdnje:

```text
"gotovo"
"radi"
"testovi prolaze"
"nema uticaja"
"scope je izolovan"
"nije prekršena arhitektura"
```

moraju imati provjerljiv dokaz.

Agent koji je implementirao task nije autoritet za kvalitet sopstvenog rada.

---

# 2. Uloge

## Human Owner

Jedini konačni autoritet za:

- scope;
- prioritet;
- business/product odluke;
- prihvatanje kompromisa;
- merge approval.

Bez eksplicitnog Human Owner odobrenja nema merge-a.

## Koordinator — default Claude Code

Odgovornosti:

- čita aktivne projektne planove;
- koristi GitNexus prije pakovanja MEDIUM/HIGH taska;
- piše Task Contract PRIJE koda;
- određuje risk tier;
- bira implementera i reviewere;
- provjerava dependency/branch baseline;
- priprema worktree;
- provjerava stvarni diff i execution evidence;
- ne vjeruje implementer reportu na riječ;
- radi ili koordinira merge;
- pokreće post-merge gate;
- ažurira `.agent/CURRENT_STATE.md`.

Koordinator nije automatski reviewer ako je implementirao task.

Codex može biti koordinator ako Human Owner tako odluči.

## Implementeri — default Pi / Crush

Odgovornosti:

- rade samo unutar `allowed_paths`;
- slijede tačan Task Contract;
- prije izmjene rade propisani GitNexus read-set;
- ne mijenjaju arhitekturu samostalno;
- ne šire scope;
- pišu testove predviđene kontraktom;
- pokreću verification;
- predaju doslovan output;
- prijavljuju `OUT_OF_SCOPE_FINDING`.

Ne commit-uju/push-uju sami osim ako Task Contract ili Human Owner to eksplicitno traži.

## Codex — default adversarial/test reviewer

Primarni fokus:

- da li test zaista dokazuje acceptance;
- da li test pada na poznatoj lošoj varijanti kada je to relevantno;
- regression risk;
- edge cases;
- diff protiv Task Contracta;
- GitNexus blast radius/detect-changes nalaz;
- semantic loopholes.

## Claude — default architecture/integration reviewer

Primarni fokus:

- Clean/Hexagonal granice;
- dependency direction;
- domain/application purity;
- provider/model separation;
- Channel/Platform/Format granice;
- persistence/transaction consistency;
- lifecycle/threading/bootstrap;
- integration sa ostatkom projekta;
- scope discipline.

Claude i Codex ne treba mehanički da ponavljaju identičnu provjeru.

---

# 3. Risk tier

## LOW

Primjeri:

- tekst/resurs;
- izolovan translation key;
- mala konfiguraciona korekcija;
- lokalni test bez runtime behavior promjene.

Proces:

```text
Task Contract
→ implementer
→ targeted verification
→ 1 nezavisni reviewer (Claude ili Codex)
→ Human Owner approval
→ merge
→ post-merge gate
```

GitNexus nije obavezan samo ako je task dokazano izolovan i ne dira shared symbol/contract.

## MEDIUM

Primjeri:

- use-case promjena;
- registry ponašanje;
- shared dataclass/protocol;
- repository adapter;
- JobManager;
- prompt schema;
- ContentPiece pipeline;
- UI state/facade;
- renderer contract.

Proces:

```text
GitNexus pre-impact
→ Task Contract
→ worktree + claim
→ implementer
→ GitNexus detect-changes
→ targeted + full relevant verification
→ 1 formal reviewer
→ Claude architecture check ako reviewer nije Claude i task dira boundary/shared contract
→ Human Owner approval
→ merge
→ post-merge gate
→ GitNexus re-index
```

## HIGH

Primjeri:

- DB schema/migration sa postojećim podacima;
- SecretStore/security invariant;
- API credential handling;
- fact/provenance invariant;
- destructive migration;
- architecture-wide refactor;
- central bootstrap/composition rewrite;
- concurrency/lifecycle promjena koja može korumpirati state;
- hard gate koji utiče na čitav project behavior.

Proces:

```text
GitNexus pre-impact
→ HIGH Task Contract + rollback plan
→ worktree + claim
→ implementer
→ targeted/adversarial tests
→ full verification
→ GitNexus detect-changes + impact review
→ Codex independent review
→ Claude independent review
→ Human Owner approval
→ merge
→ post-merge full gate
→ GitNexus re-index
```

Ako Claude ili Codex implementira HIGH task, taj isti agent ne može biti formalni reviewer.

Tada Task Contract mora eksplicitno navesti degradirani review raspored ili fresh-reviewer zamjenu; Human Owner mora to odobriti.

---

# 4. Privremeno pojačan standard za Implementation Phase 0

P0 postavlja temelj cijelog projekta, zato se standard privremeno pojačava.

Za sve P0 taskove koji diraju:

```text
architecture boundaries
config/path contracts
localization contracts
Channel/Platform/Format registry
AI Provider/Model Registry
SecretStore
SQLite/migrations/UoW
JobManager
Presentation contracts
bootstrap/composition root
CI/security gates
```

koristi:

```text
Pi/Crush implementation
→ Codex adversarial/test review
→ Claude architecture/integration review
→ Human Owner approval
```

Za trivijalne P0 setup korake (folder, .gitignore, metadata) koordinator može označiti LOW i koristiti jednog reviewera.

---

# 5. Obavezni read protocol svakog taska

Prije izmjene:

```text
1. AGENTS.md
2. CLAUDE.md
3. docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md
4. .agent/CURRENT_STATE.md
5. .agent/PROJECT_MAP.md
6. konkretan Task Contract
7. .agent/TASK_ROUTING.md
8. GitNexus context/impact ako je obavezan
9. relevantni source + tests
```

Ne čitati cijeli `docs/` i cijeli `agent_reports/` bez potrebe.

---

# 6. Task Contract je obavezan

Svaki task ima:

```text
agent_reports/<TASK-ID>-task-contract.md
```

Piše se prije implementacije.

Obavezna polja:

```yaml
task_id:
phase:
title:
risk:
coordinator:
implementer:
reviewers:
status:
created_at:
dependencies:
allowed_paths:
forbidden_paths:
gitnexus_required:
adversarial_required:
```

Tijelo mora definisati:

1. kontekst;
2. objective;
3. source-of-truth reference;
4. pre-change GitNexus evidence;
5. tačne implementation steps;
6. acceptance;
7. verification commands;
8. allowed/forbidden paths;
9. test strategy;
10. review fokus;
11. rollback ako je MEDIUM/HIGH;
12. dependency baseline;
13. worktree/branch;
14. coordination claim.

Task Contract je pretpostavka koja može biti pogrešna.

Ako implementer pronađe stvarnu nužnu korekciju:

```yaml
finding: OUT_OF_SCOPE_FINDING
description:
location:
risk:
evidence:
proposed_task:
```

Ne širi task tiho.

---

# 7. GitNexus — hard gate

GitNexus je obavezan dio procesa.

Detaljan protocol je u:

`.agent/GITNEXUS_PROTOCOL.md`

## Kada je obavezan

Uvijek za:

- MEDIUM;
- HIGH;
- refactor;
- shared interface/protocol/dataclass;
- repository contract;
- migration/schema;
- bootstrap/composition;
- Channel/Platform/Format registry contract;
- AI provider/model contract;
- localization contract;
- JobManager/concurrency;
- public API;
- promjenu funkcije/klase sa više callera;
- rename/move shared simbola.

LOW task može preskočiti samo ako Task Contract eksplicitno kaže:

```yaml
gitnexus_required: false
reason: "isolated resource-only change; no shared symbol"
```

## Pre-change

Koordinator/implementer mora imati:

```text
Repository/worktree identity
Index freshness
Target symbols
Upstream dependants
Downstream dependencies kada je relevantno
Affected execution flows
Risk/blast radius
Unknown/truncated/partial state
```

Ako GitNexus otkrije širi scope nego Task Contract:

```text
STOP
```

Redefinisati contract prije koda.

## Pre-review

Obavezno:

```text
detect-changes
```

za MEDIUM/HIGH.

Nulti rezultat nije validan ako je index stale, repo/worktree pogrešno bindovan, rezultat partial/truncated ili diff očigledno postoji.

## Post-merge

Na main:

```text
re-index / update index
```

tako da sljedeći agent ne radi sa zastarjelim grafom.

---

# 8. Git worktree

Svaki netrivijalan task:

```text
../ai-campaign-studio-worktrees/<TASK-ID>-<short-name>
```

Branch:

```text
task/<TASK-ID>-<short-name>
```

Prije branch-a:

```text
git status --short --branch
git log -5 --oneline
git log -1 --oneline main
```

Ako task zavisi od prethodnog taska, dokazati da je dependency STVARNO merged u main.

Ne granati sa zastarjelog main-a.

---

# 9. Coordination claim

Prije paralelnog rada:

```bash
python scripts/coordination.py claim --task ACS-P0-004 --agent pi --paths src/ai_campaign_studio/localization,resources/i18n,tests/unit/localization
```

Provjera:

```bash
python scripts/coordination.py status
```

Na kraju:

```bash
python scripts/coordination.py release --task ACS-P0-004
```

Claimovati konkretne paths.

Ne claimovati cijeli `agent_reports/`.

Ako claim konflikt postoji:

```text
NE pregaziti
```

ili redizajnirati task ili raditi sekvencijalno.

---

# 10. Paralelizacija

Dva taska mogu paralelno samo ako:

```text
allowed_paths(A) ∩ allowed_paths(B) = ∅
```

i nemaju skrivenu semantic dependency.

GitNexus se koristi da provjeri shared callers/processes kada sama lista fajlova nije dovoljna.

Primjer: dva taska možda ne diraju isti fajl, ali oba mijenjaju stanje koje centralni integration test očekuje.

Takvi taskovi nisu automatski nezavisni.

---

# 11. Implementer evidence

Implementer report:

```text
agent_reports/YYYY-MM-DD-<TASK-ID>-<agent>.md
```

Mora sadržati:

```text
Task
Files changed
Implementation summary
GitNexus pre-change result
GitNexus post-change/detect-changes result kada je required
Verification commands
DOSLOVAN output
Tests added/changed
Adversarial proof ako je required
OUT_OF_SCOPE_FINDINGS
Not verified
```

"Tests pass" bez outputa nije dovoljno.

---

# 12. Adversarial test

Obavezan kada task mijenja put/invariant, npr.:

```text
Domain no longer imports infrastructure
Application uses port instead of adapter
API key no longer persisted
Campaign Engine uses registry instead of hardcoded platform
ApprovedFact is immutable/versioned
View/Presentation no longer calls SQLite directly
```

Procedura:

```text
1. test tvrdi da dokazuje novi invariant;
2. privremeno vrati poznato pogrešnu varijantu;
3. test mora FAIL;
4. vrati ispravnu implementaciju;
5. isti test mora PASS;
6. dokumentuj oba outputa.
```

Ako test prolazi i na lošoj varijanti, test nije dokaz.

---

# 13. Standardna verifikacija

Task Contract navodi target commands.

P0 default:

```bash
python -m ruff check .
python -m mypy src
python -m pytest -q
python scripts/validate_resources.py
python -m ai_campaign_studio.main --health-check
```

Kasnije se dodaju relevantni integration/golden/UI/renderer testovi.

Ne tvrditi full green ako je pokrenut samo targeted test.

---

# 14. Review format

Svaki reviewer report:

```text
agent_reports/YYYY-MM-DD-<TASK-ID>-review-<agent>.md
```

Header:

```yaml
verdict: PASS|PASS_WITH_NOTES|REJECT
scope: PASS|REJECT
acceptance: PASS|REJECT
architecture: PASS|REJECT
security: PASS|REJECT
tests: PASS|REJECT
gitnexus_impact: PASS|REJECT|NOT_REQUIRED
blocking_findings: []
```

Narativ:

```text
CILJ
PROVJERENO
GITNEXUS / IMPACT
BLOCKING FINDINGS
STANDARDNA VERIFIKACIJA
ADVERSARIALNA PROVJERA
NE DIRATI U FIX RUNDI
SLJEDEĆE
```

Reviewer mora čitati stvarni diff.

---

# 15. Codex review fokus

Codex prioritetno napada:

- test koji ne razlikuje good/bad path;
- missing negative tests;
- schema output validation;
- failure/retry behavior;
- migration rollback;
- concurrency/state race;
- edge cases;
- regression;
- GitNexus affected callers/processes koji nisu testirani.

---

# 16. Claude review fokus

Claude prioritetno napada:

- dependency direction;
- Clean/Hexagonal boundary;
- domain purity;
- application-to-infrastructure coupling;
- provider-specific leakage;
- platform-specific hardcoding;
- duplication of source of truth;
- lifecycle/composition;
- over-engineering;
- scope creep;
- integration sa aktivnim planom.

---

# 17. Human approval

Reviewer PASS nije merge approval.

Koordinator mora pitati Human Ownera za eksplicitno odobrenje.

Bez:

```text
odobreno
merge
spoji
```

ili drugog jednoznačnog signala, nema merge-a.

---

# 18. Merge

Preporučeni sequence:

```text
verify branch
review complete
Human Owner approval
merge
checkout main
pull/verify main
post-merge full gate
GitNexus re-index
update CURRENT_STATE
release coordination claim
```

Ne raditi:

```text
git add .
git add -A
git reset --hard
git clean -fd
force push
```

bez eksplicitnog razloga/odobrenja.

---

# 19. Post-merge gate

Na main pokrenuti relevantni puni gate.

Za P0:

```bash
python -m ruff check .
python -m mypy src
python -m pytest -q
python scripts/validate_resources.py
python -m ai_campaign_studio.main --health-check
```

Zatim GitNexus:

```bash
npx gitnexus analyze --skip-agents-md
npx gitnexus check --cycles --repo .
```

Ako merge gate pada:

task nije DONE.

---

# 20. CURRENT_STATE

`.agent/CURRENT_STATE.md` sadrži samo:

- aktivna faza;
- aktivni dokumenti;
- trenutni P0/Faza1 gate;
- aktivni taskovi;
- poznati blokatori;
- verification baseline;
- GitNexus index status;
- sljedeći task.

Ne pretvarati ga u istorijski arhiv.

Task istorija živi u Git-u i `agent_reports/`.

---

# 21. Sensors / Habit Guides

Ne uvoditi desetine senzora unaprijed.

P0 već ima deterministički architecture-boundary test.

Novi `agent_sensors.py` dodaje se tek kada:

1. postoji ponovljen konkretan problem;
2. pravilo se može deterministički prepoznati;
3. može se replay-validirati protiv poznato loše i dobre varijante;
4. false positives su prihvatljivi.

Senzor ne zamjenjuje reviewer.

---

# 22. Prvi P0 task paketi

Implementation Phase 0 ostaje detaljan proceduralni source of truth.

Koordinator ga pakuje u male Task Contracte.

## ACS-P0-001 — Repo/tooling/bootstrap skeleton

Obuhvat približno:

```text
P0.00–P0.05
```

Default implementer:

```text
Crush
```

Risk:

```text
MEDIUM
```

Nakon što postoji dovoljno Python strukture:

```text
prvi GitNexus analyze
```

## ACS-P0-002 — Config/logging/common + architecture boundaries

Obuhvat:

```text
P0.06–P0.10
```

Default implementer:

```text
Pi
```

Risk:

```text
HIGH tokom foundation paketa
```

Obavezni Codex + Claude review.

## ACS-P0-003 — Localization + regional resources

Obuhvat:

```text
P0.11–P0.12
```

Default implementer:

```text
Pi
```

Može paralelno sa ACS-P0-004 samo ako claims nemaju presjek.

## ACS-P0-004 — Channel/Platform/Format registry

Obuhvat:

```text
P0.13
```

Default implementer:

```text
Crush
```

GitNexus obavezan jer postavlja shared contract.

## ACS-P0-005 — AI Provider/Model Registry + SecretStore

Obuhvat:

```text
P0.14–P0.15
```

Default implementer:

```text
Pi
```

Risk:

```text
HIGH
```

## ACS-P0-006 — SQLite + migrations + UoW

Obuhvat:

```text
P0.16–P0.19
```

Default implementer:

```text
Crush
```

Risk:

```text
HIGH
```

## ACS-P0-007 — Jobs + Presentation contracts + Bootstrap

Obuhvat:

```text
P0.20–P0.23
```

Default implementer:

```text
Pi
```

Risk:

```text
HIGH
```

Zavisi od 003/004/005/006.

## ACS-P0-008 — Validators + CI + security + P0 gate

Obuhvat:

```text
P0.24–P0.30
```

Default implementer:

```text
Crush
```

Risk:

```text
HIGH
```

Zavisi od svih prethodnih.

Human Owner može promijeniti assignment, ali dependency i review pravila ostaju.

---

# 23. P0 dependency DAG

```text
ACS-P0-001
     ↓
ACS-P0-002
     ↓
 ┌────┬────┬─────┐
 ↓    ↓    ↓     ↓
003  004  005   006
 └────┴────┴─────┘
        ↓
      007
        ↓
      008
        ↓
   P0-GATE PASS
```

Ne paralelizovati 003–006 dok ACS-P0-002 nije merged u main.

Prije branch-anja svakog od njih dokazati da je 002 stvarno merged.

---

# 24. GitNexus u P0

P0-001 počinje bez korisnog code graph-a.

Nakon što P0-001 napravi package skeleton:

```bash
npx gitnexus analyze --skip-agents-md
```

Od P0-002 nadalje:

GitNexus protocol je obavezan.

Poslije svakog merge-a:

```bash
npx gitnexus analyze --skip-agents-md
```

---

# 25. Definition of Done taska

Task nije DONE dok nema:

```text
Task Contract
implementation
tests
execution evidence
GitNexus evidence kada je required
review PASS
Human Owner approval
merge
post-merge gate
CURRENT_STATE update
coordination release
```

---

# 26. Definition of Done Implementation Phase 0

P0 nije DONE dok:

```text
artifacts/phase0_foundation_gate.json
```

ne kaže:

```json
{"status": "PASS"}
```

i post-merge verification na main je green.

Tek tada Faza 1 počinje.

---

# 27. Anti-patterns

Zabranjeno:

- coding prije Task Contracta;
- "gitnexus nije potreban, znam ovaj fajl";
- vjerovati zero-impact rezultatu iz pogrešnog worktree-a;
- paralelni taskovi sa preklopljenim allowed paths;
- implementer kao sopstveni reviewer;
- reviewer koji samo čita implementer summary;
- scope expansion u fix rundi;
- dupliranje translator/registry/migration runner/SecretStore sistema;
- platform `if/elif` kroz Campaign Engine;
- provider SDK poziv iz Domain/Application business logike;
- API secret u SQLite/config/logu;
- GUI framework dependency prije UI-GATE;
- merge prije Human Owner approval-a;
- P0 PASS bez stvarnih outputa.

---

# 28. Završno pravilo

Sistem je namjerno stroži na početku projekta.

Cilj nije maksimalna ceremonija.

Cilj je da arhitektonske greške budu jeftino uhvaćene dok je repo mali.

Kada prvih 10–15 taskova pokaže stabilan obrazac, Human Owner može smanjiti review trošak za LOW/MEDIUM taskove.

To je svjesna odluka, ne tiho popuštanje procesa.

---

# 29. Smanjen review trošak za LOW/MEDIUM (Human Owner odluka, 2026-09-01)

Human Owner je eksplicitno odlučio (nakon ACS-P0-001 do ACS-P0-006) da se
review trošak smanji za sve taskove koji NISU HIGH-risk/bezbjednosno
kritični, jer je puni Codex+Claude ciklus (viđeno do 5 review rundi po
tasku na ACS-P0-002) usporio tempo više nego što je opravdano za taj nivo
rizika.

## I dalje nepromijenjeno — puni ciklus (Codex + Claude + eksplicitno Human Owner merge odobrenje)

Taskovi koji diraju bilo šta sa liste iz §4 (elevated P0 standard) ili su
inače HIGH po §3:

```text
SecretStore / API credential handling
SQLite schema/migrations sa postojećim podacima
architecture boundaries / bootstrap / composition root
AI Provider/Model Registry
Channel/Platform/Format registry contract
localization contract
concurrency/lifecycle koji može korumpirati state
bilo koji drugi shared-contract/security invarijant
```

Za ove taskove ništa se ne mijenja: Pi/Crush implementacija → Codex
adversarial/test review → Claude architecture/integration review → Human
Owner eksplicitno "odobreno"/"merge"/"odobravam" prije merge-a.

## Novo — samo Claude review za LOW/MEDIUM

Za taskove van gornje liste (LOW/MEDIUM po §3, npr. čist UI state facade,
izolovana resource/config dopuna, non-shared-contract izmjena bez
security/persistence uticaja):

```text
implementacija
→ Claude review (stvarna verifikacija: diff, komande, adversarial dokaz
  ako kontrakt to traži — isti nivo rigoroznosti kao do sad, samo bez
  dodatne Codex runde)
→ Claude PASS → koordinator ODMAH commit-uje i push-uje/merguje
```

Bez čekanja na Codex rundu i bez posebnog Human Owner "odobravam" po
svakom pojedinačnom tasku iz ove kategorije — Claude PASS je dovoljan
signal za merge unutar ove kategorije.

Ako Claude tokom review-a otkrije da task ipak dira nešto sa HIGH liste
(scope se pokazao širi nego što je kontrakt najavio), STOP — vratiti na
puni Codex+Claude+Human Owner ciklus, ne tiho nastaviti olakšanim putem.

`.agent/CURRENT_STATE.md` mora imati kratku napomenu koja kategorija
review-a je trenutno na snazi, da naredna sesija/task ne posegne nazad za
starim punim ciklusom bez razloga.
