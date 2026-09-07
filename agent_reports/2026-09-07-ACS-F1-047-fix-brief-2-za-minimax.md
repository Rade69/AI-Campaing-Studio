# ACS-F1-047 — fix-brief za MiniMax (poslije Codex REJECT, PR #12)

Odnosi se na:
`H:\ai-campaign-studio-worktrees\ACS-F1-047-job-manager-wiring\agent_reports\2026-09-07-ACS-F1-047-review-codex.md`
(verdict REJECT, 2 blocking findings). Coordinator (Claude) je OBA
nalaza nezavisno reprodukovao PRIJE pisanja ovog briefa. Ovo je druga
fix-runda za PR #12 (prva je bila moj review, `2026-09-07-ACS-F1-047-review-claude.md`,
koju si ti zvao "fix-brief-3" u svom evidence-u).

PR #12 se NE MERGE-uje dok Codex ne ponovi review i ne da PASS. HIGH
task, pun ciklus i dalje važi.

## Nezavisna verifikacija (coordinator, prije ovog briefa)

- **BF-CODEX-1**: pročitan `app.js` (linije ~301-430). Potvrđeno:
  `button.disabled = true` se postavlja PRIJE submita i NIGDJE se ne
  vraća na `false` poslije uspješnog submita -- `_showCancelHint()`
  mijenja SAMO `textContent`, ne `disabled`. Disabled HTML `<button>`
  ne emituje `click` event (standardno browser ponašanje), pa
  `_onClickWhileRunning` NIKAD ne dobija priliku da se izvrši dok je
  posao RUNNING. `cancel_job` backend radi ispravno kad se pozove
  DIREKTNO (Python test to dokazuje), ali korisnik kroz GUI NEMA
  način da ga pozove.
- **BF-CODEX-2**: pročitan `_run_generate_content_locked`
  (bridge/__init__.py:804-904). Potvrđeno: `_patch_terminal_state(...)`
  je izvan `for` petlje (linije 897-904), dostiže se SAMO na prirodan
  izlazak iz petlje. `token.raise_if_cancelled()` (linija 827 na
  početku iteracije, ili 882 u `finally` nakon AI poziva) baca
  `CancellationError` koja propagira KROZ petlju, preskačući
  `_patch_terminal_state` u potpunosti -- `generated_ids`/`failed_count`
  akumulirani DO tog trenutka se GUBE, terminal `JobState` ostaje na
  default `generated_count=0, content_piece_ids=()`.

  Reprodukovao sam UŽIVO (privremen test, uklonjen odmah poslije):
  4 stavke, adapter spava 0.4s po pozivu, poll na `progress_current >= 1`
  (NE `generated_count` -- to polje se ne mijenja dok petlja radi,
  isti sync bug koji je Codex primijetio u tvom POSTOJEĆEM
  `test_cancel_job_actually_stops_the_loop`), cancel poslat, terminal
  status `CANCELLED`:
  ```text
  persisted DB rows: 2
  terminal status: CANCELLED
  terminal generated_count: 0
  ```
  Identičan obrazac kao Codex-ova reprodukcija (2 reda u bazi, 0 u
  DTO-u).

Oba nalaza potvrđena kao stvarna. Prelazimo na fix.

## Fix 1 — BF-CODEX-1: cancel dugme mora biti STVARNO klikabilno tokom RUNNING

