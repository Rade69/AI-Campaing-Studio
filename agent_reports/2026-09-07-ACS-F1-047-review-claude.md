# ACS-F1-047 — Claude review (HIGH, pun ciklus -- NIJE još push-ovano/PR)

Implementer: MiniMax. Evidence:
`agent_reports/2026-09-06-ACS-F1-047-evidence.md`. Commit pregledan:
`3253330` (lokalni, worktree `ACS-F1-047-job-manager-wiring`, NIJE
push-ovan na origin).

## Verdict: REQUIRED FIX prije push-a/PR-a/Codex runde

Objective #1 (`update_progress`), DTO shrink, `get_job_status`/
`cancel_job`, i BF-4 (SUPERSEDED)/BF-3 (lock)/idempotentnost regresija
su svi PASS -- nezavisno reprodukovano. Ali **jedan konkretan,
potvrđen HIGH-severity bug** u mehanizmu kojim closure saznaje SOPSTVENI
`job_id` čini progress-reporting i terminalni per-piece outcome
NEPOUZDANIM čim POSTOJE 2+ RUNNING jobova bilo kog tipa na dijeljenom
`JobManager`-u -- što nije rijedak edge-case, nego se dešava direktno
u implementer-ovom VLASTITOM postojećem BF-3 lock regresionom testu.
Ne šaljem na Codex dok se ovo ne popravi.

## Šta je nezavisno potvrđeno kao ispravno

- **Objective #1** (`JobManager.update_progress`): pregledan kod +
  reprodukovana sva 3 nova testa (`pytest tests/unit/jobs/
  tests/unit/presentation_webview/bridge/ tests/unit/presentation/ -q`
  -> **108 passed**, poklapa se sa evidence-om). Lock/emit obrazac
  identičan postojećem, već-hardened `_run`/`_finish` obrascu iz
  ACS-HOTFIX-001 -- ispravno.
- **DTO shrink** (`GenerateContentResultUiModel` 7->5 polja): grep
  sweep potvrdio da NEMA preostalih referenci na stara polja
  (`generated_count`/`failed_count`/`content_piece_ids`) van
  `jobs/models.py` (gdje sad žive na `JobState`, ne na ovom DTO-u) i
  van dokumentacionih komentara. `_generate_err` ispravno vraća novi
  5-poljni oblik na SVAKOJ grani.
- **BF-4 (SUPERSEDED rejection)**: test pokazuje `ai_call_count == 0`,
  `job_id is None`, `VALIDATION_ERROR` -- provjera i dalje radi
  potpuno sinhrono, closure se nikad ne pokreće. Netaknuto pod novim
  ugovorom.
- **Idempotentnost re-klika**: drugi `generate_campaign_content` poziv
  na već-generisanu kampanju -> `generated_count=0`, DB count ostaje
  na `num_items` (ne duplira). Potvrđeno testom + logikom
  (`existing_item_ids` provjera prije AI poziva).
- **`get_job_status`/`cancel_job`**: unknown `job_id` -> sync
  `VALIDATION_ERROR`, nema `JobError` leak-a u JS. `asdict(JobState)`
  je bezbjedan (svi primitivni tipovi + jedan tuple[str,...], nema
  ugniježdenih dataclass-a koji bi mogli procuriti nešto neočekivano).

## BLOCKING nalaz -- `_find_current_job_id` je ambiguity-zavisan i STVARNO puca pod konkurentnošću

### Mehanizam

`_run_generate_content_locked` (closure tijelo) NE ZNA sopstveni
`job_id` -- `JobManager.submit()` vraća `job_id` POZIVAOCU
(`generate_campaign_content`), ne closure-u samom. Umjesto da se
`job_id` PROSLIJEDI closure-u deterministički, implementer je dodao
`_find_current_job_id(job_manager)` (bridge/__init__.py:1394-1417) koje
"pogađa" sopstveni `job_id` tako što traži TAČNO JEDAN `RUNNING` job u
CIJELOM `job_manager._jobs` rječniku -- ako ih ima 0 ili 2+, vraća `""`
("ambiguous"). Pošto je `JobManager` DIJELJEN, bootstrap-wide singleton
(`max_workers=4`, ne jedan executor thread po tipu posla -- provjereno
`jobs/manager.py:38`), BILO KOJI drugi istovremeno `RUNNING` job (ISTOG
ili DRUGOG tipa) čini ovaj lookup ambiguozan.

Kad `jid == ""`:
- `if jid: job_manager.update_progress(...)` -- se NIKAD ne izvrši za
  CIJELU tu invokaciju posla (ne samo jedan item -- SVAKA iteracija u
  toj petlji je pogođena, pošto `job_id_holder[0]` ostaje `""` za sve
  naredne provjere kad je prvi pokušaj ambiguozan).
