# → ZA CODEX — ACS-F1-046 re-review (PR #11, poslije BF-1/2/3 fixa)

PR #11: https://github.com/Rade69/AI-Campaing-Studio/pull/11
Branch: `task/ACS-F1-046-kampanje-read-path` (rebase-ovan na main,
HEAD `7a109d9`).
Fix implementer: **Codex sam** (Human Owner odluka -- ista kao za
ACS-F1-047: kad Codex nađe blocking nalaz na ovom tasku, popravlja ga
direktno umjesto round-trip-a nazad implementeru). Fix evidence:
`agent_reports/2026-09-07-ACS-F1-046-fix-codex-evidence.md`.

Odnosi se na tvoj REJECT:
`agent_reports/2026-09-07-ACS-F1-046-review-codex.md` (BF-1, BF-2, BF-3).

## Šta je popravljeno (nezavisno provjereno prije ovog handoff-a)

- **BF-1** (pywebview lifecycle race): `loadCampaigns()` sad koristi
  immediate fast path kad je `window.pywebview.api.list_campaigns` već
  dostupan, inače registruje jednokratni
  `window.addEventListener('pywebviewready', loadCampaigns, {once:true})`.
  **Provjerio sam stvaran `webview` paket** (instaliran u `.venv`) --
  `finish.js` dispečuje `pywebviewready` TEK NAKON
  `window.pywebview._createApi(...)` popuni API, pa je fix
  deterministički race-free, ne pretpostavka o event-imenu.
- **BF-2** (cross-screen table corruption): Kampanje SSR tabela ima
  novi `data-campaigns-table` marker; app.js hidratacija cilja
  ISKLJUČIVO taj marker (provjera na vrhu IIFE-a, early `return` za
  svaki drugi ekran, uklonjen generički `table.table` selector u
  potpunosti). Novi izvršni Node/VM test (`test_app_js_campaign_hydration_lifecycle_and_screen_isolation`)
  pokreće STVARAN committed `app.js` kroz tri scenarija (kasna API
  injekcija, odvojena Plan kampanje tabela, immediate-path XSS) --
  **mutation-testirao sam ga**: privremeno vratio stari kod, test
  puca tačno na svim invarijantama (`readyListeners=0`,
  `lateHydrated=False`, `planUntouched=False`, `planApiCalls=1`,
  `immediateEscaped=False`); vraćen fix -- test prolazi.
- **BF-3** (merge konflikt): branch rebase-ovan preko main-a
  (GUI-009 + F1-047 su u međuvremenu merge-ovani). Potvrdio sam:
  `gh pr view 11` sad pokazuje `mergeable: MERGEABLE`,
  `mergeStateStatus: CLEAN` (bilo `CONFLICTING`/`DIRTY`). Svih 7
  bridge js_api metoda (`create_campaign_and_generate_plan`,
  `generate_campaign_content`, `get_job_status`, `cancel_job`,
  `export_campaign_package`, `configure_provider`, `list_campaigns`)
  potvrđeno prisutno nakon rebase-a, nema conflict markera, forbidden
  slojevi (domain/application/migrations) nedirani.

## Dodatna zaštita (nije bila tražena kao blocker)

Novi `test_list_campaigns_lifecycle_failure_returns_safe_exact_dto`:
`create_connection` baca sa sentinel detaljem, provjerava tačan
4-key DTO i odsustvo sentinela i u rezultatu i u `caplog`. Provjerio
sam da ovo testira `_with_call_resources`-ov POSTOJEĆI, već-siguran
`logger.error(..., type(exc).__name__)` mehanizam (isti kao ostale
bridge metode) -- nije nova ranjivost, samo nova pokrivenost.

## Verifikacija (moja, nakon rebase-a)

```text
python -m pytest -q          -> 1105 passed
python -m ruff check .       -> All checks passed!
python -m mypy src           -> Success: no issues found in 175 source files
```

CI na PR #11: zeleno. `mergeable: MERGEABLE`, `mergeStateStatus: CLEAN`.

## Tvoj fokus za ovu rundu

- Ponovo provjeri BF-1/BF-2/BF-3 fix (kod, ne samo evidence) --
  posebno da `pywebviewready` listener STVARNO ostaje jednokratan
  (`{once:true}`) i da se ne registruje duplo na ponovnom load-u.
- Ponovo provjeri da rebase nije unio regresiju u dijeljenom kodu
  (GUI-009 export lock, F1-047 job metode).
- Standardna adversarial provjera: XSS, lifecycle DTO shape,
  cross-screen isolation sa STVARNIM DOM simulacijom (ne samo
  string-assertion).

Kad završiš, javi rezultat -- koordinator prenosi Human Owner-u za
odobrenje prije merge-a (HIGH risk, pun ciklus).
