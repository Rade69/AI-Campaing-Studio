---
verdict: REJECT
scope: PASS
acceptance: REJECT
architecture: PASS
security: PASS
tests: REJECT
gitnexus_impact: PASS
blocking_findings:
  - "BF-CODEX-1: Cancel UI je nedostupan jer je generate gumb disabled tokom cijelog RUNNING perioda."
  - "BF-CODEX-2: CANCELLED JobState gubi stvarni partial outcome i može prijaviti 0 komada iako su redovi već perzistirani."
---

# CILJ

Nezavisna adversarial provjera PR-a #12 (`ACS-F1-047`) protiv Task
Contracta, sa fokusom na stvarni worker-thread lifecycle, deterministički
`job_id`, progres, otkazivanje, polling cleanup i regresije prethodnih
BF-1/3/4/5 nalaza. Pregledan je HEAD `dd04a83` na branchu
`task/ACS-F1-047-job-manager-wiring`; produkcijski kod nije mijenjan.

# URAĐENO / PROVJERENO

- Stvarni diff `main...HEAD` i oba commita PR-a pregledani su, ne samo
  implementer evidence.
- BF-5 iz Claude runde je ispravno popravljen: `JobManager.submit()`
  konstruiše `CancellationToken(job_id=job_id)` prije registracije future-a,
  a closure čita sopstveni `token.job_id`; `_find_current_job_id` više ne
  postoji.
- Test sa dva paralelna joba za različite campaign/plan parove prolazi, kao i
  worker-thread `_resource_scope` regresija.
- Sync validation, SUPERSEDED rejection, same-pair lock i idempotentni re-click
  ostali su pokriveni i prolaze.
- `get_job_status` pretvara datume/status u JSON-safe oblik; unknown ID i
  lifecycle failure ne izbacuju Python exception u JS.
- GitHub CI za PR #12 je zelen (`test`, 2m10s).

# GITNEXUS / IMPACT

`npx gitnexus status` na glavnom checkoutu: index je svjež na `341ad71`.
Upstream impact je provjeren za `JobManager`, `CancellationToken`,
`CampaignBridgeApi` i `GenerateContentResultUiModel`; graf potvrđuje očekivani
blast radius kroz bootstrap, webview entry point i presentation state/contracts.

`detect-changes --scope compare --base-ref main` na registrovanom glavnom
checkoutu nije mogao vidjeti linked-worktree PR diff i prijavio je samo tri
lokalno izmijenjena dokumentaciona fajla na mainu. To je poznato GitNexus
worktree-binding ograničenje iz projektnog protokola, pa je rezultat tretiran
kao nepouzdan, ne kao "nema impacta". Kompenzacija: puni ručni
`git diff main...HEAD`, `gh pr diff --name-only` i `rg` sweep svih callera i
promijenjenih ugovora.

# BLOCKING FINDINGS

## BF-CODEX-1 — "Otkaži" gumb se ne može kliknuti

Lokacija: `src/ai_campaign_studio/presentation_webview/static/app.js:301-302,
374-397, 427-430`.

`generateContent()` postavlja `button.disabled = true` prije submita. Nakon
uspješnog submita samo promijeni labelu u "Otkaži (generišem…)" i doda click
listener, ali gumb nigdje ne vraća u enabled stanje prije terminalnog ishoda.
Disabled HTML button ne šalje click događaj, pa `_onClickWhileRunning` i
`api.cancel_job(...)` nisu dostupni korisniku. Gumb se ponovo enable-a tek u
`_renderTerminal`, kada je otkazivanje već besmisleno.

Ovo direktno krši Objective #5 ("Dugme dobija Otkaži opciju tokom RUNNING") i
čini stvarni UI cancellation nedostupnim iako Python metoda radi kada se
pozove direktno. U repou nema JS runtime testa; SSR testovi provjeravaju samo
da gumb postoji.

Required fix: tokom aktivnog joba omogućiti stvarni cancel gesture bez
ponovnog submita (npr. eksplicitni running state / odvojen cancel gumb), te
dodati test koji stvarno dispatcha drugi korisnički klik i potvrđuje jedan
`cancel_job(job_id)` poziv.

## BF-CODEX-2 — cancellation izgubi partial rezultat iz terminalnog DTO-a

