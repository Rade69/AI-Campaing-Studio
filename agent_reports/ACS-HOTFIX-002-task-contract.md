---
task_id: ACS-HOTFIX-002
phase: Hitan hotfix -- otkriven kroz Codex adversarial review ACS-GUI-008 (BF-2)
title: "Bridge SQLite konekcija puca na svaki stvaran pywebview klik (thread-affinity crash) -- pogađa VEĆ MERGOVAN GUI-005/007 kod, ne samo GUI-008"
risk: CRITICAL
coordinator: claude
implementer: codex
reviewers: [claude]
status: "OPEN -- contract written before code, čeka implementera"
created_at: 2026-09-06
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/presentation_webview/bridge/__init__.py
  - src/ai_campaign_studio/presentation_webview/__main__.py
  - tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py
  - tests/unit/presentation_webview/test_main.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/infrastructure/database/repositories/
  - src/ai_campaign_studio/infrastructure/database/unit_of_work.py
  - resources/migrations/
  - src/ai_campaign_studio/presentation_webview/screens/
  - src/ai_campaign_studio/presentation_webview/static/app.js
gitnexus_required: true
adversarial_required: false
gitnexus:
  required: true
  note: >
    Koordinator MORA pokrenuti impact provjeru na `CampaignBridgeApi`
    prije merge-a -- ovaj task mijenja KAKO se konekcija/repo-ovi
    grade unutar bridge-a (moguće mijenja `__init__` internals za sve
    tri postojeće js_api metode), ne samo dodaje novu metodu.
---

# Kontekst

Nezavisni Codex adversarial review ACS-GUI-008-a (PR #4, task/ACS-GUI-008-
studio-sadrzaja-generate) pronašao je BF-2: bridge konstruiše JEDNU
SQLite konekciju u `CampaignBridgeApi.__init__` (na glavnom thread-u,
prije `webview.start()`), ali `sqlite3.connect()` default
(`check_same_thread=True`) znači da ta konekcija SAMO radi na thread-u
gdje je napravljena.

**Pravi pywebview dispatch model** (potvrđeno u instaliranom paketu,
`.venv/Lib/site-packages/webview/util.py:335`): SVAKI `js_api` poziv se
izvršava preko `Thread(target=_call); thread.start()` -- NOV thread za
SVAKI klik, nikad glavni thread, nikad isti thread dva puta zaredom.

**Koordinator je ovo nezavisno reprodukovao** (ne samo prihvatio
Codex-ovu tvrdnju): konstruisan `CampaignBridgeApi` na glavnom thread-u,
pozvan `create_campaign_and_generate_plan` (POSTOJEĆA, VEĆ MERGOVANA
ACS-GUI-005 metoda) sa drugog thread-a preko `threading.Thread` --
puklo identično:

```text
sqlite3.ProgrammingError: SQLite objects created in a thread can only
be used in that same thread. The object was created in thread id 11956
and this is thread id 9364.
```

**Ovo NIJE bug koji je uveo ACS-GUI-008.** Pogađa CIJELI bridge --
`create_campaign_and_generate_plan` (ACS-GUI-005) i `configure_provider`
(ACS-GUI-007), OBOJE VEĆ MERGOVANI I U PRODUKCIJI -- jednako kao i novu
`generate_campaign_content` (ACS-GUI-008, još nije mergovan). Ranije
"live end-to-end verifikacije" ovih metoda (vidi CURRENT_STATE.md
istoriju za ACS-GUI-005/007) su rađene DIREKTNOM konstrukcijom bridge-a
i pozivom metode u ISTOM skriptu/testu (isti thread) -- NIKAD kroz
stvaran `webview.start()` klik. Zato ovo nikad nije uhvaćeno do sad.

