# ACS-F1-047 — Codex review fix runda 2 (BF-CODEX-1, BF-CODEX-2) — IMPLEMENTER EVIDENCE

Implementer: MiniMax · Reviewer: Codex (runda 3, REJECT)
Review source: `agent_reports/2026-09-07-ACS-F1-047-review-codex.md`
Fix-brief source: `agent_reports/2026-09-07-ACS-F1-047-fix-brief-2-za-minimax.md`
Implementer commit (fix runda): slijedi nakon ovog evidence fajla
Prethodni implementer commit: `77a477b` (lokalni, worktree)

## Status po nalazu

| Nalaz | Opis | Status | Dokaz |
|-------|------|--------|-------|
| **BF-CODEX-1** | Generate dugme `disabled=true` kroz RUNNING → cancel klik nikad ne dolazi do `_onClickWhileRunning` | **FIX** | `app.js`: dugme ostaje `enabled` tokom RUNNING; re-entrancy guard prebačen na `button.dataset.acsJobActive` (odvojeno od `.disabled`); marker postavljen na uspješan submit, obrisan u `_renderTerminal` |
| **BF-CODEX-2** | `_patch_terminal_state` izvan for-petlje → preskače se na cancelu, terminal DTO ima `generated_count=0` | **FIX** | `bridge/__init__.py`: try/finally oko for-petlje; `_patch_terminal_state` JEDAN call-site u `finally` bloku, poziva se i na SUCCEEDED i na CANCELLED |

## Reproducibilni gate output

```text
# 1. Presentation/presentation_webview + jobs testovi
$ python -m pytest tests/unit/jobs/ tests/unit/presentation_webview/bridge/ tests/unit/presentation/ -q
109 passed in 24.39s

# 2. Puni unit suite
$ python -m pytest tests/unit -q
924 passed, 1 warning in 104.54s (0:01:44)

# 3. Lint
$ python -m ruff check .
All checks passed!

# 4. Type check
$ python -m mypy src
Success: no issues found in 175 source files

# 5. Phase0 gate + secret scan
$ python -m pytest tests/unit/scripts/test_generate_phase0_gate_report.py tests/unit/scripts/test_check_no_secrets.py -q
33 passed in 61.85s
  - phase0_foundation_gate.json: PASS
  - check_no_secrets: 26/26 PASS
```

## BF-CODEX-1 dokaz (re-entrancy marker + button enabled)

**Prije**: `button.disabled = true` postavljen prije submita; nikad se ne vraća na `false` dok je job RUNNING. HTML `<button disabled>` NE emituje `click` event (standard browser ponašanje), pa `_onClickWhileRunning` nikad ne dobija priliku da pozove `cancel_job` kroz GUI. Backend `cancel_job` radi ispravno kad se pozove direktno (testovi to dokazuju), ali korisnik NEMA način da ga pozove kroz UI.

**Naivan fix je opasan**: samo skiniti `disabled` na `false` znači da delegirani `[data-action]` listener (page-load-time, registrira se na SVAKI `[data-action]` element, poziva `generateContent(button)` iznova) hvata isti klik i šalje NOVI `generate_campaign_content` submit paralelno sa cancelom. I "Otkaži" i novi submit bi se izvršavali istovremeno.

**Poslije (Fix)**:
- `button.disabled` OSTAJE `false` tokom cijelog RUNNING perioda, tako da `click` eventi stižu do `_onClickWhileRunning`
- Re-entrancy guard u `generateContent()` prebačen sa `if (button.disabled) return;` na `if (button.dataset.acsJobActive === '1') return;` — odvojeni marker
- `dataset.acsJobActive` postavljen na `'1'` odmah nakon uspješnog submita (prije polling starta)
- `dataset.acsJobActive` obrisan u `_renderTerminal` (zajedno sa restauracijom originalnog label-a)
- Tako delegirani `[data-action]` listener u drugoj invokaciji `generateContent` vidi `acsJobActive=1` i `return`-uje; korisnički klik na dugme za vrijeme RUNNING ide kroz `_onClickWhileRunning` i šalje `cancel_job`

## BF-CODEX-2 dokaz (try/finally + parcijalni outcome)