**VAŽNO -- pročitaj prije nego počneš**: naivan fix ("samo skini
`button.disabled = false` tokom RUNNING") je NEBEZBJEDAN. Provjerio
sam `app.js` linija 3-46: postoji GLOBALNI, page-load-time delegirani
click listener na SVAKI `[data-action]` element
(`document.querySelectorAll('[data-action]').forEach(el=>el.addEventListener('click',...))`)
koji za `data-action="generate-content"` poziva `generateContent(button)`
IZNOVA. `generateContent()` na svom početku ima SAMO
`if (button.disabled) return;` kao re-entrancy guard. Ako se
`button.disabled` skine na `false` da bi `_onClickWhileRunning` mogao
da primi klik, ISTI klik će OKINUTI I delegirani listener (registrovan
prije, izvršava se prvi) koji će pozvati `generateContent(button)`
IZNOVA -- drugi, potpuno nezavisan `generate_campaign_content` submit,
uporedo sa cancel pozivom iz `_onClickWhileRunning`. Rezultat: klik na
"Otkaži" bi TIHO pokrenuo I novi posao.

**Ispravan pristup**: razdvoji "vizuelno/funkcionalno klikabilno" od
"re-entrancy guard za generateContent()". Konkretno:

1. Re-entrancy guard u `generateContent()`-u prebaci sa
   `if (button.disabled) return;` na provjeru posebnog markera, npr.
   `if (button.dataset.acsJobActive === '1') return;` -- postavi
   `button.dataset.acsJobActive = '1'` odmah nakon uspješnog submita
   (`jobId = submitResult.job_id;`), obriši ga (`delete
   button.dataset.acsJobActive;` ili `= '0'`) u `_renderTerminal`
   zajedno sa restauracijom `originalLabel`.
2. `button.disabled` OSTAJE `false` (ili se eksplicitno postavi na
   `false`) tokom cijelog RUNNING perioda TAKO DA `click` eventi
   STVARNO stižu i do delegiranog listenera (koji sad bezopasno
   `return`-uje zbog #1) i do `_onClickWhileRunning` (koji šalje
   `cancel_job`).
3. Alternativa (ako ti je jednostavnije, Codex je i to predložio):
   ODVOJEN cancel element/dugme koje se prikazuje SAMO tokom RUNNING,
   a glavno "Generiši" dugme ostaje `disabled=true` cijelo vrijeme.
   Ako ideš ovim putem, i dalje moraš voditi računa da klik na NOVI
   cancel element ne prolazi kroz isti globalni `[data-action]`
   delegate (dodaj mu poseban `id`/handler, ne `data-action` atribut
   koji bi ga uhvatio istim delegate-om, OSIM ako namjerno želiš da
   ima svoj `data-action="cancel-content"` granu u delegate-u -- tvoj
   izbor, samo dokumentuj).

**Test** (novi, u `test_kampanje_ssr.py` ili adekvatnom SSR/JS
string-assertion fajlu, ISTI stil kao postojeći `escapeHtml`/
`loadCampaigns` string-assertion test iz ACS-F1-046 -- ovaj projekat
nema JS runtime harness): string-assertion da `button.disabled` NIJE
`true` na RUNNING grani i da re-entrancy guard koristi NEŠTO DRUGO od
`.disabled`. Ako ti je moguće, DODATNO (opciono, nije blokirajuće ako
premašuje postojeći test-harness): headless DOM test koji STVARNO
dispatch-uje drugi klik i broji TAČNO JEDAN `cancel_job` poziv, NULA
dodatnih `generate_campaign_content` poziva.

## Fix 2 — BF-CODEX-2: partial outcome mora preživjeti cancellation

**Lokacija**: `_run_generate_content_locked`, `bridge/__init__.py:826-904`.

**Šta promijeniti**: obavij `for` petlju u `try/finally` tako da se
`_patch_terminal_state` poziva TAČNO JEDNOM, bez obzira da li petlja
završi prirodno ILI propagira `CancellationError`:

```python
try:
    for index, item in enumerate(plan_items):
        ... # postojeće tijelo petlje, NEPROMIJENJENO
finally:
    if jid:
        _patch_terminal_state(
            job_manager, jid,
            generated_count=len(generated_ids),
            failed_count=failed_count,
            content_piece_ids=tuple(generated_ids),
            message=first_error or "",
        )
```

Ukloniti STARI `if jid: _patch_terminal_state(...)` blok koji je bio
POSLIJE petlje (linije 897-904) -- `finally` ga zamjenjuje, JEDAN
call-site umjesto dva (i sprečava da se ubuduće opet razdvoje pa
zaborave sinhronizovati). `finally` se izvršava PRIJE nego
`CancellationError` nastavi propagirati ka `JobManager._run`, isto
kao što `_patch_terminal_state`-ov docstring već tvrdi ("called...
right BEFORE the function returns, so the job is still RUNNING") --
sad je to STVARNO tačno na oba izlazna puta, ne samo na jednom.

NE obavijati `finally` oko koda PRIJE petlje (provider
resolution/`GenerateSocialPost` konstrukcija/`existing_pieces` upit)
-- ako TO pukne, job ispravno ide u FAILED sa `generated_count=0`
(ništa nije ni pokušano), nema šta da se patch-uje.

**Test** (novi, popravi i postojeći): tvoj `test_cancel_job_actually_stops_the_loop`
trenutno sinhronizuje na `generated_count >= 1`, polje koje se NIKAD
ne mijenja dok petlja radi (samo `progress_current` se mijenja preko
`update_progress`) -- promijeni sinhronizaciju na `progress_current >= 1`.
Dodaj asertaciju (novu ili u istom testu):
`final["generated_count"] == _count_content_pieces(bridge, campaign_id)`
I `0 < final["generated_count"] < total` -- STVARAN dokaz da terminal
DTO odražava STVARNO perzistirano stanje, ne samo da je status
`CANCELLED`.

## Šta NE dirati (Codex-ovo ograničenje, i dalje važi)

- Ne vraćati `_find_current_job_id` niti bilo kakvo globalno pogađanje
  RUNNING joba -- `token.job_id` kanal ostaje.
- Ne dirati `domain/`/`application/`/`ports/`/`infrastructure/database/`
  niti export flow.
- Ne uklanjati BF-1/3/4/5 regresije, worker-thread resource test, ni
  `test_two_concurrent_jobs_each_know_their_own_job_id`.
- Ne refaktorisati cijeli `JobManager` -- fix ostaje fokusiran na
  cancel UI (app.js) i cancellation partial-state zapis (bridge
  closure).

## Verifikacija prije re-review-a

```bash
python -m pytest tests/unit/jobs/ tests/unit/presentation_webview/ tests/unit/presentation/ -v
python -m pytest -q
python -m ruff check .
python -m mypy src
```

Sve mora proći, 0 regresija. Poslije zelenog run-a, tražiti Codex
rereview PR #12-a. HIGH task ne ide na Human Owner approval dok Codex
ne da PASS na oba nalaza.
