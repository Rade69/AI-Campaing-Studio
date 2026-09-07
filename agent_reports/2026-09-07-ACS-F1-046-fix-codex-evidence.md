# ACS-F1-046 — Codex fix evidence poslije REJECT reviewa

Datum: 2026-09-07  
Worktree: `H:\ai-campaign-studio-worktrees\ACS-F1-046-kampanje-read-path`  
Branch: `task/ACS-F1-046-kampanje-read-path`  
Rebased commit: `bfb80e26796466dc0474d2bc081c0418109ad9ff`  
Rebase target: `origin/main@6ab88ca8b70742c7d7ea84964f0f406535f80928`

# CILJ

Po eksplicitnoj odluci Human Ownera, Codex je u ovoj rundi prešao iz reviewer
u implementer ulogu i popravio sva tri blocking nalaza iz
`2026-09-07-ACS-F1-046-review-codex.md`. Claude ostaje nezavisni reviewer;
Codex u ovoj rundi ne daje konačni review verdict.

# URAĐENO

## BF-1 — pywebview lifecycle

`loadCampaigns()` više nije jednokratno pozvan prije garantirane bridge
injekcije. Kampanje IIFE sada:

1. koristi immediate fast path kada je `window.pywebview.api.list_campaigns`
   već dostupan;
2. inače registruje jednokratni
   `window.addEventListener('pywebviewready', loadCampaigns, {once:true})`;
3. offline browser preview ostavlja SSR fixture netaknut jer readiness event
   tamo ne postoji.

## BF-2 — cross-screen table corruption

- Kampanje SSR tabela dobila je jedinstveni `data-campaigns-table` marker.
- Shared `app.js` bira isključivo `[data-campaigns-table]` i odmah izlazi na
  svim drugim ekranima.
- Generički `table.table` selector više ne postoji u produkcijskom JS-u.
- Dodan je izvršni Node/VM DOM regression test nad stvarnim `app.js` fajlom.
  Test dokazuje late API injection, Plan-table izolaciju, immediate fast path
  i XSS escaping.

## BF-3 — konflikt sa mainom

Branch je rebaseovan na `origin/main@6ab88ca`. Ručno su razriješeni konflikti
u shared presentation/bridge/test fajlovima tako da su sačuvani:

- GUI-009 `export_campaign_package` contract, DTO, lifecycle mapper i testovi;
- F1-047 `get_job_status`/`cancel_job` lifecycle mapperi i testovi;
- novi F1-046 `list_campaigns` contract, DTO, mapper i testovi.

Nakon rebasea nema conflict markera, Python syntax/lint prolazi, a puni suite
potvrđuje integrirano stanje.

## Dodatna zaštita

Dodan je `test_list_campaigns_lifecycle_failure_returns_safe_exact_dto`, koji
simulira `create_connection` failure sa SQL/path/sentinel detaljima i potvrđuje:

- tačan `{ok, campaigns, error_code, error_message}` DTO;
- generičku korisničku poruku;
- odsustvo sentinel exception teksta i u JS rezultatu i u logovima.

# PROMIJENJENI FIX FAJLOVI

```text
src/ai_campaign_studio/presentation_webview/screens/kampanje/__init__.py
src/ai_campaign_studio/presentation_webview/static/app.js
tests/unit/presentation_webview/test_kampanje_ssr.py
tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py
```

Rebase je dodatno spojio već odobrene ACS-F1-046 port/adapter/DTO/bridge
izmjene sa aktuelnim mainom; domain, application i migrations nisu mijenjani.

# VERIFIKACIJA

Tačan originalni adversarial repro poslije fix-a:

```json
{
  "ready_listeners": 1,
  "late_hydrated": true,
  "plan_untouched": true,
  "plan_api_calls": 0,
  "raw_xss": false
}
```

Fokusirani lifecycle/isolation testovi:

```text
7 passed, 83 deselected in 2.01s
```

Širi presentation/repository regression gate:

```text
320 passed in 36.94s
```

Puni projektni gate:

```text
pytest -q
1105 passed, 1 warning in 153.78s

ruff check .
All checks passed!

mypy src
Success: no issues found in 175 source files

node --check src/ai_campaign_studio/presentation_webview/static/app.js
PASS

git diff --check
PASS
```

Headless vizuelni sanity-check stvarnog generisanog HTML/CSS/JS-a na
1280x820 sa dva realistična reda:

```text
headers=['Kampanja', 'Brend', 'Status', 'Planirano', 'Kreirano', '']
rows=2
horizontal_overflow=False
```

Dinamička 6-kolonska tabela je vizuelno čitljiva; duži naziv i puni ISO datum
stanu bez preklapanja. Namjerna razlika prema SSR 7-kolonskom fixtureu ostaje.

# REGRESSION SURFACE

- Provjeren je jedini novi page marker i potvrđeno da se pojavljuje samo na
  Kampanje tabeli.
- U produkcijskom `app.js` više nema `table.table` selector varijante.
- Puni suite pokriva spojene GUI-009 export i F1-047 job flowove nakon rebasea.
- Shared repository portovi ostali su aditivni; njihovi postojeći potpisi nisu
  mijenjani.

# NE DIRATI

- Ne vraćati generički `.table` selector.
- Ne pomicati lifecycle poziv nazad na bezuslovni `loadCampaigns()` tokom
  parsiranja skripte.
- Ne uklanjati immediate fast path; potreban je za već-spreman bridge/test
  okruženja.
- Ne mijenjati repo ordering/latest-plan SQL, DTO shape, SSR fixture sadržaj,
  `updated_at` scope ili statički "Otvori" flow.
- Ne gubiti GUI-009/F1-047 lifecycle mappere pri budućem rebaseu.

# STANJE PREDAJE / SLJEDEĆE

Fix je implementiran i verificiran lokalno, ali nije commitovan/pushan nakon
Human Ownerove nove fix odluke. Rebase je nužno prepisao lokalni task commit;
remote PR #11 i dalje pokazuje stari head dok koordinator ne pregleda rezultat.

Sljedeće:

1. Claude radi nezavisni code/architecture/integration review ovog worktreea.
2. Nakon Claude PASS-a koordinator commit-uје četiri fix fajla + ovaj evidence
   report (review REJECT report ostaje istorijski dokaz).
3. Zbog rebasea push mora biti siguran `--force-with-lease`, zatim provjeriti
   novi PR head, mergeability i CI.
4. HIGH task tek poslije toga ide Human Owneru na konačno merge odobrenje.
