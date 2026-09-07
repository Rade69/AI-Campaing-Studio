# ACS-F1-047 — final decision packet (HIGH risk)

**Task**: `generate_campaign_content` preko `JobManager`-a — nepokretno
dugme (~2 min zamrznuto na plan sa 12 stavki), progress, otkazivanje.
Fix za Nalaz 4 iz web Claude review-a (2026-09-07).

**PR**: https://github.com/Rade69/AI-Campaing-Studio/pull/12
**HEAD**: `ee8331a` (rebase-ovan na main, sve 4 fix runde uključene)
**Implementer**: MiniMax
**Reviewers**: Claude (koordinator, 4 runde), Codex (adversarial, 3 runde)

## READY FOR HUMAN OWNER APPROVAL

## Tok review-a (kratko)

1. **Implementacija (runda 1)** — `JobManager.update_progress` (aditivno),
   `generate_campaign_content` postaje job-backed preko closure-a sa
   sopstvenim `_resource_scope` (HOTFIX-002 obrazac na job thread-u),
   `get_job_status`/`cancel_job` novi metodi, `app.js` polling+cancel UI.
2. **Claude review (runda 1)** — REQUIRED FIX prije push-a: closure nema
   deterministički način da sazna sopstveni `job_id`
   (`_find_current_job_id` ambiguity heuristika puca čim 2+ joba
   konkuriše). Fix: `CancellationToken.job_id` postavljen u `submit()`.
   Nezavisno mutation-testirano.
3. **Codex round 1** — REJECT: BF-CODEX-1 (cancel dugme trajno
   `disabled`, klik nikad ne stiže) + BF-CODEX-2 (partial outcome
   gubljen na cancellation, `_patch_terminal_state` van petlje).
4. **Fix runda 2** — `button.disabled` uklonjen sa RUNNING putanje,
   `try/finally` oko petlje. Nezavisno mutation-testirano (vraćen stari
   kod, novi test puca identično Codex-u).
5. **Codex round 2** — REJECT: BF-CODEX-3, novi nalaz KOJI SAM JA VEĆ
   PRIJAVIO Codex-u kao ne-blokirajuću opservaciju u prošloj rundi —
   Codex ga je uživo reprodukovao i eskalirao (submit-in-flight
   double-click race, marker se postavljao poslije `await`-a).
6. **Fix runda 3** — marker pomjeren na sinhrono mjesto prije `await`-a.
   Nezavisno verifikovano SOPSTVENOM Node ekstrakcijom iz stvarnog
   `app.js`-a (implementer-ov repro je bio ručno pisana kopija, slabiji
   dokaz — primijećeno i ispravljeno u mojoj verifikaciji).
7. **Codex round 3** — **PASS_WITH_NOTES, bez blocking nalaza.** Codex
   je sam pokrenuo SOPSTVENU ekstrakcionu Node reprodukciju (ne
   implementer-ovu kopiju), potvrdio sve tri prethodne ispravke drže.

Ukupno: 1 implementacija + 3 fix runde, 4 Claude review runde, 3 Codex
adversarial runde. Svaki nalaz (moj i Codex-ov) je nezavisno
reprodukovan PRIJE prosljeđivanja implementeru, i svaki fix je
nezavisno re-verifikovan (uključujući mutation-testing gdje je
primjenjivo) PRIJE nego je poslat na sljedeću review rundu.

## Šta je konačno stanje koda

- `JobManager.update_progress` — aditivan, thread-safe preko
  postojećeg `_lock` obrasca.
- `CancellationToken.job_id` — aditivan atribut, postavljen u
  `submit()` gdje je `job_id` već poznat. Deterministički kanal za
  closure da sazna sopstveni identitet, bez ambiguity-a pod
  konkurentnošću (`max_workers=4`).
- `generate_campaign_content` — sync boundary/lookup/approve/SUPERSEDED-
  reject ostaje brz i sinhron; per-piece AI petlja ide na background
  job. Vraća `job_id` odmah.
- Closure otvara SOPSTVENI `_resource_scope` (HOTFIX-002 obrazac na
  job thread-u) i drži per-pair lock (BF-3 carried forward) oko cijele
  sekvence.
- `try/finally` oko per-piece petlje — `_patch_terminal_state` se
  poziva TAČNO JEDNOM, na oba izlazna puta (prirodan kraj i
  cancellation), pa terminal `JobState` uvijek odražava STVARNO
  perzistirano stanje.
- `get_job_status`/`cancel_job` — JSON-safe, no-leak, unknown ID ->
  sync `VALIDATION_ERROR`.
- `app.js` — dugme ostaje klikabilno tokom RUNNING (cancel radi kroz
  GUI), re-entrancy guard je poseban `dataset.acsJobActive` marker
  postavljen SINHRONO prije prvog `await`-a (ne `.disabled`), sync-
  reject/IPC-blip grane čiste marker.
- DTO (`GenerateContentResultUiModel`) smanjen sa 7 na 5 polja
  (per-piece outcome sad na `JobState`, čitljiv preko `get_job_status`).

## Gate (zadnji poznat, potvrđen od koordinatora i Codex-a nezavisno)

```text
pytest -q                                    -> 1071 passed
pytest tests/unit/jobs/tests/unit/presentation_webview/tests/unit/presentation -q -> 294 passed
ruff check .                                 -> All checks passed
mypy src                                     -> Success, 175 files
CI (PR #12, gh pr checks)                    -> zeleno
```

## Poznati, prihvaćeni rezidualni rizici (ne blokiraju)

1. **Trajna JS reprodukcija (`bf-codex-3-repro.js`) nije dio CI-ja** i
   koristi ručno pisanu kopiju logike, ne ekstrakciju — Codex je ovo
   eksplicitno označio kao neblokirajuće (projekat nema JS test
   harness, kontrakt dopušta dokumentovanu ručnu verifikaciju). I ja i
   Codex smo NEZAVISNO potvrdili stvarni kod preko ekstrakcionih
   reprodukcija van te skripte. Preporuka za budućnost: mali test koji
   učitava stvaran `app.js` fragment, ili minimalni JS smoke gate kad
   projekat uspostavi tu infrastrukturu — nije dio ovog taska.
2. **Integration testovi nisu pokrenuti** (zahtijevaju prave API
   ključeve, isto ograničenje kroz sve runde) — validacija prije
   šireg release-a treba pokrenuti
   `tests/integration/presentation_webview/bridge/test_campaign_bridge_end_to_end.py`.
3. **`app.js` polling interval 1200ms** — kratki poslovi (1-2 stavke)
   možda ne pokažu vidljiv progress prije nego stignu do terminalnog
   stanja. Kozmetičko, dokumentovano od implementera u prvoj rundi,
   nije ponovo eskalirano ni od Claude ni od Codex-a u kasnijim
   rundama.

## Traženo odobrenje

HIGH risk task, pun ciklus proveden (implementer → Claude ×4 →
Codex ×3). Sve rezidualne rizike smo eksplicitno pregledali i
odlučili da ne blokiraju. Molim odobrenje za merge PR #12 u main.
