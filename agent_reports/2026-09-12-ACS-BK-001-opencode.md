---
task: ACS-BK-001 — BK-G1 Brand Knowledge Domain Foundation
implementer: opencode
worktree: H:\ai-campaign-studio-worktrees\ACS-BK-001-domain-foundation
branch: task/ACS-BK-001-domain-foundation
base: main @ befcba5 (kontrakt); kod commit d81e792 (autor: Human Owner)
status: IMPLEMENTED + VERIFIED (čeka review — MEDIUM, Claude §29)
---

# Implementer evidence — ACS-BK-001

## Task

`domain/brand_knowledge/` — `KnowledgeCategory`/`KnowledgeStatus`/`EvidenceType`
enum-i, `KnowledgeEntry` + `BrandKnowledgeSnapshot` frozen entiteti, i
kontrolisani per-kategorija field registry (plan §5). Bez SQLite/migracije,
bez LLM-a, bez GUI-ja, bez Campaign Engine integracije.

Napomena o autorstvu: kod je commit-ovan kao `d81e792` (autor Human Owner);
ova sesija (opencode) je uradila **nezavisnu verifikaciju** implementacije
protiv kontrakta i plana §3–§5/§9/§32.

## Files changed (8, scope čist)

```text
src/ai_campaign_studio/domain/brand_knowledge/__init__.py   (NOV, re-export)
src/ai_campaign_studio/domain/brand_knowledge/enums.py      (NOV)
src/ai_campaign_studio/domain/brand_knowledge/entities.py   (NOV)
src/ai_campaign_studio/domain/brand_knowledge/policies.py   (NOV)
src/ai_campaign_studio/domain/common/ids.py                 (M, +2 ID tipa)
tests/unit/domain/brand_knowledge/test_entities.py          (NOV)
tests/unit/domain/brand_knowledge/test_enums.py             (NOV)
tests/unit/domain/brand_knowledge/test_policies.py          (NOV)
```

`forbidden_paths` — **NULA izmjena** (`domain/facts/`, `domain/brand/`,
`domain/ingestion/`, `application/`, `ports/`, `infrastructure/`,
`presentation_webview/`, `resources/migrations/`). `ids.py` izmjena je čisto
aditivna (2 nove `NewType` linije na kraju, postojeće netaknute).

## Verification (nezavisno reprodukovano)

Field registry je upoređen **liniju-po-liniju** sa planom §5 — poklapa se
tačno (svih 8 kategorija, tačni field-ovi, bez izmišljenih). `KnowledgeEntry`
polja i invarijante (§4), `BrandKnowledgeSnapshot` (§5/§9), `EvidenceType`
semantika (§3.3) — sve odgovara.

```text
$ python -m pytest tests/unit/domain/brand_knowledge/ -v
26 passed in 0.06s

$ python -m pytest -q   (DeepSeek unset, PYTHONPATH=<worktree>/src)
1579 passed, 1 skipped, 1 warning in 470.80s

$ python -m ruff check .
All checks passed!

$ python -m mypy src
Success: no issues found in 222 source files
```

## ⚠️ Environmental note — `.pth` editable-install (NIJE code issue)

Bez `PYTHONPATH`, pun suite pokazuje 1 FAIL:
`tests/unit/scripts/test_generate_phase0_gate_report.py::test_gate_report_against_current_repo_passes`
sa `package_import: false` (+ kaskada `platform_registry`/`provider_registry`/
`secret_store`/`database_connection`/`migrations`/`health_check = false`).

Uzrok: dijeljeni `.venv` editable `.pth`
(`.venv/Lib/site-packages/__editable__.ai_campaign_studio-0.1.0.pth`) pokazuje
na **obrisani** worktree `...\ACS-S2-013-ci-install-followup\src`, pa
gate-report subprocess ne može `import ai_campaign_studio` → bootstrap padne.
Sa `PYTHONPATH=<worktree>/src` bootstrap vraća `health: ok` i gate-report test
prolazi (`10 passed`). Ovo je tačno propisani postupak iz
`docs/...AGENT_WORKFLOW.md` §13 ("poznata zamka — `.pth` editable-install",
"koristiti eksplicitan PYTHONPATH override ... pouzdanije za worktree
verifikaciju"). **Nije izazvano izmjenama ovog taska** (package_import ne
zavisi od `domain/brand_knowledge/`). CI (svjež `pip install -e .` u repou)
nije pogođen.

## Graft (primarni alat, §0/§1)

```text
$ graft build
✓ wiring: 4198 nodes (2255 function, 1000 method, 499 class, 444 file),
  11814 edges, 444 cards [javascript, python]   (worktree auto-detektovan)

$ graft grep "KnowledgeEntry"      → 27 hits / 15 simbola / 6 fajlova (svi u
                                     brand_knowledge/ + njegovim testovima)
$ graft callers "KnowledgeEntry"   → calls ← _entry (test helper); nula
                                     produkcionih callera (očekivano: nov domen)
$ graft grep "BrandKnowledgeSnapshot" → svi hitovi u brand_knowledge/ + testovi
$ graft blast (working tree)
  changed: 8 files in 2 areas, 30 seed symbols
  impacted: 0 symbols in 0 areas
  no indexed dependents outside the changed files themselves
```

`graft blast` potvrđuje: 8 izmijenjenih fajlova, **0 impacted simbola van
njih** — novi domen ne dira ništa postojeće (importi `FactId`/
`BrandSnapshotId`/`InvariantViolation` su read-only, bez novih zavisnosti).
Graft side effects (`graft/`, `.ignore`/`.gitignore` dodir) su očišćeni
poslije upotrebe (§2).

## GitNexus (sekundarno, probacioni period)

`npx gitnexus detect-changes --repo AI-Campaing-Studio` iz worktree-a:
nepouzdan (index izgrađen na glavnom checkoutu; worktree sibling clone) —
prijavljuje simbole iz `ports/repositories.py` (`list_snapshots`/
`BrandRepositoryPort`, tuđi S2-018 rad), ne ovaj task. Poznato worktree
binding ograničenje; Graft (primarni) je dao tačan scope.

## Mutation test

Uklonjen empty-`source_fact_ids` check iz `KnowledgeEntry.__post_init__`:

```text
$ python -m pytest tests/unit/domain/brand_knowledge/ -q
1 failed, 25 passed
  FAILED test_knowledge_entry_rejects_empty_source_fact_ids
  ("DID NOT RAISE InvariantViolation")
```

Restauracija → `26 passed`. Dokazuje da test STVARNO brani provenance
invarijantu (svaki `KnowledgeEntry` vezan za `source_fact_ids` — temelj
BK-G4 anti-hallucination validatora).

## Not verified

- Stvarni `gh pr checks` (CI) — branch još nije push-ovan/PR kreiran.
- Graft side-effect cleanup je vraćen; `graft/` cache nije commit-ovan.
