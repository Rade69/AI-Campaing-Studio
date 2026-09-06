---
task_id: ACS-HOTFIX-002
role: implementer
agent: codex
commit: 491a9a1
status: IMPLEMENTED_LOCALLY_AWAITING_PUSH_APPROVAL
---

# ACS-HOTFIX-002 — Codex implementer evidence

## CILJ

Ukloniti SQLite thread-affinity crash iz stvarnih pywebview `js_api` poziva bez korištenja `check_same_thread=False` i bez promjene poslovne logike.

## URAĐENO

- `CampaignBridgeApi` više ne čuva repozitorije/UoW vezane za startup thread.
- `create_bootstrap()` i dalje pokreće migracije jednom; startup konekcija se zatvara odmah nakon konstrukcije bridgea.
- Svaki javni bridge poziv otvara vlastitu standardnu SQLite konekciju na pozivnom worker threadu, gradi lokalni repository/UoW graf i zatvara konekciju u `finally` bloku.
- `ContextVar` veže resurse za konkretan poziv, pa istodobni threadovi ne prepisuju međusobno stanje.
- Greška otvaranja/zatvaranja konekcije ostaje unutar stabilnog `INTERNAL_ERROR` JS ugovora i ne logira sirovi exception tekst ili API ključ.
- Postojeći testovi više ne ovise o privatnoj, dugovječnoj bootstrap konekciji.

## REPRO PRIJE FIXA

```text
python -m pytest tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py::test_js_api_methods_work_from_fresh_worker_threads -q
FAILED
configure_provider -> INTERNAL_ERROR
log: configure_provider failed for provider OPENAI (err=ProgrammingError)
```

Test koristi stvarni `threading.Thread.start(); join()` i poziva bridge konstruiran na glavnom pytest threadu.

## POTVRĐENO NAKON FIXA

```text
worker-thread + migration lifecycle regression tests: 2 passed in 0.87s
bridge unit suite: 32 passed in 5.10s
full suite: 990 passed, 1 warning in 82.22s
ruff: All checks passed!
mypy: Success: no issues found in 171 source files
secret scan: NO CONFIRMED SECRET IN TRACKED FILES
git diff --check: clean
```

Foundation gate artefakt nakon punog suitea ima `status: PASS` i `no_secrets_detected: true`; generirana nepromijenjena verzija nije uključena u commit.

## GITNEXUS

- Repository: `AI-Campaing-Studio`
- Baseline/index: `main @ 08680bf`, up-to-date
- `CampaignBridgeApi` upstream: 1 direktni importer (`presentation_webview/__main__.py`), LOW
- downstream: 75 simbola, 15 direktnih zavisnosti, HIGH
- affected processes: GitNexus nije mapirao nijedan imenovani process
- Scope je zadržan na bridgeu i njegovom unit testu.
- Task-worktree `detect-changes` pokušaj: `UNKNOWN` zbog potvrđenog worktree-binding ograničenja (`Repository "." not found`; registriran je samo glavni checkout). Stvarni `git diff --name-only` sadrži samo dva allowed-path fajla.

## CONTRACT / SCOPE ODSTUPANJE

Contract traži regression provjeru tri metode, ali trenutni `main @ 08680bf` sadrži samo:

- `create_campaign_and_generate_plan`
- `configure_provider`

`generate_campaign_content` je još samo na zasebnoj ACS-GUI-008 grani/PR-u koji je review odbio. Kopiranje te metode u hotfix povuklo bi neodobreni GUI-008 scope. Zato permanentni test pokriva obje metode koje stvarno postoje na hotfix baselineu. Nakon mergea GUI-008 mora rebaseati ovaj commit, dekorirati treću metodu istim per-call lifecycleom i pokrenuti njen worker-thread test prije ponovnog reviewa.

## NE DIRATI

- Domain/Application/Ports, repository implementacije, UoW, migracije, screenove i JS.
- Ne uvoditi `check_same_thread=False`.
- Ne spajati GUI-008 funkcionalnost u ovaj hotfix PR.

## NIJE VERIFICIRANO / BLOKADA

- Push i PR/CI nisu izvršeni. Lokalni commit je `491a9a1` na grani `task/ACS-HOTFIX-002-bridge-thread-lifecycle`.
- Push na postojeći `origin` zahtijeva eksplicitno odobrenje Human Ownera; alat je odbio implicitno slanje privatnog koda.
- Treća GUI-008 metoda nije na baselineu i zato nije dio ovog commita ni testa.

## SLJEDEĆE

1. Human Owner eksplicitno odobrava push na provjereni `origin`.
2. Codex pushuje granu i otvara obavezni PR prema `main`.
3. Claude radi jedini, pojačani CRITICAL review i provjerava commit/diff/testove.
4. Nakon odobrenja/mergea GUI-008 se rebaseuje na hotfix i dodaje worker-thread dokaz za `generate_campaign_content`.
