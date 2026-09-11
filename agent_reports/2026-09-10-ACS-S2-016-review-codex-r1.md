---
task: ACS-S2-016 — S2-G7b Brand Intelligence Review UI
author: Codex (independent adversarial reviewer)
date: 2026-09-10
review_target: task/ACS-S2-016-brand-review-ui @ 4de994862e1c9df4dfadb31c6e373509ef1c4343
base: origin/main @ be3b393
verdict: REJECT
scope: PASS_WITH_JUSTIFIED_DEVIATIONS
acceptance: REJECT
architecture: REJECT
security: PASS
tests: REJECT_MISSING_ADVERSARIAL_REGRESSIONS
blocking_findings:
  - R1-BF-1
  - R1-BF-2
  - R1-BF-3
---

# ACS-S2-016 — Codex adversarial re-review, round 1

## Verdict

**REJECT — 3 blocking findings.** The committed 11 G7b tests and full suite pass,
and all four requested mutations are test-sensitive. Fresh runtime probes nevertheless
demonstrate two data-integrity defects that the suite does not cover. The UI also
silently swallows initial-load errors in direct conflict with the task contract.

The two previously documented allowed-path deviations
(`presentation/ui_models.py` and `tests/unit/ports/test_repositories.py`) are justified
and are not findings. Forbidden paths remain untouched.

## Blocking findings

### R1-BF-1 — HIGH — concurrent Assemble persists duplicate snapshot versions

`CampaignBridgeApi.assemble_brand_snapshot` reads the latest snapshot and computes
`latest.version + 1` at `bridge/__init__.py:2109-2110`, then saves only at line 2130.
There is no lock or transaction covering the read/compute/write sequence. The schema
also has no `UNIQUE (brand_id, version)` constraint (`0001_brand_facts.sql:7-20`).

This is reachable in the declared runtime. `_resource_scope` explicitly documents
that pywebview dispatches calls on worker threads and uses `ContextVar` to isolate
concurrent calls (`bridge/__init__.py:2153-2159`). The same class already uses
per-key locks for another bridge flow because two worker threads can race
(`bridge/__init__.py:439-448`). Therefore the coordinator's “single-threaded bridge”
assumption is contradicted by the implementation itself.

Deterministic real-SQLite probe:

1. Seed one brand and approve one fact.
2. Wrap `SqliteBrandRepository.get_latest_snapshot` with a two-party
   `threading.Barrier` immediately after the read.
3. Invoke the same bridge instance's `assemble_brand_snapshot({})` from two
   `ThreadPoolExecutor` workers.

Observed:

```text
results: [(ok=True, version=1), (ok=True, version=1)]
persisted_versions: [1, 1]
row_count: 2
```

Required fix: serialize the entire fact-read/latest-read/version/save critical section
with an instance-level per-brand lock (matching the existing bridge lock pattern), or
provide an equally strong atomic repository operation. Because migrations are forbidden
for G7b, the minimal in-scope fix is the per-brand bridge lock. Add a deterministic
two-thread regression test using a barrier; it must return/persist versions `[1, 2]`.

### R1-BF-2 — HIGH — snapshot assembly includes non-APPROVED facts

`SqliteFactRepository.list_approved_facts_by_brand` claims to return only APPROVED
facts, but its SQL at `sqlite_fact_repository.py:97-108` filters only by brand ID.
It never applies `approved_facts.status = 'APPROVED'`.

Real-SQLite probe:

1. Seed and approve a candidate through G7a.
2. Set the resulting `approved_facts.status` to `SOFT_DELETED` through SQL.
3. Query `list_approved_facts_by_brand`, then assemble a snapshot.

Observed:

```text
repository_statuses: ['SOFT_DELETED']
assemble: ok=True, approved_fact_count=1
```

The same defect admits `SUPERSEDED` rows. This violates the explicit “approved facts
only” contract and can permanently place unusable fact IDs in a new brand snapshot.

