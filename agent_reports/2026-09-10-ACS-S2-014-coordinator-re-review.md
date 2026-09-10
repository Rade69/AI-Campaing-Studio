---
task: ACS-S2-014 — S2-G6 Pipeline Orchestration
author: minimax (privremeni koordinator, Claude na pauzi zbog limita tokena)
date: 2026-09-10
purpose: Coordinator re-review summary sent to Codex for fresh adversarial re-review
review_target: task/ACS-S2-014-ingestion-pipeline @ cc125d4
previous_verdict: REJECT (5 blocking findings, see agent_reports/2026-09-10-ACS-S2-014-review-codex.md)
status: coordinator-independent-verification PASS, awaiting Codex adversarial re-review
---

# ACS-S2-014 — Coordinator re-review summary for Codex

## Verdict so far

Pi's fix-round 2 commit `cc125d4` (plus rebased chain `e213e55`,
`fbe5ef4`, `c88761d`) addresses all 5 blocking findings from the
previous Codex review. Coordinator independent verification PASS
on local rebase + targeted test suite + 2/2 mutation tests on
BF-1 components. This document is a summary, not the final verdict —
**Codex adversarial re-review on the new HEAD is still required**
before any merge (HIGH task, full cycle).

## Scope (post-rebase on `origin/main` @ `09650ce`)

```text
13 files changed, 2070 insertions(+), 9 deletions(-)
```

Breakdown of the diff `origin/main..HEAD` after `git rebase
origin/main` (clean rebase, 4 commits, no conflicts):

- `src/ai_campaign_studio/application/ingestion/ingest_brand_sources.py`
  (+644 lines net) — pipeline use-case (BF-1, BF-2, BF-3, BF-4)
- `src/ai_campaign_studio/application/ingestion/dependencies.py`
  (+59) — new dependency wiring for `UrlClassifierPort`
- `src/ai_campaign_studio/application/ingestion/__init__.py`
  (+18) — exports `IngestBrandSources`, `IngestBrandSourcesDependencies`
- `src/ai_campaign_studio/infrastructure/web_ingestion/url_classifier.py`
  (+171, new) — deterministic URL classifier
- `src/ai_campaign_studio/infrastructure/web_ingestion/__init__.py`
  (+4) — exports
- `tests/unit/application/ingestion/test_ingest_brand_sources.py`
  (+56) — unit tests for new dependency injection
- `tests/integration/application/ingestion/test_ingest_pipeline.py`
  (+637) — BF-1, BF-2, BF-3 reproducer tests
- `tests/integration/application/ingestion/test_real_adapter_pipeline.py`
  (+136, new) — BF-5 fixture test (real adapters on local http.server)
- `tests/unit/infrastructure/web_ingestion/test_url_classifier.py`
  (+58) — URL classifier unit tests
- `agent_reports/2026-09-10-ACS-S2-014-pi.md` (+237) — original evidence
- `agent_reports/2026-09-10-ACS-S2-014-fix-round2-evidence.md` (+59) — fix-round 2 evidence
- `tests/integration/application/ingestion/__init__.py` (empty) and
  `tests/unit/application/ingestion/__init__.py` (empty) — test dir init files

**Note on `url_classifier.py` (+171)**: this is a NEW file, not
present on main prior to S2-G6. URL classifier is G3-adjacent
infrastructure; Pi added it as a dependency for the pipeline
orchestrator to use. Not in original G6 contract scope but a
necessary addition for `assemble_url_classification` per G6's
"CLASSIFY folded into DISCOVER" model. Confirm in re-review that
this does not conflict with G3's existing classifier (if any) and
that the new file is fully exercised by `test_url_classifier.py`.

## Local verification (coordinator independent)

### Static checks (re-run on rebase'd HEAD)

```text
$ python -m ruff check .
All checks passed!  EXIT=0

$ python -m mypy src
Success: no issues found in 211 source files  EXIT=0
```

### Targeted test suite (G6 tests only)

```text
$ python -m pytest --tb=line -q \
    tests/unit/application/ingestion/test_ingest_brand_sources.py \
    tests/integration/application/ingestion/test_ingest_pipeline.py \
    tests/integration/application/ingestion/test_real_adapter_pipeline.py
4 passed in 10.18s   EXIT=0   (unit + BF-5 real-adapter fixture)

$ python -m pytest --tb=line -q \
    tests/integration/application/ingestion/test_ingest_pipeline.py
12 passed in 4.68s   EXIT=0   (full pipeline + all BF-1..BF-4 reproducer tests)

Total: 16 passed, matches Pi's evidence "16 passed in 16.47s".
```

### Mutation test (BF-1 components, two of three)

I independently verified two of the three BF-1 components Pi
documented in `fix-round2-evidence.md`. Both mutations reverted
the test to the previously-failing state with the SAME symptom
Codex reported. Restore was clean (`git diff` empty).

| Mutation | Location | Test | Symptom on mutation | After restore |
|----------|----------|------|---------------------|---------------|
| `if content is None and snapshot.raw_content_ref:` → `if content is None and False:` | `ingest_brand_sources.py:443` (BF-1 resume fallback) | `test_cancel_after_fetch_recovers_body_on_resume` | `AssertionError: assert 0 == 2` + `WARNING extract_missing_raw_body` — IDENTICAL to Codex original repro | 1 passed, file unchanged |
| `fetched += 1` → `fetched += 0` in `_compute_run_stats` | `ingest_brand_sources.py:582` (BF-1 stats from durable state) | `test_hard_kill_after_first_fetch_resumes_both_targets` | `AssertionError: assert 0 == 2` on `stats.fetched_pages` | 12 passed, file unchanged |

