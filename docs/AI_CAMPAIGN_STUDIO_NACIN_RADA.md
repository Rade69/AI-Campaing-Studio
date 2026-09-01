# AI Campaign Studio — Način rada

**Svrha ovog dokumenta:** `docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md` je
kanonski **pravilnik** (šta je dozvoljeno/zabranjeno, risk tier, gate-ovi).
Ovaj dokument je **operativni opis prakse** — konkretno, korak po korak,
šta se stvarno dešava kad task krene, ko šta radi, koji fajl nastaje kad i
zašto, sa primjerima iz stvarne istorije ovog repoa (ACS-P0-001 do
ACS-P0-006). Kad su u konfliktu, pravilnik je autoritet; ovaj dokument se
ažurira da ga tačno odražava.

Ako nešto ovdje zastari (npr. promijeni se review politika), koordinator ga
ažurira u istom tasku u kom se pravilo mijenja — isti princip kao za file
header-e (workflow §30 touched-file rule).

---

## 1. Ko je ko

```text
Human Owner    — ti. Jedini autoritet za scope, prioritet, merge odobrenje.
Coordinator    — Claude (ova sesija). Priprema, verifikuje, ne vjeruje na riječ, merguje.
Implementeri   — Pi, Crush. Rade unutar allowed_paths, pišu kod i testove.
Reviewer       — Codex. Nezavisan adversarial/test review za HIGH taskove.
```

Coordinator (Claude) nema direktan CLI pristup pravim Pi/Crush/Codex
alatima — priprema worktree i eksplicitna uputstva (Task Contract, brief),
a ti pokrećeš te agente eksterno i vraćaš mi rezultat/putanju do fajla.

---

## 2. Životni ciklus jednog taska — konkretan tok

Ovo je stvaran redoslijed, ne apstrakcija. Svaki P0 task do sada je prošao
kroz ovo.

### 2.1 Priprema (coordinator, prije bilo kakvog koda)

1. Pročitam relevantni plan dokument (P0.xx sekcija za taj task) da znam
   tačno šta se traži — fajlove, acceptance, testove.
2. **GitNexus pre-impact** — provjerim upstream/downstream uticaj na
   simbole koje task dira (npr. `ports/` folder, postojeće error klase koje
   se ponovo koriste). Rezultat ide u `gitnexus:` YAML blok kontrakta
   (`scope_fit: PASS/EXPAND_REQUIRED/UNKNOWN`).
3. **Provjera paralelizma** — ako se task planira uz drugi paralelni task,
   provjerim da su `allowed_paths` disjoint. Lekcija iz ACS-P0-005/006:
   provjeriti i package `__init__.py` fajlove, ne samo "glavne" module
   fajlove — oba taska su nezavisno listala isti `infrastructure/__init__.py`
   i to je proizvelo trivijalan ali izbjediv merge konflikt.
4. Pišem **Task Contract**: `agent_reports/ACS-P0-XXX-task-contract.md`.
   YAML header (`task_id`, `risk`, `implementer`, `reviewers`, `status`,
   `dependencies`, `allowed_paths`, `forbidden_paths`, `gitnexus_required`,
   `adversarial_required`, `gitnexus:` blok) + tijelo (Kontekst, Objective,
   Implementation steps po P0.xx podsekciji, Acceptance checklist,
   Adversarial test opis ako je required, Verification komande, Review
   focus za Codex i za mene, Rollback, Dependency baseline, Coordination).
5. Kreiram **git worktree + branch**:
   `../ai-campaign-studio-worktrees/ACS-P0-XXX-<short-name>`,
   `task/ACS-P0-XXX-<short-name>`, granato sa trenutnog `main` HEAD-a.
6. Commit-ujem kontrakt na `main`, ažuriram `.agent/CURRENT_STATE.md`
   (status: "OPEN — contract spreman, čeka implementaciju"), push-ujem.

### 2.2 Implementacija (Pi ili Crush, eksterno)

Ti pokreneš implementera u tom worktree-u sa tim kontraktom. Implementer:

- radi SAMO unutar `allowed_paths`;
- piše kod + testove prema implementation steps;
- ako je `adversarial_required: true`, izvodi FAIL→PASS proceduru (privremeno
  pokvari invarijant, dokaže da test PADA, vrati ispravno, dokaže da test
  PROLAZI) i to dokumentuje;