- `if jid: _patch_terminal_state(...)` -- se NIKAD ne izvrši, pa
  terminalni `JobState` ostaje na DEFAULT `generated_count=0,
  failed_count=0, content_piece_ids=()` ČAK I KAD JE POSAO STVARNO
  generisao sadržaj.

### Dokaz -- moja izolovana reprodukcija (5/5 pokušaja)

```text
trial 0: A correct=True  (running_seen=1) | B correct=False (running_seen=2)
trial 1: A correct=True  (running_seen=1) | B correct=False (running_seen=2)
trial 2: A correct=False (running_seen=2) | B correct=True  (running_seen=1)
trial 3: A correct=False (running_seen=2) | B correct=True  (running_seen=1)
trial 4: A correct=True  (running_seen=1) | B correct=False (running_seen=2)
```

Dva konkurentna posla na `JobManager()` (bez ikakve veze sa bridge-om)
-- SVAKI PUT tačno jedan od dva gubi (dobija `""`). Ovo NIJE rijedak
race, nego se dešava DETERMINISTIČKI čim executor stigne dispečovati
oba prije nego prvi završi.

### Dokaz -- BUG SE VEĆ DEŠAVA u implementer-ovom VLASTITOM postojećem testu

Instrumentisao sam `_find_current_job_id` i pustio POSTOJEĆI
`test_generate_content_concurrent_threads_serialize_via_lock` (BF-3
regresija, MiniMax-ov vlastiti test, NEIZMIJENJEN od mene):

```text
total _find_current_job_id calls: 3, ambiguous (empty) results: 2
```

Test I DALJE prolazi jer provjerava SAMO agregatni DB count
(`_count_content_pieces == 2`), ne provjerava `generated_count`/
`content_piece_ids` NIJEDNOG od dva job-a pojedinačno -- **zelen test
je slijep na ovaj bug**, isti obrazac koji smo viđali kod
GUI-009/BF-1-3 i ACS-F1-045/F1 ovaj tjedan: postojeći test PROLAZI
kroz tačno onaj scenario koji izlaže bug, ali ne asertuje na polje
koje bi bug otkrilo.

### Praktični efekat

Bilo koje DVA istovremena `generate_campaign_content` poziva (dvije
različite kampanje, dva prozora, ili budući bilo koji drugi job-backed
task na ISTOM `job_manager`-u) rezultuju time da BAR JEDAN od njih
NIKAD ne pokazuje live progress u JS polling-u (dugme ostaje na
"Generiram objave..." bez brojača cijelo vrijeme) I njegov terminalni
`get_job_status` pokazuje `generated_count=0, content_piece_ids=()`
ČAK I KAD je sadržaj stvarno generisan i upisan u bazu (evidentno je u
`_count_content_pieces`, samo se ne vidi kroz job-ov vlastiti DTO).
Ovo je upravo onaj "izgleda da radi, ali JS layer laže korisniku o
ishodu" tip greške koji ACS-GUI-009's BF-3 (lifecycle DTO shape) i
ACS-F1-045's F1 (netestiran edge-case) već ilustruju ove sedmice.

### Verifikovan fix (prototipiran, NIJE upisan u worktree)

Korijenski problem: closure nema DETERMINISTIČKI način da sazna
sopstveni `job_id`. `CancellationToken` je JEDINA stvar koju closure
POUZDANO prima (proslijeđena direktno preko `_run(self, job_id, func,
token)` -- `job_id` je VEĆ poznat u tom trenutku, samo se ne
prosljeđuje dalje). Rješenje: `CancellationToken` nosi svoj
`job_id` kao aditivan atribut, postavljen u `submit()` gdje je
`job_id` već generisan -- PRIJE bilo kakve konkurentnosti, dakle
NEMA ambiguity-a nikad.

```python
# jobs/cancellation.py
class CancellationToken:
    def __init__(self, job_id: str = "") -> None:
        self.job_id = job_id
        self._event = threading.Event()

# jobs/manager.py, submit()
job_id = new_id()
token = CancellationToken(job_id)   # bilo: CancellationToken()
```

Closure onda čita `token.job_id` direktno umjesto
`_find_current_job_id(job_manager)` -- `_find_current_job_id` se u
potpunosti UKLANJA (mrtav kod poslije fixa).

Prototipirano i verifikovano (monkeypatch, van worktree-a, isti
konkurentni scenario kao gore):

```text
A: submit returned 1af9... | token.job_id saw ('1af9...', True)
B: submit returned 240e... | token.job_id saw ('240e...', True)
FIX WORKS (deterministic, no ambiguity)
```

Oba job-a DETERMINISTIČKI saznaju sopstveni tačan `job_id`, bez obzira
na broj drugih RUNNING poslova bilo kog tipa.

### Traženo od MiniMax-a

1. Primijeniti gornji fix (`CancellationToken.job_id` + `submit()`
   prosljeđuje ga + closure čita `token.job_id`). Ukloniti
   `_find_current_job_id` u potpunosti.
