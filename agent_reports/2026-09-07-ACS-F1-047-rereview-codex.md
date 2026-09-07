---
verdict: REJECT
scope: PASS
acceptance: REJECT
architecture: PASS
security: PASS
tests: REJECT
gitnexus_impact: PASS
blocking_findings:
  - "BF-CODEX-3: acsJobActive se postavlja tek poslije await-a, pa brzi double-click pokreće dva joba i dva međusobno konfliktna UI trackera."
---

# CILJ

Re-review PR-a #12 (`ACS-F1-047`) na HEAD-u `c2d171f`, prvenstveno protiv
prethodnih blockera BF-CODEX-1 i BF-CODEX-2, uz adversarial provjeru novog
`acsJobActive` re-entry mehanizma. Produkcijski kod nije mijenjan.

# URAĐENO / PROVJERENO

- **BF-CODEX-1 — osnovni kvar je zatvoren:** gumb više nije `disabled` tokom
  RUNNING stanja, pa stvarni click može doći do `_onClickWhileRunning` i
  `cancel_job` poziva.
- **BF-CODEX-2 — zatvoren:** `_patch_terminal_state` je u `finally` bloku oko
  cijele per-piece petlje. Mid-flight cancellation sada zadržava
  `generated_count`, `failed_count` i `content_piece_ids` koji odgovaraju
  perzistiranom partial rezultatu.
- Popravljeni cancel test sada se sinhronizuje na `progress_current >= 1` i
  asertuje stvarni partial rezultat; ciljani test prolazi.
- Ponovno su prošli two-distinct-jobs `token.job_id` scenario i fresh worker
  thread/resource-scope scenario.
- Otkriven je novi, reproduciran re-entry blocker u samom BF-CODEX-1 fixu
  (BF-CODEX-3 ispod).

# GITNEXUS / IMPACT

Glavni checkout je indeksiran i svjež na `fac9085`. Upstream impact za
`CampaignBridgeApi` i `JobManager` ponovno pokazuje očekivani put kroz webview
entry point i bootstrap. Zbog dokumentovanog linked-worktree binding
ograničenja, PR diff je dodatno provjeren punim `git diff main...HEAD`,
`git diff f077fb6...c2d171f`, caller grepom i GitHub PR metapodacima.

# BLOCKING FINDINGS

## BF-CODEX-3 — marker ne zatvara submit-in-flight double-click prozor

Severity: **medium**, blocking za ovaj HIGH UI/concurrency task.

Lokacija: `src/ai_campaign_studio/presentation_webview/static/app.js:291-327,
374-402, 365-371`.

`generateContent()` provjerava `button.dataset.acsJobActive` na liniji 300,
ali marker postavlja tek na liniji 401, poslije:

```javascript
const submitResult = await api.generate_campaign_content(...);
```

Zato dva klika prije povratka prvog IPC poziva oba vide nepostavljen marker i
oba pozovu backend. Ovo nije samo kozmetičko dupliranje: svaka invokacija
registruje vlastiti interval i vlastiti cancel listener na istom gumbu, ali
dijele jedan `dataset.acsJobActive` i jednu labelu.

Živa offline JS reprodukcija nad stvarnom funkcijom iz `app.js`:

```text
submit_calls_before_first_response=2
acs_job_active=undefined
```

Produžena reprodukcija nakon što oba submita dobiju `job-1`/`job-2`:

```text
initial_submits=2
first_cancel_click=job-1
marker_after_job1_terminal=undefined
remaining_tracker_listeners=1
submit_calls_after_next_click=3
cancel_calls=job-1,job-2
```

Failure path:

1. Brzi double-click pokrene dva backend joba i dva pollera.
2. Prvi cancel click otkaže samo `job-1`; drugi listener se zaustavlja jer je
   prvi promijenio zajedničku labelu u `Otkazujem…`.
3. Kada `job-1` postane terminalan, njegov tracker briše zajednički active
   marker iako `job-2` još radi.
4. Sljedeći click pozove preostali cancel listener za `job-2`, ali delegirani
   generate handler na istom clicku sada vidi obrisan marker i pokrene
   `job-3`.

Backend per-pair lock sprječava duple DB redove, ali ne popravlja UI ugovor:
korisnik može proizvesti više pozadinskih jobova/pollera, jedan cancel ne
zaustavlja cijeli vidljivi rad, a tracker koji prvi završi prerano otključava
novi submit. To je direktna regresija re-entrancy zaštite i čini cancellation
ponašanje nedeterminističnim na običnom double-clicku.

Required fix: postaviti submitting/active marker **sinhrono prije prvog
`await`-a**, nakon lokalne payload/API validacije; očistiti ga na sync reject i
IPC exception granama, a na uspjehu ga zadržati do terminalnog cleanup-a.
Dodati JS runtime test sa deferred submit Promiseom koji pozove handler dva
puta prije resolve-a i asertuje tačno jedan
`generate_campaign_content` poziv, jedan poller i jedan cancel listener.

# STANDARDNA VERIFIKACIJA

```text
pytest tests/unit/jobs tests/unit/presentation_webview tests/unit/presentation -q
294 passed in 26.42s

pytest -q
1071 passed, 1 warning in 109.37s

ruff check .
All checks passed!

mypy src
Success: no issues found in 175 source files

gh pr checks 12
test  pass  1m32s
```

Ciljano:

```text
test_cancel_job_actually_stops_the_loop
test_two_concurrent_jobs_each_know_their_own_job_id
test_generate_content_works_from_fresh_worker_thread
3 passed in 5.48s
```

Zeleni Python/CI gate ne pokriva BF-CODEX-3 jer repo nema JS runtime test za
`generateContent()` re-entry/cancel ponašanje.

# ADVERSARIALNA PROVJERA

- Mid-flight partial cancellation: PASS; DTO i DB count su usklađeni.
- Cancel click na jednom aktivnom trackeru: PASS; gumb je enabled.
- Dva različita backend joba: PASS za deterministički `token.job_id`.
- Same-pair DB idempotentnost: backend lock sprečava duplikate.
- Submit-in-flight double-click: FAIL; dva submita nastaju prije markera.
- Više trackera na istom gumbu: FAIL; dijeljeni marker/label proizvode prerani
  unlock i naknadni treći submit.

# NE DIRATI U FIX RUNDI

- Ne mijenjati ispravan `try/finally` partial-outcome fix.
- Ne vraćati `button.disabled` kao RUNNING guard; to bi ponovo slomilo cancel.
- Ne vraćati `_find_current_job_id`; zadržati `token.job_id`.
- Ne širiti u domain/application/ports/database/export flow.
- Ne refaktorisati `JobManager`; BF-CODEX-3 je lokalni JS state-timing problem.

# SLJEDEĆE

PR #12 još nije spreman za Human Owner merge approval. Potrebna je uska JS
fix runda koja zatvara pre-`await` re-entry prozor i regression test sa
odgođenim submit odgovorom. Nakon toga ponoviti ciljani JS scenario, puni gate
i kratki Codex re-review.