- **ne commit-uje sam** (osim ako kontrakt eksplicitno traži drugačije);
- **po mogućnosti** piše evidence report:
  `agent_reports/YYYY-MM-DD-ACS-P0-XXX-<agent>.md` (files changed,
  implementation summary, verification output, adversarial proof,
  OUT_OF_SCOPE_FINDINGS, not verified).

**Stvaran obrazac primijećen u ovom projektu:** Pi skoro uvijek piše
detaljan report. Crush često ne piše nijedan (ACS-P0-001, ACS-P0-004
prva runda) — u tom slučaju ja rekonstruišem evidence direktno iz diff-a i
sam izvršavam adversarial dokaze koje kontrakt traži, prije nego što uopšte
krenem dalje. Ne pretpostavljam da je nešto testirano samo zato što
kontrakt to traži.

Kažeš mi: **"Pi/Crush je završio"**.

### 2.3 Verifikacija (coordinator — "ne vjeruj na riječ")

Ovo je najvažniji korak i nikad se ne preskače:

1. `git diff <base> --stat` na task branch-u — potvrdim da su svi
   izmijenjeni fajlovi unutar `allowed_paths`, ništa u `forbidden_paths`.
2. **Pročitam stvaran kod** (Read tool), ne samo dijagonalno — svaki novi
   fajl u cjelini.
3. Napravim/koristim `.venv` u worktree-u, pokrenem **sam**: `pytest`,
   `ruff check .`, `mypy src`, i sve dodatne komande iz kontrakta
   (`validate_resources.py`, `--health-check`).
4. Ako je adversarial dokaz required, **sam ponovim** proceduru (privremeno
   pokvarim invarijant preko backup/restore fajla, potvrdim FAIL, vratim,
   potvrdim PASS) — čak i ako je implementer to već uradio i dokumentovao.
5. Tek sada **commit-ujem** implementerov rad na task branch (author =
   ime implementera, committer = ja/Human Owner email — commit poruka
   objašnjava ŠTA i ZAŠTO, i eksplicitno kaže da je coordinator nezavisno
   verifikovao).
6. Pišem svoj **coordinator evidence report** (ako implementer nije, ili
   dopunu ako jeste):
   `agent_reports/YYYY-MM-DD-ACS-P0-XXX-<agent>-confirmed.md`.
7. Pišem svoj **Claude review**:
   `agent_reports/YYYY-MM-DD-ACS-P0-XXX-review-claude.md` — YAML header
   (`verdict`, `scope`, `acceptance`, `architecture`, `security`, `tests`,
   `gitnexus_impact`, `blocking_findings`) + narativ (CILJ, PROVJERENO,
   GITNEXUS/IMPACT, BLOCKING FINDINGS, STANDARDNA VERIFIKACIJA,
   ADVERSARIALNA PROVJERA, NE DIRATI U FIX RUNDI, SLJEDEĆE).

### 2.4 Codex review — samo za HIGH/bezbjednosno-kritične taskove

(Za LOW/MEDIUM, vidi §5 — ovaj korak se preskače od 2026-09-01.)

1. Pišem **Codex review request**:
   `agent_reports/YYYY-MM-DD-ACS-P0-XXX-codex-review-request.md` — tačan
   diff za pregled (branch/commit/base), read protocol, poznata
   environment ograničenja (GitNexus worktree-binding, oštećeni wheel-ovi
   viđeni ranije, sandbox temp/cache pristup), i **konkretan fokus** —
   šta tražim da posebno provjeri (edge cases koje ja nisam stigao/mogao
   testirati).
