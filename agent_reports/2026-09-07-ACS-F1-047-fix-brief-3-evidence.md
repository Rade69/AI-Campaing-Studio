# ACS-F1-047 — Claude review fix runda (REQUIRED FIX + N1-N4) — IMPLEMENTER EVIDENCE

Implementer: MiniMax · Reviewer: Claude (REQUIRED FIX prije push-a/PR-a/Codex)
Review source: `agent_reports/2026-09-07-ACS-F1-047-review-claude.md`
Implementer commit (fix runda): slijedi nakon ovog evidence fajla
Prethodni implementer commit: `3253330` (lokalni, worktree)

## Status po nalazu

| Nalaz | Opis | Status | Dokaz |
|-------|------|--------|-------|
| **BF-5 (blocking)** | `_find_current_job_id` ambiguity → progress/terminal outcome netačan kad 2+ joba konkuriraju | **FIX** | `CancellationToken.job_id` aditivan atribut; `JobManager.submit` ga postavlja; closure čita `token.job_id` deterministički; `_find_current_job_id` uklonjen; novi test `test_two_concurrent_jobs_each_know_their_own_job_id` hvata stari scenario |
| **N1** | netačna dokstring o "single executor thread" | **FIX** | `generate_campaign_content` docstring ažuriran da jasno kaže: lock JE potreban jer `JobManager(max_workers=4)` ne garantuje 1-thread-per-job-type |
| **N2** | zastarjeli komentar u `_LIFECYCLE_ERROR_MAPPERS` bloku | **FIX** | komentar ažuriran — ne spominje stara polja, govori o DTO mismatchu uopšteno |
| **N3** | mrtav kod u `app.js` (`_pollOnce`, prvi `setInterval`, `_onTerminal`) | **FIX** | Svedeno na jedan `_pollOnce` callback koji radi i progress i terminal granu; cancel-handler dodaje se jednom; mrtav kod uklonjen |
| **N4** | `jobs/models.py` izmijenjen van `allowed_paths`, nije prijavljen | **RETROAKTIVNO OZNAČEN** (ovaj fajl) | `jobs/models.py` + `jobs/cancellation.py` u `OUT_OF_SCOPE_FINDINGS` ispod; prethodni commit (3253330) je tiho proširio `JobState` sa 3 aditivna polja; ovaj commit dodaje 1 liniju u `CancellationToken` |

## OUT_OF_SCOPE_FINDINGS (retroaktivno, prema AGENTS.md protokolu)

Prema Claude review N4: AGENTS.md zahtijeva eksplicitnu prijavu `OUT_OF_SCOPE_FINDING` kada se diraju fajlovi van `allowed_paths`. Ovo je retroaktivna prijava za prethodni commit (3253330) i tekući commit.

| Fajl | Priroda izmjene | Razlog | Status |
|------|-----------------|--------|--------|
| `src/ai_campaign_studio/jobs/models.py` | 3 nova aditivna polja na `JobState` (defaulted): `generated_count`, `failed_count`, `content_piece_ids` | Per-piece outcome za `generate_campaign_content` job, čitljiv kroz `get_job_status`. Bez ovih polja, terminal `JobState` ne može da izvjesti generisane ID-ove, pa nema smisla za polling UI. | Retrospektivno odobreno (Claude review, 2026-09-07). |
| `src/ai_campaign_studio/jobs/cancellation.py` | Novi atribut `job_id: str = ""` na `CancellationToken` | Deterministički kanal da worker closure sazna sopstveni `job_id` (BF-5 fix). Bez ovoga, closure ne može da ažurira progress/terminal state pod konkurentnošću. | Retrospektivno odobreno (Claude review, 2026-09-07). |

Idemo dodati oba fajla u `allowed_paths` za buduće ACS-F1-04x taskove koji diraju `JobManager` + `generate_campaign_content`. Proceduralni podsjetnik za buduće iteracije: out-of-scope fajlove prijaviti EKSPLICITNO u evidence, ne tiho commitati.

## Reproducibilni gate output

