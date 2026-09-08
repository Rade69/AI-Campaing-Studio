---
verdict: REJECT
scope: PASS
acceptance: REJECT
architecture: PASS
security: PASS
tests: REJECT
gitnexus_impact: PASS
blocking_findings:
  - "BF-1: Node/VM harness ne dokazuje {once:true}; uklanjanje listener opcije i dalje prolazi."
  - "BF-2: Nedostaje contractom obavezan trajni real-DB test sa najmanje dvije kampanje različitih statusa."
---

# ACS-F1-051 — Codex adversarial review PR #16

## CILJ

Nezavisni review PR #16 (`task/ACS-F1-051-pocetna-read-path`, HEAD
`ca024d4`) protiv `agent_reports/ACS-F1-051-task-contract.md`, sa fokusom
na pywebview lifecycle, cross-screen izolaciju i XSS.

## PROVJERENO

- Stvarni `main...HEAD` diff i implementer evidence su pregledani; scope i
  slojevi odgovaraju contractu.
- Bridge čita stvarne kampanje/content podatke, EXPORTED ne broji kao aktivan,
  vraća pet najnovijih redova i ne izava novi activity domain koncept.
- UI koristi ekran-specifični `[data-pocetna-recent]` guard, `textContent`
  za KPI i escape za ime/status kampanje.
- Immediate API fast path i `pywebviewready` fallback postoje u produkcijskom
  kodu. Cross-screen i XSS mutacije postojeći izvršni test stvarno hvata.
- Nezavisni privremeni SQLite scenarij sa dvije kampanje (DRAFT + EXPORTED)
  potvrdio je produkcijsko ponašanje:
  `ok=True, active_campaigns=1, recent_count=2`.
- GitHub stanje: `MERGEABLE/CLEAN`; CI `test` zelen na istom HEAD-u.

## GITNEXUS / IMPACT

- `CampaignBridgeApi`: LOW upstream, jedan direktni caller
  (`presentation_webview/__main__.py`).
- `PresentationFacade`: nema upstream zavisnosti u grafu.
- Linked-worktree compare je upozorio na stale main-bound indeks; kompenzovano
  je ručnim diff/name-status/diff-check i caller sweepom.

## BLOCKING FINDINGS

### BF-1 — test ne dokazuje exactly-once listener invariant

Contract linije 85–100 i 210–214 traže jednokratni
`addwebviewready` listener i dokaz da kasni event hidrira tačno jednom.
U `tests/unit/presentation_webview/test_pocetna_ssr.py:255-258` DOM double
prima samo `(name, fn)` i odbacuje listener options. Na linijama 305–307
listener se ručno izvrši samo jednom, a završna provjera broji registrovane
funkcije, ne ponašanje nakon ponovljenog eventa.

In-memory mutacija stvarnog `app.js`:

```text
window.addEventListener('pywebviewready', loadDashboardOverview, {once:true})
-> window.addEventListener('pywebviewready', loadDashboardOverview)

postojeći očekivani rezultat: PASS
```

Dakle test ne razlikuje ugovoreni `{once:true}` od regresije. Required fix:
DOM/event double mora podržati listener options, emitovati
`pywebviewready` najmanje dvaput i dokazati samo jedan API poziv/hydration.

### BF-2 — nema obaveznog trajnog multi-campaign real-DB testa

Contract linije 155–156 i posebno 161–164 nalažu realni DB test sa najmanje
dvije kampanje različitih statusa i tačnim counterima. Commitovani testovi imaju
odvojeno jedan DRAFT slučaj i jedan EXPORTED slučaj, ali nemaju dvije kampanje u
istoj bazi. Reviewski privremeni scenario potvrđuje da trenutni kod radi, ali
nije trajni regression dokaz u PR-u.

Required fix: dodati commitovani real-SQLite test sa najmanje dvije kampanje
različitih statusa, content statusima kroz više kampanja te egzaktnim active,
planned, drafts, approved i recent rezultatima.

## STANDARDNA VERIFIKACIJA

```text
presentation/presentation_webview tests
-> 326 passed in 84.82s

focused Node/VM dashboard test on correct code
-> 1 passed

ACS_GATE_REPORT_RUNNING=1 pytest -q
-> 1156 passed, 3 skipped, 1 warning in 100.12s

real gate-report E2E
-> 1 passed in 143.24s

ruff check .
-> All checks passed!

mypy src
-> Success: no issues found in 176 source files

node --check app.js
-> PASS

git diff --check main...HEAD
-> PASS
```

## ADVERSARIALNA PROVJERA

In-memory mutacije, bez izmjene worktreea:

```text
unconditional parse-time load -> test FAIL (readyListeners=0, lateHydrated=False)
generic cross-screen selector -> test FAIL (foreignApiCalls=1, DOM touched)
raw campaign-name interpolation -> test FAIL (nameEscaped=False)
remove {once:true} only -> test PASS  [nepokrivena regresija]
```

Produkcijski kod trenutno prolazi sve izvršene scenarije; REJECT je zbog dva
eksplicitno obavezna HIGH-risk regression dokaza koja PR još nema.

## NE DIRATI

Ne mijenjati bridge/DTO/domain/repo ponašanje osim ako novi test otkrije stvarni
kvar. Reviewer nije mergeao niti pushao.

## SLJEDEĆE

Implementer dodaje dva navedena testa i traži kratak Codex re-review. Human Owner
odobrenje slijedi tek nakon PASS-a; ovaj izvještaj nije merge akcija.