**Praktična posljedica**: aplikacija, pokrenuta kao stvarna desktop app
(`python -m ai_campaign_studio.presentation_webview`) i kliknuta od
strane pravog korisnika, vjerovatno puca na SAM PRVI klik na bilo koje
dugme povezano sa bridge-om. Ovo je CRITICAL, ne HIGH -- postojeća
funkcionalnost (ne samo nova) je pogođena.

# Objective

Bridge (`CampaignBridgeApi`) ne smije držati JEDNU SQLite konekciju
kreiranu na jednom thread-u i dijeljenu preko poziva sa drugih thread-ova.
Tačan mehanizam bira implementer, ali mora zadovoljiti:

1. **Svaki `js_api` poziv mora raditi ispravno kad se izvrši sa
   DRUGAČIJEG thread-a nego thread koji je konstruisao bridge**
   (repliciranje stvarnog pywebview dispatch-a: `Thread(target=call);
   thread.start(); thread.join()`).
2. **`check_same_thread=False` BEZ popratne serijalizacije NIJE
   prihvatljivo rješenje** (Codex-ova eksplicitna napomena -- to bi
   sakrilo crash iza tihe korupcije podataka pod stvarnom
   konkurencijom, ne riješilo problem).
3. Razuman pravac (implementer odlučuje, dokumentuje zašto): svaki
   `js_api` poziv otvara SVOJU `create_connection(paths.database_path)`
   (već postoji, već dokumentovano "no global singleton, caller owns
   the connection") na POČETKU poziva, koristi je za sve repo
   operacije UNUTAR tog poziva, zatvara je na kraju (`finally`).
   Migracije (`run_migrations`) se pokreću JEDNOM pri app startup-u
   (kratkotrajna konekcija, zatvorena odmah), NE na svaki klik.
4. **SVE tri postojeće `js_api` metode** (`create_campaign_and_
   generate_plan`, `configure_provider`, i `generate_campaign_content`
   iz ACS-GUI-008 -- vidi Coordination niže za tačan status te grane)
   moraju raditi ispravno pod novom šemom, ne samo jedna.
5. Postojeći test suite (koji bridge konstruiše i poziva na ISTOM
   thread-u -- pytest default) MORA i dalje prolaziti nepromijenjen u
   ponašanju -- ovo je fix lifecycle-a, ne promjena poslovne logike.

# Implementation steps

1. Izmijeniti `CampaignBridgeApi.__init__`/internu strukturu tako da
   repo-ovi/konekcija NISU fiksirani na thread konstrukcije. Implementer
   bira: (a) svaka metoda pravi svoju konekciju+repo-ove lokalno, (b)
   neki drugi ispravan mehanizam (npr. `threading.local()` cache
   konekcije po thread-u -- PRIHVATLJIVO ako je ispravno zatvoreno kad
   thread završi, ALI pywebview pravi NOV thread po pozivu pa bi ovo u
   praksi značilo isto što i (a), samo sa dodatnom komplikacijom bez
   koristi -- (a) je vjerovatno jednostavnije i dovoljno).
2. Migracije se odvajaju od per-poziv konekcije (Objective #3).
3. **Nov, permanentan regression test** koji REPLICIRA stvaran
   pywebview dispatch: konstruiše bridge na glavnom (test) thread-u,
   poziva SVAKU od tri js_api metode sa NOVOG `threading.Thread`-a
   (`thread.start(); thread.join()`), potvrđuje uspješan rezultat
   (`ok=True` ili ispravan domain-level error, NE
   `sqlite3.ProgrammingError`/`INTERNAL_ERROR` sa "ProgrammingError" u
   poruci). Ovaj test MORA biti dio stalnog test suite-a (ne
   jednokratna skripta) -- ovo je klasa buga koja se NE SMIJE tiho
   vratiti.
4. Provjeriti da postojeći testovi (isti thread, pytest default) i
   dalje prolaze BEZ izmjene ponašanja.

# Acceptance

- [ ] Repro test (Objective/Implementation #3) postoji, POKAZUJE crash
      PRIJE fixa (implementer dokazuje ovo -- pokrenuti test na
      TRENUTNOM kodu prije izmjene, pa PONOVO nakon), i prolazi NAKON
      fixa, za SVE tri js_api metode.
- [ ] Nijedna metoda ne koristi `check_same_thread=False` bez
      dokumentovanog, ispravnog serijalizacionog mehanizma.
- [ ] Postojeći test suite (`tests/unit/presentation_webview/bridge/`)
      prolazi nepromijenjen u ponašanju.
- [ ] `python -m pytest -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.
- [ ] GitNexus impact na `CampaignBridgeApi` pokrenut i dokumentovan.
- [ ] **CI provjeren preko PR-a** (obavezno otvoriti PR).

# Verification

```bash
python -m pytest tests/unit/presentation_webview/bridge/ -v
python -m pytest -q
python -m ruff check .
python -m mypy src

git push -u origin task/ACS-HOTFIX-002-bridge-thread-lifecycle
gh pr create --base main --title "ACS-HOTFIX-002: fix SQLite thread-affinity crash in bridge"
gh pr checks
```

# Review focus -- Claude (JEDINI reviewer ovog kruga)

Codex je implementer ovog taska (sam ga je otkrio) -- NEMA odvojene
Codex adversarial runde ovaj put (isti entitet ne može biti implementer
i adversarial reviewer). Claude review mora zato biti POJAČAN:

- Repro test STVARNO koristi `threading.Thread` (ne mock/monkeypatch
  koji zaobilazi stvaran problem) -- pokrenuti ga SAM, nezavisno,
  prije i poslije fixa.
- Migracije se STVARNO pokreću samo jednom (ne po pozivu) -- provjeriti
  performanse/log dokaz, ne samo tvrdnju.
- Postojeća tri js_api metode STVARNO rade ispravno pod novom šemom --
  ne samo `create_campaign_and_generate_plan` (koju je koordinator
  reprodukovao), nego i `configure_provider` i `generate_campaign_content`.
- Nema tihog uvođenja `check_same_thread=False` bilo gdje u diff-u
  (grep dokaz).
- GitNexus impact stvarno pokrenut -- provjeriti da nijedan drugi
  poziv `CampaignBridgeApi()` (van bridge-a samog) ne pretpostavlja
  staru šemu (npr. direktan pristup `bridge._campaign_repo` iz nekog
  testa ili drugog koda -- ako se interna struktura mijenja, sve
  reference moraju biti ažurirane).

# Rollback

CRITICAL risk, ALI izolovano na jedan fajl (`bridge/__init__.py`) plus
`__main__.py` (ako migracije treba premjestiti). Rollback: revert
commit-a, vraća se na POZNATO POKVARENO stanje (trenutni CRITICAL bug),
ne na nešto novo pokvareno -- nema pogoršanja u odnosu na status quo.

# Coordination

**Blokira ACS-GUI-008 merge** (PR #4 čeka -- Codex je BF-2 označio kao
blocking, GUI-008 se ne merguje dok se ovo ne riješi). **Blokira i
ACS-GUI-009** (isti bridge fajl, isti problem bi postojao i za
`export_campaign_package` kad stigne). Preporučen redoslijed: ovaj
hotfix PRVI, pa se GUI-008 rebase-uje na njega (ili GUI-008-ova fix
runda za BF-1/BF-3/BF-4 uključi i rebase na ovaj commit).

Nakon merge-a: ažurirati CURRENT_STATE.md sa jasnom napomenom da
"live end-to-end verifikacije" GUI-005/007 iz ranije istorije NISU
zapravo prošle kroz stvaran pywebview thread dispatch -- da se ne
ponovi ista lažna sigurnost u budućim task-ovima.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-HOTFIX-002-bridge-thread-lifecycle
Branch:   task/ACS-HOTFIX-002-bridge-thread-lifecycle
Base:     main @ ccf0a6e
```