**Prije**: `_patch_terminal_state(...)` je bio POSLIJE for-petlje (linije 897-904 starog koda). Kada `token.raise_if_cancelled()` baci `CancellationError` u bilo kojem mjestu u petlji (početku iteracije ILI `finally` bloku poslije `generator.execute`), exception propagira KROZ petlju, preskačući `_patch_terminal_state` u potpunosti. `generated_ids`/`failed_count` akumulirani DO tog trenutka se GUBE. Terminal `JobState` ostaje na default `generated_count=0, content_piece_ids=()` iako je sadržaj STVARNO perzistiran.

Codex-ova reprodukcija: 4 stavke, cancel mid-loop → DB 2 reda, terminal DTO 0.

**Poslije (Fix)**:
- `try/finally` oko for-petlje — `finally` blok sadrži `if jid: _patch_terminal_state(...)`
- Jedan call-site umjesto dva (nema rizika da se ubuduće opet razdvoje pa zaborave sinhronizovati)
- `finally` se izvršava i na prirodan exit (loop završi) I na `CancellationError` propagaciju — u oba slučaja akumulatori se zapisuju u JobState
- `try/finally` obuhvata SAMO for-petlju, NE kod PRIJE petlje (provider resolution/`GenerateSocialPost` konstrukcija/`existing_pieces` upit) — ako TO pukne, job ispravno ide u FAILED sa `generated_count=0` (ništa nije pokušano)

## Test poboljšanja

### Ažuriran `test_cancel_job_actually_stops_the_loop`

Stari test je sinhronizirao na `generated_count >= 1` — polje koje se NIKAD ne mijenja tokom petlje (samo `progress_current` se ažurira preko `update_progress`). To je bio "mid-loop" tajming slučajan, ne namjeran (Codex-ov nalaz).

**Fix**: sinhronizira na `progress_current >= 1` (stvarni mid-loop signal).

**Nove asertacije**:
- `final["generated_count"] == _count_content_pieces(bridge, campaign_id)` — terminal DTO odražava stvarno perzistirano stanje, ne default nule
- `0 < final["generated_count"] < final["progress_total"]` — strogo između 0 i total, cancel je STVARNO pao mid-loop (ne na kraju, ne na početku)

Sleep po pozivu povećan sa 0.5s na 2.0s da se prozor za cancel pouzdano uhvati (prethodni 0.5s × 4 = 2s ukupno, prekratko za race-free testing).

## Šta NE dirati (Codex-ovo ograničenje, i dalje važi)

- `_find_current_job_id` se NE smije vratiti (token.job_id kanal ostaje)
- `domain/`/`application/`/`ports/`/`infrastructure/database/`/export flow nisu dirani
- BF-1/3/4/5 regresije, worker-thread resource test, `test_two_concurrent_jobs_each_know_their_own_job_id` — svi i dalje zeleni

## Šta koordinator treba uraditi

1. Push na `origin/task/ACS-F1-047-job-manager-wiring` (NE radim push kao implementer).
2. Codex ponovno provjerava PR #12 (samo BF-CODEX-1 i BF-CODEX-2 fix-ovi).
3. Ako Codex PASS, Human Owner odobrenje, pa merge.
4. PR #12 i dalje NIJE merged.

## Preostali rizici (iskreno)

1. **`button.dataset.acsJobActive` cleanup** — u tri izlazne grane (success render, IPC blip u poll, sync-layer fail) marker se briše. Ako budući refaktor doda NOVU izlaznu granu koja zaboravi `delete button.dataset[JOB_ACTIVE_ATTR]`, dugme ostaje zauvijek "aktivno" (re-entrancy guard vraća `true` na svaki sljedeći klik). Linija komentara u `app.js` to eksplicitno naglašava.

2. **`_patch_terminal_state` JEDAN call-site** — `try/finally` osigurava da se pozove i na SUCCEEDED i na CANCELLED. Ako budući refaktor pomjeri `_patch_terminal_state` VAN `finally`-a, BF-CODEX-2 se vraća. Komentar u kodu to eksplicitno naglašava ("without the ``finally`` branch the CANCELLED path was leaving...").

3. **Integration testovi nisu pokrenuti** (isti razlog kao u prethodnim rundama — `tests/integration/presentation_webview/bridge/test_campaign_bridge_end_to_end.py` zahtijeva prave API ključeve).

4. **app.js polling interval 1200ms** — kratki poslovi (< 1s ukupno) ne pokazuju progress vidljivo (razmatra se za budući task).