Required fix: add an APPROVED-status predicate to this repository query. Add real-SQLite
coverage proving APPROVED is included while SOFT_DELETED and SUPERSEDED are excluded,
and proving assembly uses only the remaining APPROVED IDs.

### R1-BF-3 — MEDIUM — initial review-load failures are invisible

The contract requires bridge/API failures to be visible through toast or inline error.
`loadFactReview` silently returns both when the bridge throws
(`static/app.js:1254-1258`) and when it returns `ok !== true` (line 1259). The existing
Node/VM test executes only the successful load and action path, so it cannot detect
this acceptance failure.

Required fix: display a safe generic toast for thrown errors and the returned
`error_message` (with a safe fallback) for error DTOs. Extend the executable Node/VM
test with both negative paths and assert the user-visible notification.

## Four requested mutation checks

All four mutations were applied at runtime via monkeypatch/test doubles, without
editing the worktree. Each original acceptance assertion failed, so the tests/probes
are materially sensitive rather than cosmetic:

| Mutation | Mutated result | Original assertion |
|---|---|---|
| Reverse the `if not facts` guard | empty snapshot returned with `ok=True`, count `0` | FAIL |
| Force every assembled version to `1` | versions `[1, 1]` | FAIL (`1 > 1`) |
| Bypass G7a `assert_candidate_proposed` | second approval returned `ok=True` | FAIL |
| Remove SourceSnapshot lookup in review mapping | URLs `['', '']` | FAIL |

These checks validate the requested no-approved-facts, sequential-version,
G7a-idempotency, and G-WI-EVIDENCE test intent. They do not cover the separate
concurrent-version defect in R1-BF-1, which needs the new barrier regression.

## Verification evidence

Fresh commands at the reviewed head:

```text
python -m pytest -q <four G7b test files>
11 passed in 5.28s

python -m pytest -q <no-approved + flow + G7a atomicity tests>
3 passed in 1.35s

python -m ruff check .
All checks passed!

python -m mypy src
Success: no issues found in 211 source files

python -m pytest -q
1488 passed, 1 skipped, 1 warning in 273.47s

git diff --check origin/main...HEAD
PASS
```

The first sandboxed full-suite attempt produced 486 setup errors because pytest could
not write `C:\\Users\\38765\\AppData\\Local\\Temp\\pytest-of-radovan`; it was rerun
with write access to the exact review environment and passed as shown above. This was
an environment failure, not a product failure.

## GitNexus / impact

The main repository index was stale and was refreshed to `be3b393`. Fresh upstream
impact reports HIGH for both `BrandRepositoryPort` and `FactRepositoryPort`
(25 impacted, 20 direct each), and LOW for `CampaignBridgeApi` (1 direct). This
confirms that repository-port changes require the HIGH-risk review treatment used
here. The secondary worktree cannot be bound independently by the installed
GitNexus CLI, so change-scope verification was compensated with the actual
`origin/main...HEAD` diff, forbidden-path checks, and direct call-site search.

## Scope and security

- Reviewed head is clean and matches its remote tracking branch.
- Diff is 14 files, +1723/-2 when both agent reports are counted.
- No changes under contract-forbidden domain, G3-G7a application, ingestion adapter,
  persistence schema, or migration paths.
- The two coordinator-documented scope deviations are low-risk DTO/test support and
  accepted.
- Executable Node/VM coverage confirms candidate content and URL HTML escaping on the
  successful rendering path; no secret or new external-I/O surface was found.

## Fix-round boundaries

Do not modify domain entities, G6/G7a use cases, web-ingestion adapters, or migrations.
The fix round should be limited to the G7b bridge lock, approved-status repository
filter, user-visible load error handling, and their targeted regression tests. After
the fix, rerun the four mutations plus the deterministic concurrency and status-filter
regressions, then repeat full ruff/mypy/pytest and independent review. No merge before
Codex PASS and explicit Human Owner approval (HIGH task).
