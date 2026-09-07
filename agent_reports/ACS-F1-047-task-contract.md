---
task_id: ACS-F1-047
phase: "Fix — background job execution (web Claude review 2026-09-07, Nalaz 4)"
title: "generate_campaign_content preko JobManager-a: nepokretno dugme, progress, otkazivanje"
risk: HIGH
coordinator: claude
implementer: TBD
reviewers: [claude, codex]
status: "OPEN -- contract written before code, čeka implementera"
created_at: 2026-09-07
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/jobs/manager.py
  - src/ai_campaign_studio/presentation_webview/bridge/__init__.py
  - src/ai_campaign_studio/presentation_webview/screens/studio_sadrzaja/__init__.py
  - src/ai_campaign_studio/presentation_webview/static/app.js
  - src/ai_campaign_studio/presentation/contracts.py
  - src/ai_campaign_studio/presentation/ui_models.py
  - tests/unit/jobs/test_manager.py
  - tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py
  - tests/unit/presentation_webview/test_studio_sadrzaja_ssr.py
  - tests/unit/presentation/test_contracts.py
  - tests/unit/presentation/test_ui_models.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/infrastructure/database/
  - resources/migrations/
  - src/ai_campaign_studio/presentation_webview/screens/pregled_izvoz/
gitnexus_required: true
adversarial_required: true
gitnexus:
  required: true
  note: >
    Mijenja `generate_campaign_content`-ov PONAŠANJE (sinhron ->
    asinhron preko job-a) i JS ugovor (rezultat postaje `job_id`, ne
    konačan rezultat). Provjeriti da nijedan POSTOJEĆI test/pozivalac
    (npr. `_call_on_fresh_thread` u bridge testovima) ne pretpostavlja
    stari sinhron ugovor bez izmjene.
---

# Kontekst

Web Claude review (2026-09-07): `JobManager` (316 LOC, `src/
ai_campaign_studio/jobs/manager.py`) i `CancellationToken` postoje,
testirani su, i NIKO ih ne koristi -- `grep job_manager` u `src/` daje
5 pogodaka, sve konstrukcija/shutdown, NULA `submit()` poziva. Umjesto
toga, `generate_campaign_content` (ACS-GUI-008, mergovano) vrti
SINHRONU `for` petlju AI poziva UNUTAR JEDNOG `js_api` poziva. Plan sa
12 stavki × ~10s po AI pozivu = ~2 minuta zamrznuto dugme, bez
progress prikaza, bez mogućnosti otkazivanja, bez djelimičnog prikaza
tokom rada (korisnik vidi rezultat tek na SAMOM KRAJU).

Koordinator potvrdio: `JobManager.submit(job_type, func) -> job_id`
(func poziva se sa `token: CancellationToken` ako ga prihvata),
`get_state(job_id) -> JobState` (ima `status`/`progress_current`/
`progress_total`/`phase`/`message` polja -- ALI trenutno NIŠTA ne piše
u `progress_current`/`progress_total` tokom izvršavanja, samo status
tranzicije), `cancel(job_id)` (kooperativno, `token.raise_if_cancelled()`).

**Scope ovog task-a**: SAMO `generate_campaign_content` (najjasniji,
najkvantifikovaniji slučaj -- "12 × 10s"). `export_campaign_package`
(ACS-GUI-009, u review-u) i `create_campaign_and_generate_plan`
(jedan AI poziv, već brz) OSTAJU sinhroni -- budući taskovi PONAVLJAJU
isti obrazac ako se pokaže potrebnim.

# Objective

## 1. `JobManager` -- dodati `update_progress` (aditivno)

```python
def update_progress(
    self, job_id: str, current: int, total: int,
    phase: str = "", message: str = "",
) -> None:
    """Update progress fields on a RUNNING job. No-op if job is terminal
    or unknown (best-effort -- a progress update losing a race with
    job completion must never raise)."""
```

Thread-safe preko POSTOJEĆEG `self._lock` (isti obrazac kao `_finish`).
Emituje nov `JobEventType` (npr. `PROGRESS`) ako `events.py` treba
dopunu -- implementer provjerava `events.py` PRIJE pisanja, dodaje
SAMO ako ne postoji ekvivalent.

