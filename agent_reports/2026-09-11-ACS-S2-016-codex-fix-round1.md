---
task: ACS-S2-016 — S2-G7b Brand Intelligence Review UI
author: Codex (fix implementer)
date: 2026-09-11
base_head: 247d2f1292cac12a1aaa30d9565a8bf3563381fb
status: IMPLEMENTED — awaiting independent round-2 review
findings_fixed: [R1-BF-1, R1-BF-2, R1-BF-3]
---

# ACS-S2-016 — Codex fix-round 1 evidence

## CILJ

Zatvoriti sva tri blocking nalaza iz Codex R1 reviewa bez izmjene domaina,
G6/G7a use-caseova, port potpisa, persistence sheme ili migracija.

## Reprodukcija prije fixa

Novi runtime regresioni testovi su prvo pokrenuti protiv koda na `247d2f1`:

```text
4 failed, 2 passed in 6.20s

race: versions [1, 1], expected [1, 2]
status: SOFT_DELETED fact returned, expected empty tuple
throw UX: toast '', expected safe fallback
failed DTO UX: toast '', expected bridge error_message
```

## Implementirano

### R1-BF-1 — snapshot version race

- `CampaignBridgeApi` sada ima instance-level per-brand lock registry.
- Lock obuhvata cijeli brand/facts/latest/version/save critical section.
- Različiti brandovi koriste različite lockove.
- Real SQLite test koristi dva `ThreadPoolExecutor` workera i
  `threading.Barrier`; potvrđuje response i persisted verzije `[1, 2]`.

### R1-BF-2 — neupotrebljivi fact statusi

- `list_approved_facts_by_brand` sada binduje
  `FactStatus.APPROVED.value` u SQL predikatu.
- Real SQLite test potvrđuje da je APPROVED uključen, a SOFT_DELETED i
  SUPERSEDED isključeni.
- Isti test potvrđuje da assembly sa samo neupotrebljivim facts vraća
  `VALIDATION_ERROR` i ne pravi prazan snapshot.

### R1-BF-3 — nevidljive load greške

- Bridge exception prikazuje sigurnu BHS fallback poruku bez exception detalja.
- `ok=False` prikazuje neprazan `error_message`, uz isti sigurni fallback.
- Dva izvršna Node/VM testa pokreću stvarni `static/app.js` i provjeravaju toast.

## Verifikacija poslije fixa

```text
Focused G7b + three reproducers:
15 passed in 11.91s

python -m ruff check .
All checks passed!

python -m mypy src
Success: no issues found in 211 source files

python -m pytest -q --tb=short
1492 passed, 1 skipped, 1 warning in 290.80s

git diff --check
PASS
```

Prvi puni-suite pokušaj bio je pokrenut paralelno sa GitNexus reindexom i
prekinut je dok je indeks mijenjao stanje. Suite je zato ponovljen nakon
završetka reindexa i tada je prošao kako je navedeno iznad.

## GitNexus

Pre-change impact je izvršen prije produkcijskih izmjena. Svjež main indeks
je prijavio LOW za `CampaignBridgeApi` (1 direktni importer) i LOW za
`SqliteFactRepository` (1 direktni importer; bridge tranzitivno). Ranija
port-level analiza je HIGH (25 impacted / 20 direct), pa port potpisi nisu
mijenjani.

Worktree je uspješno reindeksiran na `247d2f1` (16,990 nodes, 25,434 edges,
384 clusters, 211 flows). `detect-changes` je zatim pokrenut sa punom
worktree putanjom radi razdvajanja od istoimenog main indeksa:

```text
Changes: 4 files, 14 symbols
Affected processes: 34
Risk level: critical
```

Centralni `CampaignBridgeApi` i `loadFactReview` objašnjavaju širok flow
domet; zato su uz tri runtime reproduktora ponovljeni puni pytest, ruff i
mypy gate. Scope je dodatno provjeren stvarnim `git status`, `git diff`,
`git diff --check` i `rg` caller/variant pretragom.

## Scope

Produkcijske izmjene su ograničene na:

- `presentation_webview/bridge/__init__.py`
- `sqlite_fact_repository.py`
- `presentation_webview/static/app.js`

Dodana su dva integration reproduktora i dva Node/VM negativna scenarija.
Forbidden paths nisu dirani.

## Handoff

```text
CILJ: ukloniti race, status-filter i silent-error defekte iz R1.
URAĐENO: sva tri defekta reproducirana prije i zatvorena minimalnim fixevima;
         ciljani i puni gate prolaze.
NE DIRATI: domain, G6/G7a, port potpise, shemu, migracije i ostale bridge flowove.
SLJEDEĆE: fresh independent Codex/Claude-equivalent round-2 review; HIGH task
          i dalje zahtijeva Human Owner odobrenje prije mergea.
```