2. Ti proslijediš taj fajl Codex-u eksterno.
3. Kad Codex vrati `agent_reports/...-review-codex.md`:
   - Ako `REJECT` sa blocking findings: **prvo sam nezavisno reprodukujem
     SVAKI navedeni nalaz** prije nego što uopšte pripremim fix rundu — ne
     vjerujem Codex-u na riječ ništa više nego implementeru.
   - Pišem **uzak fix-round-brief**: samo fajlovi direktno vezani za
     nalaz, eksplicitna "NE DIRATI" lista (da implementer ne proširi
     scope), tačan opis minimalnog fix-a.
   - Ti proslijediš implementeru; implementer radi; ja opet verifikujem
     (§2.3, ali samo na delta protiv prethodnog commit-a, ne cio task
     ponovo) i šaljem **fresh Codex re-review**, sa oznakom round-a.
   - Ovo se ponavlja dok Codex ne vrati `PASS`/`PASS_WITH_NOTES` bez
     blocking findings. **Stvaran primjer:** ACS-P0-002 je prošao 5 rundi
     (4 uzastopna REJECT-a, svaki sa stvarnim, nezavisno potvrđenim bugom
     — od AST import-boundary bypass-a do Python LEGB scope grešaka).

### 2.5 Finalna odluka i merge

1. Kad review(evi) daju PASS: pišem **final decision packet**
   (`agent_reports/YYYY-MM-DD-ACS-P0-XXX-final-decision-packet.md`,
   `final-human-gate` skill format) — D1 readiness recommendation,
   tabela zatvorenih nalaza sa ID-jevima i dokazima, reziduelni rizici koje
   TI moraš svjesno prihvatiti, potvrđena validacija, scope status, i
   eksplicitno pitanje za tebe.