## 2. `generate_campaign_content` -- postaje job-backed

- Metoda VIŠE NE RADI posao sinhrono. Umjesto toga:
  1. Boundary validacija (ISTA kao danas -- OSTAJE sinhrona, brza).
  2. Plan/campaign lookup + status provjere (ISTO -- brzo, sinhrono,
     korisnik odmah vidi grešku ako je plan pogrešnog statusa, BEZ
     čekanja na job).
  3. Ako sve prođe: `job_id = self._bootstrap.job_manager.submit(
     "generate_campaign_content", closure)` gdje `closure` radi
     STVARAN posao (provider resolution + per-item petlja, ISTA
     logika kao danas, PREMJEŠTENA u closure), pozivajući
     `job_manager.update_progress(job_id, i, total)` nakon SVAKOG
     item-a (uspješnog ILI neuspješnog -- progress mjeri "pokušano",
     ne "uspjelo").
  4. Vraća `{"ok": true, "job_id": job_id}` ODMAH (bez čekanja na
     posao) -- NOVI, MANJI DTO oblik (implementer razmatra da li
     ovo treba biti nov `JobStartedResultUiModel` ili prošireni
     `GenerateContentResultUiModel` sa opcionim `job_id` poljem --
     birati manje-rušilački pristup prema POSTOJEĆIM testovima).
  5. Closure hvata `CancellationError` (preko `token.
     raise_if_cancelled()` provjere PRIJE svakog item-a) i zaustavlja
     petlju bez greške (JobManager sam mapira na `CANCELLED`).
- **Resource lifecycle napomena**: closure se izvršava na
  `ThreadPoolExecutor` thread-u, NE na pywebview worker thread-u koji
  je pozvao `generate_campaign_content`. To znači closure MORA SAM
  otvoriti svoju `_resource_scope()`-ekvivalentnu konekciju (ISTI
  problem koji je HOTFIX-002 riješio za `js_api` pozive, sada primijenjen
  na JOB thread) -- `@_with_call_resources` dekorator NE POKRIVA
  closure jer se ona izvršava NA DRUGOM thread-u, KASNIJE, nakon što
  je originalni `js_api` poziv VEĆ završio (i njegov `_resource_scope`
  VEĆ zatvoren). Closure treba SVOJU `with self._resource_scope():`
  (ili ekvivalentan poziv) UNUTAR sebe.

## 3. Nova READ js_api metoda: `get_job_status(job_id: str) -> dict`

- Poziva `job_manager.get_state(job_id)`, vraća JSON-safe oblik
  (`status`, `progress_current`, `progress_total`, `phase`, `message`,
  `error_code`, `error_message`). Nepoznat `job_id` -> `VALIDATION_ERROR`
  (NE baca `JobError` u JS).

## 4. Nova js_api metoda: `cancel_job(job_id: str) -> dict`

- Poziva `job_manager.cancel(job_id)`. Nepoznat `job_id` ->
  `VALIDATION_ERROR`.

## 5. `app.js`/`studio_sadrzaja` -- polling + cancel dugme

- `generateContent()` handler: umjesto čekanja na pun rezultat, prima
  `job_id`, pokreće `setInterval`/polling preko `get_job_status`
  (implementer bira razuman interval, npr. 1-2s), ažurira
  `data-generate-result` sa progress-om ("Generišem 3/12..."), STAJE
  kad status postane terminalan (`SUCCEEDED`/`FAILED`/`CANCELLED`).
  Dugme dobija "Otkaži" opciju tokom RUNNING stanja (poziva
  `cancel_job`).

# Implementation steps

1. `JobManager.update_progress` (Objective #1) + testovi (RUNNING job
   dobija progress update, terminalan job update je no-op, nepoznat
   job_id je no-op -- ne baca).