Lokacija: `src/ai_campaign_studio/presentation_webview/bridge/__init__.py:
811-904` i `tests/unit/presentation_webview/bridge/
test_campaign_bridge_api.py:2028-2096`.

`generated_ids` i `failed_count` se skupljaju tokom petlje, ali
`_patch_terminal_state(...)` se poziva samo nakon prirodnog izlaza iz petlje.
Ako `token.raise_if_cancelled()` baci na početku stavke ili u `finally` nakon
AI poziva, kontrola preskoči linije 897-904. `JobManager` zato ispravno postavi
status `CANCELLED`, ali job ostaje sa defaultnim `generated_count=0`,
`failed_count=0`, `content_piece_ids=()` iako je dio sadržaja već commitovan.
To je suprotno i docstringu na linijama 703-707/753-760 koji tvrdi da se
partial outcome patchuje na cancellation putu.

Adversarial reprodukcija sa 4 stavke i sporim fake adapterom:

```text
persisted DB rows: 2
terminal status: CANCELLED
terminal generated_count: 0
assert final["generated_count"] == persisted
E assert 0 == 2
```

Postojeći test `test_cancel_job_actually_stops_the_loop` ipak prolazi. On čeka
`generated_count >= 1`, ali to polje nikad nije ažurirano tokom RUNNING stanja;
nakon timeouta otkaže kasnije i zatim asertuje samo `0 < progress_total` kroz
`generated_count < progress_total`. Zato zelena provjera ne dokazuje ni da je
terminalni partial outcome tačan ni da je otkaz izveden u komentiranom
trenutku.

Required fix: partial counters/ID-eve atomarno zapisati i na
`CancellationError` putu prije re-raise-a, te regression test vezati za stvarno
opaženi progress/AI-call barrier i asertovati:
`0 < DB_count == generated_count == len(content_piece_ids) < total`.

# STANDARDNA VERIFIKACIJA

```text
pytest tests/unit/jobs tests/unit/presentation_webview tests/unit/presentation -q
294 passed in 28.27s

pytest -q
1071 passed, 1 warning in 114.37s

ruff check .
All checks passed!

mypy src
Success: no issues found in 175 source files

gh pr checks 12
test  pass  2m10s
```

`git diff --check main...HEAD` prolazi. Worktree je nakon uklanjanja
privremenog adversarial testa čist prije pisanja ovog necommitovanog review
reporta.

# ADVERSARIALNA PROVJERA

- Dva različita campaign/plan para paralelno: deterministički `token.job_id`
  radi i oba joba dobiju sopstveni ishod.
- Isti par paralelno: per-pair lock zadržava idempotentnost.
- Fresh pywebview thread -> zaseban job worker thread: zasebni resource scope
  radi i konekcija ne curi preko thread granice.
- Mid-flight cancel: status prelazi u `CANCELLED` i petlja staje, ali formalni
  partial outcome nije konzistentan sa bazom (BF-CODEX-2).
- Stvarni UI cancel affordance: nedostupan zbog `disabled` stanja
  (BF-CODEX-1).
- Polling cleanup: terminal i rejected-promise grane čiste interval i listener;
  nije pronađen zaseban blocker u tim granama. `setInterval` ipak može imati
  preklopljene async pollove ako IPC traje duže od 1200 ms; zabilježiti kao
  neblokirajući budući hardening, ne širiti ovu fix rundu bez potrebe.

# NE DIRATI U FIX RUNDI

- Ne vraćati `_find_current_job_id` niti bilo kakvo globalno pogađanje RUNNING
  joba; zadržati `token.job_id` kanal.
- Ne mijenjati domain/application/ports/database schema niti export flow.
- Ne uklanjati BF-1/3/4/5 regresije, worker-thread resource test ili
  two-distinct-jobs test.
- Ne refaktorisati cijeli `JobManager`; fix treba ostati fokusiran na stvarni
  cancel UI i cancellation partial-state zapis.

# SLJEDEĆE

PR #12 nije spreman za Human Owner merge approval. Potrebna je uska fix runda
za BF-CODEX-1 i BF-CODEX-2, zatim ponovno pokrenuti ciljane cancellation/UI
testove, puni gate i novu Codex re-review rundu. HIGH task ostaje bez merge-a
dok oba blockera nisu zatvorena.