2. Tražim tvoje **eksplicitno odobrenje** ("odobravam"/"merge"/"slažem
   se" — ne nagađam iz konteksta).
3. **Merge**: `git status` na `main` prvo (ako ima tuđi WIP iz druge
   sesije, `git stash push -u` prije merge-a, vratim poslije), zatim
   `git merge --no-ff task/ACS-P0-XXX-...`. Ako konflikt (rijetko, obično
   trivijalan add/add na dijeljenom `__init__.py`), rješavam ručno i
   objašnjavam u commit poruci.
4. **Post-merge full gate** na `main`: `pytest`, `ruff`, `mypy`,
   `validate_resources.py` ako postoji, `--health-check`.
5. `npx gitnexus analyze --skip-agents-md` (re-index), `npx gitnexus status`
   da potvrdim `up-to-date`.
6. `git worktree remove` (force samo ako su jedini untracked fajlovi već
   inkorporirani implementer reportovi — provjerim prvo).
7. Ažuriram `.agent/CURRENT_STATE.md` (task DONE, novi verification
   baseline, sljedeći unblocked task, DAG pomak).
8. `git push origin main <task-branch>`.

---

## 3. Paralelni rad

Kad dva taska nemaju međuzavisnost (isti nivo u DAG-u, npr. ACS-P0-003+004
ili ACS-P0-005+006):

1. Provjerim `allowed_paths(A) ∩ allowed_paths(B) = ∅` **uključujući
   package `__init__.py` fajlove** (lekcija naučena, vidi §2.1).
2. GitNexus pre-impact za OBA prije nego što se bilo koji worktree kreira.
3. Oba worktree-a/branch-a se kreiraju odjednom, oba kontrakta se pišu
   prije nego što bilo koji implementer krene.
4. Review/fix cikluse (§2.3–2.4) vodim **nezavisno** za svaki — jedan
   može biti gotov i merged dok je drugi još u fix rundi (stvaran primjer:
   ACS-P0-004 merged dok je ACS-P0-003 još čekao Codex; ACS-P0-006 merged
   prije ACS-P0-005).
5. Merge redoslijed nije bitan osim ako jedan zavisi od drugog — ali
   provjerim da drugi merge ne otvori konflikt (najčešće trivijalan, kao
   `__init__.py` primjer).

`scripts/coordination.py` (claim/status/release) iz kanonskog workflow-a
još ne postoji u ovom repou — dok god ja (jedini coordinator) vodim sve
paralelne taskove ručno kroz `.agent/CURRENT_STATE.md`, ovo nije bio
problem. Ako se ikad pojavi drugi coordinator/agent koji nezavisno grana
taskove, ovaj alat postaje neophodan.

---

## 4. GitNexus — kako se stvarno koristi

- **Pre-impact** (prije pisanja kontrakta): `context`/`impact` na ključne
  simbole koje task dira (npr. `ports/` folder, error klase koje se ponovo
  koriste). Rezultat ide u kontrakt.
- **Post-merge**: `analyze --skip-agents-md` + `status` da potvrdim
  index je `up-to-date` na novom `main` HEAD-u.
- **Poznato ograničenje**: `detect-changes`/`context`/`impact` iz **linked
  worktree-a** se binduju na registrovani glavni checkout, ne na aktivni
  worktree — vraćaju "Repository not found" ili diff glavnog checkout-a
  umjesto task branch-a. Ovo je potvrđeno i od implementera i od Codex-a i
  od mene, dosljedno, kroz cio projekat. Kompenzacija: `gitnexus_impact:
  UNKNOWN` (nikad "nema impacta"), ručni `git diff` + puno čitanje fajlova
  + live reprodukcija umjesto automatskog impact rezultata.
- `.agent/GITNEXUS_PROTOCOL.md` §9 pominje `gitnexus check --cycles` koja
  ne postoji u instaliranoj CLI verziji (`unknown command`) — poznat
  doc/tool mismatch, još nije riješen, nije blokirao nijedan task do sada.

---

## 5. Review politika — tier sistem (od 2026-09-01)

Puna verzija: `docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md` §29 (Human
Owner odluka nakon što je ACS-P0-002 sam potrošio 5 review rundi).

```text
HIGH-risk / bezbjednosno kritično (SecretStore, SQLite/migrations,
architecture boundaries/bootstrap, AI/Channel/Localization registry
contract, itd. — puna lista u §4)
  → Codex + Claude + eksplicitno Human Owner odobrenje. Nepromijenjeno.

Sve ostalo (LOW/MEDIUM)
  → SAMO Claude review. Claude PASS → coordinator ODMAH commit-uje i
    push-uje/merguje. Bez Codex runde, bez posebnog per-task odobrenja.
```

Ako se tokom Claude review-a otkrije da task ipak dira HIGH listu — STOP,
vratiti na puni ciklus, ne nastaviti olakšanim putem tiho.

---

## 6. Fajlovi koje pišemo — kompletan spisak i namjena

Sve živi u `agent_reports/` (istorija, jedan fajl po događaju) ili
`.agent/` (živi status, prepisuje se in-place).

| Fajl (u `agent_reports/`) | Ko piše | Namjena |
|---|---|---|
| `ACS-P0-XXX-task-contract.md` | coordinator | Šta implementer smije/mora, PRIJE koda |
| `YYYY-MM-DD-ACS-P0-XXX-<agent>.md` | implementer (ako predа) | Sirov izvještaj o radu |
| `YYYY-MM-DD-ACS-P0-XXX-<agent>-confirmed.md` | coordinator | Nezavisno rekonstruisan/potvrđen dokaz |
| `YYYY-MM-DD-ACS-P0-XXX-review-claude.md` | coordinator | Moj arhitekturni review |
| `YYYY-MM-DD-ACS-P0-XXX-codex-review-request.md` | coordinator | Brief za Codex (samo HIGH) |
| `YYYY-MM-DD-ACS-P0-XXX-review-codex[-roundN].md` | Codex (eksterno) | Codex verdikt |
| `YYYY-MM-DD-ACS-P0-XXX-fix-round[N]-brief.md` | coordinator | Uzak fix zahtjev poslije REJECT-a |
| `YYYY-MM-DD-ACS-P0-XXX-final-decision-packet.md` | coordinator | D1 preporuka + pitanje za Human Ownera |

| Fajl (u `.agent/`) | Ažurira | Namjena |
|---|---|---|
| `CURRENT_STATE.md` | coordinator, poslije svakog merge-a/promjene | Živi status — aktivni taskovi, gate, blokatori, verification baseline, GitNexus status, sljedeći task, aktivna review politika |
| `PROJECT_MAP.md` | coordinator, rijetko | Statička mapa — doc index, ciljna struktura, P0 task→scope tabela |
| `TASK_ROUTING.md` | coordinator, po potrebi | Dodatni read-set po tipu taska (npr. Performance/Analytics sekcija) |
| `GITNEXUS_PROTOCOL.md` | rijetko | GitNexus hard-gate protokol |

`CURRENT_STATE.md` se **ne pretvara u arhiv** — istorija taskova živi u
git-u i `agent_reports/`, CURRENT_STATE opisuje SAMO trenutno stanje.

---

## 7. GitHub

- `origin` = javan repo, `main` + svi task branch-evi se push-uju poslije
  svake značajnije izmjene (commit-then-push, ne batch na kraju).
- Prije PRVOG push-a na javan repo, provjerena cijela git istorija na
  secrete/API ključeve.
- CI (`.github/workflows/ci.yml`) pokreće `ruff` → `mypy` → `pytest` na
  svaki push/PR ka `main`. Ovo NE zamjenjuje ručni post-merge gate —
  dodatna zaštita, ne jedina.
- Merged task branch-evi se NE brišu sa remote-a — ostaju kao istorijski
  trag (branch delete je destruktivna operacija, radi se samo na
  eksplicitan zahtjev).

---

## 8. Adversarial dokaz — tačan obrazac

Kad kontrakt kaže `adversarial_required: true` (invarijant se prvi put
uvodi ili je bezbjednosno/correctness kritičan):

```text
1. Test tvrdi da dokazuje invarijant X.
2. Privremeno pokvariti implementaciju (ukloniti check, vratiti no-op,
   dodati debug log koji bi trebalo da ne postoji) — NE commit-ovati ovo.
3. Pokrenuti test → mora FAIL. Zabilježiti doslovan output.
4. Vratiti ispravnu implementaciju (byte-identično originalu — provjeriti
   `git status`/`git diff` da je restauracija čista).
5. Pokrenuti test → mora PASS. Zabilježiti doslovan output.
6. Dokumentovati OBA outputa u evidence reportu.
```

Ovo radi i implementer (za svoj kod) i coordinator (nezavisna
reprodukcija, prije commit-a) i Codex (nezavisna reprodukcija tokom
review-a). Tri nezavisna izvršenja iste procedure, ne jedno prepisano
tri puta.

---

## 9. File header konvencija (od 2026-09-01)

Puna verzija: workflow §30. Ukratko: relevantni source fajlovi (services,
registries, adapters, ports, domain, models, composition roots) imaju na
vrhu 2–5 linija koje kažu šta fajl posjeduje i šta namjerno NE radi.
Navigaciona pomoć za agente (progressive disclosure — pročitaj header prije
nego što otvoriš cio fajl), ne source of truth. Ažurira se kad task
materijalno mijenja odgovornost fajla (touched-file rule) — ne mijenja se
samo zato što je unutrašnja implementacija refaktorisana.

---

## 10. Lekcije naučene (živi spisak, dopunjava se)

- **Claude review nije adversarial po difoltu.** Na ACS-P0-002 sam prvo
  dao PASS na `test_import_boundaries.py` provjeravajući samo direktne/
  alias/uslovne import oblike — Codex je istim testom našao da relative
  import, dynamic `importlib`, i case-sensitivity bug prolaze neopaženo.
  Za buduće boundary/invariant reviewe moram eksplicitno probati te
  varijante, ne samo "direct import + alias + conditional" obrazac.
- **Implementer report nije garantovan.** Crush ga često ne piše. Kad se
  to desi, ja rekonstruišem dokaz iz diff-a i sam izvršavam sve što
  kontrakt traži — task se ne tretira kao "manje verifikovan" zbog toga.
- **`allowed_paths` disjoint provjera mora uključiti package
  `__init__.py` fajlove**, ne samo "glavne" module fajlove — inače
  trivijalan ali izbjediv add/add merge konflikt (ACS-P0-005/006).
- **GitNexus worktree-binding je strukturno ograničenje**, ne
  privremena greška — tretirati `UNKNOWN` kao `UNKNOWN`, nikad kao "nema
  impacta", dosljedno kroz cio projekat.
- **Fresh `.venv` u worktree-u ponekad ima oštećen `pydantic_core`/mypy
  `librt` wheel** (viđeno više puta) — fix je
  `pip install --force-reinstall --no-cache-dir pydantic pydantic-core mypy`,
  nije defekt u kodu, ne treba trošiti vrijeme sumnjajući u task.
- **Ne svaki Codex REJECT je proporcionalan** — od runde 3+ na istom
  fajlu, eksplicitno tražiti od Codex-a da razlikuje stvaran, izvršiv bug
  od teoretskog/kontriranog scenarija (kao u round 4/5 ACS-P0-002 brief-ovima).
  Ovo je i doveo do §5 review politike.