2. `generate_campaign_content` prerada (Objective #2) + testovi:
   vraća `job_id` odmah (ne čeka), `get_job_status` pokazuje
   `RUNNING`->`SUCCEEDED` progresiju (test sa STVARNIM `job_manager`,
   ne mock -- pollovati `get_state` dok ne postane terminalan, sa
   timeout-om), `cancel_job` STVARNO zaustavlja petlju prije zadnjeg
   item-a (test: pokreni, odmah otkaži, provjeri da NISU sve stavke
   generisane).
3. `get_job_status`/`cancel_job` (Objective #3-4) + testovi (nepoznat
   job_id, sigurnosni no-leak).
4. `app.js` polling + cancel UI (Objective #5) + test (ako postoji
   JS test harness u ovom projektu -- provjeriti prije pisanja; ako
   ne postoji, dokumentovati ručnu verifikaciju).
5. **Regression**: SVI postojeći `generate_campaign_content` testovi
   (happy path, partial failure, idempotentnost, concurrent lock,
   SUPERSEDED rejection, BF-5 error-mapper) MORAJU biti AŽURIRANI da
   rade sa novim job-backed ugovorom -- NE brisati njihovu provjeru
   suštine (idempotentnost i dalje mora vrijediti, samo se DOKAZUJE
   preko `get_job_status` nakon što se job završi, ne direktno na
   povratnu vrijednost).

# Acceptance

- [ ] `generate_campaign_content` vraća `job_id` ODMAH, ne čeka posao.
- [ ] `get_job_status`/`cancel_job` postoje, JSON-safe, no-leak.
- [ ] Progress se STVARNO ažurira tokom izvršavanja (test dokaz preko
      polling-a na stvaran `JobManager`, ne pretpostavka).
- [ ] Otkazivanje STVARNO zaustavlja petlju (test dokaz -- manje
      generisanih stavki nego ukupan broj).
- [ ] SVI postojeći BF-1/3/4/5 nalazi (idempotentnost, lock,
      SUPERSEDED, DTO oblik) OSTAJU tačni pod novim ugovorom (test
      dokaz, ne pretpostavka).
- [ ] Closure ispravno otvara/zatvara SVOJU konekciju (thread-safety
      dokaz -- pozvati sa STVARNOG `ThreadPoolExecutor` thread-a, ne
      pretpostaviti da GIL rješava sve).
- [ ] `python -m pytest tests/unit/jobs/ tests/unit/presentation_webview/
      tests/unit/presentation/ -v` prolazi.
- [ ] `python -m pytest -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.
- [ ] **CI provjeren preko PR-a.**

# Verification

```bash
python -m pytest tests/unit/jobs/ tests/unit/presentation_webview/ tests/unit/presentation/ -v
python -m pytest -q
python -m ruff check .
python -m mypy src

git push -u origin task/ACS-F1-047-job-manager-wiring
gh pr create --base main --title "ACS-F1-047: generate_campaign_content preko JobManager-a"
gh pr checks
```

# Review focus -- Claude + Codex (adversarial)

- Closure-ov resource lifecycle na job thread-u STVARNO ispravan
  (isti nivo provjere kao HOTFIX-002 -- worker-thread reprodukcija,
  ne pretpostavka).
- Otkazivanje NIJE fake -- test STVARNO pokreće posao sa VIŠE stavki,
  otkazuje PRIJE kraja, potvrđuje DA JE MANJE stavki generisano nego
  ukupno.
- Progress polling ne curi resurse (ako JS prestane pollovati zbog
  greške, da li `setInterval` ostaje zaglavljen zauvijek?).
- Postojeći GUI-008 testovi za idempotentnost/lock/SUPERSEDED/BF-5
  I DALJE STVARNO dokazuju isto ponašanje pod novim async ugovorom,
  ne samo "prilagođeni da prođu".

# Rollback

HIGH risk -- mijenja PONAŠANJE i JS ugovor VEĆ MERGOVANOG, HIGH-risk
use-case-a (tri runde review-a). Izolovano na jedan metod +
`JobManager` dopuna (aditivna). Pun review ciklus.

# Coordination

Nema zavisnosti. Prioritet #3 (poslije ACS-F1-045, ACS-F1-046) po
Human Owner odluci 2026-09-07. `export_campaign_package` (GUI-009)
može kasnije PONOVITI isti obrazac kao zaseban budući task ako se
pokaže potrebnim (export je danas brži -- render+ZIP, ne 12× AI
poziv -- manje hitno).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-047-job-manager-wiring
Branch:   task/ACS-F1-047-job-manager-wiring
Base:     main @ 70c9efa
```