Third component (`raw_content_ref=base64(...)` at
`ingest_brand_sources.py:388`, set in `_fetch`) was not mutation-
tested by me; Pi's evidence documents that it is also caught by
the same first reproducer test. Recommend Codex verify this one
on the fresh re-review.

## Fix summary (per Codex BF)

| BF | Severity | Fix location | New reproducer test |
|----|----------|--------------|---------------------|
| BF-1 | HIGH | `source_snapshots.raw_content_ref` (base64-encoded BLOB), populated at `_fetch()`:388, read at `_extract_snapshot()`:443-447; `_compute_run_stats()`:575 derives stats from durable state | `test_cancel_after_fetch_recovers_body_on_resume`, `test_hard_kill_after_first_fetch_resumes_both_targets` |
| BF-2 | MEDIUM | `_raise_if_cancelled(token)` at the start of every inner chunk/candidate loop iteration in `_extract` and `_build_facts` | `test_chunk_loop_checks_cancellation_per_iteration`, `test_candidate_loop_checks_cancellation_per_iteration` |
| BF-3 | MEDIUM | `_DOCUMENT_MIME_TYPES` mapping + `_document_mime_extension(snapshot.content_type)`; suffix checked first, then MIME | (needs verification — check `_extract_snapshot` for extensionless URL + document Content-Type path) |
| BF-4 | MEDIUM | `_extract_visual_identity` (private helper) called from `_extract_snapshot` for `PageType.HOME` and `PageType.ABOUT`; result logged only, no persistence, no port changes | (needs verification — check `_extract_snapshot` calls visual extractor only for HOME/ABOUT) |
| BF-5 | MEDIUM | New `test_real_adapter_pipeline.py` — local `http.server` serving `spikes/extraction-benchmark/corpus/klix.ba-article.html`, real `HttpFetcher` + `DomainDiscovery` + `MainContentExtractor` + `VisualIdentityAdapter` | `test_real_adapter_pipeline.py` (full file) |

## Specific re-review focus points for Codex

1. **BF-1 third mutation**: `raw_content_ref=base64.b64encode(content).decode("ascii")`
   at `ingest_brand_sources.py:388` — confirm that removing this
   line breaks the same reproducer test (I did not run this
   mutation).
2. **BF-3 reproducer**: confirm there is an integration test
   exercising an extensionless URL (e.g. `/download?id=123`) with
   `Content-Type: application/pdf`. If absent, BF-3 is not fully
   closed at the integration level.
3. **BF-4 reproducer**: confirm a spy-style test asserts that
   `_visual_identity.extract` is called exactly for `HOME` and
   `ABOUT` page types and not for `PRODUCT`/`BLOG`/`ARTICLE` and
   not for non-HTML Content-Type. If absent, BF-4 is not fully
   closed.
4. **`url_classifier.py` new file**: confirm no duplication with
   any pre-existing classifier in G3's `web_ingestion/` module
   family and that the new file's API matches the
   `UrlClassifierPort` Protocol already declared in
   `ports/web_ingestion.py`.
5. **`IngestBrandSources` stats source-of-truth**: confirm
   `stats` returned to the caller come from
   `_compute_run_stats(resolved_run_id)` (durable state), not
   from the per-call counters (`fetched`/`failed` locals in
   `_fetch`).
6. **Resume semantics for hard-kill mid-`_fetch`**: confirm the
   refetch path does not duplicate the original `SourceSnapshot`
   (id is stable: `_stable_id(run_id, target.normalized_url)`)
   and does not double-count `stats`.

## What was NOT changed (preserved from G3/G2 review)

- `recover_expired_leases` / `claim_next_crawl_target` (G2
  atomic claim/recovery) — not touched
- `HttpFetcher` / `UrlSafetyPolicy` SSRF code — not touched
  (G3 module, only injected into pipeline)
- 1:1 chunk→candidate mapping (BUILD_FACTS) — not touched
- S2-G7a (`approve_fact_candidates.py`,
  `reject_fact_candidates.py`) — not touched, no dependency
  added from G6 to G7a
- `_checkpoint` ordering logic (F1 fix from Claude) — not
  touched; DISCOVER checkpoint still AFTER `_discover()`
- Repository/port method signatures — unchanged; no new
  persistence/port method added

## Decision request

If your re-review finds no new blocking findings (or only minor
issues that the coordinator can address in a follow-up commit),
recommend **PASS** and the coordinator will:

1. `gh pr merge --squash` (no `--delete-branch`, worktree holds
   the branch) — but ONLY after Human Owner explicit approval
   (HIGH task, not §29).
2. Post-merge cycle: `git pull`, `npx gitnexus analyze`,
   `CURRENT_STATE.md` prepend, CI verification.
3. Begin S2-G7b Task Contract (HIGH, bridge + GUI ekran, last
   blocking task before "unesi URL → vidi rezultat" demo).

If you find new blocking findings, please write the fix brief
directly to `agent_reports/2026-09-10-ACS-S2-014-review-codex-r2.md`
(in this worktree) per the project's "fix-brief in agent_reports,
not scratchpad" convention.
