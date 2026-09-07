# ACS-F1-047 fix-brief-5 evidence — BF-CODEX-3 (acsJobActive marker race)

**Worktree**: `H:\ai-campaign-studio-worktrees\ACS-F1-047-job-manager-wiring`
**Branch**: `task/ACS-F1-047-job-manager-wiring` (1 commit ispred `origin/main`, NE push-ovano — koordinator radi push + PR)
**Fix-brief**: `agent_reports/2026-09-07-ACS-F1-047-fix-brief-3-za-minimax.md` (Codex REJECT #3, NE-blokirajuća opservacija eskalirana u blocking)
**Risk klasa**: HIGH — implementer NE push-uje; koordinator radi push nakon Human Owner re-review-a

## Šta BF-CODEX-3 zapravo jest

Re-entrancy marker `button.dataset.acsJobActive` postavljao se TEK
nakon `await api.generate_campaign_content(...)`. Dva brza klika u
istom event-loop ticku (prije nego IPC round-trip resolveuje) OBA
prolaze guard na vrhu `generateContent()` — jer marker još nije
setovan. Posljedica: dva submita, dva polling intervala, dva cancel
listenera na istom dugmetu. Prvi tracker koji stigne do terminalnog
stanja prerano briše dijeljeni marker → otvara vrata za TREĆI
spurious submit. Backend lock i dalje sprečava duplikate u bazi, ali
UI ugovor je nedeterministički.

## Fix (u `src/ai_campaign_studio/presentation_webview/static/app.js`)

Dva mala pomaka, oba pokrivena inline komentarom u kodu:

1. **Marker pomjeren na sinhrono mjesto prije prvog `await`-a** (linija 331)
   ```js
   // ACS-F1-047 (Codex BF-CODEX-3): set the re-entrancy marker
   // SYNCHRONOUSLY, BEFORE the first ``await``. ...
   button.dataset[JOB_ACTIVE_ATTR] = '1';
   ```
   Stari marker poslije `await`-a (koji je bio na liniji 401 u
   verziji prije ovog fix-a) UKLONJEN — ne dupliciran.

2. **Sync-reject grana čisti marker** (linija 409, `if (!submitResult || !submitResult.ok)`)
   ```js
   // marker was set SYNCHRONOUSLY above (BF-CODEX-3
   // fix), so a failed submit does NOT permanently lock the button.
   delete button.dataset[JOB_ACTIVE_ATTR];
   button.textContent = originalLabel;
   return;
   ```
   Bez ovog, `ok=false` (npr. SUPERSEDED plan, JobManager shut down)
   bi trajno zaključao dugme jer je marker sada postavljen prije
   submit Promise-a.

`button.disabled` se NE SMIJE dirati — vraćanje na `true` re-introducira
BF-CODEX-1 (otkazivanje ne bi moglo biti kliknuto). `try/finally`
iz BF-CODEX-2 ostaje netaknut.

## Standalone Node reprodukcija

Lokacija: `agent_reports/2026-09-07-ACS-F1-047-bf-codex-3-repro.js`
(izbor korisnika u `ask_user` — bez uvođenja nove trajne JS test
infrastrukture u `scripts/js_smoke_tests/`).

Bez dependencija. Pokretanje:
```bash
node agent_reports/2026-09-07-ACS-F1-047-bf-codex-3-repro.js
```

Skripta u istom fajlu sadrži TAČAN stari kod (BEFORE) i TAČAN novi
kod (AFTER) iz app.js, sa stubovima za `document` / `window.pywebview`
i odgođenim submit Promise-om kojeg kontrolišemo vani. Dva klika u
istom microtask slotu (bez `await` između njih), pa drain svih
pending submita, pa provjera `submit_calls` / `cancel_listeners` /
`pollers` brojki.

### Output reprodukcije (snimljen 2026-09-07)

```
ACS-F1-047 BF-CODEX-3 standalone reprodukcija
============================================

=== BEFORE fix (marker poslije await-a) ===
  [toast] Job job-2 started (BEFORE)
  [toast] Job job-2 started (BEFORE)
  submit_calls=2
  cancel_listeners=2
  pollers=2
  marker tokom submit-a: provjeravamo kroz final state -- cleared na kraju=true
  PASS  BEFORE submit_calls: actual=2 expected=2
  PASS  BEFORE cancel_listeners: actual=2 expected=2
  PASS  BEFORE pollers: actual=2 expected=2

=== AFTER fix (marker sinhrono prije await-a) ===
  [toast] Job job-1 started (AFTER)
  submit_calls=1
  cancel_listeners=1
  pollers=1
  marker tokom submit-a: provjeravamo kroz final state -- cleared na kraju=true
  PASS  AFTER submit_calls: actual=1 expected=1
  PASS  AFTER cancel_listeners: actual=1 expected=1
  PASS  AFTER pollers: actual=1 expected=1

=== AFTER fix: sync-reject (SUPERSEDED plan) cisti marker ===
  marker nakon sync-reject submit-a: obrisan (FIX)
  PASS  AFTER sync-reject clears marker: actual=false expected=false

============================================
REZULTAT: PASS -- BEFORE=2 submita, AFTER=1 submit, sync-reject cisti marker.
```

## Reproducibilni gate output

```text
$ python -m pytest tests/unit/jobs/ tests/unit/presentation_webview/bridge/ tests/unit/presentation/ -q
........................................................................ [ 66%]
....................................                                     [100%]
109 passed in 20.67s

$ python -m pytest tests/unit -q
924 passed, 1 warning in 110.28s (0:01:50)

$ python -m ruff check .
All checks passed!

$ python -m mypy src
Success: no issues found in 175 source files

$ python -m pytest tests/unit/scripts/test_generate_phase0_gate_report.py tests/unit/scripts/test_check_no_secrets.py -q
33 passed in 93.00s (0:01:33)
```

(Jedini `DeprecationWarning` je iz `google.genai` vendor koda za
Python 3.17, nije od našeg koda i nije blokirajući.)

## Šta je promijenjeno, šta nije dirano

**Promijenjeno** (samo ova dva fajla):
- `src/ai_campaign_studio/presentation_webview/static/app.js` —
  marker pomjeren na sinhrono mjesto + sync-reject čišćenje
- `agent_reports/2026-09-07-ACS-F1-047-bf-codex-3-repro.js` — novi
  standalone reprodukcioni fajl (korisnikov izbor: u `agent_reports/`,
  NE u `scripts/js_smoke_tests/`)

**Nije dirano** (namjerno):
- `src/ai_campaign_studio/presentation_webview/bridge/__init__.py` —
  `try/finally` oko for-petlje iz BF-CODEX-2 ostaje netaknut
- `tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py` —
  testovi za BF-CODEX-2 (asertacije za parcijalni outcome) ostaju
- `button.disabled` NE SMIJE biti vraćen na `true` — vratio bi
  BF-CODEX-1
- Codex-ovi `agent_reports/2026-09-07-ACS-F1-047-review-codex.md` i
  `agent_reports/2026-09-07-ACS-F1-047-rereview-codex.md` (nisu
  commitovani u ovoj rundi — njih commituje koordinator u zasebnom
  koraku ako želi)

## Ko pushuje i kad

**NE pushujem.** Ovaj fix je HIGH risk po pravilima workflow-a
(promjena u JavaScript kojeg Codex aktivno review-uje na PR #12,
Codex već odbio prethodni fix-brief, ovo je treći fix-brief u
nizu). Koordinator radi commit review i push na `origin` +
ruku/merge PR-a nakon Human Owner odobrenja.