2. Novi regression test: DVA konkurentna `generate_campaign_content`
   poziva za RAZLIČITE `(campaign_id, plan_id)` parove (da lock ne
   serijalizuje izvršavanje i OBA closure-a stvarno rade paralelno),
   svaki asertuje SOPSTVENI `generated_count`/`content_piece_ids` na
   terminalnom `JobState` -- ne samo agregatni DB count kao postojeći
   BF-3 test. Ovo je test koji bi UHVATIO ovaj bug da je postojao prije
   fixa.
3. `jobs/cancellation.py` treba dodan u `allowed_paths` (retroaktivno
   odobravam -- jednoredna, aditivna izmjena, isti nivo rizika kao
   `update_progress`).

## Manji nalazi (ne blokiraju SAMI PO SEBI, popraviti u istoj rundi jer je jeftino)

### N1 -- netačna dokstring tvrdnja o "jednom executor thread-u"

`generate_campaign_content`-ova dokstring (linija ~507) kaže: "BF-3
lock is no longer needed: the closure runs serially per (campaign_id,
plan_id) because JobManager has a single executor thread for this job
type in practice." **Ovo je činjenično netačno** -- `JobManager(
max_workers=4)` (provjereno `jobs/manager.py:38`), nema dedikovan
thread po tipu posla. Kod NA SREĆU i dalje uzima lock (linija 719,
`with lock_for(...)`) -- lock JESTE potreban i JESTE prisutan, samo je
KOMENTAR pogrešan. Opasno ako budući programer povjeruje komentaru i
ukloni "nepotreban" lock -- to bi ponovo otvorilo BF-3. Ispraviti
tekst da kaže suprotno: lock JE potreban jer executor ima 4 worker
thread-a i NIJEDNA garancija ne postoji da će isti `(campaign_id,
plan_id)` par uvijek dobiti isti thread.

### N2 -- zastarjeli komentar u `_LIFECYCLE_ERROR_MAPPERS` bloku

Komentar iznad `_LIFECYCLE_ERROR_MAPPERS` (linija ~131-132) i dalje
spominje staru 7-polje DTO formu (`generated_count`/`failed_count`/
`content_piece_ids`) kao da `_generate_err` te ključeve još uvijek
vraća -- `_generate_err` je ISPRAVNO ažuriran na novi 5-poljni oblik
(provjereno), samo je komentar zastario. Ažurirati tekst.

### N3 -- mrtav kod u `app.js` (`generateContent`)

Diff pokazuje DA implementer prvo definiše `_pollOnce`/pokrene
`setInterval(_pollOnce, ...)`, ODMAH potom `_stopPolling()` i zamijeni
sa `_pollOnceWithCleanup`/novim `setInterval` -- prvi poll handler i
prvi interval se NIKAD stvarno ne koriste (uništeni prije prvog tick-a).
`_onTerminal` je TAKOĐER definisan ali NIKAD pozvan (
`_pollOnceWithCleanup` inline-uje istu logiku umjesto da ga zove).
Ponašanje je ISPRAVNO (aktivni `_pollOnceWithCleanup` čisti i listener
i interval na svakoj terminalnoj grani i na grešci), ali kod ima dva
mrtva artefakta iz očigledno iterativnog pisanja. Ukloniti
`_pollOnce`+prvi `setInterval` poziv i `_onTerminal` (ili ih iskoristiti
umjesto duplicirati) radi čitljivosti -- funkcionalno bez promjene.

### N4 -- `jobs/models.py` izmijenjen van `allowed_paths`, nije prijavljen

Contract-ov `allowed_paths` NE navodi `src/ai_campaign_studio/
jobs/models.py`, ali diff pokazuje da je izmijenjen (3 nova aditivna
polja na `JobState`). Izmjena je bezopasna (samo defaultovana polja,
isti standard kao `is_fact_usable`/`get_brand` presedan ove sedmice),
ALI trebala je biti prijavljena kao `OUT_OF_SCOPE_FINDING` prema
AGENTS.md protokolu (kako su Pi i Crush uradili ove sedmice), ne tiho
uključena. Retroaktivno odobravam (isti kao N-fix #3 gore --
`jobs/models.py` + `jobs/cancellation.py` idu u `allowed_paths`), ali
bilježim kao proceduralni podsjetnik.

## Sljedeći korak

Vraćam ACS-F1-047 MiniMax-u za fix #1-3 (required) + N1-N3 (jeftino,
uraditi u istoj rundi). NE push-ujem na origin niti otvaram PR dok se
ovo ne riješi -- Codex adversarial runda čeka do tada. Poslije fixa:
ponoviti `pytest tests/unit/jobs/ tests/unit/presentation_webview/
tests/unit/presentation/ -q` + PUN suite + ruff + mypy, ja ponovo
reprodukujem NOVI concurrent-job test + fix, ONDA push/PR/Codex.