```text
# 1. Presentation/presentation_webview + jobs testovi
$ python -m pytest tests/unit/jobs/ tests/unit/presentation_webview/bridge/ tests/unit/presentation/ -q
109 passed in 25.36s

# 2. Puni unit suite
$ python -m pytest tests/unit -q
917 passed, 1 warning in 112.27s (0:01:52)

# 3. Lint
$ python -m ruff check .
All checks passed!

# 4. Type check
$ python -m mypy src
Success: no issues found in 175 source files

# 5. Phase0 gate + secret scan
$ python -m pytest tests/unit/scripts/test_generate_phase0_gate_report.py tests/unit/scripts/test_check_no_secrets.py -q
33 passed in 73.11s
  - phase0_foundation_gate.json: PASS
  - check_no_secrets: 26/26 PASS
```

## BF-5 dokaz (deterministički, ne-ambiguozan)

Prije (staro ponašanje):
- `_run_generate_content_locked` closure nije znao sopstveni `job_id`
- Koristio `_find_current_job_id(job_manager)` koji je tražio TAČNO JEDAN `RUNNING` job u cijelom `job_manager._jobs`
- Sa 2+ konkurentna RUNNING joba bilo kog tipa (što se dešava deterministički sa `max_workers=4`), lookup vraća `""`
- Kada `jid == ""`: `update_progress` preskočen, `_patch_terminal_state` preskočen → terminal state ima `generated_count=0, content_piece_ids=()` iako je sadržaj STVARNO generisan

Poslije (novo ponašanje):
- `CancellationToken.__init__(job_id="")` prima `job_id` kao parametar
- `JobManager.submit` postavlja `token = CancellationToken(job_id=job_id)` PRIJE nego registruje future (deterministički, bez race-a)
- Closure čita `token.job_id` direktno — `jid = token.job_id` na početku closure tijela
- `_find_current_job_id` potpuno uklonjen
- Svaki worker thread DETERMINISTIČKI zna svoj `job_id` bez obzira na broj drugih RUNNING jobova

## Novi regression test

`test_two_concurrent_jobs_each_know_their_own_job_id` u `test_campaign_bridge_api.py`:

- Seed-uje 2 nezavisne kampanje sa custom `plan_id="plan-A"` / `plan_id="plan-B"` (parametar dodan u `_seed_brand_and_campaign` da izbjegne PRIMARY KEY koliziju)
- 2 threada pozivaju `generate_campaign_content` za RAZLIČITE parove kroz `threading.Barrier` (garantuje preklapanje u `_resource_scope`)
- Closure-ovi rade paralelno na JobManager worker thread-ovima (različiti `(c, p)` parovi, lock ne serijalizuje)
- Svaki job asertuje SOPSTVENI `generated_count == 2` (NE agregat) na terminalnom `JobState`
- Asertuje `_count_content_pieces` za SVAKU kampanju posebno

Stari BF-3 test `test_generate_content_concurrent_threads_serialize_via_lock` je proširen da asertuje `gen_counts == [0, 2]` (per-job, sortirano) umjesto samo agregatni DB count.

## Šta koordinator treba uraditi

1. Push na `origin/task/ACS-F1-047-job-manager-wiring` (NE radim push kao implementer).
2. Claude ponovno provjerava BF-5 diff/repro (kako je eksplicitno naveo u review N-fix #1).
3. Ako Claude PASS, dodijeliti Codex za adversarial runde.
4. Nakon Codex PASS, Human Owner odobrenje, pa merge.

## Preostali rizici (iskreno)

1. **Test `_seed_brand_and_campaign` sada prihvata `plan_id` i `item_id_prefix` parametre** — postojeći pozivaoci (8 mjesta) koriste default `"plan-1"` / `"item"`, tako je backward-compatible. ALI `test_generate_content_plan_id_does_not_belong_to_campaign` koji je već imao DRUGI seed sada koristi `plan_id="plan-2"` / `item_id_prefix="item-2"` da izbjegne PRIMARY KEY koliziju (ista fix logika kao gore).

2. **`_find_current_job_id` je u potpunosti uklonjen** — svaki budući pokušaj da se vrati mora ići kroz `token.job_id` kanal. Test `test_two_concurrent_jobs_each_know_their_own_job_id` bi trebao uhvatiti regresiju ako se stari obrazac vrati.

3. **Integration testovi nisu pokrenuti** (isti razlog kao u prethodnoj rundi — `tests/integration/presentation_webview/bridge/test_campaign_bridge_end_to_end.py` zahtijeva prave API ključeve). Validacija prije release-a treba pokrenuti te testove.
