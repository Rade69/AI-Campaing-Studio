# → ZA CODEX — ACS-F1-047 treći re-review (PR #12, poslije BF-CODEX-3 fixa)

PR #12: https://github.com/Rade69/AI-Campaing-Studio/pull/12
Branch: `task/ACS-F1-047-job-manager-wiring` (rebase-ovan na main,
commit `80bdb5c`).
Implementer: MiniMax. Fix evidence:
`agent_reports/2026-09-07-ACS-F1-047-fix-brief-5-evidence.md`.

Odnosi se na tvoj drugi REJECT (BF-CODEX-3):
`H:\ai-campaign-studio-worktrees\ACS-F1-047-job-manager-wiring\agent_reports\2026-09-07-ACS-F1-047-rereview-codex.md`
(sad committed na branch).

## Šta je popravljeno (nezavisno provjereno)

`button.dataset.acsJobActive` marker je pomjeren sa "poslije `await
api.generate_campaign_content(...)`" na SINHRONO mjesto ODMAH poslije
`api`-availability provjere, PRIJE bilo kakvog `await`-a. Sync-reject
grana (`!submitResult.ok`) sad eksplicitno čisti marker
(`delete button.dataset[JOB_ACTIVE_ATTR];`) prije `return` -- bez toga
bi neuspio submit trajno zaključao dugme, pošto se marker sad
postavlja PRIJE nego se zna ishod submita.

Implementer je priložio standalone Node repro
(`agent_reports/2026-09-07-ACS-F1-047-bf-codex-3-repro.js`) -- ali
primijetio sam da taj fajl sadrži RUČNO PISANU/dupliciranu kopiju
"AFTER" logike, ne ekstrakciju iz stvarnog `app.js`-a. To je slabiji
dokaz nego što izgleda (mogao bi tiho drift-ovati od stvarnog fajla).
Zato sam napravio SOPSTVENU verifikaciju koja izvlači TAČAN
`generateContent()` tekst iz TRENUTNOG committed `app.js`-a (linije
288-503, `sed` ekstrakcija) i pokreće ga u Node-u sa stub
`document`/`window.pywebview` i kontrolisanim odgođenim submit
Promise-om:

```text
submit_calls_before_response = 1
acsJobActive during race = 1
click listeners during race = 0

VERDICT: submit_calls = 1 (FIXED)
```

Potvrđeno protiv STVARNOG koda, ne kopije. Takođe pročitao cio
`git diff` za `app.js` -- `button.disabled` NIJE vraćen (BF-CODEX-1 bi
se inače ponovo pokvario), `try/finally` iz BF-CODEX-2 netaknut.

## Verifikacija (moja, nakon rebase-a)

```text
python -m pytest -q          -> 1071 passed
python -m ruff check .       -> All checks passed!
python -m mypy src           -> Success: no issues found in 175 source files
```

CI na PR #12 (nakon force-push-a): u toku, javiću ako padne.

## Tvoj fokus za ovu rundu

- Ponovo provjeri BF-CODEX-3 fix -- posebno da marker STVARNO
  pokriva SVE sync-error grane (ne samo `!submitResult.ok` -- provjeri
  i early-return grane za `campaignId`/`planId`/`api`-nedostupnost,
  koje se dešavaju PRIJE marker-set linije, pa im ne treba čišćenje,
  ali potvrdi da tako i jest).
- Ako imaš vremena/mogućnost: pokreni SOPSTVENU JS reprodukciju
  (ne oslanjaj se samo na implementer-ov `bf-codex-3-repro.js`,
  pošto je to ručno pisana kopija, ne ekstrakcija -- vidi napomenu
  gore).
- Standardna regresija: BF-CODEX-1/2, BF-1/3/4/5, worker-thread
  resource scope, two-distinct-jobs test.

Ovo je treća uzastopna Codex runda za ovaj task -- ako je sad čisto,
molim eksplicitno PASS/PASS_WITH_NOTES da možemo ići na Human Owner
odobrenje.
